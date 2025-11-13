"""
Tools for Pydantic AI Agent - File Operations, System Commands, and Code Analysis
Designed for software engineering tasks including SWE-bench
"""

import os
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import ast

from app.utils.logger import logger
from pydantic_ai import ModelRetry


# ============================================================================
# FILE OPERATION TOOLS
# ============================================================================

class FileReadResult(BaseModel):
    """Result of reading a file"""
    content: str
    lines: int
    size_bytes: int
    path: str


async def read_file(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> FileReadResult:
    """
    Read contents of a file. Optionally specify line range.

    Args:
        file_path: Path to the file to read (relative or absolute)
        start_line: Optional starting line number (1-indexed)
        end_line: Optional ending line number (1-indexed)

    Returns:
        FileReadResult with file contents and metadata

    Example:
        read_file('src/main.py')
        read_file('utils.py', start_line=10, end_line=20)
    """
    try:
        with logger.span('read_file', file_path=file_path, start_line=start_line, end_line=end_line):
            path = Path(file_path).expanduser().resolve()

            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            if not path.is_file():
                raise ValueError(f"Path is not a file: {file_path}")

            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Handle line range
            if start_line is not None or end_line is not None:
                start = (start_line - 1) if start_line else 0
                end = end_line if end_line else len(lines)
                lines = lines[start:end]

            content = ''.join(lines)
            size = path.stat().st_size

            return FileReadResult(
                content=content,
                lines=len(lines),
                size_bytes=size,
                path=str(path)
            )
    except Exception as e:
        raise Exception(f"Error reading file {file_path}: {str(e)}")


async def write_file(file_path: str, content: str, create_dirs: bool = True) -> str:
    """
    Write content to a file. Creates parent directories if needed.

    Args:
        file_path: Path to the file to write
        content: Content to write to the file
        create_dirs: Whether to create parent directories if they don't exist

    Returns:
        Success message with file path

    Example:
        write_file('src/new_module.py', 'def hello(): pass')
    """
    try:
        with logger.span('write_file', file_path=file_path, content_length=len(content), create_dirs=create_dirs):
            path = Path(file_path).expanduser().resolve()

            if create_dirs:
                path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            return f"Successfully wrote {len(content)} bytes to {path}"
    except Exception as e:
        raise Exception(f"Error writing file {file_path}: {str(e)}")


async def edit_file(file_path: str, old_content: str, new_content: str) -> str:
    """
    Edit a file by replacing old_content with new_content.
    Use this for precise edits to existing files.

    Args:
        file_path: Path to the file to edit
        old_content: The exact text to find and replace
        new_content: The new text to insert

    Returns:
        Success message

    Example:
        edit_file('src/utils.py',
                  'def old_func():\\n    pass',
                  'def new_func():\\n    return True')
    """
    try:
        with logger.span('edit_file', file_path=file_path, old_length=len(old_content), new_length=len(new_content)):
            path = Path(file_path).expanduser().resolve()

            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            if old_content not in content:
                raise ValueError(f"Could not find old_content in file. Make sure the text matches exactly.")

            new_file_content = content.replace(old_content, new_content, 1)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_file_content)

            return f"Successfully edited {path}"
    except Exception as e:
        raise Exception(f"Error editing file {file_path}: {str(e)}")


async def list_files(
    directory: str = ".",
    pattern: str = "*",
    recursive: bool = False,
    include_dirs: bool = False,
    exclude_patterns: Optional[List[str]] = None,
    respect_gitignore: bool = True
) -> List[str]:
    """
    List files in a directory matching a pattern with smart exclusions.

    Args:
        directory: Directory to search (default: current directory)
        pattern: Glob pattern to match (default: all files)
        recursive: Whether to search recursively (default: False)
        include_dirs: Whether to include directories in results (default: False)
        exclude_patterns: Custom patterns to exclude (None = use smart defaults)
        respect_gitignore: Whether to respect .gitignore files (default: True)

    Returns:
        List of matching file/directory paths

    Example:
        list_files('.', '*.py', recursive=True)
        list_files('src', '*', include_dirs=True)
        list_files('.', '*', exclude_patterns=[])  # No exclusions
    """
    try:
        with logger.span('list_files', directory=directory, pattern=pattern, recursive=recursive, include_dirs=include_dirs):
            path = Path(directory).expanduser().resolve()

            if not path.exists():
                raise FileNotFoundError(f"Directory not found: {directory}")

            # Default exclusions (common bloat directories and files)
            default_exclusions = [
                'node_modules', '.git', '__pycache__', '.pytest_cache',
                '.venv', 'venv', 'env', '.env',
                'dist', 'build', '.next', '.nuxt', '.output',
                'coverage', '.coverage', 'htmlcov',
                '.DS_Store', '*.pyc', '*.pyo', '*.pyd',
                '.egg-info', '*.egg-info',
                '.tox', '.mypy_cache', '.ruff_cache',
                'target',  # Rust
                'bin', 'obj',  # C#
            ]

            # Use provided exclusions or defaults
            exclusions = exclude_patterns if exclude_patterns is not None else default_exclusions

            # Parse .gitignore if it exists and respect_gitignore is True
            gitignore_spec = None
            if respect_gitignore:
                gitignore_path = path / '.gitignore'
                if gitignore_path.exists():
                    try:
                        import pathspec
                        with open(gitignore_path, 'r') as f:
                            gitignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', f)
                    except ImportError:
                        logger.warning("pathspec library not installed, .gitignore will be ignored. Install with: pip install pathspec")
                    except Exception as e:
                        logger.warning(f"Failed to parse .gitignore: {e}")

            def should_exclude(p: Path) -> bool:
                """Check if path should be excluded based on patterns and .gitignore"""
                relative_path = str(p.relative_to(path))

                # Check .gitignore
                if gitignore_spec and gitignore_spec.match_file(relative_path):
                    return True

                # Check exclusion patterns
                for excl in exclusions:
                    # Check if any part of the path matches exclusion
                    parts = relative_path.split(os.sep)
                    for part in parts:
                        if excl.startswith('*'):
                            # Wildcard pattern
                            if part.endswith(excl[1:]):
                                return True
                        elif part == excl or relative_path == excl:
                            return True

                return False

            # Collect matching paths
            if recursive:
                all_paths = path.rglob(pattern)
            else:
                all_paths = path.glob(pattern)

            # Filter based on criteria
            results = []
            for p in all_paths:
                # Skip if excluded
                if should_exclude(p):
                    continue

                # Include files always, dirs only if include_dirs=True
                if p.is_file() or (include_dirs and p.is_dir()):
                    results.append(str(p.relative_to(path)))

            return sorted(results)
    except Exception as e:
        raise Exception(f"Error listing files in {directory}: {str(e)}")


async def search_in_files(pattern: str, directory: str = ".", file_pattern: str = "*.py") -> Dict[str, List[Dict[str, Any]]]:
    """
    Search for a text pattern in files. Returns matching lines with context.

    Args:
        pattern: Text pattern to search for (plain text, not regex)
        directory: Directory to search in
        file_pattern: File glob pattern to search within

    Returns:
        Dictionary mapping file paths to list of matches with line numbers

    Example:
        search_in_files('def calculate', 'src', '*.py')
    """
    try:
        with logger.span('search_in_files', pattern=pattern, directory=directory, file_pattern=file_pattern):
            path = Path(directory).expanduser().resolve()
            files = [p for p in path.rglob(file_pattern) if p.is_file()]

            results = {}

            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    matches = []
                    for i, line in enumerate(lines, 1):
                        if pattern in line:
                            matches.append({
                                'line_number': i,
                                'content': line.rstrip(),
                            })

                    if matches:
                        results[str(file_path.relative_to(path))] = matches
                except Exception:
                    continue  # Skip files that can't be read

            return results
    except Exception as e:
        raise Exception(f"Error searching files: {str(e)}")


# ============================================================================
# SYSTEM COMMAND TOOLS
# ============================================================================

class CommandResult(BaseModel):
    """Result of executing a system command"""
    stdout: str
    stderr: str
    return_code: int
    command: str


async def run_command(command: str, cwd: Optional[str] = None, timeout: int = 60) -> CommandResult:
    """
    Execute a shell command and return the output.
    Use this for git, pytest, pip, linting, and other CLI tools.

    Args:
        command: The shell command to execute
        cwd: Working directory for the command (default: current directory)
        timeout: Command timeout in seconds (default: 60)

    Returns:
        CommandResult with stdout, stderr, and return code

    Example:
        run_command('git status')
        run_command('pytest tests/test_api.py', cwd='backend')
        run_command('python -m flake8 src/')
    """
    try:
        with logger.span('run_command', command=command, cwd=cwd, timeout=timeout):
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise Exception(f"Command timed out after {timeout} seconds: {command}")

            return CommandResult(
                stdout=stdout.decode('utf-8'),
                stderr=stderr.decode('utf-8'),
                return_code=process.returncode,
                command=command
            )
    except Exception as e:
        raise Exception(f"Error running command '{command}': {str(e)}")


async def run_git_command(git_command: str, cwd: Optional[str] = None) -> str:
    """
    Execute a git command. Helper wrapper around run_command for git operations.

    Args:
        git_command: Git command (without 'git' prefix, e.g., 'status', 'diff HEAD')
        cwd: Working directory (default: current directory)

    Returns:
        Command output as string

    Example:
        run_git_command('status')
        run_git_command('log --oneline -5')
        run_git_command('diff HEAD~1')
    """
    with logger.span('run_git_command', git_command=git_command, cwd=cwd):
        result = await run_command(f"git {git_command}", cwd=cwd)

        if result.return_code != 0:
            raise Exception(f"Git command failed: {result.stderr}")

        return result.stdout


async def run_tests(test_path: str = "tests/", cwd: Optional[str] = None, verbose: bool = True) -> CommandResult:
    """
    Run pytest tests and return results.

    Args:
        test_path: Path to tests (file or directory)
        cwd: Working directory
        verbose: Whether to run in verbose mode

    Returns:
        CommandResult with test output

    Example:
        run_tests('tests/test_api.py')
        run_tests('tests/', verbose=True)
    """
    with logger.span('run_tests', test_path=test_path, cwd=cwd, verbose=verbose):
        verbosity = '-v' if verbose else ''
        return await run_command(f"pytest {test_path} {verbosity}", cwd=cwd, timeout=300)


class FunctionInfo(BaseModel):
    """Information about a function in a Python file"""
    name: str
    line_number: int
    args: List[str]
    docstring: Optional[str]


class ClassInfo(BaseModel):
    """Information about a class in a Python file"""
    name: str
    line_number: int
    methods: List[str]
    docstring: Optional[str]


class CodeStructure(BaseModel):
    """Structure analysis of a Python file"""
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    imports: List[str]

# ============================================================================
# UTILITY TOOLS
# ============================================================================

async def get_working_directory() -> str:
    """Get the current working directory."""
    with logger.span('get_working_directory'):
        return str(Path.cwd())


async def file_exists(file_path: str) -> bool:
    """Check if a file exists."""
    with logger.span('file_exists', file_path=file_path):
        return Path(file_path).expanduser().resolve().exists()


# Global dictionary to track background processes
_background_processes: dict[str, asyncio.subprocess.Process] = {}


async def start_background_process(command: str, process_id: str, cwd: Optional[str] = None) -> str:
    """
    Start a long-running background process (e.g., dev servers).

    Args:
        command: The shell command to execute
        process_id: Unique identifier for this process (for later reference)
        cwd: Working directory for the command (default: current directory)

    Returns:
        str: Confirmation message with process ID and PID

    Example:
        start_background_process('npm run dev', 'next-dev-server', 'webdev-testing/my-app')
    """
    with logger.span('start_background_process', command=command, process_id=process_id, cwd=cwd):
        try:
            # Set up environment to force non-interactive mode
            import os
            env = os.environ.copy()
            env['CI'] = 'true'
            env['FORCE_COLOR'] = '0'  # Disable color output

            # Start the process without waiting for it to complete
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
                cwd=cwd,
                env=env
            )

            # Store the process for later reference
            _background_processes[process_id] = process

            # Wait a brief moment to see if it crashes immediately
            await asyncio.sleep(2)

            if process.returncode is not None:
                # Process exited immediately - something went wrong
                stdout_data, stderr_data = await process.communicate()
                stdout = stdout_data.decode('utf-8') if stdout_data else ""
                stderr = stderr_data.decode('utf-8') if stderr_data else ""

                # Check if it's a transient error
                error_output = (stdout + stderr).lower()
                transient_indicators = [
                    'eaddrinuse', 'port already in use',
                    'resource temporarily unavailable',
                    'connection refused'
                ]

                if any(indicator in error_output for indicator in transient_indicators):
                    raise ModelRetry(
                        f"Process failed to start due to transient issue (likely port conflict or resource unavailability).\n"
                        f"Exit code: {process.returncode}\n"
                        f"Error: {stderr}\n"
                        f"Suggestion: Retry after a brief delay."
                    )
                else:
                    raise Exception(
                        f"Process exited immediately with code {process.returncode}.\n"
                        f"Stdout: {stdout}\n"
                        f"Stderr: {stderr}"
                    )

            return f"✓ Background process '{process_id}' started successfully (PID: {process.pid})\nCommand: {command}\n\nThe process is running in the background. It will continue until stopped."

        except Exception as e:
            raise Exception(f"Error starting background process '{command}': {str(e)}")


async def stop_background_process(process_id: str) -> str:
    """
    Stop a background process by its ID.

    Args:
        process_id: The unique identifier given when starting the process

    Returns:
        str: Confirmation message
    """
    with logger.span('stop_background_process', process_id=process_id):
        if process_id not in _background_processes:
            available = ', '.join(_background_processes.keys()) if _background_processes else 'none'
            raise ValueError(
                f"No background process found with ID '{process_id}'\n"
                f"Available processes: {available}\n"
                f"Suggestions:\n"
                f"1. Use list_background_processes() to see running processes\n"
                f"2. Check if the process ID is spelled correctly\n"
                f"3. The process may have already stopped or never started"
            )

        process = _background_processes[process_id]

        if process.returncode is not None:
            # Already stopped
            del _background_processes[process_id]
            return f"Process '{process_id}' was already stopped (exit code: {process.returncode})"

        # Terminate the process
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            # Force kill if it doesn't stop gracefully
            process.kill()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                raise ModelRetry(
                    f"Process '{process_id}' won't die even after SIGKILL. "
                    f"This is likely a transient system issue. Retrying may succeed."
                )
            await process.wait()

        del _background_processes[process_id]
        return f"✓ Background process '{process_id}' stopped successfully"


async def list_background_processes() -> str:
    """
    List all running background processes.

    Returns:
        str: List of process IDs and their status
    """
    with logger.span('list_background_processes'):
        if not _background_processes:
            return "No background processes running"

        result = "Background processes:\n"
        for process_id, process in list(_background_processes.items()):
            status = "running" if process.returncode is None else f"exited (code: {process.returncode})"
            result += f"  - {process_id}: {status} (PID: {process.pid})\n"

        return result
