"""
Dual-Mode Code Execution Tools for ApexAurum
=============================================

Provides both safe REPL and full Docker sandbox execution capabilities.

Tools:
- execute_python: Auto-selects between safe REPL and Docker sandbox
- execute_python_safe: Force safe REPL mode (instant, restricted)
- execute_python_sandbox: Force Docker sandbox (full capabilities)
- sandbox_workspace_list: List projects in persistent workspace
- sandbox_workspace_read: Read files from workspace
- sandbox_workspace_write: Write files to workspace

The system automatically chooses the best execution mode:
- SAFE mode: For simple math, json, string ops (instant, ~1ms)
- SANDBOX mode: For external packages, file I/O, network (Docker, ~2-5s)
"""

import logging
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Lazy-loaded sandbox manager instance
_sandbox_tools_instance = None


def _get_sandbox_tools():
    """Get or create the sandbox tools instance (lazy initialization)."""
    global _sandbox_tools_instance
    if _sandbox_tools_instance is None:
        from core.sandbox_manager import get_sandbox_manager, ExecutionMode
        workspace_path = os.environ.get('APEX_WORKSPACE', os.path.expanduser('~/apex_workspace'))
        _sandbox_tools_instance = {
            'manager': get_sandbox_manager(workspace_path=workspace_path),
            'ExecutionMode': ExecutionMode
        }
        logger.info(f"Sandbox tools initialized with workspace: {workspace_path}")
    return _sandbox_tools_instance


def execute_python(
    code: str,
    context: Dict[str, Any] = None,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Execute Python code with automatic mode selection.

    The system automatically chooses between:
    - SAFE mode: Fast, restricted execution for simple operations
    - SANDBOX mode: Full Python environment with any imports, file I/O

    Args:
        code: Python code to execute
        context: Variables to inject into execution context
        timeout: Max execution time in seconds (default: 300)

    Returns:
        Dict with success, stdout, stderr, return_value, files_created, mode_used

    Example:
        >>> execute_python("result = sum(range(100))")
        {"success": True, "return_value": 4950, "mode_used": "safe"}

        >>> execute_python("import pandas as pd; result = pd.DataFrame({'a': [1,2,3]}).sum().to_dict()")
        {"success": True, "return_value": {"a": 6}, "mode_used": "sandbox"}
    """
    try:
        tools = _get_sandbox_tools()
        result = tools['manager'].execute(
            code=code,
            mode=tools['ExecutionMode'].AUTO,
            context=context,
            timeout=timeout
        )
        return result.to_dict()
    except Exception as e:
        logger.error(f"execute_python failed: {e}")
        return {
            "success": False,
            "error": f"Execution setup failed: {str(e)}",
            "stdout": "",
            "stderr": "",
            "return_value": None,
            "mode_used": "error"
        }


def execute_python_safe(
    code: str,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Execute Python in restricted safe REPL mode.

    Use this for simple, fast operations that don't need external packages:
    - Math calculations
    - String manipulation
    - JSON parsing
    - List/dict operations
    - Using: math, json, re, datetime, collections, itertools

    This mode is instant (no container startup) but restricted.

    Args:
        code: Python code to execute
        context: Variables to inject

    Returns:
        Dict with success, stdout, stderr, return_value

    Example:
        >>> execute_python_safe("import math; result = math.sqrt(16)")
        {"success": True, "return_value": 4.0, "mode_used": "safe"}
    """
    try:
        tools = _get_sandbox_tools()
        result = tools['manager'].execute(
            code=code,
            mode=tools['ExecutionMode'].SAFE,
            context=context,
            timeout=30
        )
        return result.to_dict()
    except Exception as e:
        logger.error(f"execute_python_safe failed: {e}")
        return {
            "success": False,
            "error": f"Safe execution failed: {str(e)}",
            "stdout": "",
            "stderr": "",
            "return_value": None,
            "mode_used": "safe"
        }


def execute_python_sandbox(
    code: str,
    network: bool = False,
    timeout: int = 300,
    packages: List[str] = None,
    working_dir: str = None,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Execute Python in full isolated Docker sandbox.

    Use this when you need:
    - Any Python package (numpy, pandas, requests, opencv, etc.)
    - File I/O operations
    - Subprocess/shell commands
    - Network access (when enabled)
    - Complex multi-file projects

    The sandbox provides full Python capabilities in an isolated Docker container.
    Packages are auto-installed if not present.

    Args:
        code: Python code to execute
        network: Enable network access (default: False)
        timeout: Max execution time in seconds (default: 300)
        packages: List of packages to ensure are installed
        working_dir: Project subdirectory in workspace
        context: Variables to inject

    Returns:
        Dict with success, stdout, stderr, return_value, files_created

    Example:
        >>> execute_python_sandbox('''
        ... import pandas as pd
        ... import numpy as np
        ... df = pd.DataFrame({'x': np.random.randn(100)})
        ... df.to_csv('/workspace/outputs/data.csv')
        ... result = df.describe().to_dict()
        ... ''')
        {"success": True, "files_created": ["data.csv"], "mode_used": "sandbox"}
    """
    try:
        tools = _get_sandbox_tools()
        result = tools['manager'].execute(
            code=code,
            mode=tools['ExecutionMode'].SANDBOX,
            network=network,
            timeout=timeout,
            context=context,
            working_dir=working_dir,
            packages=packages
        )
        return result.to_dict()
    except Exception as e:
        logger.error(f"execute_python_sandbox failed: {e}")
        return {
            "success": False,
            "error": f"Sandbox execution failed: {str(e)}",
            "stdout": "",
            "stderr": "",
            "return_value": None,
            "files_created": [],
            "mode_used": "sandbox"
        }


def sandbox_workspace_list() -> Dict[str, Any]:
    """
    List all projects in the persistent sandbox workspace.

    Returns information about saved projects including name, file count,
    and last modified time.

    Returns:
        Dict with success, projects list, workspace_path

    Example:
        >>> sandbox_workspace_list()
        {
            "success": True,
            "projects": [
                {"name": "analysis", "files": 5, "modified": 1704067200},
                {"name": "web_scraper", "files": 3, "modified": 1704060000}
            ],
            "workspace_path": "/home/llm/apex_workspace"
        }
    """
    try:
        tools = _get_sandbox_tools()
        projects = tools['manager'].list_workspace_projects()
        return {
            "success": True,
            "projects": projects,
            "workspace_path": tools['manager'].config.workspace_path
        }
    except Exception as e:
        logger.error(f"sandbox_workspace_list failed: {e}")
        return {"success": False, "error": str(e)}


def sandbox_workspace_read(path: str) -> Dict[str, Any]:
    """
    Read a file from the sandbox workspace.

    Args:
        path: Relative path within workspace (e.g., "projects/myproject/main.py")

    Returns:
        Dict with success and content or error

    Example:
        >>> sandbox_workspace_read("projects/analysis/results.json")
        {"success": True, "content": "{\"accuracy\": 0.95}", "path": "/home/llm/apex_workspace/projects/analysis/results.json"}
    """
    try:
        tools = _get_sandbox_tools()
        workspace = Path(tools['manager'].config.workspace_path)
        full_path = (workspace / path).resolve()

        # Security check - ensure path is within workspace
        if not str(full_path).startswith(str(workspace.resolve())):
            return {"success": False, "error": "Path outside workspace"}

        if not full_path.exists():
            return {"success": False, "error": f"File not found: {path}"}

        content = full_path.read_text()
        return {"success": True, "content": content, "path": str(full_path)}

    except Exception as e:
        logger.error(f"sandbox_workspace_read failed: {e}")
        return {"success": False, "error": str(e)}


def sandbox_workspace_write(path: str, content: str) -> Dict[str, Any]:
    """
    Write a file to the sandbox workspace.

    Args:
        path: Relative path within workspace
        content: File content to write

    Returns:
        Dict with success and full path or error

    Example:
        >>> sandbox_workspace_write("projects/notes.txt", "Hello from sandbox!")
        {"success": True, "path": "/home/llm/apex_workspace/projects/notes.txt"}
    """
    try:
        tools = _get_sandbox_tools()
        workspace = Path(tools['manager'].config.workspace_path)
        full_path = (workspace / path).resolve()

        # Security check
        if not str(full_path).startswith(str(workspace.resolve())):
            return {"success": False, "error": "Path outside workspace"}

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        full_path.write_text(content)
        return {"success": True, "path": str(full_path)}

    except Exception as e:
        logger.error(f"sandbox_workspace_write failed: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Tool Schemas for Registration
# =============================================================================

CODE_EXECUTION_TOOL_SCHEMAS = {
    "execute_python": {
        "name": "execute_python",
        "description": """Execute Python code with automatic mode selection.

The system automatically chooses between:
• SAFE mode (instant): For simple math, json, string ops, datetime
  - Available modules: math, json, re, datetime, collections, itertools
  - No external imports, no file I/O, no network

• SANDBOX mode (Docker): For complex operations
  - ANY Python package (numpy, pandas, requests, opencv, etc.)
  - File I/O to persistent /workspace directory
  - Packages auto-install if missing

Set a variable named 'result' to capture the return value.

Examples:
- Simple: execute_python(code="result = sum(range(100))")  → uses SAFE mode
- Complex: execute_python(code="import pandas as pd; ...")  → uses SANDBOX mode""",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "context": {
                    "type": "object",
                    "description": "Variables to inject into execution context"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds",
                    "default": 300
                }
            },
            "required": ["code"]
        }
    },
    "execute_python_safe": {
        "name": "execute_python_safe",
        "description": """Execute Python in restricted safe REPL mode (instant, no Docker).

Use for simple, fast operations:
- Math calculations (math module available)
- String manipulation
- JSON parsing (json module available)
- Date/time operations (datetime module available)
- List/dict operations
- Regex (re module available)

This mode is instant (~1ms) but restricted - no external packages, no file I/O.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "context": {
                    "type": "object",
                    "description": "Variables to inject"
                }
            },
            "required": ["code"]
        }
    },
    "execute_python_sandbox": {
        "name": "execute_python_sandbox",
        "description": """Execute Python in full isolated Docker sandbox.

Use when you need:
- Any Python package (numpy, pandas, requests, opencv, scikit-learn, etc.)
- File I/O operations (save to /workspace for persistence)
- Subprocess/shell commands
- Network access (set network=True)
- Complex multi-file projects

Pre-installed packages: numpy, pandas, scipy, matplotlib, seaborn, scikit-learn,
requests, beautifulsoup4, pillow, and more.

Workspace at /workspace is persistent across executions.
Use working_dir parameter to organize into project subdirectories.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "network": {
                    "type": "boolean",
                    "description": "Enable network access",
                    "default": False
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds",
                    "default": 300
                },
                "packages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Packages to ensure are installed"
                },
                "working_dir": {
                    "type": "string",
                    "description": "Project subdirectory name in workspace"
                },
                "context": {
                    "type": "object",
                    "description": "Variables to inject"
                }
            },
            "required": ["code"]
        }
    },
    "sandbox_workspace_list": {
        "name": "sandbox_workspace_list",
        "description": """List all projects in the persistent sandbox workspace.

Returns information about saved projects including name, file count,
and last modified time. Use this to see what projects exist.""",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "sandbox_workspace_read": {
        "name": "sandbox_workspace_read",
        "description": """Read a file from the sandbox workspace.

Use to retrieve files created by sandbox executions or to inspect project contents.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path within workspace (e.g., 'projects/myproject/main.py')"
                }
            },
            "required": ["path"]
        }
    },
    "sandbox_workspace_write": {
        "name": "sandbox_workspace_write",
        "description": """Write a file to the sandbox workspace.

Use to create or update files that can be accessed by sandbox executions.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path within workspace"
                },
                "content": {
                    "type": "string",
                    "description": "File content to write"
                }
            },
            "required": ["path", "content"]
        }
    }
}
