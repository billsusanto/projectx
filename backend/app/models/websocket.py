"""Pydantic models for WebSocket message types."""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel
from enum import Enum
from app.models.conversation import MessageRoleEnum


class PartKind(str, Enum):
    """Types of message parts."""
    TEXT = "text"
    THINKING = "thinking"
    TOOL_CALL = "tool-call"
    TOOL_RETURN = "tool-return"
    USER_PROMPT = "user-prompt"
    SYSTEM_PROMPT = "system-prompt"


class ToolStatus(str, Enum):
    """Status of tool execution."""
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


class MessagePartBase(BaseModel):
    """Base model for message parts."""
    part_kind: PartKind
    content: Optional[str] = None

    # Thinking-specific fields
    provider_name: Optional[str] = None
    signature: Optional[str] = None
    id: Optional[str] = None

    # Tool-specific fields
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    status: Optional[ToolStatus] = None
    error_message: Optional[str] = None


class NodeData(BaseModel):
    """Data structure for node_added message."""
    id: str
    step: int
    parts: List[MessagePartBase]
    model_name: Optional[str] = None
    timestamp: Optional[str] = None


class ConversationCreatedMessage(BaseModel):
    """Message sent when a new conversation is created."""
    type: Literal["conversation_created"]
    conversation_id: int


class MessageMessage(BaseModel):
    """Full message with all parts."""
    type: Literal["message"]
    id: int
    parts: List[MessagePartBase]
    role: MessageRoleEnum
    conversation_id: int
    created_at: str
    model_name: Optional[str] = None
    timestamp: Optional[str] = None


class MessagePartMessage(BaseModel):
    """Individual message part (for streaming)."""
    type: Literal["message_part"]
    message_id: int
    part: MessagePartBase
    role: MessageRoleEnum
    conversation_id: int


class NodeAddedMessage(BaseModel):
    """Message indicating a new node was added to the execution graph."""
    type: Literal["node_added"]
    message_id: int
    node: NodeData
    conversation_id: int


class TextChunkMessage(BaseModel):
    """Streaming text chunk."""
    type: Literal["text_chunk"]
    message_id: int
    chunk: str
    role: MessageRoleEnum
    conversation_id: int


class MessageCompleteMessage(BaseModel):
    """Message indicating a message is complete."""
    type: Literal["message_complete"]
    id: int
    role: MessageRoleEnum
    conversation_id: int
    created_at: str
    model_name: Optional[str] = None
    timestamp: Optional[str] = None


class ToolStartMessage(BaseModel):
    """Message indicating a tool execution has started."""
    type: Literal["tool_start"]
    message_id: int
    tool_name: str
    args: Dict[str, Any]
    conversation_id: int


class ToolCompleteMessage(BaseModel):
    """Message indicating a tool execution has completed."""
    type: Literal["tool_complete"]
    message_id: int
    tool_name: str
    result: Any
    conversation_id: int
    status: ToolStatus = ToolStatus.SUCCESS  # Tool execution status
    error_message: Optional[str] = None  # Detailed error message if status is ERROR


class ErrorMessage(BaseModel):
    """Error message."""
    type: Literal["error"]
    error: str
    conversation_id: Optional[int] = None


# Union type of all WebSocket messages
WebSocketMessage = Union[
    ConversationCreatedMessage,
    MessageMessage,
    MessagePartMessage,
    NodeAddedMessage,
    TextChunkMessage,
    MessageCompleteMessage,
    ToolStartMessage,
    ToolCompleteMessage,
    ErrorMessage,
]
