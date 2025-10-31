from fastapi import WebSocket, APIRouter, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart, ModelMessage

from app.utils.logger import logger
from app.database import async_session, get_session
from app.models import Conversation, Message, ConversationRead, MessageRead, MessageRoleEnum
from app.services.connection_manager import manager

router = APIRouter(
    prefix="/messaging",
    tags=["messaging"]
)

@router.websocket("/ws")
async def websocket_messaging_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    async with async_session() as session:
        try:
            while True:
                # Receive JSON message from client
                data = await websocket.receive_json()
                with logger.span(f"Received: {data}"):

                    content = data.get("content")
                    conversation_id = data.get("conversation_id")

                    if not content:
                        await websocket.send_json({"error": "Message content is required"})
                        continue

                    # Auto-create conversation on first message
                    if not conversation_id:
                        new_conversation = Conversation(title="New Conversation")
                        session.add(new_conversation)
                        await session.commit()
                        await session.refresh(new_conversation)

                        conversation_id = new_conversation.id
                        logger.info(f"Created new conversation: conversation_id: {conversation_id}")

                        # Send conversation_id back to client
                        await websocket.send_json({
                            "type": "conversation_created",
                            "conversation_id": conversation_id
                        })

                    messagingAgent = Agent(
                        'anthropic:claude-sonnet-4-5',
                        output_type=str,
                        system_prompt='You are AgentX, part of ProjectX, a single agent and project that can handle anything the user requests.',
                    )

                    # Verify conversation exists
                    conversation = await session.get(Conversation, conversation_id)
                    if not conversation:
                        await websocket.send_json({"error": f"Conversation {conversation_id} not found"})
                        continue

                    # Save user message
                    user_message = Message(
                        content=content,
                        role=MessageRoleEnum.USER,
                        conversation_id=conversation_id
                    )
                    session.add(user_message)
                    await session.commit()
                    await session.refresh(user_message)

                    logger.info(f"Saved user message: {user_message.content}")

                    # Send user message back
                    await websocket.send_json({
                        "type": "message",
                        "id": user_message.id,
                        "content": user_message.content,
                        "role": "user",
                        "conversation_id": conversation_id,
                        "created_at": user_message.created_at.isoformat()
                    })

                    # Generate agent response
                    agent_response = await messagingAgent.run(content)

                    # Save agent message
                    agent_message = Message(
                        content=agent_response.output,
                        role=MessageRoleEnum.AGENT,
                        conversation_id=conversation_id
                    )
                    session.add(agent_message)
                    await session.commit()
                    await session.refresh(agent_message)

                    logger.info(f"Agent response: {agent_response.all_messages()}")

                    # Send agent message
                    await websocket.send_json({
                        "type": "message",
                        "id": agent_message.id,
                        "content": agent_message.content,
                        "role": "agent",
                        "conversation_id": conversation_id,
                        "created_at": agent_message.created_at.isoformat()
                    })

        except WebSocketDisconnect:
            logger.info("Client disconnected")
            manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"Error in WebSocket: {e}")
            manager.disconnect(websocket)


@router.get("/conversations", response_model=List[ConversationRead])
async def get_conversations(session: AsyncSession = Depends(get_session)):
    """Get all conversations"""
    result = await session.execute(select(Conversation))
    conversations = result.scalars().all()
    return conversations


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageRead])
async def get_conversation_history(
    conversation_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get all messages in a conversation"""
    conversation = await session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    return messages


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Delete a conversation"""
    conversation = await session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await session.delete(conversation)
    await session.commit()

    return {"message": f"Conversation {conversation_id} deleted"}
