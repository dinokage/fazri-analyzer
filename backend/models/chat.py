"""
Pydantic models for the chatbot feature
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """A single message in the conversation"""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., min_length=1, max_length=500, description="User's message")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID to continue a conversation")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context hints")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Show me anomalies in the library today",
                "conversation_id": None,
                "context": {"user_role": "admin"}
            }
        }


class ToolCall(BaseModel):
    """Represents a tool that was called during the conversation"""
    tool_name: str
    parameters: Dict[str, Any]
    result_summary: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str = Field(..., description="The assistant's response")
    conversation_id: str = Field(..., description="Conversation ID for continuing the conversation")
    tools_used: List[str] = Field(default_factory=list, description="List of tools that were called")
    data: Optional[Dict[str, Any]] = Field(None, description="Structured data from tool calls")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "response": "I found 3 anomalies in Library zones today...",
                "conversation_id": "conv-abc123",
                "tools_used": ["get_anomalies"],
                "data": {"anomalies": [], "count": 3},
                "metadata": {
                    "model": "claude-sonnet-4-20250514",
                    "tokens_used": 1250,
                    "processing_time_ms": 1340
                }
            }
        }


class ConversationState(BaseModel):
    """Model for storing conversation state in Redis"""
    conversation_id: str
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    tool_calls_count: int = 0
    context: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    error_code: str
    details: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Rate limit exceeded",
                "error_code": "RATE_LIMITED",
                "details": "Please wait 60 seconds before sending another message."
            }
        }
