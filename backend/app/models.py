from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from typing import Optional, List, Literal
from enum import Enum
from sqlalchemy import Column, DateTime, func

class PriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class MessageRoleEnum(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

class TodoBase(SQLModel):
    title: str = Field(max_length=200, index=True)
    description: Optional[str] = Field(default=None)
    completed: bool = Field(default=False)
    priority: Optional[PriorityEnum] = Field(default=None)
    due_date: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

class Todo(TodoBase, table=True):
    __tablename__ = "todos"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )

class TodoCreate(TodoBase):
    pass

class TodoUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None)
    completed: Optional[bool] = Field(default=None)
    priority: Optional[PriorityEnum] = Field(default=None)
    due_date: Optional[datetime] = Field(default=None)

class TodoRead(TodoBase):
    id: int
    created_at: datetime
    updated_at: datetime

class ConversationBase(SQLModel):
    title: str = Field(max_length=200, default="New Chat")

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
    content: str = Field(min_length=1, max_length=5000)
    role: MessageRoleEnum
    conversation_id: int = Field(foreign_key="conversations.id")

class Message(MessageBase, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    conversation: Optional[Conversation] = Relationship(back_populates="messages")

class MessageCreate(SQLModel):
    content: str = Field(min_length=1, max_length=5000)
    conversation_id: Optional[int] = None

class MessageRead(MessageBase):
    id: int
    created_at: datetime