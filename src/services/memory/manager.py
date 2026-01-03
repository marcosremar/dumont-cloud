"""
Memory Manager - High-level API for agent memory operations.

Provides a simple interface for:
- Creating/managing memory stores
- Adding and retrieving memories
- Extracting facts from conversations
- Provider-agnostic memory operations
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import (
    MemoryProvider,
    MemoryConfig,
    Memory,
    MemoryType,
    get_provider,
    list_providers
)

logger = logging.getLogger(__name__)

# Global instance
_memory_manager: Optional["MemoryManager"] = None


class MemoryManager:
    """
    High-level memory management for AI agents.

    Usage:
        manager = MemoryManager()
        await manager.initialize(config)

        # Create store for agent-user pair
        store_id = await manager.create_store(agent_id, user_id)

        # Add conversation to memory
        await manager.add_conversation(store_id, messages)

        # Get relevant context for new query
        context = await manager.get_context(store_id, user_query)
    """

    def __init__(self):
        self._provider: Optional[MemoryProvider] = None
        self._config: Optional[MemoryConfig] = None

    async def initialize(self, config: Optional[MemoryConfig] = None) -> bool:
        """
        Initialize the memory manager with a provider.

        If no config is provided, uses GCP with default settings.
        Idempotent: if already initialized with same provider, returns True.
        """
        try:
            config = config or MemoryConfig(provider="gcp")

            # If already initialized with same provider, skip
            if self.is_initialized and self._config and self._config.provider == config.provider:
                logger.debug(f"MemoryManager already initialized with {config.provider}")
                return True

            self._config = config

            # Get provider class
            provider_cls = get_provider(self._config.provider)
            if not provider_cls:
                logger.error(f"Unknown provider: {self._config.provider}")
                logger.info(f"Available providers: {list_providers()}")
                return False

            # Create and initialize provider
            self._provider = provider_cls(self._config)
            success = await self._provider.initialize()

            if success:
                logger.info(f"MemoryManager initialized with {self._config.provider} provider")
            return success

        except Exception as e:
            logger.error(f"Failed to initialize MemoryManager: {e}")
            return False

    @property
    def is_initialized(self) -> bool:
        return self._provider is not None and self._provider.is_initialized

    async def create_store(self, agent_id: str, user_id: str) -> str:
        """Create a memory store for an agent-user pair."""
        if not self.is_initialized:
            raise RuntimeError("MemoryManager not initialized")
        return await self._provider.create_memory_store(agent_id, user_id)

    async def delete_store(self, store_id: str) -> bool:
        """Delete a memory store."""
        if not self.is_initialized:
            raise RuntimeError("MemoryManager not initialized")
        return await self._provider.delete_memory_store(store_id)

    async def add_conversation(
        self,
        store_id: str,
        messages: List[Dict[str, str]],
        extract_facts: bool = True
    ) -> List[str]:
        """
        Add conversation messages to memory.

        Args:
            store_id: The memory store ID
            messages: List of {"role": "user/assistant", "content": "..."}
            extract_facts: Whether to extract facts from the conversation

        Returns:
            List of memory IDs created
        """
        if not self.is_initialized:
            raise RuntimeError("MemoryManager not initialized")

        memory_ids = []

        # Add each message as a conversation memory
        for msg in messages:
            memory = Memory(
                content=msg["content"],
                memory_type=MemoryType.CONVERSATION,
                role=msg.get("role", "user"),
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            memory_id = await self._provider.add_memory(store_id, memory)
            memory_ids.append(memory_id)

        # Optionally extract facts
        if extract_facts and len(messages) >= 2:
            facts = await self._provider.extract_facts(messages)
            for fact in facts:
                fact_id = await self._provider.add_memory(store_id, fact)
                memory_ids.append(fact_id)

        return memory_ids

    async def add_fact(
        self,
        store_id: str,
        content: str,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a fact/preference to memory."""
        if not self.is_initialized:
            raise RuntimeError("MemoryManager not initialized")

        memory = Memory(
            content=content,
            memory_type=MemoryType.FACT,
            confidence=confidence,
            metadata=metadata or {},
            source="manual",
        )
        return await self._provider.add_memory(store_id, memory)

    async def get_context(
        self,
        store_id: str,
        query: str,
        include_recent: bool = True,
        include_facts: bool = True,
        max_memories: int = 10
    ) -> Dict[str, Any]:
        """
        Get relevant context for a query.

        Returns a structured context object with:
        - relevant_memories: Semantically similar past conversations
        - facts: User facts/preferences
        - recent_messages: Recent conversation history

        This is designed to be injected into the system prompt.
        """
        if not self.is_initialized:
            raise RuntimeError("MemoryManager not initialized")

        context = {
            "relevant_memories": [],
            "facts": [],
            "recent_messages": [],
        }

        # Get semantically relevant memories
        relevant = await self._provider.search_memories(
            store_id,
            query,
            memory_types=[MemoryType.CONVERSATION, MemoryType.EPISODIC],
            limit=max_memories // 2,
        )
        context["relevant_memories"] = [m.to_dict() for m in relevant]

        # Get user facts/preferences
        if include_facts:
            facts = await self._provider.search_memories(
                store_id,
                query,
                memory_types=[MemoryType.FACT],
                limit=5,
            )
            context["facts"] = [m.to_dict() for m in facts]

        # Get recent conversation history
        if include_recent:
            recent = await self._provider.get_recent_memories(
                store_id,
                limit=10,
                memory_types=[MemoryType.CONVERSATION],
            )
            context["recent_messages"] = [m.to_dict() for m in recent]

        return context

    async def format_context_for_prompt(
        self,
        store_id: str,
        query: str
    ) -> str:
        """
        Get context formatted as a string for system prompt injection.

        Example output:
        ---
        ## User Memory

        ### Known Facts
        - User prefers concise answers
        - User is working on a Python project
        - User's timezone is UTC-3

        ### Relevant Past Conversations
        - [2 days ago] Discussed database optimization
        - [1 week ago] Helped with API authentication
        ---
        """
        context = await self.get_context(store_id, query)

        parts = ["## User Memory\n"]

        # Format facts
        if context["facts"]:
            parts.append("### Known Facts")
            for fact in context["facts"]:
                confidence = fact.get("confidence", 1.0)
                conf_str = f" ({int(confidence * 100)}% confident)" if confidence < 1.0 else ""
                parts.append(f"- {fact['content']}{conf_str}")
            parts.append("")

        # Format relevant memories
        if context["relevant_memories"]:
            parts.append("### Relevant Past Conversations")
            for mem in context["relevant_memories"]:
                # Calculate relative time
                created = datetime.fromisoformat(mem["created_at"])
                delta = datetime.utcnow() - created
                if delta.days > 0:
                    time_str = f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
                elif delta.seconds > 3600:
                    hours = delta.seconds // 3600
                    time_str = f"{hours} hour{'s' if hours > 1 else ''} ago"
                else:
                    time_str = "recently"

                role = mem.get("role", "unknown")
                content = mem["content"][:100] + "..." if len(mem["content"]) > 100 else mem["content"]
                parts.append(f"- [{time_str}] {role}: {content}")
            parts.append("")

        if len(parts) == 1:
            return ""  # No context available

        return "\n".join(parts)

    async def search(
        self,
        store_id: str,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search memories by semantic similarity.

        Args:
            store_id: The memory store ID
            query: Search query
            memory_types: Filter by types ("conversation", "fact", "episodic")
            limit: Max results

        Returns:
            List of memory dictionaries
        """
        if not self.is_initialized:
            raise RuntimeError("MemoryManager not initialized")

        types = None
        if memory_types:
            types = [MemoryType(t) for t in memory_types]

        memories = await self._provider.search_memories(
            store_id, query, memory_types=types, limit=limit
        )
        return [m.to_dict() for m in memories]

    async def delete_memory(self, store_id: str, memory_id: str) -> bool:
        """Delete a specific memory."""
        if not self.is_initialized:
            raise RuntimeError("MemoryManager not initialized")
        return await self._provider.delete_memory(store_id, memory_id)

    async def clear_conversations(self, store_id: str) -> int:
        """
        Clear conversation history while keeping facts.
        Returns number of memories deleted.
        """
        if not self.is_initialized:
            raise RuntimeError("MemoryManager not initialized")

        # Get all conversation memories
        conversations = await self._provider.get_recent_memories(
            store_id,
            limit=1000,
            memory_types=[MemoryType.CONVERSATION],
        )

        count = 0
        for mem in conversations:
            if await self._provider.delete_memory(store_id, mem.id):
                count += 1

        logger.info(f"Cleared {count} conversation memories from store {store_id}")
        return count


def get_memory_manager() -> MemoryManager:
    """Get the global MemoryManager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


async def initialize_memory_manager(config: Optional[MemoryConfig] = None) -> bool:
    """Initialize the global MemoryManager."""
    manager = get_memory_manager()
    return await manager.initialize(config)
