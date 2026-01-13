"""
Tools Module

Collection of tools for Claude to use:
- Utilities: Time, calculator, string operations
- Filesystem: File/directory operations (sandboxed)
- Code Execution: Safe Python code execution
- Memory: Key-value memory storage
- Agents: Multi-agent spawning and Socratic council
- Vector Search: Semantic search and knowledge base
- Music: AI music generation via Suno API

Each tool module provides:
- Tool implementation functions
- TOOL_SCHEMAS dict with Claude-compatible schemas
"""

# Import tool functions
from .utilities import (
    get_current_time,
    calculator,
    reverse_string,
    count_words,
    random_number,
    session_info,
    UTILITY_TOOL_SCHEMAS,
)

from .filesystem import (
    fs_read_file,
    fs_write_file,
    fs_list_files,
    fs_mkdir,
    fs_delete,
    fs_exists,
    fs_get_info,
    fs_read_lines,
    fs_edit,
    FILESYSTEM_TOOL_SCHEMAS,
)

from .code_execution import (
    execute_python,
    execute_python_safe,
    execute_python_sandbox,
    sandbox_workspace_list,
    sandbox_workspace_read,
    sandbox_workspace_write,
    CODE_EXECUTION_TOOL_SCHEMAS,
)

from .memory import (
    memory_store,
    memory_retrieve,
    memory_list,
    memory_delete,
    memory_search,
    MEMORY_TOOL_SCHEMAS,
)

from .agents import (
    agent_spawn,
    agent_status,
    agent_result,
    agent_list,
    socratic_council,
    AGENT_TOOL_SCHEMAS,
)

from .vector_search import (
    vector_add,
    vector_search,
    vector_delete,
    vector_list_collections,
    vector_get_stats,
    vector_add_knowledge,
    vector_search_knowledge,
    vector_search_village,
    enrich_with_thread_context,
    memory_health_stale,
    memory_health_low_access,
    memory_health_duplicates,
    memory_consolidate,
    memory_migration_run,
    village_convergence_detect,
    forward_crumbs_get,
    forward_crumb_leave,
    VECTOR_TOOL_SCHEMAS,
)

from .music import (
    music_generate,
    music_status,
    music_result,
    music_list,
    # Curation tools (Phase 1.5)
    music_favorite,
    music_library,
    music_search,
    music_play,
    # Composition tools (Phase 2)
    midi_create,
    music_compose,
    MUSIC_TOOL_SCHEMAS,
)

from .datasets import (
    dataset_list,
    dataset_query,
    DATASET_LIST_SCHEMA,
    DATASET_QUERY_SCHEMA,
)

# Dataset tool schemas
DATASET_TOOL_SCHEMAS = {
    "dataset_list": DATASET_LIST_SCHEMA,
    "dataset_query": DATASET_QUERY_SCHEMA,
}

# Combine all schemas
ALL_TOOL_SCHEMAS = {
    **UTILITY_TOOL_SCHEMAS,
    **FILESYSTEM_TOOL_SCHEMAS,
    **CODE_EXECUTION_TOOL_SCHEMAS,
    **MEMORY_TOOL_SCHEMAS,
    **AGENT_TOOL_SCHEMAS,
    **VECTOR_TOOL_SCHEMAS,
    **MUSIC_TOOL_SCHEMAS,
    **DATASET_TOOL_SCHEMAS,
}

# Map tool names to functions
ALL_TOOLS = {
    # Utilities
    "get_current_time": get_current_time,
    "calculator": calculator,
    "reverse_string": reverse_string,
    "count_words": count_words,
    "random_number": random_number,
    "session_info": session_info,
    # Filesystem
    "fs_read_file": fs_read_file,
    "fs_write_file": fs_write_file,
    "fs_list_files": fs_list_files,
    "fs_mkdir": fs_mkdir,
    "fs_delete": fs_delete,
    "fs_exists": fs_exists,
    "fs_get_info": fs_get_info,
    "fs_read_lines": fs_read_lines,
    "fs_edit": fs_edit,
    # Code execution & Sandbox
    "execute_python": execute_python,
    "execute_python_safe": execute_python_safe,
    "execute_python_sandbox": execute_python_sandbox,
    "sandbox_workspace_list": sandbox_workspace_list,
    "sandbox_workspace_read": sandbox_workspace_read,
    "sandbox_workspace_write": sandbox_workspace_write,
    # Memory
    "memory_store": memory_store,
    "memory_retrieve": memory_retrieve,
    "memory_list": memory_list,
    "memory_delete": memory_delete,
    "memory_search": memory_search,
    # Agents
    "agent_spawn": agent_spawn,
    "agent_status": agent_status,
    "agent_result": agent_result,
    "agent_list": agent_list,
    "socratic_council": socratic_council,
    # Vector Search
    "vector_add": vector_add,
    "vector_search": vector_search,
    "vector_delete": vector_delete,
    "vector_list_collections": vector_list_collections,
    "vector_get_stats": vector_get_stats,
    "vector_add_knowledge": vector_add_knowledge,
    "vector_search_knowledge": vector_search_knowledge,
    "vector_search_village": vector_search_village,
    # Memory Health (Phase 3)
    "memory_health_stale": memory_health_stale,
    "memory_health_low_access": memory_health_low_access,
    "memory_health_duplicates": memory_health_duplicates,
    "memory_consolidate": memory_consolidate,
    "memory_migration_run": memory_migration_run,
    # Village Insights
    "village_convergence_detect": village_convergence_detect,
    # Forward Crumb Protocol
    "forward_crumbs_get": forward_crumbs_get,
    "forward_crumb_leave": forward_crumb_leave,
    # Music Generation
    "music_generate": music_generate,
    "music_status": music_status,
    "music_result": music_result,
    "music_list": music_list,
    # Music Curation (Phase 1.5)
    "music_favorite": music_favorite,
    "music_library": music_library,
    "music_search": music_search,
    "music_play": music_play,
    # Music Composition (Phase 2)
    "midi_create": midi_create,
    "music_compose": music_compose,
    # Dataset Tools
    "dataset_list": dataset_list,
    "dataset_query": dataset_query,
}

__all__ = [
    # Utilities
    "get_current_time",
    "calculator",
    "reverse_string",
    "count_words",
    "random_number",
    "session_info",
    # Filesystem
    "fs_read_file",
    "fs_write_file",
    "fs_list_files",
    "fs_mkdir",
    "fs_delete",
    "fs_exists",
    "fs_get_info",
    "fs_read_lines",
    "fs_edit",
    # Code execution & Sandbox
    "execute_python",
    "execute_python_safe",
    "execute_python_sandbox",
    "sandbox_workspace_list",
    "sandbox_workspace_read",
    "sandbox_workspace_write",
    # Memory
    "memory_store",
    "memory_retrieve",
    "memory_list",
    "memory_delete",
    "memory_search",
    # Agents
    "agent_spawn",
    "agent_status",
    "agent_result",
    "agent_list",
    "socratic_council",
    # Vector Search
    "vector_add",
    "vector_search",
    "vector_delete",
    "vector_list_collections",
    "vector_get_stats",
    "vector_add_knowledge",
    "vector_search_knowledge",
    "vector_search_village",
    "enrich_with_thread_context",
    # Memory Health
    "memory_health_stale",
    "memory_health_low_access",
    "memory_health_duplicates",
    "memory_consolidate",
    "memory_migration_run",
    # Village Insights
    "village_convergence_detect",
    # Forward Crumb Protocol
    "forward_crumbs_get",
    "forward_crumb_leave",
    # Music Generation
    "music_generate",
    "music_status",
    "music_result",
    "music_list",
    # Music Curation (Phase 1.5)
    "music_favorite",
    "music_library",
    "music_search",
    "music_play",
    # Music Composition (Phase 2)
    "midi_create",
    "music_compose",
    # Dataset Tools
    "dataset_list",
    "dataset_query",
    # Schemas
    "UTILITY_TOOL_SCHEMAS",
    "FILESYSTEM_TOOL_SCHEMAS",
    "CODE_EXECUTION_TOOL_SCHEMAS",
    "MEMORY_TOOL_SCHEMAS",
    "AGENT_TOOL_SCHEMAS",
    "VECTOR_TOOL_SCHEMAS",
    "MUSIC_TOOL_SCHEMAS",
    "DATASET_TOOL_SCHEMAS",
    "ALL_TOOL_SCHEMAS",
    "ALL_TOOLS",
]


def register_all_tools(registry):
    """
    Register all tools with a ToolRegistry.

    Args:
        registry: ToolRegistry instance from core.tool_processor

    Example:
        >>> from core import ToolRegistry
        >>> from tools import register_all_tools
        >>> registry = ToolRegistry()
        >>> register_all_tools(registry)
    """
    for name, func in ALL_TOOLS.items():
        schema = ALL_TOOL_SCHEMAS.get(name)
        registry.register(name, func, schema)
