"""
Strands Agents with AgentCore Memory (Long-Term Memory) - MemoryManager

This script demonstrates how to build an intelligent customer support agent using 
Strands agents integrated with AgentCore Memory via hooks using MemoryManager and 
MemorySessionManager. The agent focuses on long-term memory for customer interaction 
history, remembering purchase details, and providing personalized support based on 
previous conversations and user preferences.

Tutorial Details:
- Tutorial type: Long Term Conversational
- Agent type: Customer Support
- Agentic Framework: Strands Agents
- LLM model: Amazon Nova Lite v1.0
- Components: AgentCore Semantic and User Preferences Memory Extraction,
              Hooks for storing and retrieving Memory

Scenario:
The agent remembers customer context, including order history, preferences, and 
previous issues, enabling more personalized and effective support. Conversations 
are automatically stored using memory hooks. Multiple memory strategies (semantic 
and user preference) capture a wide range of relevant information.

Prerequisites:
- Python 3.10+
- AWS credentials with AgentCore Memory permissions
- Amazon Bedrock AgentCore SDK with MemoryManager support
- Access to Amazon Bedrock models
- IAM permissions to create roles

Usage:
    python customer_support_memory_manager.py
"""

import logging
import json
import os
from typing import Dict, List, Optional
from datetime import datetime

# Boto3 imports
import boto3
from botocore.exceptions import ClientError

# Strands Agent imports
from strands import Agent, tool
from strands.hooks import (
    AfterInvocationEvent,
    HookProvider,
    HookRegistry,
    MessageAddedEvent
)

# Web search imports
from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException

# Memory management imports
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import (
    CustomSemanticStrategy,
    CustomUserPreferenceStrategy,
    ExtractionConfig,
    ConsolidationConfig
)
from bedrock_agentcore.memory.constants import (
    ConversationalMessage,
    MessageRole,
    RetrievalConfig
)
from bedrock_agentcore.memory.session import MemorySession, MemorySessionManager
from bedrock_agentcore.memory.models import MemoryRecord

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("customer-support")

# Configuration
REGION = os.getenv('AWS_REGION', 'us-east-1')
CUSTOMER_ID = "customer_001"
SESSION_ID = f"support_{datetime.now().strftime('%Y%m%d%H%M%S')}"
MEMORY_NAME = "CustomerSupportLongTermMemory"
MODEL_ID = "amazon.nova-lite-v1:0"

# Define message role constants
USER = MessageRole.USER
ASSISTANT = MessageRole.ASSISTANT


# ============================================================================
# IAM Role Creation
# ============================================================================

def create_memory_execution_role(region: str = REGION) -> str:
    """Create IAM role for AgentCore Memory custom strategies.
    
    Custom memory strategies require an execution role that allows AgentCore 
    Memory to invoke Bedrock models for extraction and consolidation.
    
    Args:
        region: AWS region
    
    Returns:
        str: ARN of the created or existing IAM role
    
    Raises:
        ClientError: If IAM operations fail
    """
    iam_client = boto3.client('iam', region_name=region)
    sts_client = boto3.client('sts', region_name=region)
    
    # Get current AWS account ID
    account_id = sts_client.get_caller_identity()['Account']
    role_name = "AgentCoreMemoryExecutionRole"
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    
    # Trust policy for AgentCore Memory service
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {
                    "Service": ["bedrock-agentcore.amazonaws.com"]
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": account_id
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"
                    }
                }
            }
        ]
    }
    
    # Permissions policy for Bedrock model invocation
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                "Resource": [
                    "arn:aws:bedrock:*::foundation-model/*",
                    "arn:aws:bedrock:*:*:inference-profile/*"
                ],
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceAccount": account_id
                    }
                }
            }
        ]
    }
    
    try:
        # Check if role already exists
        try:
            existing_role = iam_client.get_role(RoleName=role_name)
            logger.info(f"✅ IAM role already exists: {role_arn}")
            return role_arn
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchEntity':
                raise
        
        # Create the role
        logger.info(f"Creating IAM role: {role_name}")
        iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Execution role for AgentCore Memory custom strategies",
            Tags=[{'Key': 'Purpose', 'Value': 'AgentCoreMemory'}]
        )
        
        # Attach the permissions policy
        policy_name = "AgentCoreMemoryBedrockAccess"
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(permissions_policy)
        )
        
        logger.info(f"✅ Successfully created IAM role: {role_arn}")
        logger.info("   - Trust policy: AgentCore Memory service can assume this role")
        logger.info("   - Permissions: bedrock:InvokeModel and InvokeModelWithResponseStream")
        
        return role_arn
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDenied':
            logger.error("❌ Access denied creating IAM role. Required permissions:")
            logger.error("   - iam:CreateRole, iam:PutRolePolicy, iam:GetRole")
        else:
            logger.error(f"❌ Failed to create IAM role: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error creating IAM role: {e}")
        raise


# ============================================================================
# Agent Tools
# ============================================================================

@tool
def web_search(query: str, max_results: int = 3) -> str:
    """Search the web for product information, troubleshooting guides, or support articles.
    
    Args:
        query: Search query for product info or troubleshooting
        max_results: Maximum number of results to return
    
    Returns:
        str: Search results with titles and snippets
    """
    try:
        results = DDGS().text(query, region="us-en", max_results=max_results)
        if not results:
            return "No search results found."
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            body = result.get('body', 'No description')
            formatted_results.append(f"{i}. {title}\n   {body}")
        
        return "\n".join(formatted_results)
    except RatelimitException:
        return "Rate limit reached: Please try again after a short delay."
    except DDGSException as e:
        return f"Search Error: {e}"
    except Exception as e:
        return f"Search error: {str(e)}"


@tool
def check_order_status(order_number: str) -> str:
    """Check the status of a customer order.
    
    Args:
        order_number: The order number to check
    
    Returns:
        str: Order status information
    """
    # Simulate order lookup
    mock_orders = {
        "123456": "iPhone 15 Pro - Delivered on June 5, 2025",
        "654321": "Sennheiser Headphones - Delivered on June 25, 2025, 1-year warranty active",
        "789012": "Samsung Galaxy S23 - In transit, expected delivery on July 1, 2025",
    }
    
    status = mock_orders.get(
        order_number,
        f"Order {order_number} not found. Please verify the order number."
    )
    return status


# ============================================================================
# Memory Setup Functions
# ============================================================================

def setup_memory(
    region: str = REGION,
    memory_name: str = MEMORY_NAME,
    execution_role_arn: str = None
):
    """Create or retrieve memory resource with long-term strategies.
    
    Creates memory with CustomUserPreferenceStrategy and CustomSemanticStrategy
    for capturing customer preferences and support interaction facts.
    
    Args:
        region: AWS region for memory resource
        memory_name: Name for the memory resource
        execution_role_arn: IAM role ARN for custom strategies (required)
    
    Returns:
        tuple: (memory object, memory_id)
    
    Raises:
        Exception: If memory creation fails
    """
    logger.info(f"Setting up long-term memory in region: {region}")
    
    # Initialize Memory Manager
    memory_manager = MemoryManager(region_name=region)
    logger.info(f"✅ MemoryManager initialized for region: {region}")
    
    # Define memory strategies
    strategies = [
        CustomUserPreferenceStrategy(
            name="CustomerPreferences",
            description="Captures customer preferences and behavior",
            extraction_config=ExtractionConfig(
                append_to_prompt="Extract customer preferences and behavior patterns",
                model_id="anthropic.claude-3-sonnet-20240229-v1:0"
            ),
            consolidation_config=ConsolidationConfig(
                append_to_prompt="Consolidate customer preferences",
                model_id="anthropic.claude-3-sonnet-20240229-v1:0"
            ),
            namespaces=["support/customer/{actorId}/preferences"]
        ),
        CustomSemanticStrategy(
            name="CustomerSupportSemantic",
            description="Stores facts from conversations",
            extraction_config=ExtractionConfig(
                append_to_prompt="Extract factual information from customer support conversations",
                model_id="anthropic.claude-3-sonnet-20240229-v1:0"
            ),
            consolidation_config=ConsolidationConfig(
                append_to_prompt="Consolidate semantic insights from support interactions",
                model_id="anthropic.claude-3-sonnet-20240229-v1:0"
            ),
            namespaces=["support/customer/{actorId}/semantic"]
        )
    ]
    
    # Log strategy configuration
    logger.info(f"✅ Configured {len(strategies)} memory strategies:")
    for i, strategy in enumerate(strategies, 1):
        logger.info(f"  {i}. {strategy.name} ({type(strategy).__name__})")
        logger.info(f"     Description: {strategy.description}")
        logger.info(f"     Namespaces: {strategy.namespaces}")
    
    # Create memory resource
    logger.info(f"Creating memory '{memory_name}' with {len(strategies)} strategies...")
    
    try:
        memory = memory_manager.get_or_create_memory(
            name=memory_name,
            strategies=strategies,
            description="Memory for customer support agent",
            event_expiry_days=90,  # Memories expire after 90 days
            memory_execution_role_arn=execution_role_arn,
        )
        memory_id = memory.id
        logger.info(f"✅ Successfully created/retrieved memory:")
        logger.info(f"   Memory ID: {memory_id}")
        logger.info(f"   Memory Name: {memory.name}")
        logger.info(f"   Memory Status: {memory.status}")
        
        return memory, memory_id
        
    except Exception as e:
        logger.error(f"❌ Memory creation failed: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
        # Cleanup on error
        if 'memory_id' in locals():
            try:
                logger.info(f"Attempting cleanup of partially created memory: {memory_id}")
                memory_manager.delete_memory(memory_id)
                logger.info(f"✅ Successfully cleaned up memory: {memory_id}")
            except Exception as cleanup_error:
                logger.error(f"❌ Failed to clean up memory: {cleanup_error}")
        
        raise


def setup_session(
    memory_id: str,
    actor_id: str,
    session_id: str,
    region: str = REGION
):
    """Initialize session manager and create memory session.
    
    Args:
        memory_id: ID of the memory resource
        actor_id: Unique customer identifier
        session_id: Unique session identifier
        region: AWS region
    
    Returns:
        tuple: (session_manager, customer_session)
    """
    # Initialize the session memory manager
    session_manager = MemorySessionManager(memory_id=memory_id, region_name=region)
    
    # Create a memory session for the specific customer
    customer_session = session_manager.create_memory_session(
        actor_id=actor_id,
        session_id=session_id
    )
    
    logger.info(f"✅ Session manager initialized for memory: {memory_id}")
    logger.info(f"✅ Customer session created for actor: {actor_id}")
    logger.info(f"   Session ID: {session_id}")
    
    return session_manager, customer_session


def seed_customer_history(customer_session: MemorySession):
    """Seed the customer session with previous interaction history.
    
    Args:
        customer_session: MemorySession to seed with data
    """
    previous_interactions = [
        ConversationalMessage(
            "I bought a new iPhone 15 Pro on June 1st, 2025. Order number is 123456.",
            USER
        ),
        ConversationalMessage(
            "Thank you for your purchase! I can see your iPhone 15 Pro order #123456 was delivered successfully. How can I help you today?",
            ASSISTANT
        ),
        ConversationalMessage(
            "I also ordered Sennheiser headphones on June 20th. Order number 654321. They came with 1-year warranty.",
            USER
        ),
        ConversationalMessage(
            "Perfect! I have your Sennheiser headphones order #654321 on file with the 1-year warranty. Both your iPhone and headphones should work great together.",
            ASSISTANT
        ),
        ConversationalMessage(
            "I'm looking for a good laptop. I prefer ThinkPad models.",
            USER
        ),
        ConversationalMessage(
            "Great choice! ThinkPads are excellent for their durability and performance. Let me help you find the right model for your needs.",
            ASSISTANT
        )
    ]
    
    try:
        event_response = customer_session.add_turns(previous_interactions)
        logger.info(f"✅ Seeded customer history using MemorySession")
        logger.info(f"   Event ID: {event_response['eventId']}")
    except Exception as e:
        logger.error(f"⚠️ Error seeding history: {e}")


# ============================================================================
# Memory Hook Provider
# ============================================================================

class CustomerSupportMemoryHooks(HookProvider):
    """Memory hooks for customer support agent with MemorySession."""
    
    def __init__(self, customer_session: MemorySession):
        """Initialize with a pre-configured MemorySession.
        
        Args:
            customer_session: MemorySession instance for this customer
        """
        self.customer_session = customer_session
        
        # Define retrieval configuration for different memory types
        self.retrieval_config = {
            "support/customer/{actorId}/preferences": RetrievalConfig(
                top_k=3,
                relevance_score=0.3
            ),
            "support/customer/{actorId}/semantic": RetrievalConfig(
                top_k=5,
                relevance_score=0.2
            )
        }
    
    def retrieve_customer_context(self, event: MessageAddedEvent):
        """Retrieve customer context before processing support query.
        
        Searches long-term memory for relevant customer preferences and 
        previous support interactions, then injects them into the agent's 
        system prompt for context-aware responses.
        
        Args:
            event: MessageAddedEvent containing the new user message
        """
        messages = event.agent.messages
        if messages[-1]["role"] == "user" and "toolResult" not in messages[-1]["content"][0]:
            user_query = messages[-1]["content"][0]["text"]
            
            try:
                relevant_memories = []
                
                # Search across different memory namespaces
                for namespace_template, config in self.retrieval_config.items():
                    # Resolve namespace template with actual actor ID
                    resolved_namespace = namespace_template.format(
                        actorId=self.customer_session._actor_id
                    )
                    
                    # Use MemorySession API
                    memories = self.customer_session.search_long_term_memories(
                        query=user_query,
                        namespace_prefix=resolved_namespace,
                        top_k=config.top_k
                    )
                    
                    # Filter by relevance score
                    filtered_memories = [
                        memory for memory in memories
                        if memory.get("score", 0) >= config.relevance_score
                    ]
                    
                    relevant_memories.extend(filtered_memories)
                    logger.info(
                        f"Found {len(filtered_memories)} relevant memories in {resolved_namespace}"
                    )
                
                # Inject context into agent's system prompt if memories found
                if relevant_memories:
                    context_text = self._format_context(relevant_memories)
                    original_prompt = event.agent.system_prompt
                    enhanced_prompt = f"{original_prompt}\n\nCustomer Context:\n{context_text}"
                    event.agent.system_prompt = enhanced_prompt
                    logger.info(
                        f"✅ Injected {len(relevant_memories)} memories into agent context"
                    )
                    
            except Exception as e:
                logger.error(f"Failed to retrieve customer context: {e}")
    
    def _format_context(self, memories: List[MemoryRecord]) -> str:
        """Format retrieved memories for agent context.
        
        Args:
            memories: List of MemoryRecord objects
        
        Returns:
            str: Formatted context string
        """
        context_lines = []
        for i, memory in enumerate(memories[:5], 1):  # Limit to top 5
            content = memory.get('content', {}).get('text', 'No content available')
            score = memory.get('score', 0)
            context_lines.append(f"{i}. (Score: {score:.2f}) {content[:200]}...")
        
        return "\n".join(context_lines)
    
    def save_support_interaction(self, event: AfterInvocationEvent):
        """Save support interaction after agent responds.
        
        Automatically stores the customer query and agent response as a 
        conversational turn in the memory system.
        
        Args:
            event: AfterInvocationEvent containing the completed interaction
        """
        try:
            messages = event.agent.messages
            if len(messages) >= 2 and messages[-1]["role"] == "assistant":
                # Get last customer query and agent response
                customer_query = None
                agent_response = None
                
                for msg in reversed(messages):
                    if msg["role"] == "assistant" and not agent_response:
                        agent_response = msg["content"][0]["text"]
                    elif msg["role"] == "user" and not customer_query and "toolResult" not in msg["content"][0]:
                        customer_query = msg["content"][0]["text"]
                        break
                
                if customer_query and agent_response:
                    # Use MemorySession to store interaction
                    interaction_messages = [
                        ConversationalMessage(customer_query, USER),
                        ConversationalMessage(agent_response, ASSISTANT)
                    ]
                    
                    result = self.customer_session.add_turns(interaction_messages)
                    logger.info(
                        f"✅ Saved interaction using MemorySession - Event ID: {result['eventId']}"
                    )
                    
        except Exception as e:
            logger.error(f"Failed to save support interaction: {e}")
    
    def register_hooks(self, registry: HookRegistry) -> None:
        """Register customer support memory hooks.
        
        Args:
            registry: HookRegistry to register callbacks with
        """
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_support_interaction)
        logger.info("✅ Customer support memory hooks registered with MemorySession")


# ============================================================================
# Agent Creation
# ============================================================================

def create_customer_support_agent(
    customer_session: MemorySession,
    model_id: str = MODEL_ID
) -> Agent:
    """Create customer support agent with memory and tools.
    
    Args:
        customer_session: MemorySession instance for this customer
        model_id: Model identifier for the LLM
    
    Returns:
        Agent: Configured Strands agent with memory hooks and tools
    """
    # Create memory hooks
    support_hooks = CustomerSupportMemoryHooks(customer_session)
    
    # Create agent
    agent = Agent(
        hooks=[support_hooks],
        model=model_id,
        tools=[web_search, check_order_status],
        system_prompt="""You are a helpful customer support agent with access to customer history and order information.
        
Your role:
- Help customers with their orders, returns, and product issues
- Use customer context to provide personalized support
- Search for product information when needed
- Be empathetic and solution-focused
- Reference previous orders and preferences when relevant

Always be professional, helpful, and aim to resolve customer issues efficiently."""
    )
    
    logger.info("✅ Customer support agent created with MemorySession integration")
    return agent


# ============================================================================
# Utility Functions
# ============================================================================

def cleanup_memory(memory_id: str, region: str = REGION):
    """Delete memory resource.
    
    Args:
        memory_id: ID of memory resource to delete
        region: AWS region
    """
    try:
        memory_manager = MemoryManager(region_name=region)
        memory_manager.delete_memory(memory_id)
        logger.info(f"✅ Deleted memory: {memory_id}")
    except Exception as e:
        logger.error(f"Failed to delete memory: {e}")


# ============================================================================
# Test Scenarios
# ============================================================================

def run_test_scenarios(agent: Agent):
    """Run customer support test scenarios.
    
    Args:
        agent: Customer support agent to test
    """
    test_scenarios = [
        {
            "name": "iPhone performance issue",
            "query": "My iPhone is running very slow and gets hot when charging. Can you help?",
            "emoji": "📱"
        },
        {
            "name": "Bluetooth connectivity issue",
            "query": "My iPhone won't connect to my Sennheiser headphones via Bluetooth. How do I fix this?",
            "emoji": "🎧"
        },
        {
            "name": "Order status check",
            "query": "Can you check the status of my recent orders?",
            "emoji": "📦"
        },
        {
            "name": "Product recommendation",
            "query": "I'm still interested in buying a laptop. What ThinkPad models do you recommend?",
            "emoji": "💻"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print("\n" + "=" * 70)
        logger.info(f"🧪 Running Test {i}: {scenario['name']}")
        print(f"\nUser: {scenario['query']}")
        print(f"\nAgent Response:")
        print("-" * 70)
        
        try:
            response = agent(scenario['query'])
            print(f"\n{scenario['emoji']} {response}")
            logger.info(f"✅ Test {i} completed successfully")
        except Exception as e:
            logger.error(f"❌ Test {i} failed: {e}")
            print(f"\n❌ Error: {e}")
    
    print("\n" + "=" * 70)
    logger.info("🎉 All customer support scenario tests completed!")


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main function to demonstrate customer support agent with long-term memory."""
    
    logger.info("🚀 Starting Customer Support Agent with Long-Term Memory")
    logger.info("=" * 70)
    
    try:
        # Step 1: Create IAM execution role
        logger.info("Step 1: Creating IAM execution role...")
        execution_role_arn = create_memory_execution_role()
        
        # Step 2: Setup memory with strategies
        logger.info("\nStep 2: Setting up memory with long-term strategies...")
        memory, memory_id = setup_memory(execution_role_arn=execution_role_arn)
        
        # Step 3: Setup session
        logger.info("\nStep 3: Setting up customer session...")
        session_manager, customer_session = setup_session(
            memory_id=memory_id,
            actor_id=CUSTOMER_ID,
            session_id=SESSION_ID
        )
        
        # Step 4: Seed customer history
        logger.info("\nStep 4: Seeding customer history...")
        seed_customer_history(customer_session)
        
        # Step 5: Create agent
        logger.info("\nStep 5: Creating customer support agent...")
        agent = create_customer_support_agent(customer_session)
        
        # Step 6: Run test scenarios
        logger.info("\nStep 6: Running test scenarios...")
        run_test_scenarios(agent)
        
        # Optional cleanup (commented out by default)
        # print("\n" + "=" * 70)
        # print("=== Cleanup ===")
        # cleanup_memory(memory_id)
        
        logger.info("=" * 70)
        logger.info("✅ Demo completed successfully!")
        
        print("\n" + "=" * 70)
        print("Agent is ready for interactive use!")
        print("You can continue the conversation by calling:")
        print('  agent("Your message here")')
        print("\nTo cleanup (delete memory):")
        print(f'  cleanup_memory("{memory_id}")')
        print("=" * 70)
        
        return agent, customer_session, memory_id
        
    except KeyboardInterrupt:
        logger.info("\n\n👋 Interrupted by user")
        return None, None, None
    except Exception as e:
        logger.error(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


if __name__ == "__main__":
    agent, customer_session, memory_id = main()
