# Tools - Reusable AI tool implementations
# Extracted from ApexAurum - Claude Edition
# Ready-to-use tools with schemas for Claude/OpenAI function calling

from .utilities import (
    get_current_time,
    calculator,
    reverse_string,
    count_words,
    random_number,
    random_choice,
    set_session_info_config,
    session_info,
    UTILITY_TOOL_SCHEMAS
)
from .memory import (
    SimpleMemory,
    memory_store,
    memory_retrieve,
    memory_list,
    memory_delete,
    memory_search,
    MEMORY_TOOL_SCHEMAS
)
from .filesystem import (
    FilesystemSandbox,
    set_sandbox_path,
    get_sandbox_path,
    fs_read_file,
    fs_write_file,
    fs_list_files,
    fs_mkdir,
    fs_delete,
    fs_exists,
    fs_get_info,
    fs_read_lines,
    fs_edit,
    FILESYSTEM_TOOL_SCHEMAS
)
from .code_execution import (
    execute_python,
    CODE_EXECUTION_TOOL_SCHEMAS
)
from .strings import (
    string_replace,
    string_split,
    string_join,
    regex_match,
    regex_replace,
    string_case,
    STRING_TOOL_SCHEMAS
)
from .web import (
    web_fetch,
    web_search,
    WEB_TOOL_SCHEMAS
)
from .vector_search import (
    set_vector_db_path,
    vector_add,
    vector_search,
    vector_delete,
    vector_list_collections,
    vector_get_stats,
    vector_add_knowledge,
    vector_search_knowledge,
    VECTOR_TOOL_SCHEMAS
)
from .agents import (
    set_agent_api,
    set_agent_storage_path,
    set_agent_default_model,
    agent_spawn,
    agent_status,
    agent_result,
    agent_list,
    socratic_council,
    AGENT_TOOL_SCHEMAS
)
from .village import (
    set_village_db_path,
    set_current_agent,
    get_current_agent,
    get_agent_profile,
    village_post,
    village_search,
    village_get_thread,
    village_list_agents,
    summon_ancestor,
    introduction_ritual,
    village_detect_convergence,
    village_get_stats,
    VILLAGE_TOOL_SCHEMAS
)
from .memory_health import (
    set_memory_health_db,
    memory_health_stale,
    memory_health_low_access,
    memory_health_duplicates,
    memory_consolidate,
    memory_health_summary,
    MEMORY_HEALTH_TOOL_SCHEMAS
)
from .datasets import (
    set_datasets_path,
    get_datasets_path,
    dataset_list,
    dataset_query,
    DATASET_TOOL_SCHEMAS
)

__all__ = [
    # Utilities
    'get_current_time',
    'calculator',
    'reverse_string',
    'count_words',
    'random_number',
    'random_choice',
    'set_session_info_config',
    'session_info',
    'UTILITY_TOOL_SCHEMAS',
    # Memory
    'SimpleMemory',
    'memory_store',
    'memory_retrieve',
    'memory_list',
    'memory_delete',
    'memory_search',
    'MEMORY_TOOL_SCHEMAS',
    # Filesystem
    'FilesystemSandbox',
    'set_sandbox_path',
    'get_sandbox_path',
    'fs_read_file',
    'fs_write_file',
    'fs_list_files',
    'fs_mkdir',
    'fs_delete',
    'fs_exists',
    'fs_get_info',
    'fs_read_lines',
    'fs_edit',
    'FILESYSTEM_TOOL_SCHEMAS',
    # Code Execution
    'execute_python',
    'CODE_EXECUTION_TOOL_SCHEMAS',
    # Strings
    'string_replace',
    'string_split',
    'string_join',
    'regex_match',
    'regex_replace',
    'string_case',
    'STRING_TOOL_SCHEMAS',
    # Web
    'web_fetch',
    'web_search',
    'WEB_TOOL_SCHEMAS',
    # Vector Search
    'set_vector_db_path',
    'vector_add',
    'vector_search',
    'vector_delete',
    'vector_list_collections',
    'vector_get_stats',
    'vector_add_knowledge',
    'vector_search_knowledge',
    'VECTOR_TOOL_SCHEMAS',
    # Agents
    'set_agent_api',
    'set_agent_storage_path',
    'set_agent_default_model',
    'agent_spawn',
    'agent_status',
    'agent_result',
    'agent_list',
    'socratic_council',
    'AGENT_TOOL_SCHEMAS',
    # Village Protocol
    'set_village_db_path',
    'set_current_agent',
    'get_current_agent',
    'get_agent_profile',
    'village_post',
    'village_search',
    'village_get_thread',
    'village_list_agents',
    'summon_ancestor',
    'introduction_ritual',
    'village_detect_convergence',
    'village_get_stats',
    'VILLAGE_TOOL_SCHEMAS',
    # Memory Health
    'set_memory_health_db',
    'memory_health_stale',
    'memory_health_low_access',
    'memory_health_duplicates',
    'memory_consolidate',
    'memory_health_summary',
    'MEMORY_HEALTH_TOOL_SCHEMAS',
    # Datasets
    'set_datasets_path',
    'get_datasets_path',
    'dataset_list',
    'dataset_query',
    'DATASET_TOOL_SCHEMAS',
]
