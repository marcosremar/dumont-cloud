"""
Base classes for Memory Providers.

Architecture designed for easy provider switching:
- GCP Vertex AI (default - user has credits)
- Pinecone (future)
- Chroma (future - local/self-hosted)
- Weaviate (future)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid


class MemoryType(str, Enum):
    """Types of memory that can be stored."""
    CONVERSATION = "conversation"  # Chat history
    FACT = "fact"                  # User facts/preferences
    EPISODIC = "episodic"          # Specific events/experiences
    SEMANTIC = "semantic"          # General knowledge


@dataclass
class Memory:
    """A single memory unit."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    memory_type: MemoryType = MemoryType.CONVERSATION
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # For conversation memories
    role: Optional[str] = None  # user, assistant, system

    # For fact/preference memories
    confidence: float = 1.0
    source: Optional[str] = None  # Where this memory came from

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "role": self.role,
            "confidence": self.confidence,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data.get("content", ""),
            memory_type=MemoryType(data.get("memory_type", "conversation")),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.utcnow(),
            role=data.get("role"),
            confidence=data.get("confidence", 1.0),
            source=data.get("source"),
        )


@dataclass
class MemoryConfig:
    """Configuration for a memory store."""
    provider: str = "gcp"  # gcp, pinecone, chroma, weaviate

    # GCP specific
    gcp_project_id: Optional[str] = None
    gcp_location: str = "us-central1"
    gcp_index_endpoint: Optional[str] = None

    # Embedding model
    embedding_model: str = "text-embedding-004"  # Vertex AI default
    embedding_dimensions: int = 768

    # Pinecone specific (future)
    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    pinecone_index_name: Optional[str] = None

    # Chroma specific (future)
    chroma_host: Optional[str] = None
    chroma_port: int = 8000
    chroma_collection: Optional[str] = None

    # General settings
    similarity_threshold: float = 0.7  # Minimum similarity for retrieval
    max_memories: int = 10  # Max memories to retrieve per query

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "gcp_project_id": self.gcp_project_id,
            "gcp_location": self.gcp_location,
            "embedding_model": self.embedding_model,
            "embedding_dimensions": self.embedding_dimensions,
            "similarity_threshold": self.similarity_threshold,
            "max_memories": self.max_memories,
        }


class MemoryProvider(ABC):
    """
    Abstract base class for memory providers.

    All providers must implement these methods to be compatible
    with the Dumont Cloud agent memory system.
    """

    def __init__(self, config: MemoryConfig):
        self.config = config
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the provider connection.
        Returns True if successful.
        """
        pass

    @abstractmethod
    async def create_memory_store(self, agent_id: str, user_id: str) -> str:
        """
        Create a new memory store for an agent-user pair.
        Returns the store ID.
        """
        pass

    @abstractmethod
    async def delete_memory_store(self, store_id: str) -> bool:
        """Delete a memory store and all its contents."""
        pass

    @abstractmethod
    async def add_memory(
        self,
        store_id: str,
        memory: Memory
    ) -> str:
        """
        Add a memory to the store.
        Returns the memory ID.
        """
        pass

    @abstractmethod
    async def add_memories(
        self,
        store_id: str,
        memories: List[Memory]
    ) -> List[str]:
        """
        Batch add memories to the store.
        Returns list of memory IDs.
        """
        pass

    @abstractmethod
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
        Returns list of memories sorted by relevance.
        """
        pass

    @abstractmethod
    async def get_memory(self, store_id: str, memory_id: str) -> Optional[Memory]:
        """Get a specific memory by ID."""
        pass

    @abstractmethod
    async def update_memory(
        self,
        store_id: str,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update a memory's content and/or metadata."""
        pass

    @abstractmethod
    async def delete_memory(self, store_id: str, memory_id: str) -> bool:
        """Delete a specific memory."""
        pass

    @abstractmethod
    async def get_recent_memories(
        self,
        store_id: str,
        limit: int = 20,
        memory_types: Optional[List[MemoryType]] = None
    ) -> List[Memory]:
        """Get most recent memories (for conversation context)."""
        pass

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        pass

    @abstractmethod
    async def extract_facts(self, conversation: List[Dict[str, str]]) -> List[Memory]:
        """
        Extract facts/preferences from a conversation.
        Uses LLM to identify important information to remember.
        """
        pass

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def provider_name(self) -> str:
        return self.config.provider


# Provider registry for dynamic loading
_PROVIDERS: Dict[str, type] = {}


def register_provider(name: str):
    """Decorator to register a memory provider."""
    def decorator(cls):
        _PROVIDERS[name] = cls
        return cls
    return decorator


def get_provider(name: str) -> Optional[type]:
    """Get a provider class by name."""
    return _PROVIDERS.get(name)


def list_providers() -> List[str]:
    """List all registered provider names."""
    return list(_PROVIDERS.keys())
