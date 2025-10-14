"""
Strands Agents with AgentCore Memory (Short-Term Memory) - Using MemoryManager

This script demonstrates how to build a personal agent using Strands agents with 
AgentCore short-term memory using MemoryManager and MemorySessionManager.

Tutorial Details:
- Tutorial type: Short Term Conversational
- Agent type: Personal Agent
- Agentic Framework: Strands Agents
- LLM model: Amazon Nova Lite v1.0
- Components: AgentCore Short-term Memory with MemoryManager, 
              AgentInitializedEvent and MessageAddedEvent hooks

Prerequisites:
- Python 3.10+
- AWS credentials with AgentCore Memory permissions
- Amazon Bedrock AgentCore SDK with MemoryManager support
- Access to Amazon Bedrock models

Usage:
    python personal_agent_memory_manager.py
"""

import logging
import os
from datetime import datetime
from typing import Optional

# Strands Agent imports
from strands import Agent, tool
from strands.hooks import (
    AgentInitializedEvent, 
    HookProvider, 
    HookRegistry, 
    MessageAddedEvent
)

# Memory management imports
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole
from bedrock_agentcore.memory.session import MemorySession, MemorySessionManager

# Web search imports
from ddgs.exceptions import DDGSException, RatelimitException
from ddgs import DDGS

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("personal-agent")

# Configuration
REGION = os.getenv('AWS_REGION', 'us-east-1')
ACTOR_ID = "user_123"  # Unique identifier (AgentID, User ID, etc.)
SESSION_ID = "personal_session_001"  # Unique session identifier
MEMORY_NAME = "PersonalAgentMemoryManager"
MODEL_ID = "amazon.nova-lite-v1:0"


# ============================================================================
# Web Search Tool
# ============================================================================

@tool
def websearch(keywords: str, region: str = "us-en", max_results: int = 5) -> str:
    """Search the web for updated information.
    
    Args:
        keywords (str): The search query keywords.
        region (str): The search region: wt-wt, us-en, uk-en, ru-ru, etc.
        max_results (int): The maximum number of results to return.
    
    Returns:
        str: Search results or error message.
    """
    try:
        results = DDGS().text(keywords, region=region, max_results=max_results)
        return results if results else "No results found."
    except RatelimitException:
        return "Rate limit reached. Please try again later."
    except DDGSException as e:
        return f"Search error: {e}"
    except Exception as e:
        return f"Search error: {str(e)}"


# ============================================================================
# Memory Hook Provider
# ============================================================================

class MemoryHookProvider(HookProvider):
    """Hook provider for automatic memory operations with MemorySession."""
    
    def __init__(self, memory_session: MemorySession):
        """Initialize with a pre-configured MemorySession.
        
        Args:
            memory_session: MemorySession instance bound to actor/session
        """
        self.memory_session = memory_session
    
    def on_agent_initialized(self, event: AgentInitializedEvent):
        """Load recent conversation history when agent starts.
        
        Args:
            event: AgentInitializedEvent containing agent instance
        """
        try:
            # Retrieve last 5 conversation turns
            recent_turns = self.memory_session.get_last_k_turns(k=5)
            
            if recent_turns:
                # Format conversation history for context
                context_messages = []
                for turn in recent_turns:
                    for message in turn:
                        # Handle both EventMessage objects and dict formats
                        if hasattr(message, 'role') and hasattr(message, 'content'):
                            role = message['role']
                            content = message['content']
                        else:
                            role = message.get('role', 'unknown')
                            content = message.get('content', {}).get('text', '')
                        context_messages.append(f"{role}: {content}")
                
                context = "\n".join(context_messages)
                # Add context to agent's system prompt
                event.agent.system_prompt += f"\n\nRecent conversation:\n{context}"
                logger.info(
                    f"✅ Loaded {len(recent_turns)} conversation turns using MemorySession"
                )
        except Exception as e:
            logger.error(f"Memory load error: {e}")

    def on_message_added(self, event: MessageAddedEvent):
        """Store messages in memory after they are added.
        
        Args:
            event: MessageAddedEvent containing the agent and new message
        """
        messages = event.agent.messages
        try:
            if messages and len(messages) > 0 and messages[-1]["content"][0].get("text"):
                message_text = messages[-1]["content"][0]["text"]
                message_role = (
                    MessageRole.USER 
                    if messages[-1]["role"] == "user" 
                    else MessageRole.ASSISTANT
                )
                
                # Store message using memory session
                result = self.memory_session.add_turns(
                    messages=[ConversationalMessage(message_text, message_role)]
                )
                
                event_id = result['eventId']
                logger.info(
                    f"✅ Stored message with Event ID: {event_id}, "
                    f"Role: {message_role.value}"
                )
        except Exception as e:
            logger.error(f"Memory save error: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
    
    def register_hooks(self, registry: HookRegistry):
        """Register hooks with the agent's hook registry.
        
        Args:
            registry: HookRegistry to register callbacks with
        """
        registry.add_callback(MessageAddedEvent, self.on_message_added)
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)
        logger.info("✅ Memory hooks registered with MemorySession")


# ============================================================================
# Memory Setup Functions
# ============================================================================

def setup_memory(region: str = REGION, memory_name: str = MEMORY_NAME):
    """Create or retrieve memory resource using MemoryManager.
    
    Args:
        region: AWS region for memory resource
        memory_name: Name for the memory resource
    
    Returns:
        tuple: (memory object, memory_id)
    
    Raises:
        Exception: If memory creation fails
    """
    logger.info(f"Setting up memory in region: {region}")
    
    # Initialize Memory Manager
    memory_manager = MemoryManager(region_name=region)
    logger.info(f"✅ MemoryManager initialized for region: {region}")
    
    # Create memory resource
    logger.info(f"Creating memory '{memory_name}' for short-term conversational storage...")
    
    try:
        memory = memory_manager.get_or_create_memory(
            name=memory_name,
            strategies=[],  # No strategies for short-term memory
            description="Short-term memory for personal agent",
            event_expiry_days=7,  # Retention period
            memory_execution_role_arn=None,  # Optional for short-term memory
        )
        memory_id = memory.id
        logger.info(f"✅ Successfully created/retrieved memory with MemoryManager:")
        logger.info(f"   Memory ID: {memory_id}")
        logger.info(f"   Memory Name: {memory.name}")
        logger.info(f"   Memory Status: {memory.status}")
        
        return memory, memory_id
        
    except Exception as e:
        logger.error(f"❌ Memory creation failed: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise


def setup_session(memory_id: str, actor_id: str, session_id: str, region: str = REGION):
    """Initialize session manager and create memory session.
    
    Args:
        memory_id: ID of the memory resource
        actor_id: Unique actor identifier
        session_id: Unique session identifier
        region: AWS region
    
    Returns:
        tuple: (session_manager, user_session)
    """
    # Initialize the session memory manager
    session_manager = MemorySessionManager(memory_id=memory_id, region_name=region)
    
    # Create a memory session for the specific actor/session combination
    user_session = session_manager.create_memory_session(
        actor_id=actor_id, 
        session_id=session_id
    )
    
    logger.info(f"✅ Session manager initialized for memory: {memory_id}")
    logger.info(f"✅ Memory session created for actor: {actor_id}, session: {session_id}")
    
    return session_manager, user_session


# ============================================================================
# Agent Creation
# ============================================================================

def create_personal_agent(
    user_session: MemorySession, 
    model_id: str = MODEL_ID
) -> Agent:
    """Create personal agent with memory and web search capabilities.
    
    Args:
        user_session: MemorySession instance for this agent
        model_id: Model identifier for the LLM
    
    Returns:
        Agent: Configured Strands agent with memory and tools
    """
    agent = Agent(
        name="PersonalAssistant",
        model=model_id,
        system_prompt=f"""You are a helpful personal assistant with web search capabilities.
        
        You can help with:
        - General questions and information lookup
        - Web searches for current information
        - Personal task management
        
        When you need current information, use the websearch function.
        Today's date: {datetime.today().strftime('%Y-%m-%d')}
        Be friendly and professional.""",
        hooks=[MemoryHookProvider(user_session)], 
        tools=[websearch],
    )
    logger.info("✅ Personal agent created with MemorySession and web search")
    return agent


# ============================================================================
# Utility Functions
# ============================================================================

def view_memory_contents(user_session: MemorySession, k: int = 3):
    """Display stored memory contents.
    
    Args:
        user_session: MemorySession to query
        k: Number of recent turns to retrieve
    """
    print("\n=== Memory Contents ===")
    recent_turns = user_session.get_last_k_turns(k=k)
    
    if not recent_turns:
        print("No conversation history found.")
        return
    
    for i, turn in enumerate(recent_turns, 1):
        print(f"Turn {i}:")
        for message in turn:
            role = message['role']
            content = message['content']['text']
            content_preview = (
                content[:100] + "..." 
                if len(content) > 100 
                else content
            )
            print(f"  {role}: {content_preview}")
        print()


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
# Main Execution
# ============================================================================

def main():
    """Main function to demonstrate the personal agent with memory."""
    
    logger.info("🚀 Starting Personal Agent with AgentCore Memory")
    logger.info("=" * 70)
    
    # Step 1: Setup memory
    memory, memory_id = setup_memory()
    
    # Step 2: Setup session
    session_manager, user_session = setup_session(
        memory_id=memory_id,
        actor_id=ACTOR_ID,
        session_id=SESSION_ID
    )
    
    # Step 3: Create agent
    agent = create_personal_agent(user_session)
    
    # Step 4: Test conversation with memory
    print("\n" + "=" * 70)
    print("=== First Conversation ===")
    print("=" * 70)
    
    print("\nUser: My name is Alex and I'm interested in learning about AI.")
    print("Agent: ", end="")
    agent("My name is Alex and I'm interested in learning about AI.")
    
    print("\n" + "-" * 70)
    print("\nUser: Can you search for the latest AI trends in 2025?")
    print("Agent: ", end="")
    agent("Can you search for the latest AI trends in 2025?")
    
    print("\n" + "-" * 70)
    print("\nUser: I'm particularly interested in machine learning applications.")
    print("Agent: ", end="")
    agent("I'm particularly interested in machine learning applications.")
    
    # Step 5: Test memory continuity with new agent instance
    print("\n" + "=" * 70)
    print("=== User Returns - New Session ===")
    print("=" * 70)
    
    new_agent = create_personal_agent(user_session)
    
    print("\nUser: What was my name again?")
    print("Agent: ", end="")
    new_agent("What was my name again?")
    
    print("\n" + "-" * 70)
    print("\nUser: Can you search for more information about machine learning?")
    print("Agent: ", end="")
    new_agent("Can you search for more information about machine learning?")
    
    # Step 6: View stored memory
    print("\n" + "=" * 70)
    view_memory_contents(user_session, k=3)
    
    # Optional cleanup (commented out by default)
    # print("\n" + "=" * 70)
    # print("=== Cleanup ===")
    # cleanup_memory(memory_id)
    
    logger.info("=" * 70)
    logger.info("✅ Demo completed successfully!")
    
    return agent, user_session, memory_id


if __name__ == "__main__":
    try:
        agent, user_session, memory_id = main()
        
        # Keep the session active for interactive use
        print("\n" + "=" * 70)
        print("Agent is ready for interactive use!")
        print("You can continue the conversation by calling:")
        print('  agent("Your message here")')
        print("\nTo view memory contents:")
        print("  view_memory_contents(user_session)")
        print("\nTo cleanup (delete memory):")
        print(f'  cleanup_memory("{memory_id}")')
        print("=" * 70)
        
    except KeyboardInterrupt:
        logger.info("\n\n👋 Interrupted by user")
    except Exception as e:
        logger.error(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
