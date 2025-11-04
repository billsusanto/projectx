from fastapi import WebSocket, APIRouter, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List, Optional
from pathlib import Path
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    ModelRequest, ModelResponse, UserPromptPart, TextPart, ModelMessage,
    ToolCallPart, ToolReturnPart, ThinkingPart, SystemPromptPart
)
from dataclasses import dataclass
import asyncio

from app.utils.logger import logger
from app.database import async_session, get_session
from app.models import Conversation, Message, ConversationRead, MessageRead, MessageRoleEnum
from app.services.connection_manager import manager

from app.tools import (
    read_file, write_file, edit_file, list_files, search_in_files,
    run_command, run_git_command, run_tests,
    get_working_directory, file_exists
)

router = APIRouter(
    prefix="/messaging",
    tags=["messaging"]
)

# SWE-bench evaluation directory - all file operations restricted to this directory
SANDBOX_DIR = Path("~/Documents/Projects/projectx/swe_bench_eval").expanduser().resolve()

# Dependency for streaming updates
@dataclass
class StreamingContext:
    websocket: WebSocket
    agent_message_id: int
    conversation_id: int

async def send_tool_update(websocket: WebSocket, message_id: int, tool_name: str, update_type: str, data: dict, conversation_id: int):
    """Send a tool update via WebSocket for UI status updates."""
    await websocket.send_json({
        "type": update_type,
        "message_id": message_id,
        "tool_name": tool_name,
        **data,
        "conversation_id": conversation_id,
    })

def validate_path_in_sandbox(file_path: str) -> Path:
    """
    Validate that a file path is within the sandbox directory.
    Returns the resolved absolute path if valid, raises ValueError if not.
    """
    try:
        resolved_path = Path(file_path).expanduser().resolve()

        # Check if the path is within sandbox (or is the sandbox itself)
        if resolved_path == SANDBOX_DIR or SANDBOX_DIR in resolved_path.parents or resolved_path.is_relative_to(SANDBOX_DIR):
            return resolved_path
        else:
            raise ValueError(
                f"Access denied: Path '{file_path}' is outside the allowed workspace.\n"
                f"All operations must be within: {SANDBOX_DIR}"
            )
    except Exception as e:
        raise ValueError(f"Invalid path '{file_path}': {str(e)}")

def estimate_token_count(message_history: List[ModelMessage]) -> int:
    """Estimate token count for message history.

    Uses a rough approximation: 1 token ≈ 4 characters for English text.
    This is conservative and works reasonably well for Claude models.
    """
    total_chars = 0
    for msg in message_history:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if hasattr(part, 'content') and part.content:
                    total_chars += len(str(part.content))
        elif isinstance(msg, ModelResponse):
            for part in msg.parts:
                if hasattr(part, 'content') and part.content:
                    total_chars += len(str(part.content))
                # Also count tool arguments and results
                if hasattr(part, 'args') and part.args:
                    total_chars += len(str(part.args))

    # Rough estimate: 1 token ≈ 4 characters
    estimated_tokens = total_chars // 4
    return estimated_tokens


async def summarize_history_if_needed(message_history: List[ModelMessage], token_threshold: int) -> List[ModelMessage]:
    """Summarize message history if token count exceeds threshold.

    Follows the pattern from: https://ai.pydantic.dev/message-history/#runcontext-parameter
    """
    if not message_history:
        return message_history

    token_count = estimate_token_count(message_history)
    logger.info(f"Message history token count: {token_count}")

    if token_count < token_threshold:
        return message_history

    logger.info(f"Token count ({token_count}) exceeds threshold ({token_threshold}), summarizing history...")

    # Create a summarization agent (simple, no tools needed for summarization)
    from pydantic_ai import Agent
    summarizer = Agent(
        'anthropic:claude-sonnet-4-5',
        output_type=str,
        system_prompt=(
            'You are a conversation summarizer. '
            'Given a conversation history, provide a concise summary that captures:\n'
            '1. Key topics discussed\n'
            '2. Important decisions or findings\n'
            '3. Current context and state\n'
            '4. Any unresolved issues or next steps\n\n'
            'Keep the summary focused and under 500 tokens.'
        )
    )

    # Convert history to a string representation for summarization
    history_text = []
    for msg in message_history:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if hasattr(part, 'content') and part.content:
                    history_text.append(f"User: {part.content}")
        elif isinstance(msg, ModelResponse):
            for part in msg.parts:
                if part.part_kind == 'text' and hasattr(part, 'content') and part.content:
                    history_text.append(f"Agent: {part.content}")
                elif part.part_kind == 'tool-call':
                    history_text.append(f"Tool called: {part.tool_name}")

    history_str = "\n\n".join(history_text[-50:])  # Last 50 messages to keep summary relevant

    # Generate summary
    summary_result = await summarizer.run(
        f"Summarize this conversation history:\n\n{history_str}"
    )
    summary = summary_result.output

    logger.info(f"Generated summary (length: {len(summary)})")

    # Replace old history with summary as a system message
    # Keep the last few messages for immediate context
    recent_messages = message_history[-5:] if len(message_history) > 5 else message_history

    # Create a summarized history: [summary] + [recent messages]
    from pydantic_ai.messages import SystemPromptPart
    summarized_history = [
        ModelRequest(parts=[SystemPromptPart(content=f"Previous conversation summary:\n{summary}")])
    ] + recent_messages

    new_token_count = estimate_token_count(summarized_history)
    logger.info(f"Reduced token count from {token_count} to {new_token_count}")

    return summarized_history


def convert_db_messages_to_history(db_messages: List[Message]) -> List[ModelMessage]:
    """Convert database messages to Pydantic AI message history format"""
    history = []

    for msg in db_messages:
        if msg.role == MessageRoleEnum.USER:
            history.append(
                ModelRequest(parts=[UserPromptPart(content=msg.content)])
            )
        elif msg.role == MessageRoleEnum.AGENT:
            # If parts are stored in database, reconstruct them
            if msg.parts and 'parts' in msg.parts:
                parts = []
                tool_call_ids = set()
                tool_return_ids = set()

                for part_dict in msg.parts['parts']:
                    part_kind = part_dict.get('part_kind')
                    if part_kind == 'text':
                        parts.append(TextPart(content=part_dict.get('content', '')))
                    elif part_kind == 'thinking':
                        parts.append(ThinkingPart(content=part_dict.get('content', '')))
                    elif part_kind == 'tool-call':
                        tool_call_id = part_dict.get('tool_call_id')
                        if tool_call_id:
                            tool_call_ids.add(tool_call_id)
                        parts.append(ToolCallPart(
                            tool_name=part_dict.get('tool_name', ''),
                            args=part_dict.get('args', {}),
                            tool_call_id=tool_call_id
                        ))
                    elif part_kind == 'tool-return':
                        tool_call_id = part_dict.get('tool_call_id')
                        if tool_call_id:
                            tool_return_ids.add(tool_call_id)
                        parts.append(ToolReturnPart(
                            tool_name=part_dict.get('tool_name', ''),
                            content=part_dict.get('content'),
                            tool_call_id=tool_call_id
                        ))

                # Validate: all tool calls must have returns
                unprocessed_calls = tool_call_ids - tool_return_ids
                if unprocessed_calls:
                    logger.warning(
                        f"Message {msg.id} has unprocessed tool calls: {unprocessed_calls}. "
                        f"Filtering out incomplete tool calls to maintain valid history.",
                        extra={
                            "message_id": msg.id,
                            "tool_calls": list(tool_call_ids),
                            "tool_returns": list(tool_return_ids),
                            "unprocessed": list(unprocessed_calls),
                            "parts_before_filter": len(parts)
                        }
                    )
                    # Filter out tool-call parts without returns
                    parts = [
                        p for p in parts
                        if not (isinstance(p, ToolCallPart) and p.tool_call_id in unprocessed_calls)
                    ]
                    logger.info(f"Parts after filtering: {len(parts)}")

                if parts:
                    history.append(ModelResponse(parts=parts))
                else:
                    # Fallback to content if parts parsing failed
                    history.append(ModelResponse(parts=[TextPart(content=msg.content)]))
            else:
                # Legacy: use content field
                history.append(ModelResponse(parts=[TextPart(content=msg.content)]))

    return history

# Initialize agent at module level with StreamingContext dependency
messagingAgent = Agent(
    'anthropic:claude-sonnet-4-5',
    output_type=str,
    deps_type=StreamingContext,
    model_settings={
        'thinking': {
            'type': 'enabled',
            'budget_tokens': 10000  # Allow up to 10k tokens for thinking
        }
    },
    system_prompt=(
        'You are AgentX, a software engineering AI agent specialized in solving SWE-bench tasks. '
        f'Your workspace is: {SANDBOX_DIR}\n\n'
        'IMPORTANT: All file operations must be within your workspace directory. '
        'You cannot access files outside this directory.\n\n'
        'You have access to file operations, system commands, and code analysis tools. '
        'When solving problems:\n'
        '1. Use list_files_tool and read_file_tool to understand the codebase\n'
        '2. Use search_in_files_tool to find relevant code\n'
        '3. Use edit_file_tool or write_file_tool to make changes\n'
        '4. Use run_tests_tool to verify your changes\n'
        '5. Use run_git_command_tool to check status and diffs\n\n'
        'Always explain your reasoning before taking action. '
        'Use relative paths from your workspace directory when possible.'
    ),
)

# Register file operation tools
@messagingAgent.tool
async def read_file_tool(ctx: RunContext[StreamingContext], file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """Read contents of a file within the workspace. Optionally specify line range."""
    try:
        await send_tool_update(
            ctx.deps.websocket,
            ctx.deps.agent_message_id,
            "read_file_tool",
            "tool_start",
            {"args": {"file_path": file_path, "start_line": start_line, "end_line": end_line}},
            ctx.deps.conversation_id
        )

        validate_path_in_sandbox(file_path)
        result = await read_file(file_path, start_line, end_line)
        output = f"File: {result.path}\nLines: {result.lines}\n\n{result.content}"

        await send_tool_update(
            ctx.deps.websocket,
            ctx.deps.agent_message_id,
            "read_file_tool",
            "tool_complete",
            {"result": output},
            ctx.deps.conversation_id
        )
        return output
    except ValueError as e:
        error_msg = f"Error: {str(e)}"
        await send_tool_update(
            ctx.deps.websocket,
            ctx.deps.agent_message_id,
            "read_file_tool",
            "tool_complete",
            {"result": error_msg},
            ctx.deps.conversation_id
        )
        return error_msg

@messagingAgent.tool
async def write_file_tool(ctx: RunContext[StreamingContext], file_path: str, content: str) -> str:
    """Write content to a file within the workspace. Creates parent directories if needed."""
    try:
        await ctx.deps.websocket.send_json({
            "type": "tool_start",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "write_file_tool",
            "args": {"file_path": file_path, "content": content[:100] + "..." if len(content) > 100 else content},
            "conversation_id": ctx.deps.conversation_id,
        })

        validate_path_in_sandbox(file_path)
        result = await write_file(file_path, content)

        await ctx.deps.websocket.send_json({
            "type": "tool_complete",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "write_file_tool",
            "result": result,
            "conversation_id": ctx.deps.conversation_id,
        })
        return result
    except ValueError as e:
        error_msg = f"Error: {str(e)}"
        await ctx.deps.websocket.send_json({
            "type": "tool_complete",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "write_file_tool",
            "result": error_msg,
            "conversation_id": ctx.deps.conversation_id,
        })
        return error_msg

@messagingAgent.tool
async def edit_file_tool(ctx: RunContext[StreamingContext], file_path: str, old_content: str, new_content: str) -> str:
    """Edit a file within the workspace by replacing old_content with new_content."""
    try:
        await ctx.deps.websocket.send_json({
            "type": "tool_start",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "edit_file_tool",
            "args": {"file_path": file_path, "old_content": old_content[:50] + "...", "new_content": new_content[:50] + "..."},
            "conversation_id": ctx.deps.conversation_id,
        })

        validate_path_in_sandbox(file_path)
        result = await edit_file(file_path, old_content, new_content)

        await ctx.deps.websocket.send_json({
            "type": "tool_complete",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "edit_file_tool",
            "result": result,
            "conversation_id": ctx.deps.conversation_id,
        })
        return result
    except ValueError as e:
        error_msg = f"Error: {str(e)}"
        await ctx.deps.websocket.send_json({
            "type": "tool_complete",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "edit_file_tool",
            "result": error_msg,
            "conversation_id": ctx.deps.conversation_id,
        })
        return error_msg

@messagingAgent.tool
async def list_files_tool(ctx: RunContext[StreamingContext], directory: str = ".", pattern: str = "*", recursive: bool = False) -> List[str]:
    """List files in a directory within the workspace matching a pattern."""
    try:
        # Send tool call notification
        await send_tool_update(
            ctx.deps.websocket,
            ctx.deps.agent_message_id,
            "list_files_tool",
            "tool_start",
            {"args": {"directory": directory, "pattern": pattern, "recursive": recursive}},
            ctx.deps.conversation_id
        )

        # Convert relative "." to the sandbox directory
        if directory == ".":
            directory = str(SANDBOX_DIR)
        else:
            validate_path_in_sandbox(directory)

        result = await list_files(directory, pattern, recursive)

        # Send tool completion notification with delay
        await send_tool_update(
            ctx.deps.websocket,
            ctx.deps.agent_message_id,
            "list_files_tool",
            "tool_complete",
            {"result": result},
            ctx.deps.conversation_id
        )

        return result
    except ValueError as e:
        error_result = [f"Error: {str(e)}"]
        await send_tool_update(
            ctx.deps.websocket,
            ctx.deps.agent_message_id,
            "list_files_tool",
            "tool_complete",
            {"result": error_result},
            ctx.deps.conversation_id
        )
        return error_result

@messagingAgent.tool
async def search_in_files_tool(ctx: RunContext[StreamingContext], pattern: str, directory: str = ".", file_pattern: str = "*.py") -> str:
    """Search for a text pattern in files within the workspace. Returns matching lines with context."""
    try:
        await ctx.deps.websocket.send_json({
            "type": "tool_start",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "search_in_files_tool",
            "args": {"pattern": pattern, "directory": directory, "file_pattern": file_pattern},
            "conversation_id": ctx.deps.conversation_id,
        })

        # Convert relative "." to the sandbox directory
        if directory == ".":
            directory = str(SANDBOX_DIR)
        else:
            validate_path_in_sandbox(directory)

        results = await search_in_files(pattern, directory, file_pattern)
        if not results:
            result = f"No matches found for '{pattern}'"
        else:
            output = []
            for file_path, matches in results.items():
                output.append(f"\n{file_path}:")
                for match in matches:
                    output.append(f"  Line {match['line_number']}: {match['content']}")
            result = "\n".join(output)

        await ctx.deps.websocket.send_json({
            "type": "tool_complete",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "search_in_files_tool",
            "result": result,
            "conversation_id": ctx.deps.conversation_id,
        })
        return result
    except ValueError as e:
        error_msg = f"Error: {str(e)}"
        await ctx.deps.websocket.send_json({
            "type": "tool_complete",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "search_in_files_tool",
            "result": error_msg,
            "conversation_id": ctx.deps.conversation_id,
        })
        return error_msg

@messagingAgent.tool
async def run_command_tool(ctx: RunContext[StreamingContext], command: str, cwd: Optional[str] = None, timeout: int = 60) -> str:
    """Execute a shell command within the workspace and return the output."""
    try:
        await send_tool_update(
            ctx.deps.websocket,
            ctx.deps.agent_message_id,
            "run_command_tool",
            "tool_start",
            {"args": {"command": command, "cwd": cwd, "timeout": timeout}},
            ctx.deps.conversation_id
        )

        # Default to sandbox directory if no cwd specified
        if cwd is None:
            cwd = str(SANDBOX_DIR)
        else:
            validate_path_in_sandbox(cwd)

        result = await run_command(command, cwd, timeout)
        output = f"Return code: {result.return_code}\n\nStdout:\n{result.stdout}\n\nStderr:\n{result.stderr}"

        await send_tool_update(
            ctx.deps.websocket,
            ctx.deps.agent_message_id,
            "run_command_tool",
            "tool_complete",
            {"result": output},
            ctx.deps.conversation_id
        )
        return output
    except ValueError as e:
        error_msg = f"Error: {str(e)}"
        await send_tool_update(
            ctx.deps.websocket,
            ctx.deps.agent_message_id,
            "run_command_tool",
            "tool_complete",
            {"result": error_msg},
            ctx.deps.conversation_id
        )
        return error_msg

@messagingAgent.tool
async def run_git_command_tool(ctx: RunContext[StreamingContext], git_command: str, cwd: Optional[str] = None) -> str:
    """Execute a git command (without 'git' prefix) within the workspace."""
    try:
        await ctx.deps.websocket.send_json({
            "type": "tool_start",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "run_git_command_tool",
            "args": {"git_command": git_command, "cwd": cwd},
            "conversation_id": ctx.deps.conversation_id,
        })

        # Default to sandbox directory if no cwd specified
        if cwd is None:
            cwd = str(SANDBOX_DIR)
        else:
            validate_path_in_sandbox(cwd)

        result = await run_git_command(git_command, cwd)

        await ctx.deps.websocket.send_json({
            "type": "tool_complete",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "run_git_command_tool",
            "result": result,
            "conversation_id": ctx.deps.conversation_id,
        })
        return result
    except ValueError as e:
        error_msg = f"Error: {str(e)}"
        await ctx.deps.websocket.send_json({
            "type": "tool_complete",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "run_git_command_tool",
            "result": error_msg,
            "conversation_id": ctx.deps.conversation_id,
        })
        return error_msg

@messagingAgent.tool
async def run_tests_tool(ctx: RunContext[StreamingContext], test_path: str = "tests/", cwd: Optional[str] = None) -> str:
    """Run pytest tests within the workspace and return results."""
    try:
        await ctx.deps.websocket.send_json({
            "type": "tool_start",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "run_tests_tool",
            "args": {"test_path": test_path, "cwd": cwd},
            "conversation_id": ctx.deps.conversation_id,
        })

        # Default to sandbox directory if no cwd specified
        if cwd is None:
            cwd = str(SANDBOX_DIR)
        else:
            validate_path_in_sandbox(cwd)

        result = await run_tests(test_path, cwd)
        output = f"Return code: {result.return_code}\n\n{result.stdout}\n\n{result.stderr}"

        await ctx.deps.websocket.send_json({
            "type": "tool_complete",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "run_tests_tool",
            "result": output,
            "conversation_id": ctx.deps.conversation_id,
        })
        return output
    except ValueError as e:
        error_msg = f"Error: {str(e)}"
        await ctx.deps.websocket.send_json({
            "type": "tool_complete",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "run_tests_tool",
            "result": error_msg,
            "conversation_id": ctx.deps.conversation_id,
        })
        return error_msg

@messagingAgent.tool
async def get_working_directory_tool(ctx: RunContext[StreamingContext]) -> str:
    """Get the workspace directory."""
    # Send tool call notification
    await send_tool_update(
        ctx.deps.websocket,
        ctx.deps.agent_message_id,
        "get_working_directory_tool",
        "tool_start",
        {"args": {}},
        ctx.deps.conversation_id
    )

    result = str(SANDBOX_DIR)

    # Send tool completion notification with delay
    await send_tool_update(
        ctx.deps.websocket,
        ctx.deps.agent_message_id,
        "get_working_directory_tool",
        "tool_complete",
        {"result": result},
        ctx.deps.conversation_id
    )

    return result

@messagingAgent.tool
async def file_exists_tool(ctx: RunContext[StreamingContext], file_path: str) -> bool:
    """Check if a file exists within the workspace."""
    try:
        await ctx.deps.websocket.send_json({
            "type": "tool_start",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "file_exists_tool",
            "args": {"file_path": file_path},
            "conversation_id": ctx.deps.conversation_id,
        })

        validate_path_in_sandbox(file_path)
        result = await file_exists(file_path)

        await ctx.deps.websocket.send_json({
            "type": "tool_complete",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "file_exists_tool",
            "result": result,
            "conversation_id": ctx.deps.conversation_id,
        })
        return result
    except ValueError as e:
        # Return False with error message as string (tools can't return complex types)
        await ctx.deps.websocket.send_json({
            "type": "tool_complete",
            "message_id": ctx.deps.agent_message_id,
            "tool_name": "file_exists_tool",
            "result": False,
            "conversation_id": ctx.deps.conversation_id,
        })
        return False

@router.websocket("/ws")
async def websocket_messaging_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    async with async_session() as session:
        try:
            while True:
                # Receive JSON message from client
                data = await websocket.receive_json()
            
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

                # Verify conversation exists
                conversation = await session.get(Conversation, conversation_id)
                if not conversation:
                    await websocket.send_json({"error": f"Conversation {conversation_id} not found"})
                    continue

                with logger.span(f"Conversation run"):

                    with logger.span("User message"):
                        # Save user message
                        user_message = Message(
                            content=content,
                            role=MessageRoleEnum.USER,
                            conversation_id=conversation_id
                        )

                        logger.info(f"user_message: : {user_message.content}")

                        session.add(user_message)
                        await session.commit()
                        await session.refresh(user_message)

                        logger.info(f"Saved user_message")

                        # Send user message back with parts format
                        await websocket.send_json({
                            "type": "message",
                            "id": user_message.id,
                            "parts": [{"part_kind": "user-prompt", "content": user_message.content}],
                            "role": "user",
                            "conversation_id": conversation_id,
                            "created_at": user_message.created_at.isoformat()
                        })

                    # Retrieve conversation history
                    history_result = await session.execute(
                        select(Message)
                        .where(Message.conversation_id == conversation_id)
                        .where(Message.id != user_message.id)
                        .order_by(Message.created_at)
                    )
                    previous_messages = history_result.scalars().all()
                    message_history = convert_db_messages_to_history(previous_messages)

                    # Summarize history if token count exceeds threshold (DISABLED FOR NOW)
                    # TOKEN_THRESHOLD = int(0.7 * 200_000)  # 140,000 tokens
                    # message_history = await summarize_history_if_needed(message_history, TOKEN_THRESHOLD)

                    with logger.span("Agent run"):
                        # Create agent message upfront to get an ID
                        agent_message = Message(
                            content="",  # Will be updated after completion
                            role=MessageRoleEnum.AGENT,
                            conversation_id=conversation_id
                        )
                        session.add(agent_message)
                        await session.commit()
                        await session.refresh(agent_message)

                        # Create streaming context for dependency injection
                        streaming_ctx = StreamingContext(
                            websocket=websocket,
                            agent_message_id=agent_message.id,
                            conversation_id=conversation_id
                        )

                        # Run agent with iter() for streaming control
                        from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart, ThinkingPart
                        from pydantic_ai._agent_graph import CallToolsNode
                        from pydantic_graph import End

                        # Track metadata
                        all_parts_for_db = []  # Complete parts with all metadata for database
                        latest_model_name = None
                        latest_timestamp = None
                        tool_calls_count = 0
                        thinking_blocks_count = 0
                        final_output = ""
                        sent_parts = set()  # Track which parts we've already sent

                        # Use iter() for step-by-step control
                        step_number = 0
                        async with messagingAgent.iter(
                            content,
                            message_history=message_history,
                            deps=streaming_ctx
                        ) as run:
                            while not isinstance(run.next_node, End):
                                node = await run.next(run.next_node)
                                step_number += 1

                                # Process CallToolsNode which contains model responses
                                if isinstance(node, CallToolsNode):
                                    response = node.model_response
                                    latest_model_name = response.model_name
                                    latest_timestamp = response.timestamp

                                    # Create a node_added message for this step
                                    node_message = {
                                        "type": "node_added",
                                        "node": {
                                            "id": f"step-{step_number}",
                                            "step": step_number,
                                            "parts": [],
                                            "model_name": latest_model_name,
                                            "timestamp": latest_timestamp.isoformat() if latest_timestamp else None,
                                        },
                                        "message_id": agent_message.id,
                                        "conversation_id": conversation_id,
                                    }

                                    # Add each part to this node
                                    for part in response.parts:
                                        part_key = f"{part.part_kind}-{id(part)}"

                                        if part_key in sent_parts:
                                            continue
                                        sent_parts.add(part_key)

                                        # Build part dict
                                        part_dict = {'part_kind': part.part_kind}

                                        if part.part_kind == 'user-prompt' or part.part_kind == 'system-prompt':
                                            continue

                                        if hasattr(part, 'content'):
                                            part_dict['content'] = part.content

                                        # Handle each part type
                                        if part.part_kind == 'text':
                                            part_dict['id'] = getattr(part, 'id', None)
                                            logger.info(f"Processing text part: id={part_dict['id']}, content_length={len(part_dict.get('content', ''))}, content={part_dict.get('content', '')}")

                                        elif part.part_kind == 'thinking':
                                            thinking_blocks_count += 1
                                            part_dict['provider_name'] = getattr(part, 'provider_name', None)
                                            part_dict['signature'] = getattr(part, 'signature', None)
                                            part_dict['id'] = getattr(part, 'id', None)
                                            logger.info(f"Processing thinking part: id={part_dict['id']}, provider={part_dict['provider_name']}, content_length={len(part_dict.get('content', ''))}")

                                        elif part.part_kind == 'tool-call':
                                            tool_calls_count += 1
                                            part_dict['tool_name'] = part.tool_name
                                            # Ensure args is a dict (it should be, but ensure it's JSON-serializable)
                                            part_dict['args'] = dict(part.args) if part.args else {}
                                            part_dict['tool_call_id'] = part.tool_call_id
                                            logger.info(f"Processing tool-call part: tool_name={part_dict['tool_name']}, tool_call_id={part_dict['tool_call_id']}, args={part_dict['args']}")

                                        elif part.part_kind == 'tool-return':
                                            part_dict['tool_name'] = part.tool_name
                                            # Ensure content is JSON-serializable
                                            if isinstance(part.content, (list, dict)):
                                                import json
                                                part_dict['content'] = json.dumps(part.content)
                                            elif part.content is None:
                                                part_dict['content'] = None
                                            else:
                                                part_dict['content'] = str(part.content)
                                            part_dict['tool_call_id'] = part.tool_call_id
                                            logger.info(f"Processing tool-return part: tool_name={part_dict['tool_name']}, tool_call_id={part_dict['tool_call_id']}, content_type={type(part.content).__name__}")

                                        # Exclude tool parts from node_added (they're sent via tool_start/tool_complete)
                                        if part.part_kind not in ['tool-call', 'tool-return']:
                                            node_message["node"]["parts"].append(part_dict)

                                        # Save all parts to database
                                        all_parts_for_db.append(part_dict)

                                    # Send the complete node with all its parts
                                    if node_message["node"]["parts"]:
                                        await websocket.send_json(node_message)

                            # Get final result - extract the actual output string from AgentRunResult
                            final_output = run.result.output if hasattr(run.result, 'output') else str(run.result)

                        # All parts already sent during iteration
                        # Update agent message with final output AND parts
                        agent_message.content = final_output
                        agent_message.parts = {
                            "parts": all_parts_for_db,
                            "model_name": latest_model_name,
                            "timestamp": latest_timestamp.isoformat() if latest_timestamp else None
                        }
                        session.add(agent_message)
                        await session.commit()

                        # Summary logging
                        logger.info(
                            f"Agent response summary: {len(all_parts_for_db)} parts, {tool_calls_count} tool calls, {thinking_blocks_count} thinking blocks",
                            extra={
                                "total_parts": len(all_parts_for_db),
                                "tool_calls_count": tool_calls_count,
                                "thinking_blocks_count": thinking_blocks_count,
                                "part_kinds": [p['part_kind'] for p in all_parts_for_db],
                                "conversation_id": conversation_id,
                                "model_name": latest_model_name
                            }
                        )

                    # Send completion message
                    await websocket.send_json({
                        "type": "message_complete",
                        "id": agent_message.id,
                        "role": "agent",
                        "model_name": latest_model_name,
                        "timestamp": latest_timestamp.isoformat() if latest_timestamp else None,
                        "conversation_id": conversation_id,
                        "created_at": agent_message.created_at.isoformat()
                    })

        except WebSocketDisconnect:
            logger.info("Client disconnected")
            manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"Error in WebSocket: {e}", exc_info=True)

            # Try to send error message to client
            try:
                await websocket.send_json({
                    "type": "error",
                    "error": str(e),
                    "conversation_id": conversation_id if 'conversation_id' in locals() else None
                })
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")

            # If we have an incomplete agent_message, clean it up
            if 'agent_message' in locals() and 'session' in locals():
                try:
                    # Rollback any uncommitted changes
                    await session.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback session: {rollback_error}")

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
