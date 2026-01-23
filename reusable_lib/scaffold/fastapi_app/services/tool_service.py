"""
Tool Service

Manages AI tools from reusable_lib.
Handles tool registration, execution, and schema generation.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Callable

# Import from reusable_lib
import sys
from pathlib import Path

# Path setup for dual tools/ imports:
# - ApexAurum/tools/ (suno_compiler, audio_editor, music, vision, eeg)
# - reusable_lib/tools/ (via reusable_lib.tools namespace)
lib_path = Path(__file__).parent.parent.parent.parent  # reusable_lib/
project_root = lib_path.parent  # ApexAurum/

# IMPORTANT: Project root MUST be at index 0 for tools.* imports to find
# ApexAurum/tools/ before reusable_lib/tools/
# Remove existing entries and re-add in correct order
for path in [str(project_root), str(lib_path)]:
    if path in sys.path:
        sys.path.remove(path)
sys.path.insert(0, str(project_root))
sys.path.insert(1, str(lib_path))

from reusable_lib.tools import (
    get_current_time,
    calculator,
    count_words,
    random_number,
    set_session_info_config,
    session_info,
    UTILITY_TOOL_SCHEMAS,
    memory_store,
    memory_retrieve,
    memory_search,
    memory_delete,
    memory_list,
    MEMORY_TOOL_SCHEMAS,
    # Filesystem tools
    set_sandbox_path,
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
    # Code execution
    execute_python,
    CODE_EXECUTION_TOOL_SCHEMAS,
    # String tools
    string_replace,
    string_split,
    string_join,
    regex_match,
    regex_replace,
    string_case,
    STRING_TOOL_SCHEMAS,
    # Web tools
    web_fetch,
    web_search,
    WEB_TOOL_SCHEMAS,
    # Vector tools
    set_vector_db_path,
    vector_add,
    vector_search,
    vector_delete,
    vector_list_collections,
    vector_get_stats,
    vector_add_knowledge,
    vector_search_knowledge,
    VECTOR_TOOL_SCHEMAS,
    # Agent tools
    set_agent_api,
    set_agent_storage_path,
    set_agent_default_model,
    agent_spawn,
    agent_status,
    agent_result,
    agent_list,
    socratic_council,
    AGENT_TOOL_SCHEMAS,
    # Village Protocol tools
    set_village_db_path,
    set_current_agent,
    village_post,
    village_search,
    village_get_thread,
    village_list_agents,
    summon_ancestor,
    introduction_ritual,
    village_detect_convergence,
    village_get_stats,
    VILLAGE_TOOL_SCHEMAS,
    # Memory Health tools
    set_memory_health_db,
    memory_health_stale,
    memory_health_low_access,
    memory_health_duplicates,
    memory_consolidate,
    memory_health_summary,
    MEMORY_HEALTH_TOOL_SCHEMAS,
    # Dataset tools
    set_datasets_path,
    dataset_list,
    dataset_query,
    DATASET_TOOL_SCHEMAS,
)

# Import from parent project tools (Suno Compiler and Audio Editor)
from tools.suno_compiler import (
    suno_prompt_build,
    suno_prompt_preset_save,
    suno_prompt_preset_load,
    suno_prompt_preset_list,
    SUNO_PROMPT_BUILD_SCHEMA,
    SUNO_PROMPT_PRESET_SAVE_SCHEMA,
    SUNO_PROMPT_PRESET_LOAD_SCHEMA,
    SUNO_PROMPT_PRESET_LIST_SCHEMA,
)

from tools.audio_editor import (
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

# Music tools from parent project
from tools.music import (
    music_generate,
    music_status,
    music_result,
    music_list,
    music_favorite,
    music_library,
    music_search,
    music_play,
    midi_create,
    music_compose,
    MUSIC_TOOL_SCHEMAS,
)

from services.llm_service import get_llm_client
from services.event_service import get_event_broadcaster
from app_config import settings

logger = logging.getLogger(__name__)

# Tool Groups - categorize tools for selection UI
TOOL_GROUPS = {
    "utility": {
        "name": "Utility",
        "icon": "🔧",
        "tools": ["get_current_time", "calculator", "count_words", "random_number", "session_info"],
        "description": "Basic utilities: time, math, word count"
    },
    "memory": {
        "name": "Memory",
        "icon": "🧠",
        "tools": ["memory_store", "memory_retrieve", "memory_search", "memory_delete", "memory_list"],
        "description": "Key-value persistent memory"
    },
    "filesystem": {
        "name": "Filesystem",
        "icon": "📁",
        "tools": ["fs_read_file", "fs_write_file", "fs_list_files", "fs_mkdir", "fs_delete",
                  "fs_exists", "fs_get_info", "fs_read_lines", "fs_edit"],
        "description": "File operations in sandbox"
    },
    "code": {
        "name": "Code Execution",
        "icon": "💻",
        "tools": ["execute_python"],
        "description": "Run Python code safely"
    },
    "string": {
        "name": "String",
        "icon": "📝",
        "tools": ["string_replace", "string_split", "string_join", "regex_match", "regex_replace", "string_case"],
        "description": "Text manipulation"
    },
    "web": {
        "name": "Web",
        "icon": "🌐",
        "tools": ["web_fetch", "web_search"],
        "description": "Fetch URLs, search web"
    },
    "vector": {
        "name": "Vector DB",
        "icon": "🔍",
        "tools": ["vector_add", "vector_search", "vector_delete", "vector_list_collections",
                  "vector_get_stats", "vector_add_knowledge", "vector_search_knowledge"],
        "description": "Semantic search & knowledge"
    },
    "agent": {
        "name": "Agents",
        "icon": "🤖",
        "tools": ["agent_spawn", "agent_status", "agent_result", "agent_list", "socratic_council"],
        "description": "Multi-agent orchestration"
    },
    "village": {
        "name": "Village Protocol",
        "icon": "🏘️",
        "tools": ["village_post", "village_search", "village_get_thread", "village_list_agents",
                  "summon_ancestor", "introduction_ritual", "village_detect_convergence", "village_get_stats"],
        "description": "Multi-agent memory realm"
    },
    "memory_health": {
        "name": "Memory Health",
        "icon": "🏥",
        "tools": ["memory_health_stale", "memory_health_low_access", "memory_health_duplicates",
                  "memory_consolidate", "memory_health_summary"],
        "description": "Adaptive memory maintenance"
    },
    "dataset": {
        "name": "Datasets",
        "icon": "📊",
        "tools": ["dataset_list", "dataset_query"],
        "description": "Query vector datasets"
    },
    "suno": {
        "name": "Suno Compiler",
        "icon": "🎼",
        "tools": ["suno_prompt_build", "suno_prompt_preset_save", "suno_prompt_preset_load", "suno_prompt_preset_list"],
        "description": "Music prompt generation"
    },
    "audio": {
        "name": "Audio Editor",
        "icon": "🎚️",
        "tools": ["audio_info", "audio_trim", "audio_fade", "audio_normalize", "audio_loop",
                  "audio_concat", "audio_speed", "audio_reverse", "audio_list_files", "audio_get_waveform"],
        "description": "Audio file manipulation"
    },
    "music": {
        "name": "Music Generation",
        "icon": "🎵",
        "tools": ["music_generate", "music_status", "music_result", "music_list", "music_favorite",
                  "music_library", "music_search", "music_play", "midi_create", "music_compose"],
        "description": "Suno AI music & MIDI"
    },
}

# Preset tool selections for different use cases
TOOL_PRESETS = {
    "minimal": {
        "name": "Minimal (Fast)",
        "description": "Basic tools for small models - time, memory, web, file basics",
        "groups": ["utility", "memory", "web"],
        "extra_tools": ["fs_read_file", "fs_write_file", "fs_list_files"]
    },
    "standard": {
        "name": "Standard",
        "description": "Common tools - files, code, strings, web, datasets",
        "groups": ["utility", "memory", "filesystem", "code", "string", "web", "dataset"]
    },
    "creative": {
        "name": "Creative",
        "description": "Music and audio - Suno, MIDI, audio editing, files",
        "groups": ["utility", "suno", "audio", "music", "filesystem"]
    },
    "research": {
        "name": "Research",
        "description": "Vector search, agents, Village Protocol, memory health",
        "groups": ["utility", "memory", "vector", "agent", "village", "memory_health", "dataset", "web"]
    },
    "full": {
        "name": "Full (All Tools)",
        "description": "Everything enabled",
        "groups": list(TOOL_GROUPS.keys())
    }
}


class ToolService:
    """
    Service for managing and executing AI tools.
    """

    def __init__(self, settings_path: Optional[Path] = None):
        """Initialize with built-in tools."""
        self.tools: Dict[str, Callable] = {}
        self.schemas: Dict[str, Dict] = {}

        # Tool selection state
        self.settings_path = settings_path or Path("./data/tool_settings.json")
        self.excluded_tools: set = set()
        self.excluded_groups: set = set()

        # Load saved settings
        self._load_settings()

        # Register built-in tools
        self._register_builtin_tools()

    def _load_settings(self):
        """Load tool settings from file."""
        try:
            if self.settings_path.exists():
                import json
                with open(self.settings_path) as f:
                    data = json.load(f)
                    self.excluded_tools = set(data.get("excluded_tools", []))
                    self.excluded_groups = set(data.get("excluded_groups", []))
                    logger.info(f"Loaded tool settings: {len(self.excluded_groups)} groups, {len(self.excluded_tools)} tools excluded")
        except Exception as e:
            logger.warning(f"Could not load tool settings: {e}")

    def save_settings(self):
        """Save tool settings to file."""
        try:
            import json
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_path, 'w') as f:
                json.dump({
                    "excluded_tools": list(self.excluded_tools),
                    "excluded_groups": list(self.excluded_groups)
                }, f, indent=2)
            logger.info(f"Saved tool settings")
        except Exception as e:
            logger.error(f"Could not save tool settings: {e}")

    def get_tool_groups(self) -> Dict[str, Any]:
        """Get all tool groups with their tools and enabled state."""
        groups = {}
        for group_id, group_info in TOOL_GROUPS.items():
            groups[group_id] = {
                **group_info,
                "enabled": group_id not in self.excluded_groups,
                "tool_states": {
                    tool: tool not in self.excluded_tools
                    for tool in group_info["tools"]
                }
            }
        return groups

    def get_tool_presets(self) -> Dict[str, Any]:
        """Get available tool presets."""
        return TOOL_PRESETS

    def apply_preset(self, preset_id: str) -> Dict[str, Any]:
        """Apply a tool preset."""
        if preset_id not in TOOL_PRESETS:
            return {"success": False, "error": f"Unknown preset: {preset_id}"}

        preset = TOOL_PRESETS[preset_id]
        enabled_groups = set(preset.get("groups", []))

        # Exclude all groups not in preset
        self.excluded_groups = set(TOOL_GROUPS.keys()) - enabled_groups

        # Handle extra_tools (tools enabled even if their group is disabled)
        extra_tools = set(preset.get("extra_tools", []))

        # Reset tool exclusions, then exclude tools from disabled groups
        self.excluded_tools = set()
        for group_id, group_info in TOOL_GROUPS.items():
            if group_id in self.excluded_groups:
                for tool in group_info["tools"]:
                    if tool not in extra_tools:
                        self.excluded_tools.add(tool)

        self.save_settings()

        enabled_count = len(self.get_enabled_tools())
        return {
            "success": True,
            "preset": preset_id,
            "enabled_count": enabled_count,
            "message": f"Applied '{preset['name']}' preset: {enabled_count} tools enabled"
        }

    def set_group_enabled(self, group_id: str, enabled: bool):
        """Enable or disable an entire tool group."""
        if group_id not in TOOL_GROUPS:
            return

        if enabled:
            self.excluded_groups.discard(group_id)
            # Also enable all tools in the group
            for tool in TOOL_GROUPS[group_id]["tools"]:
                self.excluded_tools.discard(tool)
        else:
            self.excluded_groups.add(group_id)
            # Also disable all tools in the group
            for tool in TOOL_GROUPS[group_id]["tools"]:
                self.excluded_tools.add(tool)

        self.save_settings()

    def set_tool_enabled(self, tool_name: str, enabled: bool):
        """Enable or disable a single tool."""
        if enabled:
            self.excluded_tools.discard(tool_name)
        else:
            self.excluded_tools.add(tool_name)
        self.save_settings()

    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a tool is enabled."""
        return tool_name not in self.excluded_tools

    def get_enabled_tools(self) -> List[str]:
        """Get list of enabled tool names."""
        return [name for name in self.tools.keys() if name not in self.excluded_tools]

    def get_enabled_schemas(self) -> List[Dict]:
        """Get schemas only for enabled tools."""
        return [
            schema for name, schema in self.schemas.items()
            if name not in self.excluded_tools
        ]

    def _register_builtin_tools(self):
        """Register tools from reusable_lib."""
        # Utility tools
        self.register("get_current_time", get_current_time, UTILITY_TOOL_SCHEMAS.get("get_current_time"))
        self.register("calculator", calculator, UTILITY_TOOL_SCHEMAS.get("calculator"))
        self.register("count_words", count_words, UTILITY_TOOL_SCHEMAS.get("count_words"))
        self.register("random_number", random_number, UTILITY_TOOL_SCHEMAS.get("random_number"))

        # Session info tool - configure with data dir and register
        set_session_info_config(
            data_dir=str(settings.DATA_DIR),
            tool_count=0  # Will be updated after all tools registered
        )
        self.register("session_info", session_info, UTILITY_TOOL_SCHEMAS.get("session_info"))

        # Memory tools
        self.register("memory_store", memory_store, MEMORY_TOOL_SCHEMAS.get("memory_store"))
        self.register("memory_retrieve", memory_retrieve, MEMORY_TOOL_SCHEMAS.get("memory_retrieve"))
        self.register("memory_search", memory_search, MEMORY_TOOL_SCHEMAS.get("memory_search"))
        self.register("memory_delete", memory_delete, MEMORY_TOOL_SCHEMAS.get("memory_delete"))
        self.register("memory_list", memory_list, MEMORY_TOOL_SCHEMAS.get("memory_list"))

        # Filesystem tools - set sandbox to data/sandbox
        sandbox_path = settings.DATA_DIR / "sandbox"
        set_sandbox_path(str(sandbox_path))

        self.register("fs_read_file", fs_read_file, FILESYSTEM_TOOL_SCHEMAS.get("fs_read_file"))
        self.register("fs_write_file", fs_write_file, FILESYSTEM_TOOL_SCHEMAS.get("fs_write_file"))
        self.register("fs_list_files", fs_list_files, FILESYSTEM_TOOL_SCHEMAS.get("fs_list_files"))
        self.register("fs_mkdir", fs_mkdir, FILESYSTEM_TOOL_SCHEMAS.get("fs_mkdir"))
        self.register("fs_delete", fs_delete, FILESYSTEM_TOOL_SCHEMAS.get("fs_delete"))
        self.register("fs_exists", fs_exists, FILESYSTEM_TOOL_SCHEMAS.get("fs_exists"))
        self.register("fs_get_info", fs_get_info, FILESYSTEM_TOOL_SCHEMAS.get("fs_get_info"))
        self.register("fs_read_lines", fs_read_lines, FILESYSTEM_TOOL_SCHEMAS.get("fs_read_lines"))
        self.register("fs_edit", fs_edit, FILESYSTEM_TOOL_SCHEMAS.get("fs_edit"))

        # Code execution tool
        self.register("execute_python", execute_python, CODE_EXECUTION_TOOL_SCHEMAS.get("execute_python"))

        # String tools
        self.register("string_replace", string_replace, STRING_TOOL_SCHEMAS.get("string_replace"))
        self.register("string_split", string_split, STRING_TOOL_SCHEMAS.get("string_split"))
        self.register("string_join", string_join, STRING_TOOL_SCHEMAS.get("string_join"))
        self.register("regex_match", regex_match, STRING_TOOL_SCHEMAS.get("regex_match"))
        self.register("regex_replace", regex_replace, STRING_TOOL_SCHEMAS.get("regex_replace"))
        self.register("string_case", string_case, STRING_TOOL_SCHEMAS.get("string_case"))

        # Web tools
        self.register("web_fetch", web_fetch, WEB_TOOL_SCHEMAS.get("web_fetch"))
        self.register("web_search", web_search, WEB_TOOL_SCHEMAS.get("web_search"))

        # Vector tools - set storage path
        vector_path = settings.DATA_DIR / "vectors"
        set_vector_db_path(str(vector_path))

        self.register("vector_add", vector_add, VECTOR_TOOL_SCHEMAS.get("vector_add"))
        self.register("vector_search", vector_search, VECTOR_TOOL_SCHEMAS.get("vector_search"))
        self.register("vector_delete", vector_delete, VECTOR_TOOL_SCHEMAS.get("vector_delete"))
        self.register("vector_list_collections", vector_list_collections, VECTOR_TOOL_SCHEMAS.get("vector_list_collections"))
        self.register("vector_get_stats", vector_get_stats, VECTOR_TOOL_SCHEMAS.get("vector_get_stats"))
        self.register("vector_add_knowledge", vector_add_knowledge, VECTOR_TOOL_SCHEMAS.get("vector_add_knowledge"))
        self.register("vector_search_knowledge", vector_search_knowledge, VECTOR_TOOL_SCHEMAS.get("vector_search_knowledge"))

        # Agent tools - set storage path and API function
        agent_storage = settings.DATA_DIR / "agents.json"
        set_agent_storage_path(str(agent_storage))
        set_agent_default_model(settings.DEFAULT_MODEL)

        # Create API call wrapper for agents
        def agent_api_call(messages, system, model, max_tokens):
            """API call function for agent execution."""
            try:
                client = get_llm_client()
                # Client.chat() expects prompt as first positional arg
                response = client.chat(
                    prompt=messages,  # Can be str or List[Dict]
                    model=model,
                    system=system,
                    max_tokens=max_tokens
                )
                return response.content
            except Exception as e:
                logger.error(f"Agent API call failed: {e}")
                raise

        set_agent_api(agent_api_call)

        self.register("agent_spawn", agent_spawn, AGENT_TOOL_SCHEMAS.get("agent_spawn"))
        self.register("agent_status", agent_status, AGENT_TOOL_SCHEMAS.get("agent_status"))
        self.register("agent_result", agent_result, AGENT_TOOL_SCHEMAS.get("agent_result"))
        self.register("agent_list", agent_list, AGENT_TOOL_SCHEMAS.get("agent_list"))
        self.register("socratic_council", socratic_council, AGENT_TOOL_SCHEMAS.get("socratic_council"))

        # Village Protocol tools - set storage path (uses vector DB)
        village_path = settings.DATA_DIR / "village"
        set_village_db_path(str(village_path))

        # Set default agent (can be changed at runtime)
        set_current_agent("CLAUDE")

        self.register("village_post", village_post, VILLAGE_TOOL_SCHEMAS.get("village_post"))
        self.register("village_search", village_search, VILLAGE_TOOL_SCHEMAS.get("village_search"))
        self.register("village_get_thread", village_get_thread, VILLAGE_TOOL_SCHEMAS.get("village_get_thread"))
        self.register("village_list_agents", village_list_agents, VILLAGE_TOOL_SCHEMAS.get("village_list_agents"))
        self.register("summon_ancestor", summon_ancestor, VILLAGE_TOOL_SCHEMAS.get("summon_ancestor"))
        self.register("introduction_ritual", introduction_ritual, VILLAGE_TOOL_SCHEMAS.get("introduction_ritual"))
        self.register("village_detect_convergence", village_detect_convergence, VILLAGE_TOOL_SCHEMAS.get("village_detect_convergence"))
        self.register("village_get_stats", village_get_stats, VILLAGE_TOOL_SCHEMAS.get("village_get_stats"))

        # Memory Health tools - uses same vector DB
        from reusable_lib.vector import VectorDB
        vector_path = settings.DATA_DIR / "vectors"
        memory_health_db = VectorDB(persist_directory=str(vector_path))
        set_memory_health_db(memory_health_db)

        self.register("memory_health_stale", memory_health_stale, MEMORY_HEALTH_TOOL_SCHEMAS.get("memory_health_stale"))
        self.register("memory_health_low_access", memory_health_low_access, MEMORY_HEALTH_TOOL_SCHEMAS.get("memory_health_low_access"))
        self.register("memory_health_duplicates", memory_health_duplicates, MEMORY_HEALTH_TOOL_SCHEMAS.get("memory_health_duplicates"))
        self.register("memory_consolidate", memory_consolidate, MEMORY_HEALTH_TOOL_SCHEMAS.get("memory_consolidate"))
        self.register("memory_health_summary", memory_health_summary, MEMORY_HEALTH_TOOL_SCHEMAS.get("memory_health_summary"))

        # Dataset tools
        datasets_path = settings.DATA_DIR / "datasets"
        datasets_path.mkdir(parents=True, exist_ok=True)
        set_datasets_path(str(datasets_path))

        self.register("dataset_list", dataset_list, DATASET_TOOL_SCHEMAS.get("dataset_list"))
        self.register("dataset_query", dataset_query, DATASET_TOOL_SCHEMAS.get("dataset_query"))

        # Suno Prompt Compiler tools
        self.register("suno_prompt_build", suno_prompt_build, SUNO_PROMPT_BUILD_SCHEMA)
        self.register("suno_prompt_preset_save", suno_prompt_preset_save, SUNO_PROMPT_PRESET_SAVE_SCHEMA)
        self.register("suno_prompt_preset_load", suno_prompt_preset_load, SUNO_PROMPT_PRESET_LOAD_SCHEMA)
        self.register("suno_prompt_preset_list", suno_prompt_preset_list, SUNO_PROMPT_PRESET_LIST_SCHEMA)

        # Audio Editor tools
        self.register("audio_info", audio_info, AUDIO_EDITOR_TOOL_SCHEMAS.get("audio_info"))
        self.register("audio_trim", audio_trim, AUDIO_EDITOR_TOOL_SCHEMAS.get("audio_trim"))
        self.register("audio_fade", audio_fade, AUDIO_EDITOR_TOOL_SCHEMAS.get("audio_fade"))
        self.register("audio_normalize", audio_normalize, AUDIO_EDITOR_TOOL_SCHEMAS.get("audio_normalize"))
        self.register("audio_loop", audio_loop, AUDIO_EDITOR_TOOL_SCHEMAS.get("audio_loop"))
        self.register("audio_concat", audio_concat, AUDIO_EDITOR_TOOL_SCHEMAS.get("audio_concat"))
        self.register("audio_speed", audio_speed, AUDIO_EDITOR_TOOL_SCHEMAS.get("audio_speed"))
        self.register("audio_reverse", audio_reverse, AUDIO_EDITOR_TOOL_SCHEMAS.get("audio_reverse"))
        self.register("audio_list_files", audio_list_files, AUDIO_EDITOR_TOOL_SCHEMAS.get("audio_list_files"))
        self.register("audio_get_waveform", audio_get_waveform, AUDIO_EDITOR_TOOL_SCHEMAS.get("audio_get_waveform"))

        # Music Generation tools
        self.register("music_generate", music_generate, MUSIC_TOOL_SCHEMAS.get("music_generate"))
        self.register("music_status", music_status, MUSIC_TOOL_SCHEMAS.get("music_status"))
        self.register("music_result", music_result, MUSIC_TOOL_SCHEMAS.get("music_result"))
        self.register("music_list", music_list, MUSIC_TOOL_SCHEMAS.get("music_list"))
        self.register("music_favorite", music_favorite, MUSIC_TOOL_SCHEMAS.get("music_favorite"))
        self.register("music_library", music_library, MUSIC_TOOL_SCHEMAS.get("music_library"))
        self.register("music_search", music_search, MUSIC_TOOL_SCHEMAS.get("music_search"))
        self.register("music_play", music_play, MUSIC_TOOL_SCHEMAS.get("music_play"))
        self.register("midi_create", midi_create, MUSIC_TOOL_SCHEMAS.get("midi_create"))
        self.register("music_compose", music_compose, MUSIC_TOOL_SCHEMAS.get("music_compose"))

        # Update session_info with actual tool count
        set_session_info_config(tool_count=len(self.tools))

        logger.info(f"Registered {len(self.tools)} built-in tools")

    def register(self, name: str, func: Callable, schema: Optional[Dict] = None):
        """
        Register a tool.

        Args:
            name: Tool name
            func: Tool function
            schema: Optional schema (will generate basic one if not provided)
        """
        self.tools[name] = func
        self.schemas[name] = schema or self._generate_schema(name, func)

    def _generate_schema(self, name: str, func: Callable) -> Dict:
        """Generate a basic schema from function signature."""
        import inspect
        sig = inspect.signature(func)

        parameters = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ["self", "cls"]:
                continue

            param_schema = {"type": "string"}  # Default type

            if param.annotation != inspect.Parameter.empty:
                type_map = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object"
                }
                param_schema["type"] = type_map.get(param.annotation, "string")

            parameters[param_name] = param_schema

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "name": name,
            "description": func.__doc__ or f"Execute {name}",
            "input_schema": {
                "type": "object",
                "properties": parameters,
                "required": required
            }
        }

    def get_tool_list(self) -> List[Dict]:
        """Get list of all tools with schemas."""
        return [
            {
                "name": name,
                "description": schema.get("description", ""),
                "parameters": schema.get("input_schema", {}).get("properties", {})
            }
            for name, schema in self.schemas.items()
        ]

    def get_tool(self, name: str) -> Optional[Dict]:
        """Get a specific tool's info."""
        if name not in self.tools:
            return None
        return {
            "name": name,
            "schema": self.schemas.get(name, {}),
            "registered": True
        }

    def execute_without_broadcast(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool without event broadcasting.

        Use this when broadcasting is handled at a higher level (e.g., async routes).

        Args:
            name: Tool name
            arguments: Arguments to pass

        Returns:
            Tool result

        Raises:
            ValueError: If tool not found
        """
        if name not in self.tools:
            raise ValueError(f"Tool not found: {name}")

        func = self.tools[name]
        logger.info(f"Executing tool: {name} with args: {arguments}")

        try:
            result = func(**arguments)
            logger.info(f"Tool {name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            raise

    def execute(self, name: str, arguments: Dict[str, Any], agent_id: Optional[str] = None) -> Any:
        """
        Execute a tool with event broadcasting for Village GUI.

        Args:
            name: Tool name
            arguments: Arguments to pass
            agent_id: Optional agent ID for event attribution

        Returns:
            Tool result

        Raises:
            ValueError: If tool not found
        """
        if name not in self.tools:
            raise ValueError(f"Tool not found: {name}")

        func = self.tools[name]
        logger.info(f"Executing tool: {name} with args: {arguments}")

        # Broadcast start event for Village GUI
        broadcaster = get_event_broadcaster()
        broadcaster.tool_start_sync(name, arguments, agent_id=agent_id)

        try:
            result = func(**arguments)
            logger.info(f"Tool {name} completed successfully")

            # Broadcast complete event
            broadcaster.tool_complete_sync(name, result, success=True, agent_id=agent_id)

            return result
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")

            # Broadcast error event
            broadcaster.tool_complete_sync(name, str(e), success=False, agent_id=agent_id)

            raise

    def get_openai_schemas(self) -> List[Dict]:
        """Get schemas in OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": schema.get("description", ""),
                    "parameters": schema.get("input_schema", {})
                }
            }
            for name, schema in self.schemas.items()
        ]

    def get_anthropic_schemas(self) -> List[Dict]:
        """Get schemas in Anthropic/Claude format."""
        return list(self.schemas.values())

    def build_system_prompt(self, base_prompt: Optional[str] = None, use_enabled_only: bool = True) -> str:
        """
        Build a system prompt that includes tool descriptions.

        This helps models understand what tools are available and how to use them.
        Works with models that don't have native tool-calling support.

        Args:
            base_prompt: Optional base system prompt to prepend
            use_enabled_only: If True, only include enabled tools (respects exclusions)

        Returns:
            System prompt with tool instructions
        """
        parts = []

        if base_prompt:
            parts.append(base_prompt.strip())

        # Get schemas (filtered or all)
        if use_enabled_only:
            schemas_to_use = {name: self.schemas[name] for name in self.get_enabled_tools() if name in self.schemas}
        else:
            schemas_to_use = self.schemas

        if not schemas_to_use:
            parts.append("\n(No tools available)")
            return "\n".join(parts)

        # Add tool instructions
        parts.append(f"\n## Available Tools ({len(schemas_to_use)})\n")
        parts.append("You have access to the following tools. To use a tool, respond with a JSON object in this exact format:")
        parts.append('```json\n{"tool": "tool_name", "arguments": {"arg1": "value1"}}\n```\n')
        parts.append("After receiving a tool result, incorporate it into your response naturally.\n")
        parts.append("### Tools:\n")

        for name, schema in schemas_to_use.items():
            desc = schema.get("description", "No description")
            params = schema.get("input_schema", {}).get("properties", {})
            required = schema.get("input_schema", {}).get("required", [])

            parts.append(f"**{name}**: {desc}")
            if params:
                param_strs = []
                for pname, pinfo in params.items():
                    ptype = pinfo.get("type", "string")
                    req = " (required)" if pname in required else ""
                    pdesc = pinfo.get("description", "")
                    param_strs.append(f"  - `{pname}` ({ptype}{req}): {pdesc}")
                parts.append("\n".join(param_strs))
            parts.append("")

        return "\n".join(parts)

    async def chat_with_tools(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        tool_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Chat with automatic tool execution.

        Args:
            prompt: User prompt
            model: Model to use
            system: System prompt
            tool_filter: List of tool names to enable (None = all)

        Returns:
            Dict with response and tool calls
        """
        client = get_llm_client()
        model = model or settings.DEFAULT_MODEL

        # Filter tools if specified
        if tool_filter is not None:
            tools = [s for n, s in self.schemas.items() if n in tool_filter]
        else:
            tools = list(self.schemas.values())

        # Build system prompt with tool instructions
        tool_system = system or ""
        if tools:
            tool_system += "\n\nYou have access to tools. When you need to use a tool, respond with a JSON object: {\"tool\": \"tool_name\", \"arguments\": {...}}"

        # Get response
        response = client.chat(
            prompt,
            model=model,
            system=tool_system,
            tools=self.get_openai_schemas() if tool_filter is None else None
        )

        result = {
            "content": response.content,
            "model": response.model,
            "tool_calls": [],
            "tool_results": []
        }

        # Check for tool calls in response
        if response.has_tool_calls:
            for tool_call in response.tool_calls:
                func = tool_call.get("function", {})
                tool_name = func.get("name")
                arguments = json.loads(func.get("arguments", "{}"))

                result["tool_calls"].append({
                    "tool": tool_name,
                    "arguments": arguments
                })

                # Execute tool
                try:
                    tool_result = self.execute(tool_name, arguments)
                    result["tool_results"].append({
                        "tool": tool_name,
                        "result": tool_result,
                        "success": True
                    })
                except Exception as e:
                    result["tool_results"].append({
                        "tool": tool_name,
                        "error": str(e),
                        "success": False
                    })

        # Also try to parse tool calls from content (for models without native tool support)
        elif response.content:
            try:
                parsed = json.loads(response.content)
                if isinstance(parsed, dict) and "tool" in parsed:
                    tool_name = parsed["tool"]
                    arguments = parsed.get("arguments", {})

                    result["tool_calls"].append({
                        "tool": tool_name,
                        "arguments": arguments
                    })

                    try:
                        tool_result = self.execute(tool_name, arguments)
                        result["tool_results"].append({
                            "tool": tool_name,
                            "result": tool_result,
                            "success": True
                        })
                    except Exception as e:
                        result["tool_results"].append({
                            "tool": tool_name,
                            "error": str(e),
                            "success": False
                        })
            except json.JSONDecodeError:
                pass  # Not a tool call

        return result
