"""
Google Cloud Platform Memory Provider using Vertex AI.

Uses:
- Vertex AI Embeddings (gemini-embedding-001 or text-embedding-004)
- Vertex AI Vector Search for similarity search
- Firestore for metadata storage
- Gemini for fact extraction

This is the default provider since the user has GCP credits.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

from .base import (
    MemoryProvider,
    MemoryConfig,
    Memory,
    MemoryType,
    register_provider
)

logger = logging.getLogger(__name__)


@register_provider("gcp")
class GCPMemoryProvider(MemoryProvider):
    """
    GCP Vertex AI Memory Provider.

    Architecture:
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │  Vertex AI      │    │  Vertex AI      │    │    Firestore    │
    │  Embeddings     │───►│  Vector Search  │◄──►│   (metadata)    │
    │  (text→vector)  │    │  (similarity)   │    │                 │
    └─────────────────┘    └─────────────────┘    └─────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │     Gemini      │
                          │ (fact extract)  │
                          └─────────────────┘
    """

    def __init__(self, config: MemoryConfig):
        super().__init__(config)
        self._aiplatform = None
        self._firestore = None
        self._vertexai = None
        self._embedding_model = None
        self._generative_model = None

    async def initialize(self) -> bool:
        """Initialize GCP clients."""
        try:
            # Import GCP libraries
            from google.cloud import aiplatform
            from google.cloud import firestore
            import vertexai
            from vertexai.language_models import TextEmbeddingModel

            # Initialize Vertex AI
            project_id = self.config.gcp_project_id
            location = self.config.gcp_location

            if not project_id:
                # Try to get from environment or default credentials
                import google.auth
                _, project_id = google.auth.default()

            vertexai.init(project=project_id, location=location)
            aiplatform.init(project=project_id, location=location)

            # Initialize embedding model
            self._embedding_model = TextEmbeddingModel.from_pretrained(
                self.config.embedding_model
            )

            # Initialize Firestore for metadata
            self._firestore = firestore.AsyncClient(project=project_id)

            # Initialize Gemini for fact extraction
            from vertexai.generative_models import GenerativeModel
            self._generative_model = GenerativeModel("gemini-1.5-flash")

            self._initialized = True
            logger.info(f"GCP Memory Provider initialized (project: {project_id})")
            return True

        except ImportError as e:
            logger.error(f"Missing GCP dependencies: {e}")
            logger.info("Install with: pip install google-cloud-aiplatform google-cloud-firestore")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize GCP Memory Provider: {e}")
            return False

    def _get_store_collection(self, store_id: str):
        """Get Firestore collection for a memory store."""
        return self._firestore.collection("memory_stores").document(store_id)

    def _get_memories_collection(self, store_id: str):
        """Get Firestore collection for memories in a store."""
        return self._get_store_collection(store_id).collection("memories")

    async def create_memory_store(self, agent_id: str, user_id: str) -> str:
        """Create a new memory store for an agent-user pair."""
        # Generate deterministic store ID
        store_id = hashlib.sha256(f"{agent_id}:{user_id}".encode()).hexdigest()[:16]
        store_id = f"store_{store_id}"

        # Create store document in Firestore
        store_ref = self._get_store_collection(store_id)
        await store_ref.set({
            "agent_id": agent_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "memory_count": 0,
            "last_accessed": datetime.utcnow().isoformat(),
        })

        logger.info(f"Created memory store: {store_id} for agent={agent_id}, user={user_id}")
        return store_id

    async def delete_memory_store(self, store_id: str) -> bool:
        """Delete a memory store and all its contents."""
        try:
            # Delete all memories in the store
            memories_ref = self._get_memories_collection(store_id)
            async for doc in memories_ref.stream():
                await doc.reference.delete()

            # Delete the store document
            await self._get_store_collection(store_id).delete()

            logger.info(f"Deleted memory store: {store_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory store {store_id}: {e}")
            return False

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector using Vertex AI."""
        try:
            embeddings = self._embedding_model.get_embeddings([text])
            return embeddings[0].values
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return []

    async def add_memory(self, store_id: str, memory: Memory) -> str:
        """Add a single memory to the store."""
        try:
            # Generate embedding if not provided
            if not memory.embedding:
                memory.embedding = await self.generate_embedding(memory.content)

            # Store in Firestore
            memory_ref = self._get_memories_collection(store_id).document(memory.id)
            await memory_ref.set({
                **memory.to_dict(),
                "embedding": memory.embedding,
            })

            # Update store metadata
            store_ref = self._get_store_collection(store_id)
            await store_ref.update({
                "memory_count": firestore.Increment(1),
                "last_accessed": datetime.utcnow().isoformat(),
            })

            logger.debug(f"Added memory {memory.id} to store {store_id}")
            return memory.id

        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise

    async def add_memories(self, store_id: str, memories: List[Memory]) -> List[str]:
        """Batch add memories to the store."""
        ids = []
        for memory in memories:
            memory_id = await self.add_memory(store_id, memory)
            ids.append(memory_id)
        return ids

    async def search_memories(
        self,
        store_id: str,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10,
        min_similarity: Optional[float] = None
    ) -> List[Memory]:
        """
        Search for relevant memories using semantic similarity.

        Uses cosine similarity between query embedding and stored embeddings.
        """
        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query)
            if not query_embedding:
                return []

            # Get all memories from store (in production, use Vector Search index)
            memories_ref = self._get_memories_collection(store_id)
            results = []

            async for doc in memories_ref.stream():
                data = doc.to_dict()

                # Filter by memory type if specified
                if memory_types:
                    mem_type = MemoryType(data.get("memory_type", "conversation"))
                    if mem_type not in memory_types:
                        continue

                # Calculate cosine similarity
                stored_embedding = data.get("embedding", [])
                if stored_embedding:
                    similarity = self._cosine_similarity(query_embedding, stored_embedding)

                    # Apply threshold
                    threshold = min_similarity or self.config.similarity_threshold
                    if similarity >= threshold:
                        memory = Memory.from_dict(data)
                        results.append((similarity, memory))

            # Sort by similarity and limit
            results.sort(key=lambda x: x[0], reverse=True)
            return [m for _, m in results[:limit]]

        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def get_memory(self, store_id: str, memory_id: str) -> Optional[Memory]:
        """Get a specific memory by ID."""
        try:
            doc = await self._get_memories_collection(store_id).document(memory_id).get()
            if doc.exists:
                return Memory.from_dict(doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {e}")
            return None

    async def update_memory(
        self,
        store_id: str,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update a memory's content and/or metadata."""
        try:
            # Generate new embedding for updated content
            embedding = await self.generate_embedding(content)

            update_data = {
                "content": content,
                "embedding": embedding,
                "updated_at": datetime.utcnow().isoformat(),
            }
            if metadata:
                update_data["metadata"] = metadata

            await self._get_memories_collection(store_id).document(memory_id).update(update_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return False

    async def delete_memory(self, store_id: str, memory_id: str) -> bool:
        """Delete a specific memory."""
        try:
            await self._get_memories_collection(store_id).document(memory_id).delete()

            # Update store count
            store_ref = self._get_store_collection(store_id)
            await store_ref.update({
                "memory_count": firestore.Increment(-1),
            })
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    async def get_recent_memories(
        self,
        store_id: str,
        limit: int = 20,
        memory_types: Optional[List[MemoryType]] = None
    ) -> List[Memory]:
        """Get most recent memories for conversation context."""
        try:
            query = self._get_memories_collection(store_id).order_by(
                "created_at", direction=firestore.Query.DESCENDING
            ).limit(limit)

            results = []
            async for doc in query.stream():
                data = doc.to_dict()
                if memory_types:
                    mem_type = MemoryType(data.get("memory_type", "conversation"))
                    if mem_type not in memory_types:
                        continue
                results.append(Memory.from_dict(data))

            return results
        except Exception as e:
            logger.error(f"Failed to get recent memories: {e}")
            return []

    async def extract_facts(self, conversation: List[Dict[str, str]]) -> List[Memory]:
        """
        Extract facts and preferences from a conversation using Gemini.
        """
        try:
            # Format conversation for analysis
            conv_text = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in conversation
            ])

            prompt = f"""Analyze this conversation and extract important facts, preferences, or information about the user that should be remembered for future conversations.

Conversation:
{conv_text}

Return a JSON array of facts. Each fact should have:
- "content": the fact/preference (string)
- "type": one of "fact", "preference", "context", "goal"
- "confidence": how certain this fact is (0.0-1.0)

Only extract truly important information that would be useful in future conversations.
If no important facts are found, return an empty array [].

Return ONLY valid JSON, no other text."""

            response = await self._generative_model.generate_content_async(prompt)
            response_text = response.text.strip()

            # Parse JSON response
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]

            facts_data = json.loads(response_text)

            # Convert to Memory objects
            memories = []
            for fact in facts_data:
                memory = Memory(
                    content=fact.get("content", ""),
                    memory_type=MemoryType.FACT,
                    confidence=fact.get("confidence", 0.8),
                    metadata={
                        "fact_type": fact.get("type", "fact"),
                        "extracted_from": "conversation",
                    },
                    source="auto_extraction",
                )
                memories.append(memory)

            logger.info(f"Extracted {len(memories)} facts from conversation")
            return memories

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse facts JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to extract facts: {e}")
            return []
