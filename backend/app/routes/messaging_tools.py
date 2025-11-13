"""
Agent tool wrappers for the messaging agent.

This module contains all the @messagingAgent.tool decorated functions
that wrap the core tool implementations from app.tools with:
- WebSocket streaming context
- Path validation and sandbox enforcement
- Status update messaging
"""
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_ai import RunContext

from app.tools import (
    read_file, write_file, edit_file, list_files, search_in_files,
    run_command, run_git_command, run_tests,
    start_background_process, stop_background_process, list_background_processes,
    get_working_directory, file_exists,
    PathValidator
)
from app.utils.logger import logger


# This will be imported from messaging.py
SANDBOX_DIR = None
path_validator = None
messagingAgent = None
StreamingContext = None
send_tool_update = None


def initialize_tools(sandbox_dir: Path, validator: PathValidator, agent, streaming_context, tool_update_fn):
    """Initialize the module-level variables needed by the tools."""
    global SANDBOX_DIR, path_validator, messagingAgent, StreamingContext, send_tool_update
    SANDBOX_DIR = sandbox_dir
    path_validator = validator
    messagingAgent = agent
    StreamingContext = streaming_context
    send_tool_update = tool_update_fn


# Register file operation tools
def register_read_file_tool():
    @messagingAgent.tool
    async def read_file_tool(
        ctx: RunContext[StreamingContext],
        file_path: str = Field(description="Path to the file to read, relative to workspace (e.g., 'src/main.py' or './README.md')"),
        start_line: Optional[int] = Field(None, description="Optional starting line number (1-indexed). If provided, only reads from this line onwards."),
        end_line: Optional[int] = Field(None, description="Optional ending line number (1-indexed). If provided with start_line, only reads the specified range.")
    ) -> str:
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

            # Resolve relative paths relative to SANDBOX_DIR
            full_path = SANDBOX_DIR / file_path
            path_validator.validate(str(full_path))
            result = await read_file(str(full_path), start_line, end_line)
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
        except Exception as e:
            # Catch all exceptions to ensure tool_complete is always sent
            error_msg = f"Error: {str(e)}"
            await send_tool_update(
                ctx.deps.websocket,
                ctx.deps.agent_message_id,
                "read_file_tool",
                "tool_complete",
                {"result": error_msg},
                ctx.deps.conversation_id,
                status="error",
                error_message=str(e)
            )
            return error_msg


def register_write_file_tool():
    @messagingAgent.tool
    async def write_file_tool(
        ctx: RunContext[StreamingContext],
        file_path: str = Field(description="Path where the file should be written, relative to workspace (e.g., 'src/new_file.py'). Parent directories will be created if they don't exist."),
        content: str = Field(description="The complete content to write to the file. This will overwrite any existing content.")
    ) -> str:
        """Write content to a file within the workspace. Creates parent directories if needed."""
        try:
            await ctx.deps.websocket.send_json({
                "type": "tool_start",
                "message_id": ctx.deps.agent_message_id,
                "tool_name": "write_file_tool",
                "args": {"file_path": file_path, "content": content[:100] + "..." if len(content) > 100 else content},
                "conversation_id": ctx.deps.conversation_id,
            })

            # Resolve relative paths relative to SANDBOX_DIR
            full_path = SANDBOX_DIR / file_path
            path_validator.validate(str(full_path))
            result = await write_file(str(full_path), content)

            await ctx.deps.websocket.send_json({
                "type": "tool_complete",
                "message_id": ctx.deps.agent_message_id,
                "tool_name": "write_file_tool",
                "result": result,
                "conversation_id": ctx.deps.conversation_id,
                "status": "success",
            })
            return result
        except Exception as e:
            # Catch all exceptions to ensure tool_complete is always sent
            error_msg = f"Error: {str(e)}"
            await ctx.deps.websocket.send_json({
                "type": "tool_complete",
                "message_id": ctx.deps.agent_message_id,
                "tool_name": "write_file_tool",
                "result": error_msg,
                "conversation_id": ctx.deps.conversation_id,
                "status": "error",
                "error_message": str(e),
            })
            return error_msg


def register_edit_file_tool():
    @messagingAgent.tool
    async def edit_file_tool(
        ctx: RunContext[StreamingContext],
        file_path: str = Field(description="Path to the file to edit, relative to workspace (e.g., 'src/config.py')"),
        old_content: str = Field(description="The exact text to find and replace in the file. Must match exactly including whitespace."),
        new_content: str = Field(description="The new text that will replace old_content. Can be the same length, shorter, or longer.")
    ) -> str:
        """Edit a file within the workspace by replacing old_content with new_content."""
        try:
            await ctx.deps.websocket.send_json({
                "type": "tool_start",
                "message_id": ctx.deps.agent_message_id,
                "tool_name": "edit_file_tool",
                "args": {"file_path": file_path, "old_content": old_content[:50] + "...", "new_content": new_content[:50] + "..."},
                "conversation_id": ctx.deps.conversation_id,
            })

            # Resolve relative paths relative to SANDBOX_DIR
            full_path = SANDBOX_DIR / file_path
            path_validator.validate(str(full_path))
            result = await edit_file(str(full_path), old_content, new_content)

            await ctx.deps.websocket.send_json({
                "type": "tool_complete",
                "message_id": ctx.deps.agent_message_id,
                "tool_name": "edit_file_tool",
                "result": result,
                "conversation_id": ctx.deps.conversation_id,
                "status": "success",
            })
            return result
        except Exception as e:
            # Catch all exceptions to ensure tool_complete is always sent
            error_msg = f"Error: {str(e)}"
            await ctx.deps.websocket.send_json({
                "type": "tool_complete",
                "message_id": ctx.deps.agent_message_id,
                "tool_name": "edit_file_tool",
                "result": error_msg,
                "conversation_id": ctx.deps.conversation_id,
                "status": "error",
                "error_message": str(e),
            })
            return error_msg


def register_list_files_tool():
    @messagingAgent.tool
    async def list_files_tool(
        ctx: RunContext[StreamingContext],
        directory: str = Field(default=".", description="Directory to list files from, relative to workspace (e.g., 'src' or '.'). Use '.' for workspace root."),
        pattern: str = Field(default="*", description="Glob pattern to filter files (e.g., '*.py' for Python files, '*.js' for JavaScript, or '*' for all files)"),
        recursive: bool = Field(default=False, description="If True, searches subdirectories recursively. If False, only lists files in the specified directory."),
        include_dirs: bool = Field(default=False, description="If True, includes directories in the results. If False, only returns files."),
        exclude_patterns: Optional[List[str]] = Field(default=None, description="List of patterns to exclude (e.g., ['node_modules', '*.pyc']). If None, uses smart defaults (node_modules, .git, __pycache__, dist, etc.). Set to empty list [] to disable exclusions."),
        respect_gitignore: bool = Field(default=True, description="If True, respects .gitignore files in the directory. If False, ignores .gitignore.")
    ) -> List[str]:
        """List files/directories in the workspace with smart exclusions. By default excludes common bloat directories like node_modules, .git, __pycache__, dist, build, etc."""
        try:
            # Send tool call notification
            await send_tool_update(
                ctx.deps.websocket,
                ctx.deps.agent_message_id,
                "list_files_tool",
                "tool_start",
                {"args": {"directory": directory, "pattern": pattern, "recursive": recursive, "include_dirs": include_dirs}},
                ctx.deps.conversation_id
            )

            # Convert relative "." to the sandbox directory
            if directory == ".":
                directory = str(SANDBOX_DIR)
            else:
                # Resolve relative paths relative to SANDBOX_DIR
                full_path = SANDBOX_DIR / directory
                path_validator.validate(str(full_path))
                directory = str(full_path)

            result = await list_files(directory, pattern, recursive, include_dirs, exclude_patterns, respect_gitignore)

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
        except Exception as e:
            # Catch all exceptions to ensure tool_complete is always sent
            error_result = [f"Error: {str(e)}"]
            await send_tool_update(
                ctx.deps.websocket,
                ctx.deps.agent_message_id,
                "list_files_tool",
                "tool_complete",
                {"result": error_result},
                ctx.deps.conversation_id,
                status="error",
                error_message=str(e)
            )
            return error_result


def register_search_in_files_tool():
    @messagingAgent.tool
    async def search_in_files_tool(
        ctx: RunContext[StreamingContext],
        pattern: str = Field(description="Text or regex pattern to search for (e.g., 'def calculate' or 'import.*numpy')"),
        directory: str = Field(default=".", description="Directory to search in, relative to workspace (e.g., 'src' or '.'). Use '.' for workspace root."),
        file_pattern: str = Field(default="*.py", description="File pattern to search within (e.g., '*.py' for Python, '*.js' for JavaScript, '*' for all files)")
    ) -> str:
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
                # Resolve relative paths relative to SANDBOX_DIR
                full_path = SANDBOX_DIR / directory
                path_validator.validate(str(full_path))
                directory = str(full_path)

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
                "status": "success",
            })
            return result
        except Exception as e:
            # Catch all exceptions to ensure tool_complete is always sent
            error_msg = f"Error: {str(e)}"
            await ctx.deps.websocket.send_json({
                "type": "tool_complete",
                "message_id": ctx.deps.agent_message_id,
                "tool_name": "search_in_files_tool",
                "result": error_msg,
                "conversation_id": ctx.deps.conversation_id,
                "status": "error",
                "error_message": str(e),
            })
            return error_msg


def register_run_command_tool():
    @messagingAgent.tool
    async def run_command_tool(
        ctx: RunContext[StreamingContext],
        command: str = Field(description="The shell command to execute (e.g., 'npm install', 'git status', 'python script.py'). REQUIRED parameter. Use 'npx -y' for npm commands to skip prompts."),
        cwd: Optional[str] = Field(None, description="Working directory for command execution, relative to workspace (e.g., 'src' or './frontend'). Defaults to workspace root if not specified."),
        timeout: int = Field(default=300, description="Command timeout in seconds. Default is 300 seconds (5 minutes). Increase for long-running installations or builds.")
    ) -> str:
        """Execute a shell command within the workspace and return the output.

        Args:
            command (str): REQUIRED. The shell command to execute (e.g., "npm install", "git status").
            cwd (str, optional): Working directory path. Defaults to sandbox workspace.
            timeout (int, optional): Command timeout in seconds. Default is 300 seconds for package installations.

        Returns:
            str: The command output including return code, stdout, and stderr.
        """
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
                # Resolve relative paths relative to SANDBOX_DIR
                full_path = SANDBOX_DIR / cwd
                path_validator.validate(str(full_path))
                cwd = str(full_path)

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
        except Exception as e:
            # Catch all exceptions to ensure tool_complete is always sent
            error_msg = f"Error: {str(e)}"
            await send_tool_update(
                ctx.deps.websocket,
                ctx.deps.agent_message_id,
                "run_command_tool",
                "tool_complete",
                {"result": error_msg},
                ctx.deps.conversation_id,
                status="error",
                error_message=str(e)
            )
            return error_msg


def register_run_git_command_tool():
    @messagingAgent.tool
    async def run_git_command_tool(
        ctx: RunContext[StreamingContext],
        git_command: str = Field(description="Git command to execute WITHOUT 'git' prefix (e.g., 'status', 'diff', 'log --oneline -5', 'add .', 'commit -m \"message\"')"),
        cwd: Optional[str] = Field(None, description="Working directory for git command, relative to workspace. Defaults to workspace root if not specified.")
    ) -> str:
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
                # Resolve relative paths relative to SANDBOX_DIR
                full_path = SANDBOX_DIR / cwd
                path_validator.validate(str(full_path))
                cwd = str(full_path)

            result = await run_git_command(git_command, cwd)

            await ctx.deps.websocket.send_json({
                "type": "tool_complete",
                "message_id": ctx.deps.agent_message_id,
                "tool_name": "run_git_command_tool",
                "result": result,
                "conversation_id": ctx.deps.conversation_id,
                "status": "success",
            })
            return result
        except Exception as e:
            # Catch all exceptions to ensure tool_complete is always sent
            error_msg = f"Error: {str(e)}"
            await ctx.deps.websocket.send_json({
                "type": "tool_complete",
                "message_id": ctx.deps.agent_message_id,
                "tool_name": "run_git_command_tool",
                "result": error_msg,
                "conversation_id": ctx.deps.conversation_id,
                "status": "error",
                "error_message": str(e),
            })
            return error_msg


def register_run_tests_tool():
    @messagingAgent.tool
    async def run_tests_tool(
        ctx: RunContext[StreamingContext],
        test_path: str = Field(default="tests/", description="Path to test file or directory to run (e.g., 'tests/', 'tests/test_api.py', or 'tests/test_auth.py::test_login')"),
        cwd: Optional[str] = Field(None, description="Working directory for test execution, relative to workspace. Defaults to workspace root if not specified.")
    ) -> str:
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
                # Resolve relative paths relative to SANDBOX_DIR
                full_path = SANDBOX_DIR / cwd
                path_validator.validate(str(full_path))
                cwd = str(full_path)

            result = await run_tests(test_path, cwd)
            output = f"Return code: {result.return_code}\n\n{result.stdout}\n\n{result.stderr}"

            await ctx.deps.websocket.send_json({
                "type": "tool_complete",
                "message_id": ctx.deps.agent_message_id,
                "tool_name": "run_tests_tool",
                "result": output,
                "conversation_id": ctx.deps.conversation_id,
                "status": "success",
            })
            return output
        except Exception as e:
            # Catch all exceptions to ensure tool_complete is always sent
            error_msg = f"Error: {str(e)}"
            await ctx.deps.websocket.send_json({
                "type": "tool_complete",
                "message_id": ctx.deps.agent_message_id,
                "tool_name": "run_tests_tool",
                "result": error_msg,
                "conversation_id": ctx.deps.conversation_id,
                "status": "error",
                "error_message": str(e),
            })
            return error_msg


def register_get_working_directory_tool():
    @messagingAgent.tool
    async def get_working_directory_tool(ctx: RunContext[StreamingContext]) -> str:
        """Get the current workspace directory path. Use this to understand where file operations will be performed."""
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


def register_file_exists_tool():
    @messagingAgent.tool
    async def file_exists_tool(
        ctx: RunContext[StreamingContext],
        file_path: str = Field(description="Path to check for existence, relative to workspace (e.g., 'src/config.py' or './package.json')")
    ) -> bool:
        """Check if a file exists within the workspace."""
        try:
            await ctx.deps.websocket.send_json({
                "type": "tool_start",
                "message_id": ctx.deps.agent_message_id,
                "tool_name": "file_exists_tool",
                "args": {"file_path": file_path},
                "conversation_id": ctx.deps.conversation_id,
            })

            # Resolve relative paths relative to SANDBOX_DIR
            full_path = SANDBOX_DIR / file_path
            path_validator.validate(str(full_path))
            result = await file_exists(str(full_path))

            await ctx.deps.websocket.send_json({
                "type": "tool_complete",
                "message_id": ctx.deps.agent_message_id,
                "tool_name": "file_exists_tool",
                "result": result,
                "conversation_id": ctx.deps.conversation_id,
                "status": "success",
            })
            return result
        except Exception as e:
            # Catch all exceptions to ensure tool_complete is always sent
            # Return False with error message as string (tools can't return complex types)
            await ctx.deps.websocket.send_json({
                "type": "tool_complete",
                "message_id": ctx.deps.agent_message_id,
                "tool_name": "file_exists_tool",
                "result": False,
                "conversation_id": ctx.deps.conversation_id,
                "status": "error",
                "error_message": str(e),
            })
            return False


def register_start_dev_server_tool():
    @messagingAgent.tool
    async def start_dev_server_tool(
        ctx: RunContext[StreamingContext],
        command: str = Field(description="The long-running command to execute in background (e.g., 'npm run dev', 'yarn dev', 'python manage.py runserver'). REQUIRED parameter."),
        process_id: str = Field(description="Unique identifier for this background process (e.g., 'next-dev-server', 'django-server', 'webpack-watcher'). Used to stop the process later. REQUIRED parameter."),
        cwd: Optional[str] = Field(None, description="Working directory for the process, relative to workspace (e.g., 'frontend' or './my-app'). Defaults to workspace root if not specified.")
    ) -> str:
        """Start a long-running development server or background process.

        Use this for commands that run indefinitely like 'npm run dev', 'yarn dev', etc.
        DO NOT use run_command_tool for these - it will timeout!

        Args:
            command (str): REQUIRED. The command to run (e.g., "npm run dev").
            process_id (str): REQUIRED. Unique ID for this process (e.g., "next-dev-server").
            cwd (str, optional): Working directory path. Defaults to sandbox workspace.

        Returns:
            str: Confirmation with process ID and PID.

        Example tool calls:
            {"command": "npm run dev", "process_id": "next-dev-server", "cwd": "webdev-testing/my-app"}
            {"command": "python manage.py runserver", "process_id": "django-server"}
        """
        try:
            await send_tool_update(
                ctx.deps.websocket,
                ctx.deps.agent_message_id,
                "start_dev_server_tool",
                "tool_start",
                {"args": {"command": command, "process_id": process_id, "cwd": cwd}},
                ctx.deps.conversation_id
            )

            # Default to sandbox directory if no cwd specified
            if cwd is None:
                cwd = str(SANDBOX_DIR)
            else:
                # Resolve relative paths relative to SANDBOX_DIR
                full_path = SANDBOX_DIR / cwd
                path_validator.validate(str(full_path))
                cwd = str(full_path)

            result = await start_background_process(command, process_id, cwd)

            await send_tool_update(
                ctx.deps.websocket,
                ctx.deps.agent_message_id,
                "start_dev_server_tool",
                "tool_complete",
                {"result": result},
                ctx.deps.conversation_id
            )
            return result
        except Exception as e:
            error_msg = f"Error starting background process: {str(e)}"
            await send_tool_update(
                ctx.deps.websocket,
                ctx.deps.agent_message_id,
                "start_dev_server_tool",
                "tool_complete",
                {"error": error_msg},
                ctx.deps.conversation_id
            )
            return error_msg


def register_stop_dev_server_tool():
    @messagingAgent.tool
    async def stop_dev_server_tool(
        ctx: RunContext[StreamingContext],
        process_id: str = Field(description="The unique identifier of the process to stop (e.g., 'next-dev-server', 'django-server'). Must match the process_id used when starting. REQUIRED parameter.")
    ) -> str:
        """Stop a running background process by its ID.

        Args:
            process_id (str): REQUIRED. The ID given when starting the process.

        Returns:
            str: Confirmation message.
        """
        try:
            await send_tool_update(
                ctx.deps.websocket,
                ctx.deps.agent_message_id,
                "stop_dev_server_tool",
                "tool_start",
                {"args": {"process_id": process_id}},
                ctx.deps.conversation_id
            )

            result = await stop_background_process(process_id)

            await send_tool_update(
                ctx.deps.websocket,
                ctx.deps.agent_message_id,
                "stop_dev_server_tool",
                "tool_complete",
                {"result": result},
                ctx.deps.conversation_id
            )
            return result
        except Exception as e:
            error_msg = f"Error stopping background process: {str(e)}"
            await send_tool_update(
                ctx.deps.websocket,
                ctx.deps.agent_message_id,
                "stop_dev_server_tool",
                "tool_complete",
                {"error": error_msg},
                ctx.deps.conversation_id
            )
            return error_msg


def register_list_dev_servers_tool():
    @messagingAgent.tool
    async def list_dev_servers_tool(ctx: RunContext[StreamingContext]) -> str:
        """List all running background processes/dev servers. Returns process IDs, PIDs, commands, and status for each running process."""
        try:
            await send_tool_update(
                ctx.deps.websocket,
                ctx.deps.agent_message_id,
                "list_dev_servers_tool",
                "tool_start",
                {"args": {}},
                ctx.deps.conversation_id
            )

            result = await list_background_processes()

            await send_tool_update(
                ctx.deps.websocket,
                ctx.deps.agent_message_id,
                "list_dev_servers_tool",
                "tool_complete",
                {"result": result},
                ctx.deps.conversation_id
            )
            return result
        except Exception as e:
            error_msg = f"Error listing background processes: {str(e)}"
            await send_tool_update(
                ctx.deps.websocket,
                ctx.deps.agent_message_id,
                "list_dev_servers_tool",
                "tool_complete",
                {"error": error_msg},
                ctx.deps.conversation_id
            )
            return error_msg


def register_all_tools():
    """Register all agent tools with the messagingAgent."""
    register_read_file_tool()
    register_write_file_tool()
    register_edit_file_tool()
    register_list_files_tool()
    register_search_in_files_tool()
    register_run_command_tool()
    register_run_git_command_tool()
    register_run_tests_tool()
    register_get_working_directory_tool()
    register_file_exists_tool()
    register_start_dev_server_tool()
    register_stop_dev_server_tool()
    register_list_dev_servers_tool()
