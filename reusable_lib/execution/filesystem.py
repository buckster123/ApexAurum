"""
Sandboxed Filesystem Tools

Safe filesystem operations within a sandboxed directory.
All operations are restricted to the sandbox directory for security.

Features:
- Path validation prevents directory traversal attacks
- Configurable sandbox directory
- Full CRUD operations for files and directories
- Line-based file reading for large files
- Surgical string-based file editing

Usage:
    from reusable_lib.execution import (
        fs_read_file,
        fs_write_file,
        fs_edit,
        set_sandbox_path,
        FILESYSTEM_TOOL_SCHEMAS
    )

    # Set custom sandbox path
    set_sandbox_path("./my_sandbox")

    # Basic operations
    fs_write_file("test.txt", "Hello, world!")
    content = fs_read_file("test.txt")

    # Surgical editing
    fs_edit("config.py", "DEBUG = True", "DEBUG = False")

    # Register with AI API
    tools = list(FILESYSTEM_TOOL_SCHEMAS.values())
"""

import os
import logging
import shutil
from pathlib import Path
from typing import Union, List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class FilesystemSandbox:
    """
    Manages sandboxed filesystem operations.

    Ensures all file operations are restricted to a specific directory,
    preventing access to sensitive system files.
    """

    def __init__(self, sandbox_dir: str = "./sandbox"):
        """
        Initialize filesystem sandbox.

        Args:
            sandbox_dir: Path to sandbox directory
        """
        self.sandbox_dir = Path(sandbox_dir).resolve()
        self._ensure_sandbox_exists()

    def _ensure_sandbox_exists(self):
        """Create sandbox directory if it doesn't exist."""
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, path: str) -> Path:
        """
        Resolve and validate a path within the sandbox.

        Args:
            path: Relative or absolute path

        Returns:
            Absolute path within sandbox

        Raises:
            ValueError: If path escapes sandbox
        """
        target = (self.sandbox_dir / path).resolve()

        # Security check: ensure path is within sandbox
        try:
            target.relative_to(self.sandbox_dir)
        except ValueError:
            raise ValueError(f"Path '{path}' escapes sandbox directory")

        return target

    def get_relative_path(self, absolute_path: Path) -> str:
        """Convert absolute path to sandbox-relative path."""
        return str(absolute_path.relative_to(self.sandbox_dir))


# Global sandbox instance
_sandbox: Optional[FilesystemSandbox] = None


def _get_sandbox() -> FilesystemSandbox:
    """Get or create the default sandbox instance."""
    global _sandbox
    if _sandbox is None:
        _sandbox = FilesystemSandbox()
    return _sandbox


def set_sandbox_path(path: str):
    """
    Set the sandbox directory path.

    Args:
        path: Path to sandbox directory

    Example:
        >>> set_sandbox_path("./data")
    """
    global _sandbox
    _sandbox = FilesystemSandbox(path)
    logger.info(f"Sandbox path set to: {path}")


def fs_read_file(path: str, encoding: str = "utf-8") -> Union[str, Dict]:
    """
    Read contents of a file.

    Args:
        path: Path to file (relative to sandbox)
        encoding: File encoding (default: utf-8)

    Returns:
        File contents as string, or error dict
    """
    try:
        target = _get_sandbox().resolve_path(path)

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
) -> Dict:
    """
    Write content to a file.

    Args:
        path: Path to file (relative to sandbox)
        content: Content to write
        encoding: File encoding (default: utf-8)
        mode: Write mode - "overwrite" or "append"

    Returns:
        Status dict with success/error
    """
    try:
        target = _get_sandbox().resolve_path(path)

        # Create parent directories if needed
        target.parent.mkdir(parents=True, exist_ok=True)

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
) -> Union[List[str], Dict]:
    """
    List files and directories.

    Args:
        path: Directory path (relative to sandbox)
        recursive: Whether to list recursively
        pattern: Glob pattern to match (e.g., "*.txt")

    Returns:
        List of file/directory paths, or error dict
    """
    try:
        sandbox = _get_sandbox()
        target = sandbox.resolve_path(path)

        if not target.exists():
            return {"error": f"Path not found: {path}"}

        if not target.is_dir():
            return {"error": f"Not a directory: {path}"}

        if recursive:
            matches = target.rglob(pattern)
        else:
            matches = target.glob(pattern)

        results = []
        for match in sorted(matches):
            try:
                rel_path = match.relative_to(sandbox.sandbox_dir)
                results.append(str(rel_path))
            except ValueError:
                continue

        logger.info(f"Listed {len(results)} items in {path}")
        return results

    except Exception as e:
        logger.error(f"Error listing files in {path}: {e}")
        return {"error": str(e)}


def fs_mkdir(path: str) -> Dict:
    """
    Create a directory.

    Args:
        path: Directory path (relative to sandbox)

    Returns:
        Status dict
    """
    try:
        target = _get_sandbox().resolve_path(path)
        target.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created directory: {path}")

        return {"success": True, "path": path}

    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")
        return {"error": str(e), "success": False}


def fs_delete(path: str, recursive: bool = False) -> Dict:
    """
    Delete a file or directory.

    Args:
        path: Path to delete (relative to sandbox)
        recursive: Whether to delete directories recursively

    Returns:
        Status dict
    """
    try:
        target = _get_sandbox().resolve_path(path)

        if not target.exists():
            return {"error": f"Path not found: {path}"}

        if target.is_file():
            target.unlink()
            logger.info(f"Deleted file: {path}")
        elif target.is_dir():
            if recursive:
                shutil.rmtree(target)
                logger.info(f"Deleted directory recursively: {path}")
            else:
                target.rmdir()
                logger.info(f"Deleted empty directory: {path}")
        else:
            return {"error": f"Unknown file type: {path}"}

        return {"success": True, "path": path}

    except Exception as e:
        logger.error(f"Error deleting {path}: {e}")
        return {"error": str(e), "success": False}


def fs_exists(path: str) -> Dict:
    """
    Check if a path exists.

    Args:
        path: Path to check (relative to sandbox)

    Returns:
        Dict with exists status and type
    """
    try:
        target = _get_sandbox().resolve_path(path)

        exists = target.exists()
        file_type = None

        if exists:
            if target.is_file():
                file_type = "file"
            elif target.is_dir():
                file_type = "directory"
            else:
                file_type = "other"

        return {"exists": exists, "type": file_type, "path": path}

    except Exception as e:
        logger.error(f"Error checking existence of {path}: {e}")
        return {"error": str(e)}


def fs_get_info(path: str) -> Dict:
    """
    Get information about a file or directory.

    Args:
        path: Path (relative to sandbox)

    Returns:
        Dict with file info (size, modified time, etc.)
    """
    try:
        target = _get_sandbox().resolve_path(path)

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
    end_line: Optional[int] = None,
    encoding: str = "utf-8"
) -> Dict:
    """
    Read specific lines from a file with line numbers.

    Args:
        path: Path to file (relative to sandbox)
        start_line: First line to read (1-indexed, default: 1)
        end_line: Last line to read (inclusive, default: end of file)
        encoding: File encoding (default: utf-8)

    Returns:
        Dict with content (numbered lines), total_lines, and range info
    """
    try:
        target = _get_sandbox().resolve_path(path)

        if not target.exists():
            return {"error": f"File not found: {path}", "success": False}

        if not target.is_file():
            return {"error": f"Not a file: {path}", "success": False}

        with open(target, "r", encoding=encoding) as f:
            all_lines = f.readlines()

        total_lines = len(all_lines)

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
                "message": f"Start line {start_line} exceeds file length ({total_lines})"
            }

        selected_lines = all_lines[start_line - 1:end_line]

        numbered_content = ""
        for i, line in enumerate(selected_lines, start=start_line):
            line_text = line.rstrip('\n\r')
            numbered_content += f"{i:>6}: {line_text}\n"

        logger.info(f"Read lines {start_line}-{end_line} from {path}")

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
) -> Dict:
    """
    Edit a file by replacing a string with another string.

    Enables surgical edits without rewriting entire files.
    The old_string must be unique in the file (unless replace_all=True).

    Args:
        path: Path to file (relative to sandbox)
        old_string: Text to find and replace (must match exactly)
        new_string: Text to replace with (can be empty to delete)
        replace_all: Replace all occurrences (default: False)
        encoding: File encoding (default: utf-8)

    Returns:
        Dict with success status and edit details
    """
    try:
        target = _get_sandbox().resolve_path(path)

        if not target.exists():
            return {"error": f"File not found: {path}", "success": False}

        if not target.is_file():
            return {"error": f"Not a file: {path}", "success": False}

        with open(target, "r", encoding=encoding) as f:
            content = f.read()

        occurrences = content.count(old_string)

        if occurrences == 0:
            preview = old_string[:50] + ('...' if len(old_string) > 50 else '')
            return {
                "error": f"String not found in file: '{preview}'",
                "success": False
            }

        if occurrences > 1 and not replace_all:
            return {
                "error": (
                    f"String found {occurrences} times. "
                    "Use replace_all=True or provide more context."
                ),
                "success": False,
                "occurrences": occurrences
            }

        if replace_all:
            new_content = content.replace(old_string, new_string)
            replacements = occurrences
        else:
            new_content = content.replace(old_string, new_string, 1)
            replacements = 1

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


# Tool schemas for AI API registration
FILESYSTEM_TOOL_SCHEMAS = {
    "fs_read_file": {
        "name": "fs_read_file",
        "description": "Read the contents of a file from the sandbox directory",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file (relative to sandbox)"
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
                    "description": "Path to the file (relative to sandbox)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write"
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8"
                },
                "mode": {
                    "type": "string",
                    "enum": ["overwrite", "append"],
                    "description": "Write mode",
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
                    "description": "Directory path (default: '.')",
                    "default": "."
                },
                "recursive": {
                    "type": "boolean",
                    "description": "List recursively",
                    "default": False
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (default: '*')",
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
                    "description": "Directory path to create"
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
                    "description": "Path to delete"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Delete directories recursively",
                    "default": False
                }
            },
            "required": ["path"]
        }
    },
    "fs_exists": {
        "name": "fs_exists",
        "description": "Check if a file or directory exists",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to check"
                }
            },
            "required": ["path"]
        }
    },
    "fs_get_info": {
        "name": "fs_get_info",
        "description": "Get information about a file or directory",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to get info for"
                }
            },
            "required": ["path"]
        }
    },
    "fs_read_lines": {
        "name": "fs_read_lines",
        "description": "Read specific lines from a file with line numbers",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file"
                },
                "start_line": {
                    "type": "integer",
                    "description": "First line (1-indexed)",
                    "default": 1
                },
                "end_line": {
                    "type": "integer",
                    "description": "Last line (inclusive)"
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding",
                    "default": "utf-8"
                }
            },
            "required": ["path"]
        }
    },
    "fs_edit": {
        "name": "fs_edit",
        "description": "Edit a file by finding and replacing a string",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file"
                },
                "old_string": {
                    "type": "string",
                    "description": "Text to find and replace"
                },
                "new_string": {
                    "type": "string",
                    "description": "Replacement text"
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences",
                    "default": False
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding",
                    "default": "utf-8"
                }
            },
            "required": ["path", "old_string", "new_string"]
        }
    }
}
