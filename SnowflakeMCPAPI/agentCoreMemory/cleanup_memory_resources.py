"""
Cleanup Memory Resources
Script to delete short-term and long-term memory resources from AWS Bedrock AgentCore
"""

import boto3
import logging
from typing import List, Dict
from dotenv import load_dotenv
import os
import argparse

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MemoryResourceCleanup:
    """Clean up AWS Bedrock AgentCore memory resources"""
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize cleanup client
        
        Args:
            region: AWS region
        """
        self.region = region
        self.client = boto3.client('bedrock-agent', region_name=region)
        logger.info(f"✅ Initialized cleanup client for region: {region}")
    
    def list_all_memories(self) -> List[Dict]:
        """
        List all memory resources in the account
        
        Returns:
            List of memory resources
        """
        try:
            logger.info("🔍 Listing all memory resources...")
            response = self.client.list_knowledge_bases()
            
            # Note: The actual API might be different, adjust based on AWS documentation
            # This is a placeholder - you may need to use list_memories() or similar
            memories = []
            
            # Try to list memories (adjust based on actual AWS API)
            try:
                memory_response = self.client.list_memories()
                memories = memory_response.get('memories', [])
            except Exception as e:
                logger.warning(f"Could not list memories directly: {e}")
            
            logger.info(f"Found {len(memories)} memory resources")
            return memories
            
        except Exception as e:
            logger.error(f"Error listing memories: {e}")
            return []
    
    def delete_memory_by_id(self, memory_id: str) -> bool:
        """
        Delete a specific memory resource by ID
        
        Args:
            memory_id: The memory ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"🗑️  Deleting memory: {memory_id}")
            
            # Delete the memory
            self.client.delete_memory(memoryId=memory_id)
            
            logger.info(f"✅ Successfully deleted memory: {memory_id}")
            return True
            
        except self.client.exceptions.ResourceNotFoundException:
            logger.warning(f"⚠️  Memory not found: {memory_id}")
            return False
        except Exception as e:
            logger.error(f"❌ Error deleting memory {memory_id}: {e}")
            return False
    
    def delete_all_memories(self, confirm: bool = False) -> int:
        """
        Delete all memory resources
        
        Args:
            confirm: If True, proceed with deletion without prompting
            
        Returns:
            Number of memories deleted
        """
        memories = self.list_all_memories()
        
        if not memories:
            logger.info("No memories found to delete")
            return 0
        
        if not confirm:
            print(f"\n⚠️  WARNING: This will delete {len(memories)} memory resources!")
            print("Memory IDs:")
            for memory in memories:
                print(f"  - {memory.get('memoryId', 'Unknown')}")
            
            confirmation = input("\nType 'DELETE' to confirm: ")
            if confirmation != "DELETE":
                logger.info("Deletion cancelled by user")
                return 0
        
        deleted_count = 0
        for memory in memories:
            memory_id = memory.get('memoryId')
            if memory_id:
                if self.delete_memory_by_id(memory_id):
                    deleted_count += 1
        
        logger.info(f"✅ Deleted {deleted_count} out of {len(memories)} memories")
        return deleted_count
    
    def delete_memory_by_name_pattern(self, pattern: str) -> int:
        """
        Delete memories matching a name pattern
        
        Args:
            pattern: Name pattern to match (e.g., "PersonalAgent*")
            
        Returns:
            Number of memories deleted
        """
        memories = self.list_all_memories()
        deleted_count = 0
        
        for memory in memories:
            memory_id = memory.get('memoryId', '')
            memory_name = memory.get('name', '')
            
            # Simple pattern matching
            if pattern.replace('*', '') in memory_id or pattern.replace('*', '') in memory_name:
                logger.info(f"Matching pattern '{pattern}': {memory_id}")
                if self.delete_memory_by_id(memory_id):
                    deleted_count += 1
        
        logger.info(f"✅ Deleted {deleted_count} memories matching pattern '{pattern}'")
        return deleted_count


def cleanup_specific_memories():
    """Cleanup specific known memory resources"""
    cleanup = MemoryResourceCleanup()
    
    # Known memory IDs from your scripts
    short_term_memory_id = "PersonalAgentMemoryManager-66nEyV3ZOl"
    
    logger.info("=" * 70)
    logger.info("Cleaning up specific memory resources")
    logger.info("=" * 70)
    
    # Delete short-term memory
    logger.info("\n1. Cleaning up SHORT-TERM memory...")
    cleanup.delete_memory_by_id(short_term_memory_id)
    
    # Delete any long-term memory (pattern-based)
    logger.info("\n2. Cleaning up LONG-TERM memories...")
    cleanup.delete_memory_by_name_pattern("LongTerm*")
    
    logger.info("\n✅ Cleanup completed!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Cleanup AWS Bedrock AgentCore memory resources"
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--memory-id',
        help='Specific memory ID to delete'
    )
    parser.add_argument(
        '--pattern',
        help='Delete memories matching name pattern (e.g., "PersonalAgent*")'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Delete ALL memory resources (requires confirmation)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all memory resources without deleting'
    )
    parser.add_argument(
        '--specific',
        action='store_true',
        help='Delete known specific memories from your scripts'
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompts'
    )
    
    args = parser.parse_args()
    
    cleanup = MemoryResourceCleanup(region=args.region)
    
    logger.info("=" * 70)
    logger.info("AWS Bedrock AgentCore Memory Cleanup Tool")
    logger.info("=" * 70)
    
    if args.list:
        # List all memories
        memories = cleanup.list_all_memories()
        if memories:
            print("\n📋 Memory Resources:")
            for i, memory in enumerate(memories, 1):
                print(f"\n{i}. Memory ID: {memory.get('memoryId', 'Unknown')}")
                print(f"   Name: {memory.get('name', 'N/A')}")
                print(f"   Status: {memory.get('status', 'N/A')}")
        else:
            print("No memory resources found")
    
    elif args.specific:
        # Delete specific known memories
        cleanup_specific_memories()
    
    elif args.memory_id:
        # Delete specific memory by ID
        cleanup.delete_memory_by_id(args.memory_id)
    
    elif args.pattern:
        # Delete by pattern
        cleanup.delete_memory_by_name_pattern(args.pattern)
    
    elif args.all:
        # Delete all memories
        cleanup.delete_all_memories(confirm=args.yes)
    
    else:
        # Show help
        parser.print_help()
        print("\n💡 Examples:")
        print("  # List all memories")
        print("  python cleanup_memory_resources.py --list")
        print("\n  # Delete specific memory")
        print("  python cleanup_memory_resources.py --memory-id PersonalAgentMemoryManager-66nEyV3ZOl")
        print("\n  # Delete memories by pattern")
        print("  python cleanup_memory_resources.py --pattern 'PersonalAgent*'")
        print("\n  # Delete known specific memories")
        print("  python cleanup_memory_resources.py --specific")
        print("\n  # Delete ALL memories (with confirmation)")
        print("  python cleanup_memory_resources.py --all")
        print("\n  # Delete ALL memories (skip confirmation)")
        print("  python cleanup_memory_resources.py --all --yes")


if __name__ == "__main__":
    main()
