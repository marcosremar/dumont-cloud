"""
Memory API Endpoints for Agent Memory Management.

Provides REST API for:
- Creating/managing memory stores
- Adding and retrieving memories
- Searching memories semantically
- Getting context for agent conversations
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from ....services.memory import MemoryManager, MemoryConfig, Memory, MemoryType
from ....services.memory.manager import get_memory_manager, initialize_memory_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["Memory"])


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateStoreRequest(BaseModel):
    """Request to create a memory store."""
    agent_id: str = Field(..., description="Agent ID")
    user_id: str = Field(..., description="User ID")


class CreateStoreResponse(BaseModel):
    """Response with created store ID."""
    store_id: str
    agent_id: str
    user_id: str
    created_at: str


class AddMemoryRequest(BaseModel):
    """Request to add a memory."""
    content: str = Field(..., description="Memory content")
    memory_type: str = Field("conversation", description="Type: conversation, fact, episodic")
    role: Optional[str] = Field(None, description="Role for conversation: user, assistant")
    confidence: float = Field(1.0, ge=0, le=1, description="Confidence score")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AddConversationRequest(BaseModel):
    """Request to add conversation messages."""
    messages: List[Dict[str, str]] = Field(..., description="List of {role, content} messages")
    extract_facts: bool = Field(True, description="Auto-extract facts from conversation")


class SearchRequest(BaseModel):
    """Request to search memories."""
    query: str = Field(..., description="Search query")
    memory_types: Optional[List[str]] = Field(None, description="Filter by types")
    limit: int = Field(10, ge=1, le=50, description="Max results")


class GetContextRequest(BaseModel):
    """Request to get context for a query."""
    query: str = Field(..., description="Current user query")
    include_recent: bool = Field(True, description="Include recent messages")
    include_facts: bool = Field(True, description="Include user facts")
    max_memories: int = Field(10, ge=1, le=20, description="Max memories to retrieve")


class MemoryResponse(BaseModel):
    """Response with memory data."""
    id: str
    content: str
    memory_type: str
    role: Optional[str] = None
    confidence: float = 1.0
    created_at: str
    metadata: Optional[Dict[str, Any]] = None


class ContextResponse(BaseModel):
    """Response with context for agent."""
    relevant_memories: List[Dict[str, Any]]
    facts: List[Dict[str, Any]]
    recent_messages: List[Dict[str, Any]]
    formatted_prompt: Optional[str] = None


class MemoryConfigRequest(BaseModel):
    """Configuration for memory provider."""
    provider: str = Field("gcp", description="Provider: gcp, pinecone, chroma")
    gcp_project_id: Optional[str] = Field(None, description="GCP project ID")
    gcp_location: str = Field("us-central1", description="GCP location")
    embedding_model: str = Field("text-embedding-004", description="Embedding model")
    similarity_threshold: float = Field(0.7, ge=0, le=1, description="Min similarity")


# =============================================================================
# Dependency: Get initialized MemoryManager
# =============================================================================

async def get_manager() -> MemoryManager:
    """Get the memory manager, initializing if needed."""
    manager = get_memory_manager()
    if not manager.is_initialized:
        # Try to initialize with default GCP config
        success = await manager.initialize()
        if not success:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory service not initialized. Configure GCP credentials."
            )
    return manager


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/initialize")
async def initialize_memory(config: Optional[MemoryConfigRequest] = None):
    """
    Initialize the memory service with a provider configuration.

    If no config is provided, uses GCP with default settings.
    Requires GCP credentials to be configured (GOOGLE_APPLICATION_CREDENTIALS).
    """
    try:
        mem_config = None
        if config:
            mem_config = MemoryConfig(
                provider=config.provider,
                gcp_project_id=config.gcp_project_id,
                gcp_location=config.gcp_location,
                embedding_model=config.embedding_model,
                similarity_threshold=config.similarity_threshold,
            )

        success = await initialize_memory_manager(mem_config)

        if success:
            return {
                "success": True,
                "message": f"Memory service initialized with {config.provider if config else 'gcp'} provider"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize memory service"
            )
    except Exception as e:
        logger.error(f"Failed to initialize memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/status")
async def memory_status():
    """Check memory service status."""
    manager = get_memory_manager()
    return {
        "initialized": manager.is_initialized,
        "provider": manager._config.provider if manager._config else None,
    }


@router.post("/stores", response_model=CreateStoreResponse)
async def create_memory_store(
    request: CreateStoreRequest,
    manager: MemoryManager = Depends(get_manager)
):
    """
    Create a memory store for an agent-user pair.

    Each agent-user combination gets a unique store for their conversation
    history and extracted facts.
    """
    try:
        store_id = await manager.create_store(request.agent_id, request.user_id)
        return CreateStoreResponse(
            store_id=store_id,
            agent_id=request.agent_id,
            user_id=request.user_id,
            created_at=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Failed to create store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/stores/{store_id}")
async def delete_memory_store(
    store_id: str,
    manager: MemoryManager = Depends(get_manager)
):
    """Delete a memory store and all its contents."""
    success = await manager.delete_store(store_id)
    if success:
        return {"success": True, "message": f"Store {store_id} deleted"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Store {store_id} not found"
    )


@router.post("/stores/{store_id}/memories")
async def add_memory(
    store_id: str,
    request: AddMemoryRequest,
    manager: MemoryManager = Depends(get_manager)
):
    """Add a single memory to a store."""
    try:
        if request.memory_type == "fact":
            memory_id = await manager.add_fact(
                store_id,
                request.content,
                confidence=request.confidence,
                metadata=request.metadata,
            )
        else:
            # Create memory object
            memory = Memory(
                content=request.content,
                memory_type=MemoryType(request.memory_type),
                role=request.role,
                confidence=request.confidence,
                metadata=request.metadata or {},
            )
            memory_id = await manager._provider.add_memory(store_id, memory)

        return {"memory_id": memory_id}
    except Exception as e:
        logger.error(f"Failed to add memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/stores/{store_id}/conversation")
async def add_conversation(
    store_id: str,
    request: AddConversationRequest,
    manager: MemoryManager = Depends(get_manager)
):
    """
    Add conversation messages to memory.

    Optionally extracts facts/preferences from the conversation.
    """
    try:
        memory_ids = await manager.add_conversation(
            store_id,
            request.messages,
            extract_facts=request.extract_facts,
        )
        return {
            "memory_ids": memory_ids,
            "count": len(memory_ids),
        }
    except Exception as e:
        logger.error(f"Failed to add conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/stores/{store_id}/search", response_model=List[MemoryResponse])
async def search_memories(
    store_id: str,
    request: SearchRequest,
    manager: MemoryManager = Depends(get_manager)
):
    """
    Search memories by semantic similarity.

    Returns memories most relevant to the query.
    """
    try:
        results = await manager.search(
            store_id,
            request.query,
            memory_types=request.memory_types,
            limit=request.limit,
        )
        return [
            MemoryResponse(
                id=m["id"],
                content=m["content"],
                memory_type=m["memory_type"],
                role=m.get("role"),
                confidence=m.get("confidence", 1.0),
                created_at=m["created_at"],
                metadata=m.get("metadata"),
            )
            for m in results
        ]
    except Exception as e:
        logger.error(f"Failed to search memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/stores/{store_id}/context", response_model=ContextResponse)
async def get_context(
    store_id: str,
    request: GetContextRequest,
    manager: MemoryManager = Depends(get_manager)
):
    """
    Get context for an agent query.

    Returns relevant memories, facts, and recent messages
    to be injected into the agent's system prompt.
    """
    try:
        context = await manager.get_context(
            store_id,
            request.query,
            include_recent=request.include_recent,
            include_facts=request.include_facts,
            max_memories=request.max_memories,
        )

        # Also get formatted prompt
        formatted = await manager.format_context_for_prompt(store_id, request.query)

        return ContextResponse(
            relevant_memories=context["relevant_memories"],
            facts=context["facts"],
            recent_messages=context["recent_messages"],
            formatted_prompt=formatted if formatted else None,
        )
    except Exception as e:
        logger.error(f"Failed to get context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/stores/{store_id}/memories/{memory_id}")
async def delete_memory(
    store_id: str,
    memory_id: str,
    manager: MemoryManager = Depends(get_manager)
):
    """Delete a specific memory."""
    success = await manager.delete_memory(store_id, memory_id)
    if success:
        return {"success": True}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Memory {memory_id} not found"
    )


@router.delete("/stores/{store_id}/conversations")
async def clear_conversations(
    store_id: str,
    manager: MemoryManager = Depends(get_manager)
):
    """Clear conversation history while keeping facts."""
    count = await manager.clear_conversations(store_id)
    return {
        "success": True,
        "deleted_count": count,
    }
