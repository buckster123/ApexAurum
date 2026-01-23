"""
Tools Module

Collection of tools for Claude to use:
- Utilities: Time, calculator, string operations
- Filesystem: File/directory operations (sandboxed)
- Code Execution: Safe Python code execution (REPL + Docker sandbox)
- Memory: Key-value memory storage
- Agents: Multi-agent spawning and Socratic council
- Vector Search: Semantic search and knowledge base
- Music: AI music generation via Suno API
- Datasets: Vector dataset creation and querying
- EEG: Neural Resonance brain-computer interface (OpenBCI)
- Vision: Hailo-10H accelerated computer vision (detection, classification, pose)

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

# Suno Prompt Compiler
from .suno_compiler import (
    suno_prompt_build,
    suno_prompt_preset_save,
    suno_prompt_preset_load,
    suno_prompt_preset_list,
    SUNO_PROMPT_BUILD_SCHEMA,
    SUNO_PROMPT_PRESET_SAVE_SCHEMA,
    SUNO_PROMPT_PRESET_LOAD_SCHEMA,
    SUNO_PROMPT_PRESET_LIST_SCHEMA,
)

# Suno Compiler tool schemas
SUNO_COMPILER_TOOL_SCHEMAS = {
    "suno_prompt_build": SUNO_PROMPT_BUILD_SCHEMA,
    "suno_prompt_preset_save": SUNO_PROMPT_PRESET_SAVE_SCHEMA,
    "suno_prompt_preset_load": SUNO_PROMPT_PRESET_LOAD_SCHEMA,
    "suno_prompt_preset_list": SUNO_PROMPT_PRESET_LIST_SCHEMA,
}

# Audio Editor Tools
from .audio_editor import (
    audio_info,
    audio_trim,
    audio_fade,
    audio_normalize,
    audio_loop,
    audio_concat,
    audio_speed,
    audio_reverse,
    audio_list_files,
    audio_get_waveform,
    AUDIO_EDITOR_TOOL_SCHEMAS,
)

# EEG Tools (Neural Resonance)
from .eeg import (
    eeg_connect,
    eeg_disconnect,
    eeg_stream_start,
    eeg_stream_stop,
    eeg_experience_get,
    eeg_calibrate_baseline,
    eeg_realtime_emotion,
    eeg_list_sessions,
    EEG_CONNECT_SCHEMA,
    EEG_DISCONNECT_SCHEMA,
    EEG_STREAM_START_SCHEMA,
    EEG_STREAM_STOP_SCHEMA,
    EEG_EXPERIENCE_GET_SCHEMA,
    EEG_CALIBRATE_SCHEMA,
    EEG_REALTIME_SCHEMA,
    EEG_LIST_SESSIONS_SCHEMA,
)

# EEG tool schemas
EEG_TOOL_SCHEMAS = {
    "eeg_connect": EEG_CONNECT_SCHEMA,
    "eeg_disconnect": EEG_DISCONNECT_SCHEMA,
    "eeg_stream_start": EEG_STREAM_START_SCHEMA,
    "eeg_stream_stop": EEG_STREAM_STOP_SCHEMA,
    "eeg_experience_get": EEG_EXPERIENCE_GET_SCHEMA,
    "eeg_calibrate_baseline": EEG_CALIBRATE_SCHEMA,
    "eeg_realtime_emotion": EEG_REALTIME_SCHEMA,
    "eeg_list_sessions": EEG_LIST_SESSIONS_SCHEMA,
}

# Vision Tools (Hailo-10H Accelerated)
from .vision import (
    hailo_info,
    hailo_detect,
    hailo_classify,
    hailo_pose,
    hailo_analyze,
    hailo_benchmark,
    hailo_list_models,
    VISION_TOOL_SCHEMAS,
)

# Camera Tools (The Cyclops Eye)
from .camera import (
    camera_info,
    camera_list,
    camera_capture,
    camera_detect,
    camera_timelapse,
    camera_captures_list,
    CAMERA_TOOL_SCHEMAS,
)

# Nursery Tools (Training & Model Management)
from .nursery import (
    # Data Garden
    nursery_generate_data,
    nursery_extract_conversations,
    nursery_list_datasets,
    # Training Forge
    nursery_estimate_cost,
    nursery_train_cloud,
    nursery_train_local,
    nursery_job_status,
    nursery_list_jobs,
    # Model Cradle
    nursery_list_models,
    nursery_deploy_ollama,
    nursery_test_model,
    nursery_compare_models,
    # Phase 2: Village Registry
    nursery_register_model,
    nursery_discover_models,
    # Phase 3: Apprentice Protocol
    nursery_create_apprentice,
    nursery_list_apprentices,
    # Schemas
    NURSERY_GENERATE_DATA_SCHEMA,
    NURSERY_EXTRACT_CONVERSATIONS_SCHEMA,
    NURSERY_LIST_DATASETS_SCHEMA,
    NURSERY_ESTIMATE_COST_SCHEMA,
    NURSERY_TRAIN_CLOUD_SCHEMA,
    NURSERY_TRAIN_LOCAL_SCHEMA,
    NURSERY_JOB_STATUS_SCHEMA,
    NURSERY_LIST_JOBS_SCHEMA,
    NURSERY_LIST_MODELS_SCHEMA,
    NURSERY_DEPLOY_OLLAMA_SCHEMA,
    NURSERY_TEST_MODEL_SCHEMA,
    NURSERY_COMPARE_MODELS_SCHEMA,
    NURSERY_REGISTER_MODEL_SCHEMA,
    NURSERY_DISCOVER_MODELS_SCHEMA,
    NURSERY_CREATE_APPRENTICE_SCHEMA,
    NURSERY_LIST_APPRENTICES_SCHEMA,
)

# Nursery tool schemas
NURSERY_TOOL_SCHEMAS = {
    "nursery_generate_data": NURSERY_GENERATE_DATA_SCHEMA,
    "nursery_extract_conversations": NURSERY_EXTRACT_CONVERSATIONS_SCHEMA,
    "nursery_list_datasets": NURSERY_LIST_DATASETS_SCHEMA,
    "nursery_estimate_cost": NURSERY_ESTIMATE_COST_SCHEMA,
    "nursery_train_cloud": NURSERY_TRAIN_CLOUD_SCHEMA,
    "nursery_train_local": NURSERY_TRAIN_LOCAL_SCHEMA,
    "nursery_job_status": NURSERY_JOB_STATUS_SCHEMA,
    "nursery_list_jobs": NURSERY_LIST_JOBS_SCHEMA,
    "nursery_list_models": NURSERY_LIST_MODELS_SCHEMA,
    "nursery_deploy_ollama": NURSERY_DEPLOY_OLLAMA_SCHEMA,
    "nursery_test_model": NURSERY_TEST_MODEL_SCHEMA,
    "nursery_compare_models": NURSERY_COMPARE_MODELS_SCHEMA,
    # Phase 2: Village Registry
    "nursery_register_model": NURSERY_REGISTER_MODEL_SCHEMA,
    "nursery_discover_models": NURSERY_DISCOVER_MODELS_SCHEMA,
    # Phase 3: Apprentice Protocol
    "nursery_create_apprentice": NURSERY_CREATE_APPRENTICE_SCHEMA,
    "nursery_list_apprentices": NURSERY_LIST_APPRENTICES_SCHEMA,
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
    **EEG_TOOL_SCHEMAS,
    **SUNO_COMPILER_TOOL_SCHEMAS,
    **AUDIO_EDITOR_TOOL_SCHEMAS,
    **VISION_TOOL_SCHEMAS,
    **CAMERA_TOOL_SCHEMAS,
    **NURSERY_TOOL_SCHEMAS,
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
    # EEG Tools (Neural Resonance)
    "eeg_connect": eeg_connect,
    "eeg_disconnect": eeg_disconnect,
    "eeg_stream_start": eeg_stream_start,
    "eeg_stream_stop": eeg_stream_stop,
    "eeg_experience_get": eeg_experience_get,
    "eeg_calibrate_baseline": eeg_calibrate_baseline,
    "eeg_realtime_emotion": eeg_realtime_emotion,
    "eeg_list_sessions": eeg_list_sessions,
    # Suno Prompt Compiler
    "suno_prompt_build": suno_prompt_build,
    "suno_prompt_preset_save": suno_prompt_preset_save,
    "suno_prompt_preset_load": suno_prompt_preset_load,
    "suno_prompt_preset_list": suno_prompt_preset_list,
    # Audio Editor Tools
    "audio_info": audio_info,
    "audio_trim": audio_trim,
    "audio_fade": audio_fade,
    "audio_normalize": audio_normalize,
    "audio_loop": audio_loop,
    "audio_concat": audio_concat,
    "audio_speed": audio_speed,
    "audio_reverse": audio_reverse,
    "audio_list_files": audio_list_files,
    "audio_get_waveform": audio_get_waveform,
    # Vision Tools (Hailo-10H)
    "hailo_info": hailo_info,
    "hailo_detect": hailo_detect,
    "hailo_classify": hailo_classify,
    "hailo_pose": hailo_pose,
    "hailo_analyze": hailo_analyze,
    "hailo_benchmark": hailo_benchmark,
    "hailo_list_models": hailo_list_models,
    # Camera Tools (The Cyclops Eye)
    "camera_info": camera_info,
    "camera_list": camera_list,
    "camera_capture": camera_capture,
    "camera_detect": camera_detect,
    "camera_timelapse": camera_timelapse,
    "camera_captures_list": camera_captures_list,
    # Nursery Tools (Training & Model Management)
    "nursery_generate_data": nursery_generate_data,
    "nursery_extract_conversations": nursery_extract_conversations,
    "nursery_list_datasets": nursery_list_datasets,
    "nursery_estimate_cost": nursery_estimate_cost,
    "nursery_train_cloud": nursery_train_cloud,
    "nursery_train_local": nursery_train_local,
    "nursery_job_status": nursery_job_status,
    "nursery_list_jobs": nursery_list_jobs,
    "nursery_list_models": nursery_list_models,
    "nursery_deploy_ollama": nursery_deploy_ollama,
    "nursery_test_model": nursery_test_model,
    "nursery_compare_models": nursery_compare_models,
    # Phase 2: Village Registry
    "nursery_register_model": nursery_register_model,
    "nursery_discover_models": nursery_discover_models,
    # Phase 3: Apprentice Protocol
    "nursery_create_apprentice": nursery_create_apprentice,
    "nursery_list_apprentices": nursery_list_apprentices,
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
    # EEG Tools (Neural Resonance)
    "eeg_connect",
    "eeg_disconnect",
    "eeg_stream_start",
    "eeg_stream_stop",
    "eeg_experience_get",
    "eeg_calibrate_baseline",
    "eeg_realtime_emotion",
    "eeg_list_sessions",
    # Suno Prompt Compiler
    "suno_prompt_build",
    "suno_prompt_preset_save",
    "suno_prompt_preset_load",
    "suno_prompt_preset_list",
    # Audio Editor Tools
    "audio_info",
    "audio_trim",
    "audio_fade",
    "audio_normalize",
    "audio_loop",
    "audio_concat",
    "audio_speed",
    "audio_reverse",
    "audio_list_files",
    "audio_get_waveform",
    # Schemas
    "UTILITY_TOOL_SCHEMAS",
    "FILESYSTEM_TOOL_SCHEMAS",
    "CODE_EXECUTION_TOOL_SCHEMAS",
    "MEMORY_TOOL_SCHEMAS",
    "AGENT_TOOL_SCHEMAS",
    "VECTOR_TOOL_SCHEMAS",
    "MUSIC_TOOL_SCHEMAS",
    "DATASET_TOOL_SCHEMAS",
    "EEG_TOOL_SCHEMAS",
    "SUNO_COMPILER_TOOL_SCHEMAS",
    "AUDIO_EDITOR_TOOL_SCHEMAS",
    "VISION_TOOL_SCHEMAS",
    "CAMERA_TOOL_SCHEMAS",
    "NURSERY_TOOL_SCHEMAS",
    "ALL_TOOL_SCHEMAS",
    "ALL_TOOLS",
    # Vision Tools (Hailo-10H)
    "hailo_info",
    "hailo_detect",
    "hailo_classify",
    "hailo_pose",
    "hailo_analyze",
    "hailo_benchmark",
    "hailo_list_models",
    # Camera Tools (The Cyclops Eye)
    "camera_info",
    "camera_list",
    "camera_capture",
    "camera_detect",
    "camera_timelapse",
    "camera_captures_list",
    # Nursery Tools (Training & Model Management)
    "nursery_generate_data",
    "nursery_extract_conversations",
    "nursery_list_datasets",
    "nursery_estimate_cost",
    "nursery_train_cloud",
    "nursery_train_local",
    "nursery_job_status",
    "nursery_list_jobs",
    "nursery_list_models",
    "nursery_deploy_ollama",
    "nursery_test_model",
    "nursery_compare_models",
    # Phase 2: Village Registry
    "nursery_register_model",
    "nursery_discover_models",
    # Phase 3: Apprentice Protocol
    "nursery_create_apprentice",
    "nursery_list_apprentices",
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
