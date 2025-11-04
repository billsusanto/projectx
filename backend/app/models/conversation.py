from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from typing import Optional, List, Any, Dict
from enum import Enum
from sqlalchemy import Column, DateTime, JSON, func

class MessageRoleEnum(str, Enum):
    USER = "USER"
    AGENT = "AGENT"

class ConversationBase(SQLModel):
    title: str = Field(max_length=200, default="New Conversation")

class Conversation(ConversationBase, table=True):
    __tablename__ = "conversations"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )

    messages: List["Message"] = Relationship(back_populates="conversation")

class ConversationCreate(ConversationBase):
    pass

class ConversationRead(ConversationBase):
    id: int
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = None

class MessageBase(SQLModel):
    content: str = Field(min_length=1, max_length=25_000)
    role: MessageRoleEnum
    conversation_id: int = Field(foreign_key="conversations.id")
    parts: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON, nullable=True))

class Message(MessageBase, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    conversation: Optional[Conversation] = Relationship(back_populates="messages")

class MessageCreate(SQLModel):
    content: str = Field(min_length=1, max_length=25_000)
    conversation_id: Optional[int] = None
    parts: Optional[Dict[str, Any]] = None

class MessageRead(MessageBase):
    id: int
    created_at: datetime
    parts: Optional[Dict[str, Any]] = None
