"""
Chat API routes for the Fazri Analyzer chatbot.
Provides endpoints for conversational AI interactions using Gemini.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import logging
import redis

from models.chat import ChatRequest, ChatResponse, ErrorResponse
from services.chatbot.orchestrator import ChatOrchestrator
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chatbot"])

# Redis client for conversation state
_redis_client = None


def get_redis_client():
    """Get or create Redis client"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True
            )
            # Test connection
            _redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {str(e)}. Conversation history will not be persisted.")
            _redis_client = None
    return _redis_client


def get_chat_orchestrator() -> ChatOrchestrator:
    """Dependency to get ChatOrchestrator instance"""
    if not settings.CHATBOT_ENABLED:
        raise HTTPException(status_code=503, detail="Chatbot is currently disabled")

    if not settings.GOOGLE_API_KEY:
        raise HTTPException(status_code=503, detail="Chatbot is not configured (missing API key)")

    return ChatOrchestrator(
        neo4j_uri=settings.NEO4J_URI,
        neo4j_user=settings.NEO4J_USER,
        neo4j_password=settings.NEO4J_PASSWORD,
        redis_client=get_redis_client()
    )


@router.post(
    "/message",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Service unavailable"}
    },
    summary="Send a chat message",
    description="Send a natural language message to the chatbot and receive a response. The chatbot can query campus data including anomalies, occupancy, entity locations, and more."
)
async def send_message(
    request: ChatRequest,
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator)
):
    """
    Send a message to the chatbot.

    The chatbot uses Gemini with function calling to:
    - Query anomaly data
    - Check zone occupancy
    - Search for entities (people)
    - Get entity locations
    - Get zone activity summaries
    - Get entity activity timelines

    Example queries:
    - "Show me critical anomalies today"
    - "How many people are in the library?"
    - "Where is John Smith?"
    - "What happened in Lab 101 this morning?"
    """
    try:
        result = await orchestrator.process_message(
            message=request.message,
            conversation_id=request.conversation_id,
            context=request.context
        )

        return ChatResponse(
            response=result["response"],
            conversation_id=result["conversation_id"],
            tools_used=result["tools_used"],
            data=result["data"],
            metadata=result["metadata"]
        )

    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )


@router.delete(
    "/conversation/{conversation_id}",
    summary="Clear conversation history",
    description="Clear the conversation history for a specific conversation ID"
)
async def clear_conversation(
    conversation_id: str,
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator)
):
    """Clear conversation history for the given conversation ID"""
    success = await orchestrator.clear_conversation(conversation_id)

    if success:
        return {"message": "Conversation cleared", "conversation_id": conversation_id}
    else:
        return {"message": "No conversation found or Redis not available", "conversation_id": conversation_id}


@router.get(
    "/health",
    summary="Check chatbot health",
    description="Check if the chatbot service is healthy and properly configured"
)
async def health_check():
    """Health check endpoint for the chatbot service"""
    use_vertex = settings.USE_VERTEX_AI

    health_status = {
        "status": "healthy",
        "chatbot_enabled": settings.CHATBOT_ENABLED,
        "model": settings.CHATBOT_MODEL,
        "backend": "vertex_ai" if use_vertex else "google_ai_studio",
        "api_key_configured": bool(settings.VERTEX_PROJECT_ID) if use_vertex else bool(settings.GOOGLE_API_KEY),
        "redis_connected": False
    }

    if use_vertex:
        health_status["vertex_project"] = settings.VERTEX_PROJECT_ID
        health_status["vertex_location"] = settings.VERTEX_LOCATION

    # Check Redis connection
    redis_client = get_redis_client()
    if redis_client:
        try:
            redis_client.ping()
            health_status["redis_connected"] = True
        except Exception:
            pass

    # Overall status
    if not settings.CHATBOT_ENABLED:
        health_status["status"] = "disabled"
    elif use_vertex and not settings.VERTEX_PROJECT_ID:
        health_status["status"] = "misconfigured (missing VERTEX_PROJECT_ID)"
    elif not use_vertex and not settings.GOOGLE_API_KEY:
        health_status["status"] = "misconfigured (missing GOOGLE_API_KEY)"

    return health_status


@router.get(
    "/tools",
    summary="List available tools",
    description="List all tools available to the chatbot for querying data"
)
async def list_tools():
    """List all available tools that the chatbot can use"""
    from services.chatbot.tools import TOOL_DEFINITIONS

    tools_summary = []
    for tool in TOOL_DEFINITIONS:
        tools_summary.append({
            "name": tool["name"],
            "description": tool["description"],
            "parameters": list(tool["parameters"].get("properties", {}).keys())
        })

    return {
        "tools": tools_summary,
        "count": len(tools_summary)
    }
