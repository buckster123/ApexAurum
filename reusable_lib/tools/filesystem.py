"""
Filesystem Tools for Claude

Safe filesystem operations within a sandboxed directory.
All operations are restricted to the sandbox directory for security.

Tools:
- fs_read_file: Read file contents
- fs_write_file: Write to file
- fs_list_files: List directory contents
- fs_mkdir: Create directory
- fs_delete: Delete file or directory
- fs_exists: Check if path exists
- fs_get_info: Get file/directory info
"""

import os
import logging
from pathlib import Path
from typing import Union, List, Dict, Any
import json

logger = logging.getLogger(__name__)

# Default sandbox directory (relative to project root)
DEFAULT_SANDBOX_DIR = "./sandbox"


class FilesystemSandbox:
    """Manages sandboxed filesystem operations"""

    def __init__(self, sandbox_dir: str = DEFAULT_SANDBOX_DIR):
        """
        Initialize filesystem sandbox.

        Args:
            sandbox_dir: Path to sandbox directory
        """
        self.sandbox_dir = Path(sandbox_dir).resolve()
        self._ensure_sandbox_exists()

    def _ensure_sandbox_exists(self):
        """Create sandbox directory if it doesn't exist"""
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: str) -> Path:
        """
        Resolve and validate a path within the sandbox.

        Args:
            path: Relative or absolute path

        Returns:
            Absolute path within sandbox

        Raises:
            ValueError: If path escapes sandbox
        """
        # Convert to Path and resolve
        target = (self.sandbox_dir / path).resolve()

        # Security check: ensure path is within sandbox
        try:
            target.relative_to(self.sandbox_dir)
        except ValueError:
            raise ValueError(f"Path '{path}' escapes sandbox directory")

        return target


# Global sandbox instance
_sandbox = FilesystemSandbox()


def set_sandbox_path(path: str):
    """
    Set the sandbox directory for filesystem operations.

    Call this at application startup to configure where files
    will be stored.

    Args:
        path: Path to sandbox directory
    """
    global _sandbox
    _sandbox = FilesystemSandbox(path)
    logger.info(f"Filesystem sandbox set to: {_sandbox.sandbox_dir}")


def get_sandbox_path() -> str:
    """Get the current sandbox directory path."""
    return str(_sandbox.sandbox_dir)


def fs_read_file(path: str, encoding: str = "utf-8") -> Union[str, dict]:
    """
    Read contents of a file.

    Args:
        path: Path to file (relative to sandbox)
        encoding: File encoding (default: utf-8)

    Returns:
        File contents as string, or error dict

    Example:
        >>> fs_read_file("test.txt")
        "Hello, world!"
    """
    try:
        target = _sandbox._resolve_path(path)

        if not target.exists():
            return {"error": f"File not found: {path}"}

        if not target.is_file():
            return {"error": f"Not a file: {path}"}

        with open(target, "r", encoding=encoding) as f:
            content = f.read()

        logger.info(f"Read file: {path} ({len(content)} bytes)")
        return content

    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
        return {"error": str(e)}


def fs_write_file(
    path: str,
    content: str,
    encoding: str = "utf-8",
    mode: str = "overwrite"
) -> dict:
    """
    Write content to a file.

    Args:
        path: Path to file (relative to sandbox)
        content: Content to write
        encoding: File encoding (default: utf-8)
        mode: Write mode - "overwrite" or "append"

    Returns:
        Status dict with success/error

    Example:
        >>> fs_write_file("test.txt", "Hello, world!")
        {"success": True, "path": "test.txt", "bytes_written": 13}
    """
    try:
        target = _sandbox._resolve_path(path)

        # Create parent directories if needed
        target.parent.mkdir(parents=True, exist_ok=True)

        # Determine write mode
        write_mode = "a" if mode == "append" else "w"

        with open(target, write_mode, encoding=encoding) as f:
            bytes_written = f.write(content)

        logger.info(f"Wrote file: {path} ({bytes_written} bytes, mode={mode})")

        return {
            "success": True,
            "path": path,
            "bytes_written": bytes_written,
            "mode": mode
        }

    except Exception as e:
        logger.error(f"Error writing file {path}: {e}")
        return {"error": str(e), "success": False}


def fs_list_files(
    path: str = ".",
    recursive: bool = False,
    pattern: str = "*"
) -> Union[List[str], dict]:
    """
    List files and directories.

    Args:
        path: Directory path (relative to sandbox)
        recursive: Whether to list recursively
        pattern: Glob pattern to match (e.g., "*.txt")

    Returns:
        List of file/directory paths, or error dict

    Example:
        >>> fs_list_files(".", pattern="*.txt")
        ["test.txt", "notes.txt"]
    """
    try:
        target = _sandbox._resolve_path(path)

        if not target.exists():
            return {"error": f"Path not found: {path}"}

        if not target.is_dir():
            return {"error": f"Not a directory: {path}"}

        # List files
        if recursive:
            matches = target.rglob(pattern)
        else:
            matches = target.glob(pattern)

        # Convert to relative paths
        results = []
        for match in sorted(matches):
            try:
                rel_path = match.relative_to(_sandbox.sandbox_dir)
                results.append(str(rel_path))
            except ValueError:
                continue

        logger.info(f"Listed {len(results)} items in {path}")
        return results

    except Exception as e:
        logger.error(f"Error listing files in {path}: {e}")
        return {"error": str(e)}


def fs_mkdir(path: str) -> dict:
    """
    Create a directory.

    Args:
        path: Directory path (relative to sandbox)

    Returns:
        Status dict

    Example:
        >>> fs_mkdir("new_folder")
        {"success": True, "path": "new_folder"}
    """
    try:
        target = _sandbox._resolve_path(path)
        target.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created directory: {path}")

        return {
            "success": True,
            "path": path
        }

    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")
        return {"error": str(e), "success": False}


def fs_delete(path: str, recursive: bool = False) -> dict:
    """
    Delete a file or directory.

    Args:
        path: Path to delete (relative to sandbox)
        recursive: Whether to delete directories recursively

    Returns:
        Status dict

    Example:
        >>> fs_delete("old_file.txt")
        {"success": True, "path": "old_file.txt"}
    """
    try:
        target = _sandbox._resolve_path(path)

        if not target.exists():
            return {"error": f"Path not found: {path}"}

        if target.is_file():
            target.unlink()
            logger.info(f"Deleted file: {path}")
        elif target.is_dir():
            if recursive:
                import shutil
                shutil.rmtree(target)
                logger.info(f"Deleted directory recursively: {path}")
            else:
                target.rmdir()
                logger.info(f"Deleted empty directory: {path}")
        else:
            return {"error": f"Unknown file type: {path}"}

        return {
            "success": True,
            "path": path
        }

    except Exception as e:
        logger.error(f"Error deleting {path}: {e}")
        return {"error": str(e), "success": False}


def fs_exists(path: str) -> dict:
    """
    Check if a path exists.

    Args:
        path: Path to check (relative to sandbox)

    Returns:
        Dict with exists status and type

    Example:
        >>> fs_exists("test.txt")
        {"exists": True, "type": "file"}
    """
    try:
        target = _sandbox._resolve_path(path)

        exists = target.exists()
        file_type = None

        if exists:
            if target.is_file():
                file_type = "file"
            elif target.is_dir():
                file_type = "directory"
            else:
                file_type = "other"

        return {
            "exists": exists,
            "type": file_type,
            "path": path
        }

    except Exception as e:
        logger.error(f"Error checking existence of {path}: {e}")
        return {"error": str(e)}


def fs_get_info(path: str) -> dict:
    """
    Get information about a file or directory.

    Args:
        path: Path (relative to sandbox)

    Returns:
        Dict with file info (size, modified time, etc.)

    Example:
        >>> fs_get_info("test.txt")
        {"size": 1024, "modified": "2024-01-01T12:00:00", ...}
    """
    try:
        target = _sandbox._resolve_path(path)

        if not target.exists():
            return {"error": f"Path not found: {path}"}

        stat = target.stat()

        info = {
            "path": path,
            "exists": True,
            "type": "file" if target.is_file() else "directory",
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
        }

        if target.is_file():
            info["extension"] = target.suffix

        logger.info(f"Got info for: {path}")
        return info

    except Exception as e:
        logger.error(f"Error getting info for {path}: {e}")
        return {"error": str(e)}


def fs_read_lines(
    path: str,
    start_line: int = 1,
    end_line: int = None,
    encoding: str = "utf-8"
) -> dict:
    """
    Read specific lines from a file with line numbers.

    Args:
        path: Path to file (relative to sandbox)
        start_line: First line to read (1-indexed, default: 1)
        end_line: Last line to read (inclusive, default: end of file)
        encoding: File encoding (default: utf-8)

    Returns:
        Dict with content (numbered lines), total_lines, and range info

    Example:
        >>> fs_read_lines("main.py", start_line=10, end_line=20)
        {
            "success": True,
            "content": "10: def foo():\\n11:     return bar\\n...",
            "start_line": 10,
            "end_line": 20,
            "total_lines": 150
        }
    """
    try:
        target = _sandbox._resolve_path(path)

        if not target.exists():
            return {"error": f"File not found: {path}", "success": False}

        if not target.is_file():
            return {"error": f"Not a file: {path}", "success": False}

        with open(target, "r", encoding=encoding) as f:
            all_lines = f.readlines()

        total_lines = len(all_lines)

        # Validate line numbers
        if start_line < 1:
            start_line = 1
        if end_line is None or end_line > total_lines:
            end_line = total_lines
        if start_line > total_lines:
            return {
                "success": True,
                "content": "",
                "start_line": start_line,
                "end_line": end_line,
                "total_lines": total_lines,
                "message": f"Start line {start_line} exceeds file length ({total_lines} lines)"
            }

        # Extract requested lines (convert to 0-indexed)
        selected_lines = all_lines[start_line - 1:end_line]

        # Format with line numbers
        numbered_content = ""
        for i, line in enumerate(selected_lines, start=start_line):
            # Remove trailing newline for consistent formatting, then add back
            line_text = line.rstrip('\n\r')
            numbered_content += f"{i:>6}: {line_text}\n"

        logger.info(f"Read lines {start_line}-{end_line} from {path} ({total_lines} total)")

        return {
            "success": True,
            "content": numbered_content,
            "start_line": start_line,
            "end_line": end_line,
            "lines_returned": len(selected_lines),
            "total_lines": total_lines,
            "path": path
        }

    except Exception as e:
        logger.error(f"Error reading lines from {path}: {e}")
        return {"error": str(e), "success": False}


def fs_edit(
    path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
    encoding: str = "utf-8"
) -> dict:
    """
    Edit a file by replacing a string with another string.

    This enables surgical edits without rewriting entire files.
    The old_string must be unique in the file (unless replace_all=True).

    Args:
        path: Path to file (relative to sandbox)
        old_string: Text to find and replace (must match exactly)
        new_string: Text to replace with (can be empty to delete)
        replace_all: Replace all occurrences (default: False, requires unique match)
        encoding: File encoding (default: utf-8)

    Returns:
        Dict with success status and edit details

    Example:
        >>> fs_edit("main.py", old_string="def foo():", new_string="def bar():")
        {"success": True, "replacements": 1, "path": "main.py"}

        >>> fs_edit("config.py", old_string="DEBUG = True", new_string="DEBUG = False")
        {"success": True, "replacements": 1}

        >>> fs_edit("main.py", old_string="old_var", new_string="new_var", replace_all=True)
        {"success": True, "replacements": 5}
    """
    try:
        target = _sandbox._resolve_path(path)

        if not target.exists():
            return {"error": f"File not found: {path}", "success": False}

        if not target.is_file():
            return {"error": f"Not a file: {path}", "success": False}

        # Read current content
        with open(target, "r", encoding=encoding) as f:
            content = f.read()

        # Check if old_string exists
        occurrences = content.count(old_string)

        if occurrences == 0:
            return {
                "error": f"String not found in file: '{old_string[:50]}{'...' if len(old_string) > 50 else ''}'",
                "success": False
            }

        if occurrences > 1 and not replace_all:
            return {
                "error": f"String found {occurrences} times. Use replace_all=True to replace all, or provide more context to make it unique.",
                "success": False,
                "occurrences": occurrences
            }

        # Perform replacement
        if replace_all:
            new_content = content.replace(old_string, new_string)
            replacements = occurrences
        else:
            new_content = content.replace(old_string, new_string, 1)
            replacements = 1

        # Write back
        with open(target, "w", encoding=encoding) as f:
            f.write(new_content)

        logger.info(f"Edited {path}: {replacements} replacement(s)")

        return {
            "success": True,
            "path": path,
            "replacements": replacements,
            "bytes_before": len(content),
            "bytes_after": len(new_content)
        }

    except Exception as e:
        logger.error(f"Error editing {path}: {e}")
        return {"error": str(e), "success": False}


# Tool schemas for registration
FILESYSTEM_TOOL_SCHEMAS = {
    "fs_read_file": {
        "name": "fs_read_file",
        "description": "Read the contents of a file from the sandbox directory",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file (relative to sandbox directory)"
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8"
                }
            },
            "required": ["path"]
        }
    },
    "fs_write_file": {
        "name": "fs_write_file",
        "description": "Write content to a file in the sandbox directory",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file (relative to sandbox directory)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8"
                },
                "mode": {
                    "type": "string",
                    "enum": ["overwrite", "append"],
                    "description": "Write mode: 'overwrite' replaces file, 'append' adds to end",
                    "default": "overwrite"
                }
            },
            "required": ["path", "content"]
        }
    },
    "fs_list_files": {
        "name": "fs_list_files",
        "description": "List files and directories in the sandbox",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path (relative to sandbox, default: '.')",
                    "default": "."
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to list recursively (default: false)",
                    "default": False
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter results (default: '*')",
                    "default": "*"
                }
            },
            "required": []
        }
    },
    "fs_mkdir": {
        "name": "fs_mkdir",
        "description": "Create a directory in the sandbox",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to create (relative to sandbox)"
                }
            },
            "required": ["path"]
        }
    },
    "fs_delete": {
        "name": "fs_delete",
        "description": "Delete a file or directory from the sandbox",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to delete (relative to sandbox)"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to delete directories recursively (default: false)",
                    "default": False
                }
            },
            "required": ["path"]
        }
    },
    "fs_exists": {
        "name": "fs_exists",
        "description": "Check if a file or directory exists in the sandbox",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to check (relative to sandbox)"
                }
            },
            "required": ["path"]
        }
    },
    "fs_get_info": {
        "name": "fs_get_info",
        "description": "Get detailed information about a file or directory",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path (relative to sandbox)"
                }
            },
            "required": ["path"]
        }
    },
    "fs_read_lines": {
        "name": "fs_read_lines",
        "description": """Read specific lines from a file with line numbers.

Use this to inspect parts of a file without loading the entire content.
Lines are returned with line numbers for easy reference.

Examples:
- Read first 50 lines: fs_read_lines(path="main.py", end_line=50)
- Read lines 100-150: fs_read_lines(path="main.py", start_line=100, end_line=150)
- Read from line 200 to end: fs_read_lines(path="main.py", start_line=200)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file (relative to sandbox)"
                },
                "start_line": {
                    "type": "integer",
                    "description": "First line to read (1-indexed, default: 1)",
                    "default": 1
                },
                "end_line": {
                    "type": "integer",
                    "description": "Last line to read (inclusive, default: end of file)"
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8"
                }
            },
            "required": ["path"]
        }
    },
    "fs_edit": {
        "name": "fs_edit",
        "description": """Edit a file by finding and replacing a string.

This enables surgical edits without rewriting entire files. The old_string
must be unique in the file unless replace_all=True.

Tips:
- Include surrounding context (nearby lines) to ensure uniqueness
- Use replace_all=True for renaming variables across a file
- Set new_string="" to delete text
- Preserves file encoding and line endings

Examples:
- Rename function: fs_edit(path="main.py", old_string="def foo():", new_string="def bar():")
- Fix a bug: fs_edit(path="config.py", old_string="DEBUG = True", new_string="DEBUG = False")
- Delete code: fs_edit(path="main.py", old_string="# TODO: remove this\\nold_code()", new_string="")
- Rename all: fs_edit(path="main.py", old_string="old_name", new_string="new_name", replace_all=True)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file (relative to sandbox)"
                },
                "old_string": {
                    "type": "string",
                    "description": "Exact text to find and replace"
                },
                "new_string": {
                    "type": "string",
                    "description": "Text to replace with (empty string to delete)"
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences (default: false, requires unique match)",
                    "default": False
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8"
                }
            },
            "required": ["path", "old_string", "new_string"]
        }
    }
}
