"""
Mock Memory Provider for testing without GCP credentials.

This provider stores everything in memory and uses a simple
embedding approximation for testing purposes.
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from .base import (
    MemoryProvider,
    MemoryConfig,
    Memory,
    MemoryType,
    register_provider
)

logger = logging.getLogger(__name__)


@register_provider("mock")
class MockMemoryProvider(MemoryProvider):
    """
    In-memory mock provider for testing.

    Features:
    - Stores all data in dictionaries
    - Uses simple hash-based "embeddings"
    - No external dependencies
    """

    def __init__(self, config: MemoryConfig):
        super().__init__(config)
        self._stores: Dict[str, Dict[str, Any]] = {}
        self._memories: Dict[str, Dict[str, Memory]] = {}

    async def initialize(self) -> bool:
        """Initialize mock provider (always succeeds)."""
        self._initialized = True
        logger.info("Mock Memory Provider initialized (no GCP required)")
        return True

    async def create_memory_store(self, agent_id: str, user_id: str) -> str:
        """Create or get existing memory store."""
        store_id = hashlib.sha256(f"{agent_id}:{user_id}".encode()).hexdigest()[:16]
        store_id = f"store_{store_id}"

        # Return existing store if it exists (don't overwrite!)
        if store_id in self._stores:
            logger.debug(f"Returning existing mock store: {store_id}")
            return store_id

        self._stores[store_id] = {
            "agent_id": agent_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._memories[store_id] = {}

        logger.info(f"Created mock store: {store_id}")
        return store_id

    async def delete_memory_store(self, store_id: str) -> bool:
        """Delete a memory store."""
        if store_id in self._stores:
            del self._stores[store_id]
            del self._memories[store_id]
            return True
        return False

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a simple hash-based "embedding" for testing.

        This is NOT a real embedding - just deterministic vectors
        based on text hash for testing similarity search logic.
        """
        # Create a deterministic 128-dim vector from text hash
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        embedding = []
        for i in range(0, 64, 2):
            val = int(text_hash[i:i+2], 16) / 255.0 - 0.5
            embedding.append(val)

        # Pad to 128 dims
        while len(embedding) < 128:
            embedding.append(0.0)

        return embedding

    async def add_memory(self, store_id: str, memory: Memory) -> str:
        """Add a memory to the store."""
        if store_id not in self._memories:
            raise ValueError(f"Store {store_id} not found")

        # Generate embedding if not provided
        if not memory.embedding:
            memory.embedding = await self.generate_embedding(memory.content)

        self._memories[store_id][memory.id] = memory
        logger.debug(f"Added memory {memory.id} to store {store_id}")
        return memory.id

    async def add_memories(self, store_id: str, memories: List[Memory]) -> List[str]:
        """Batch add memories."""
        ids = []
        for memory in memories:
            memory_id = await self.add_memory(store_id, memory)
            ids.append(memory_id)
        return ids

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def search_memories(
        self,
        store_id: str,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10,
        min_similarity: Optional[float] = None
    ) -> List[Memory]:
        """Search memories by similarity."""
        if store_id not in self._memories:
            return []

        query_embedding = await self.generate_embedding(query)
        # Use very low threshold for mock (hash-based embeddings don't have real similarity)
        threshold = min_similarity or 0.0  # Accept all for mock testing

        results = []
        for memory in self._memories[store_id].values():
            # Filter by type
            if memory_types and memory.memory_type not in memory_types:
                continue

            # Calculate similarity
            if memory.embedding:
                similarity = self._cosine_similarity(query_embedding, memory.embedding)
                if similarity >= threshold:
                    results.append((similarity, memory))

        # Sort by similarity
        results.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in results[:limit]]

    async def get_memory(self, store_id: str, memory_id: str) -> Optional[Memory]:
        """Get a specific memory."""
        if store_id in self._memories:
            return self._memories[store_id].get(memory_id)
        return None

    async def update_memory(
        self,
        store_id: str,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update a memory."""
        if store_id in self._memories and memory_id in self._memories[store_id]:
            memory = self._memories[store_id][memory_id]
            memory.content = content
            memory.embedding = await self.generate_embedding(content)
            memory.updated_at = datetime.utcnow()
            if metadata:
                memory.metadata = metadata
            return True
        return False

    async def delete_memory(self, store_id: str, memory_id: str) -> bool:
        """Delete a memory."""
        if store_id in self._memories and memory_id in self._memories[store_id]:
            del self._memories[store_id][memory_id]
            return True
        return False

    async def get_recent_memories(
        self,
        store_id: str,
        limit: int = 20,
        memory_types: Optional[List[MemoryType]] = None
    ) -> List[Memory]:
        """Get recent memories."""
        if store_id not in self._memories:
            return []

        memories = list(self._memories[store_id].values())

        # Filter by type
        if memory_types:
            memories = [m for m in memories if m.memory_type in memory_types]

        # Sort by created_at descending
        memories.sort(key=lambda m: m.created_at, reverse=True)
        return memories[:limit]

    async def extract_facts(self, conversation: List[Dict[str, str]]) -> List[Memory]:
        """
        Extract facts from conversation (mock version).

        In production, this uses Gemini. For testing, we extract
        simple patterns.
        """
        facts = []

        for msg in conversation:
            content = msg.get("content", "").lower()

            # Simple pattern matching for testing
            if "my name is" in content:
                name = content.split("my name is")[-1].strip().split()[0]
                facts.append(Memory(
                    content=f"User's name is {name}",
                    memory_type=MemoryType.FACT,
                    confidence=0.9,
                    source="auto_extraction",
                ))

            if "i prefer" in content or "i like" in content:
                pref = content.split("prefer")[-1] if "prefer" in content else content.split("like")[-1]
                facts.append(Memory(
                    content=f"User preference: {pref.strip()[:50]}",
                    memory_type=MemoryType.FACT,
                    confidence=0.7,
                    source="auto_extraction",
                ))

        logger.info(f"Extracted {len(facts)} facts from conversation (mock)")
        return facts
