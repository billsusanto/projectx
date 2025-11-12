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


async def list_files(directory: str = ".", pattern: str = "*", recursive: bool = False) -> List[str]:
    """
    List files in a directory matching a pattern.

    Args:
        directory: Directory to search (default: current directory)
        pattern: Glob pattern to match (default: all files)
        recursive: Whether to search recursively (default: False)

    Returns:
        List of matching file paths

    Example:
        list_files('.', '*.py', recursive=True)
        list_files('src', 'test_*.py')
    """
    try:
        path = Path(directory).expanduser().resolve()

        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if recursive:
            files = [str(p.relative_to(path)) for p in path.rglob(pattern) if p.is_file()]
        else:
            files = [str(p.relative_to(path)) for p in path.glob(pattern) if p.is_file()]

        return sorted(files)
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
    return str(Path.cwd())


async def file_exists(file_path: str) -> bool:
    """Check if a file exists."""
    return Path(file_path).expanduser().resolve().exists()
