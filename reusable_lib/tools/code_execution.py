"""
Safe Python Code Execution
==========================

Lightweight code execution with safety restrictions.
No Docker required - uses restricted execution environment.

Tools:
- execute_python: Execute Python code with safety restrictions
"""

import logging
import sys
import io
import traceback
import signal
from typing import Dict, Any, Optional
from contextlib import redirect_stdout, redirect_stderr

logger = logging.getLogger(__name__)

# Allowed modules for safe execution
SAFE_MODULES = {
    'math', 'json', 're', 'datetime', 'collections', 'itertools',
    'functools', 'operator', 'string', 'random', 'statistics',
    'decimal', 'fractions', 'copy', 'pprint', 'textwrap',
    'unicodedata', 'hashlib', 'base64', 'binascii', 'struct',
}

# Blocked builtins for security
BLOCKED_BUILTINS = {
    'exec', 'eval', 'compile', 'open', 'input', '__import__',
    'breakpoint', 'globals', 'locals', 'vars', 'dir',
    'getattr', 'setattr', 'delattr', 'hasattr',
}


class TimeoutError(Exception):
    """Raised when code execution times out."""
    pass


def _timeout_handler(signum, frame):
    """Signal handler for execution timeout."""
    raise TimeoutError("Code execution timed out")


def _create_safe_globals() -> Dict[str, Any]:
    """Create a restricted globals dict for safe execution."""
    safe_builtins = {
        k: v for k, v in __builtins__.items()
        if k not in BLOCKED_BUILTINS
    } if isinstance(__builtins__, dict) else {
        k: getattr(__builtins__, k) for k in dir(__builtins__)
        if k not in BLOCKED_BUILTINS and not k.startswith('_')
    }

    # Add safe modules
    safe_globals = {'__builtins__': safe_builtins}

    for mod_name in SAFE_MODULES:
        try:
            safe_globals[mod_name] = __import__(mod_name)
        except ImportError:
            pass

    return safe_globals


def _check_code_safety(code: str) -> Optional[str]:
    """
    Check code for potentially dangerous patterns.
    Returns error message if unsafe, None if OK.
    """
    dangerous_patterns = [
        ('import os', 'os module not allowed'),
        ('import sys', 'sys module not allowed'),
        ('import subprocess', 'subprocess not allowed'),
        ('import socket', 'socket not allowed'),
        ('import shutil', 'shutil not allowed'),
        ('__import__', '__import__ not allowed'),
        ('exec(', 'exec not allowed'),
        ('eval(', 'eval not allowed'),
        ('open(', 'open() not allowed - use fs_* tools for file operations'),
        ('compile(', 'compile not allowed'),
    ]

    for pattern, msg in dangerous_patterns:
        if pattern in code:
            return msg

    return None


def execute_python(
    code: str,
    timeout: int = 30,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute Python code in a restricted environment.

    Safe for simple operations:
    - Math calculations
    - String manipulation
    - JSON parsing
    - Date/time operations
    - List/dict operations
    - Regex matching

    Available modules: math, json, re, datetime, collections, itertools,
    functools, random, statistics, decimal, hashlib, base64, and more.

    Args:
        code: Python code to execute
        timeout: Max execution time in seconds (default: 30)
        context: Variables to inject into execution context

    Returns:
        Dict with success, stdout, stderr, return_value, error

    Example:
        >>> execute_python("result = sum(range(100))")
        {"success": True, "return_value": 4950, "stdout": "", "stderr": ""}

        >>> execute_python("import math; result = math.sqrt(16)")
        {"success": True, "return_value": 4.0, "stdout": "", "stderr": ""}
    """
    # Check for dangerous patterns
    safety_error = _check_code_safety(code)
    if safety_error:
        return {
            "success": False,
            "error": f"Security violation: {safety_error}",
            "stdout": "",
            "stderr": "",
            "return_value": None
        }

    # Create restricted execution environment
    safe_globals = _create_safe_globals()
    local_vars = {}

    # Inject context variables
    if context:
        local_vars.update(context)

    # Capture stdout/stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    result = {
        "success": False,
        "stdout": "",
        "stderr": "",
        "return_value": None,
        "error": None
    }

    # Set up timeout (Unix only)
    old_handler = None
    try:
        if hasattr(signal, 'SIGALRM'):
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)
    except (ValueError, OSError):
        # Can't set signal in some environments (e.g., threads)
        pass

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, safe_globals, local_vars)

        result["success"] = True
        result["stdout"] = stdout_capture.getvalue()
        result["stderr"] = stderr_capture.getvalue()

        # Extract result variable if set
        if 'result' in local_vars:
            result["return_value"] = local_vars['result']

    except TimeoutError:
        result["error"] = f"Execution timed out after {timeout} seconds"
        result["stderr"] = stderr_capture.getvalue()

    except SyntaxError as e:
        result["error"] = f"Syntax error: {e}"
        result["stderr"] = traceback.format_exc()

    except NameError as e:
        result["error"] = f"Name error: {e}"
        result["stderr"] = traceback.format_exc()

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        result["stderr"] = traceback.format_exc()

    finally:
        # Cancel timeout
        if old_handler is not None:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    return result


# =============================================================================
# Tool Schema
# =============================================================================

CODE_EXECUTION_TOOL_SCHEMAS = {
    "execute_python": {
        "name": "execute_python",
        "description": """Execute Python code in a restricted safe environment.

Safe for:
- Math calculations (math module available)
- String manipulation
- JSON parsing (json module available)
- Date/time operations (datetime module available)
- List/dict operations
- Regex (re module available)
- Random numbers (random module available)
- Statistics (statistics module available)
- Encoding (base64, hashlib available)

NOT available (for security):
- File I/O (use fs_* tools instead)
- Network access
- System commands
- External packages

Set a variable named 'result' to capture the return value.

Modules are PRE-LOADED (no import needed):
  math, json, re, datetime, collections, itertools, functools,
  random, statistics, decimal, hashlib, base64, string, copy

Examples:
- Math: execute_python(code="result = math.sqrt(16)")
- JSON: execute_python(code="result = json.loads('{\"a\": 1}')")
- Date: execute_python(code="result = datetime.datetime.now().isoformat()")
- Stats: execute_python(code="result = statistics.mean([1,2,3,4,5])")""",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max execution time in seconds (default: 30)",
                    "default": 30
                },
                "context": {
                    "type": "object",
                    "description": "Variables to inject into execution context"
                }
            },
            "required": ["code"]
        }
    }
}
