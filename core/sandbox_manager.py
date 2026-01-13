"""
Sandbox Manager for ApexAurum
=============================
Provides isolated Python execution environment using Docker containers.
Designed for Raspberry Pi 5 (ARM64) with persistent workspace support.

Features:
- Dual-mode execution (safe REPL vs full sandbox)
- Persistent workspace across executions
- Configurable network access
- Resource limits (CPU, memory, time)
- Package installation on-the-fly
- Artifact capture (files, plots, outputs)
"""

import docker
import os
import json
import tempfile
import shutil
import time
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import threading
import queue

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    SAFE = "safe"           # Current restricted REPL
    SANDBOX = "sandbox"     # Full Docker container
    AUTO = "auto"           # Let the system decide based on code analysis


@dataclass
class ExecutionResult:
    """Result from code execution"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    files_created: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    mode_used: ExecutionMode = ExecutionMode.SAFE
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_value": self.return_value,
            "files_created": self.files_created,
            "execution_time": self.execution_time,
            "mode_used": self.mode_used.value,
            "error": self.error
        }


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution"""
    # Resource limits
    cpu_limit: float = 1.0          # Number of CPUs (0.5 = half a core)
    memory_limit: str = "1g"        # Memory limit (e.g., "512m", "1g")
    timeout: int = 300              # Execution timeout in seconds
    
    # Network
    network_enabled: bool = False   # Allow network access
    
    # Workspace
    workspace_path: str = ""        # Host path for persistent workspace
    
    # Container settings
    image_name: str = "apex-sandbox:latest"
    auto_install_packages: bool = True  # pip install missing packages
    
    # What to capture
    capture_plots: bool = True      # Capture matplotlib figures
    capture_files: bool = True      # Track created files


class SandboxManager:
    """
    Manages Docker-based sandbox execution for ApexAurum agents.
    
    Usage:
        manager = SandboxManager(workspace_path="/home/pi/apex_workspace")
        result = manager.execute(code, network=True)
    """
    
    def __init__(
        self,
        workspace_path: str = None,
        config: SandboxConfig = None
    ):
        self.config = config or SandboxConfig()
        
        # Set up workspace
        if workspace_path:
            self.config.workspace_path = workspace_path
        elif not self.config.workspace_path:
            self.config.workspace_path = os.path.expanduser("~/apex_workspace")
        
        # Ensure workspace exists
        self._setup_workspace()
        
        # Docker client (lazy init)
        self._docker_client = None
        self._container_pool: List[str] = []
        self._pool_lock = threading.Lock()
        
        # Track installed packages per session
        self._installed_packages: set = set()
        
        logger.info(f"SandboxManager initialized with workspace: {self.config.workspace_path}")
    
    @property
    def docker_client(self):
        """Lazy initialization of Docker client"""
        if self._docker_client is None:
            try:
                self._docker_client = docker.from_env()
                # Verify connection
                self._docker_client.ping()
                logger.info("Docker client connected successfully")
            except docker.errors.DockerException as e:
                logger.error(f"Failed to connect to Docker: {e}")
                raise RuntimeError(
                    "Docker is not available. Please ensure Docker is installed and running.\n"
                    "On Pi: sudo apt install docker.io && sudo usermod -aG docker $USER"
                ) from e
        return self._docker_client
    
    def _setup_workspace(self):
        """Create workspace directory structure"""
        workspace = Path(self.config.workspace_path)
        
        # Main directories
        (workspace / "projects").mkdir(parents=True, exist_ok=True)
        (workspace / "outputs").mkdir(exist_ok=True)
        (workspace / "data").mkdir(exist_ok=True)
        (workspace / "temp").mkdir(exist_ok=True)
        (workspace / ".cache").mkdir(exist_ok=True)  # For pip cache
        
        logger.info(f"Workspace ready at {workspace}")
    
    def _analyze_code(self, code: str) -> Dict[str, Any]:
        """
        Analyze code to determine execution requirements.
        Used for AUTO mode and to detect needed packages.
        """
        analysis = {
            "needs_sandbox": False,
            "imports": [],
            "uses_subprocess": False,
            "uses_file_io": False,
            "uses_network": False,
            "risky_operations": []
        }
        
        # Simple heuristic analysis
        lines = code.lower()
        
        # Check for imports
        import_keywords = ["import ", "from "]
        for line in code.split("\n"):
            stripped = line.strip()
            for kw in import_keywords:
                if stripped.startswith(kw):
                    # Extract module name
                    if stripped.startswith("from "):
                        module = stripped.split()[1].split(".")[0]
                    else:
                        module = stripped.split()[1].split(".")[0].split(",")[0]
                    analysis["imports"].append(module)
        
        # Check for operations that need sandbox
        sandbox_indicators = [
            ("subprocess", "uses_subprocess"),
            ("os.system", "uses_subprocess"),
            ("popen", "uses_subprocess"),
            ("open(", "uses_file_io"),
            ("pathlib", "uses_file_io"),
            ("requests", "uses_network"),
            ("urllib", "uses_network"),
            ("socket", "uses_network"),
            ("http", "uses_network"),
        ]
        
        for indicator, flag in sandbox_indicators:
            if indicator in lines:
                analysis[flag] = True
                analysis["needs_sandbox"] = True
        
        # Non-whitelisted imports need sandbox
        safe_modules = {
            "math", "json", "re", "datetime", "collections",
            "itertools", "functools", "string", "random"
        }
        for imp in analysis["imports"]:
            if imp not in safe_modules:
                analysis["needs_sandbox"] = True
                break
        
        return analysis
    
    def execute(
        self,
        code: str,
        mode: Union[ExecutionMode, str] = ExecutionMode.AUTO,
        network: bool = None,
        timeout: int = None,
        context: Dict[str, Any] = None,
        working_dir: str = None,
        packages: List[str] = None
    ) -> ExecutionResult:
        """
        Execute Python code in the appropriate environment.
        
        Args:
            code: Python code to execute
            mode: SAFE, SANDBOX, or AUTO
            network: Override network access setting
            timeout: Override timeout setting
            context: Variables to inject into execution context
            working_dir: Subdirectory within workspace to use
            packages: Additional packages to ensure are installed
            
        Returns:
            ExecutionResult with stdout, stderr, files, etc.
        """
        start_time = time.time()
        
        # Convert string mode to enum
        if isinstance(mode, str):
            mode = ExecutionMode(mode.lower())
        
        # Auto-detect mode if needed
        if mode == ExecutionMode.AUTO:
            analysis = self._analyze_code(code)
            mode = ExecutionMode.SANDBOX if analysis["needs_sandbox"] else ExecutionMode.SAFE
            logger.debug(f"Auto-detected mode: {mode.value} (analysis: {analysis})")
        
        # Route to appropriate executor
        if mode == ExecutionMode.SAFE:
            result = self._execute_safe(code, context, timeout)
        else:
            result = self._execute_sandbox(
                code=code,
                network=network if network is not None else self.config.network_enabled,
                timeout=timeout or self.config.timeout,
                context=context,
                working_dir=working_dir,
                packages=packages
            )
        
        result.execution_time = time.time() - start_time
        result.mode_used = mode
        
        return result
    
    def _execute_safe(
        self,
        code: str,
        context: Dict[str, Any] = None,
        timeout: int = None
    ) -> ExecutionResult:
        """
        Execute in restricted safe REPL (current ApexAurum behavior).
        This is a simplified version - integrate with your existing safe executor.
        """
        import io
        import contextlib
        import math
        import json as json_module
        import re
        import datetime
        import collections
        import itertools
        import functools
        import random
        import string

        timeout = timeout or 30

        # Safe modules that can be imported
        safe_modules = {
            "math": math,
            "json": json_module,
            "re": re,
            "datetime": datetime,
            "collections": collections,
            "itertools": itertools,
            "functools": functools,
            "random": random,
            "string": string,
        }

        # Restricted __import__ that only allows safe modules
        def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name in safe_modules:
                return safe_modules[name]
            raise ImportError(f"Import of '{name}' is not allowed in safe mode. Use sandbox mode for external packages.")

        # Restricted globals
        safe_builtins = {
            "abs": abs, "all": all, "any": any, "bool": bool,
            "dict": dict, "enumerate": enumerate, "filter": filter,
            "float": float, "int": int, "len": len, "list": list,
            "map": map, "max": max, "min": min, "pow": pow,
            "print": print, "range": range, "round": round,
            "set": set, "sorted": sorted, "str": str, "sum": sum,
            "tuple": tuple, "type": type, "zip": zip,
            "True": True, "False": False, "None": None,
            "__import__": restricted_import,
        }

        safe_globals = {
            "__builtins__": safe_builtins,
            # Pre-load safe modules so they're available without import
            **safe_modules,
        }
        
        # Add context
        if context:
            safe_globals.update(context)
        
        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        local_vars = {}
        
        try:
            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):
                exec(code, safe_globals, local_vars)
            
            # Get return value if '_result' was set
            return_value = local_vars.get("_result", local_vars.get("result"))
            
            return ExecutionResult(
                success=True,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                return_value=return_value
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                error=f"{type(e).__name__}: {str(e)}"
            )
    
    def _execute_sandbox(
        self,
        code: str,
        network: bool,
        timeout: int,
        context: Dict[str, Any] = None,
        working_dir: str = None,
        packages: List[str] = None
    ) -> ExecutionResult:
        """Execute code in Docker container with full capabilities."""
        
        container = None
        temp_dir = None
        
        try:
            # Prepare workspace path
            workspace = Path(self.config.workspace_path)
            if working_dir:
                work_path = workspace / "projects" / working_dir
                work_path.mkdir(parents=True, exist_ok=True)
            else:
                work_path = workspace / "temp"
            
            # Create temp directory for this execution
            temp_dir = tempfile.mkdtemp(dir=work_path)
            
            # Write the code to execute
            code_file = Path(temp_dir) / "script.py"
            
            # Wrap code with context injection and result capture
            wrapped_code = self._wrap_code(code, context, packages)
            code_file.write_text(wrapped_code)
            
            # Prepare container configuration
            container_config = {
                "image": self.config.image_name,
                "command": ["python", "/execution/script.py"],
                "volumes": {
                    temp_dir: {"bind": "/execution", "mode": "rw"},
                    str(workspace): {"bind": "/workspace", "mode": "rw"},
                    str(workspace / ".cache"): {"bind": "/root/.cache/pip", "mode": "rw"},
                },
                "working_dir": "/execution",
                "detach": True,
                "mem_limit": self.config.memory_limit,
                "nano_cpus": int(self.config.cpu_limit * 1e9),
                "network_mode": "bridge" if network else "none",
                "environment": {
                    "PYTHONUNBUFFERED": "1",
                    "PIP_CACHE_DIR": "/root/.cache/pip",
                },
            }
            
            # Start container
            container = self.docker_client.containers.run(**container_config)
            
            # Wait for completion with timeout
            try:
                exit_result = container.wait(timeout=timeout)
                exit_code = exit_result.get("StatusCode", -1)
            except Exception as e:
                # Timeout or other error
                container.kill()
                return ExecutionResult(
                    success=False,
                    error=f"Execution timeout ({timeout}s) or error: {str(e)}"
                )
            
            # Capture logs
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            
            # Check for result file
            result_file = Path(temp_dir) / "_result.json"
            return_value = None
            if result_file.exists():
                try:
                    return_value = json.loads(result_file.read_text())
                except:
                    pass
            
            # Find created files
            files_created = []
            if self.config.capture_files:
                for f in Path(temp_dir).rglob("*"):
                    if f.is_file() and f.name not in ["script.py", "_result.json"]:
                        files_created.append(str(f.relative_to(temp_dir)))
            
            return ExecutionResult(
                success=(exit_code == 0),
                stdout=stdout,
                stderr=stderr,
                return_value=return_value,
                files_created=files_created,
                error=None if exit_code == 0 else f"Exit code: {exit_code}"
            )
            
        except docker.errors.ImageNotFound:
            return ExecutionResult(
                success=False,
                error=f"Sandbox image '{self.config.image_name}' not found. "
                      f"Please build it first: docker build -t {self.config.image_name} ."
            )
        except Exception as e:
            logger.exception("Sandbox execution failed")
            return ExecutionResult(
                success=False,
                error=f"Sandbox error: {type(e).__name__}: {str(e)}"
            )
        finally:
            # Cleanup container
            if container:
                try:
                    container.remove(force=True)
                except:
                    pass
    
    def _wrap_code(
        self,
        code: str,
        context: Dict[str, Any] = None,
        packages: List[str] = None
    ) -> str:
        """Wrap user code with setup and result capture"""
        
        lines = []
        
        # Package installation
        if packages or self.config.auto_install_packages:
            lines.append("""
import subprocess
import sys

def ensure_packages(packages):
    for pkg in packages:
        try:
            __import__(pkg.split('[')[0].replace('-', '_'))
        except ImportError:
            print(f"Installing {pkg}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                pkg, "-q", "--disable-pip-version-check"
            ])
""")
            if packages:
                lines.append(f"ensure_packages({packages!r})")
        
        # Auto-detect and install imports
        if self.config.auto_install_packages:
            # Extract imports from code
            imports = []
            for line in code.split("\n"):
                stripped = line.strip()
                if stripped.startswith("import "):
                    mod = stripped.split()[1].split(".")[0].split(",")[0]
                    imports.append(mod)
                elif stripped.startswith("from "):
                    mod = stripped.split()[1].split(".")[0]
                    imports.append(mod)
            
            if imports:
                # Map common import names to pip packages
                pip_names = {
                    "cv2": "opencv-python",
                    "PIL": "Pillow",
                    "sklearn": "scikit-learn",
                    "yaml": "pyyaml",
                    "bs4": "beautifulsoup4",
                }
                pip_packages = [pip_names.get(m, m) for m in imports]
                lines.append(f"""
try:
    ensure_packages({pip_packages!r})
except Exception as e:
    print(f"Warning: Package installation issue: {{e}}")
""")
        
        # Context injection
        if context:
            lines.append(f"\n# Injected context")
            lines.append(f"__context__ = {json.dumps(context)}")
            for key, value in context.items():
                if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                    lines.append(f"{key} = __context__[{key!r}]")
        
        # Setup for plot capture
        if self.config.capture_plots:
            lines.append("""
import sys
import os

# Configure matplotlib for headless operation
import matplotlib
matplotlib.use('Agg')

# Patch plt.show() to save figures
_figure_count = [0]
_original_show = None

def _capture_show():
    import matplotlib.pyplot as plt
    _figure_count[0] += 1
    filename = f"figure_{_figure_count[0]}.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"[Saved figure: {filename}]")
    plt.close()

try:
    import matplotlib.pyplot as plt
    _original_show = plt.show
    plt.show = _capture_show
except:
    pass
""")
        
        # The actual user code
        lines.append("\n# ===== User Code =====")
        lines.append(code)
        lines.append("# ===== End User Code =====\n")
        
        # Result capture
        lines.append("""
# Save result if defined
import json
_result_vars = ['result', '_result', 'output', '_output']
for _var in _result_vars:
    if _var in dir() and _var in locals():
        try:
            _val = locals()[_var]
            with open('_result.json', 'w') as f:
                json.dump(_val, f, default=str)
            break
        except:
            pass
""")
        
        return "\n".join(lines)
    
    def build_image(self, force: bool = False) -> bool:
        """Build the sandbox Docker image"""
        
        # Check if image exists
        if not force:
            try:
                self.docker_client.images.get(self.config.image_name)
                logger.info(f"Image {self.config.image_name} already exists")
                return True
            except docker.errors.ImageNotFound:
                pass
        
        logger.info(f"Building sandbox image: {self.config.image_name}")
        
        # Dockerfile content
        dockerfile = """
FROM python:3.11-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    git \\
    curl \\
    libffi-dev \\
    libssl-dev \\
    && rm -rf /var/lib/apt/lists/*

# Install common Python packages
RUN pip install --no-cache-dir \\
    numpy \\
    pandas \\
    matplotlib \\
    seaborn \\
    scipy \\
    scikit-learn \\
    requests \\
    beautifulsoup4 \\
    lxml \\
    pyyaml \\
    python-dotenv \\
    tqdm \\
    pillow \\
    httpx

# Create workspace
WORKDIR /workspace

# Default command
CMD ["python"]
"""
        
        # Create temp build context
        with tempfile.TemporaryDirectory() as build_dir:
            dockerfile_path = Path(build_dir) / "Dockerfile"
            dockerfile_path.write_text(dockerfile)
            
            try:
                image, logs = self.docker_client.images.build(
                    path=build_dir,
                    tag=self.config.image_name,
                    rm=True,
                    platform="linux/arm64"  # For Pi 5
                )
                
                for log in logs:
                    if "stream" in log:
                        logger.debug(log["stream"].strip())
                
                logger.info(f"Successfully built {self.config.image_name}")
                return True
                
            except docker.errors.BuildError as e:
                logger.error(f"Failed to build image: {e}")
                return False
    
    def cleanup_workspace(self, older_than_days: int = 7):
        """Clean up old temp files in workspace"""
        import time
        
        temp_dir = Path(self.config.workspace_path) / "temp"
        cutoff = time.time() - (older_than_days * 86400)
        
        cleaned = 0
        for item in temp_dir.iterdir():
            if item.is_dir() and item.stat().st_mtime < cutoff:
                shutil.rmtree(item)
                cleaned += 1
        
        logger.info(f"Cleaned up {cleaned} old temp directories")
        return cleaned
    
    def list_workspace_projects(self) -> List[Dict]:
        """List all projects in workspace"""
        projects_dir = Path(self.config.workspace_path) / "projects"
        projects = []
        
        for item in projects_dir.iterdir():
            if item.is_dir():
                projects.append({
                    "name": item.name,
                    "path": str(item),
                    "files": len(list(item.rglob("*"))),
                    "modified": item.stat().st_mtime
                })
        
        return sorted(projects, key=lambda x: x["modified"], reverse=True)


# Convenience function for direct use
_default_manager: Optional[SandboxManager] = None

def get_sandbox_manager(**kwargs) -> SandboxManager:
    """Get or create the default sandbox manager"""
    global _default_manager
    if _default_manager is None:
        _default_manager = SandboxManager(**kwargs)
    return _default_manager


def execute_python(
    code: str,
    mode: str = "auto",
    network: bool = False,
    timeout: int = 300,
    context: dict = None
) -> dict:
    """
    Convenience function for executing Python code.
    
    This is the main entry point for ApexAurum tools.
    
    Args:
        code: Python code to execute
        mode: "safe", "sandbox", or "auto"
        network: Allow network access (sandbox mode only)
        timeout: Execution timeout in seconds
        context: Variables to inject
        
    Returns:
        dict with success, stdout, stderr, return_value, etc.
    """
    manager = get_sandbox_manager()
    result = manager.execute(
        code=code,
        mode=mode,
        network=network,
        timeout=timeout,
        context=context
    )
    return result.to_dict()
