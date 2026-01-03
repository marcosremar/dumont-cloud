"""
Agents API Endpoints - Create and manage AI agents with memory support.

This module provides:
- CRUD operations for agents
- Memory integration for agents
- Agent configuration management
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json

# In-memory storage (replace with database in production)
_agents_store: Dict[str, Dict[str, Any]] = {}

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Agents"])


# =============================================================================
# Request/Response Models
# =============================================================================

class MemoryConfigRequest(BaseModel):
    """Memory configuration for an agent."""
    enabled: bool = Field(True, description="Enable memory for this agent")
    provider: str = Field("gcp", description="Memory provider: gcp, mock, pinecone, chroma")


class AgentConfigRequest(BaseModel):
    """Agent configuration."""
    model: str = Field(..., description="Model ID (e.g., openai/gpt-4o)")
    instructions: Optional[str] = Field(None, description="System prompt")
    tools: List[str] = Field(default_factory=list, description="Enabled tools")
    functions: List[Dict[str, Any]] = Field(default_factory=list, description="Custom functions")
    params: Optional[Dict[str, Any]] = Field(None, description="Model parameters")
    response_format: str = Field("text", description="Response format: text, json")


class CreateAgentRequest(BaseModel):
    """Request to create a new agent."""
    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    description: Optional[str] = Field(None, max_length=500, description="Agent description")
    config: AgentConfigRequest
    memory: Optional[MemoryConfigRequest] = Field(None, description="Memory configuration")


class AgentResponse(BaseModel):
    """Response with agent data."""
    id: str
    name: str
    description: Optional[str]
    config: Dict[str, Any]
    memory: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str


class ChatRequest(BaseModel):
    """Request for agent chat."""
    message: str = Field(..., description="User message")
    user_id: str = Field(..., description="User ID for memory")
    include_memory: bool = Field(True, description="Include memory context")


class ChatResponse(BaseModel):
    """Response from agent chat."""
    response: str
    memory_context: Optional[Dict[str, Any]] = None
    memories_added: int = 0


# =============================================================================
# Helper Functions
# =============================================================================

async def get_or_create_memory_store(agent_id: str, user_id: str, provider: str = "mock") -> Optional[str]:
    """Get or create a memory store for agent-user pair."""
    try:
        from ....services.memory import MemoryManager, MemoryConfig
        from ....services.memory.manager import get_memory_manager, initialize_memory_manager

        manager = get_memory_manager()

        # Initialize if needed
        if not manager.is_initialized:
            config = MemoryConfig(provider=provider)
            await initialize_memory_manager(config)
            manager = get_memory_manager()

        # Create store
        store_id = await manager.create_store(agent_id, user_id)
        return store_id

    except Exception as e:
        logger.error(f"Failed to create memory store: {e}")
        return None


# =============================================================================
# Endpoints
# =============================================================================

@router.post("", response_model=AgentResponse)
async def create_agent(request: CreateAgentRequest):
    """
    Create a new AI agent.

    If memory is enabled, initializes a memory store for the agent.
    """
    agent_id = f"agent_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()

    agent_data = {
        "id": agent_id,
        "name": request.name,
        "description": request.description,
        "config": request.config.model_dump(),
        "memory": request.memory.model_dump() if request.memory else None,
        "created_at": now,
        "updated_at": now,
    }

    # Store agent
    _agents_store[agent_id] = agent_data

    logger.info(f"Created agent: {agent_id} (memory: {request.memory.enabled if request.memory else False})")

    return AgentResponse(**agent_data)


@router.get("", response_model=List[AgentResponse])
async def list_agents():
    """List all agents."""
    return [AgentResponse(**agent) for agent in _agents_store.values()]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get a specific agent."""
    if agent_id not in _agents_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    return AgentResponse(**_agents_store[agent_id])


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent."""
    if agent_id not in _agents_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    del _agents_store[agent_id]
    return {"success": True, "message": f"Agent {agent_id} deleted"}


@router.post("/{agent_id}/chat", response_model=ChatResponse)
async def chat_with_agent(agent_id: str, request: ChatRequest):
    """
    Chat with an agent.

    If memory is enabled:
    1. Retrieves relevant context from memory
    2. Includes context in the prompt
    3. Saves the conversation to memory
    """
    if agent_id not in _agents_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    agent = _agents_store[agent_id]
    memory_config = agent.get("memory")
    memory_context = None
    memories_added = 0

    # Get memory context if enabled
    if memory_config and memory_config.get("enabled") and request.include_memory:
        try:
            from ....services.memory.manager import get_memory_manager

            # Get or create store (this initializes the manager if needed)
            store_id = await get_or_create_memory_store(
                agent_id,
                request.user_id,
                memory_config.get("provider", "mock")
            )

            if store_id:
                manager = get_memory_manager()

                # Get context for the message
                memory_context = await manager.get_context(
                    store_id,
                    request.message,
                    include_recent=True,
                    include_facts=True,
                )

                # Add this conversation to memory
                messages = [
                    {"role": "user", "content": request.message},
                ]
                memory_ids = await manager.add_conversation(
                    store_id,
                    messages,
                    extract_facts=True
                )
                memories_added = len(memory_ids)

        except Exception as e:
            logger.error(f"Memory error: {e}")

    # Build response (in production, this would call the LLM)
    # For now, return a mock response showing memory integration
    response_text = f"[Agent {agent['name']}] Received your message."

    if memory_context:
        facts = memory_context.get("facts", [])
        recent = memory_context.get("recent_messages", [])
        if facts:
            response_text += f" I remember {len(facts)} facts about you."
        if recent:
            response_text += f" We've had {len(recent)} recent exchanges."

    return ChatResponse(
        response=response_text,
        memory_context=memory_context,
        memories_added=memories_added,
    )


@router.get("/{agent_id}/memory/{user_id}")
async def get_agent_memory(agent_id: str, user_id: str):
    """
    Get memory context for a specific agent-user pair.

    Useful for debugging and viewing stored memories.
    """
    if agent_id not in _agents_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    agent = _agents_store[agent_id]
    memory_config = agent.get("memory")

    if not memory_config or not memory_config.get("enabled"):
        return {"message": "Memory not enabled for this agent", "memories": []}

    try:
        from ....services.memory.manager import get_memory_manager

        manager = get_memory_manager()
        if not manager.is_initialized:
            return {"message": "Memory service not initialized", "memories": []}

        store_id = await get_or_create_memory_store(
            agent_id,
            user_id,
            memory_config.get("provider", "mock")
        )

        if store_id:
            recent = await manager._provider.get_recent_memories(store_id, limit=50)
            return {
                "store_id": store_id,
                "memory_count": len(recent),
                "memories": [m.to_dict() for m in recent]
            }

    except Exception as e:
        logger.error(f"Failed to get memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
