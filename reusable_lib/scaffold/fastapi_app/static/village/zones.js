/**
 * Village Zone Definitions
 *
 * Each zone has:
 * - position (x, y) - center point
 * - size (width, height)
 * - color - fill color
 * - label - display name
 * - description - what happens here
 * - icon - emoji for the zone
 */

export const CANVAS_WIDTH = 800;
export const CANVAS_HEIGHT = 600;

export const ZONES = {
    village_square: {
        x: 400, y: 300,
        width: 120, height: 120,
        color: '#2d3436',
        label: 'Village Square',
        icon: '🏠',
        description: 'The central gathering place. Agents idle here between tasks and return here after completing work.'
    },
    dj_booth: {
        x: 100, y: 300,
        width: 100, height: 80,
        color: '#6c5ce7',
        label: 'DJ Booth',
        icon: '🎵',
        description: 'Music generation station. Create AI-generated music, manage playlists, and compose MIDI.'
    },
    memory_garden: {
        x: 400, y: 80,
        width: 140, height: 80,
        color: '#00b894',
        label: 'Memory Garden',
        icon: '🌿',
        description: 'The knowledge repository. Store, search, and retrieve memories and vector embeddings.'
    },
    file_shed: {
        x: 700, y: 300,
        width: 100, height: 80,
        color: '#fdcb6e',
        label: 'File Shed',
        icon: '📁',
        description: 'File system workshop. Read, write, and manage files in the sandbox.'
    },
    workshop: {
        x: 400, y: 520,
        width: 120, height: 80,
        color: '#e17055',
        label: 'Workshop',
        icon: '⚙️',
        description: 'Code execution forge. Run Python code in a sandboxed environment.'
    },
    bridge_portal: {
        x: 700, y: 80,
        width: 100, height: 80,
        color: '#a29bfe',
        label: 'Bridge Portal',
        icon: '🌉',
        description: 'Agent coordination hub. Spawn agents, check status, and manage the village protocol.'
    }
};

/**
 * Tools available in each zone (for display)
 */
export const ZONE_TOOLS = {
    village_square: ['get_current_time', 'calculate', 'web_search', 'web_fetch'],
    dj_booth: ['music_generate', 'music_status', 'music_result', 'music_list', 'music_favorite', 'music_library', 'music_search', 'music_play', 'midi_create', 'music_compose'],
    memory_garden: ['vector_add', 'vector_search', 'vector_delete', 'vector_list_collections', 'vector_get_stats', 'vector_add_knowledge', 'vector_search_knowledge', 'memory_store', 'memory_retrieve', 'memory_search', 'memory_delete', 'memory_list', 'memory_health_stale', 'memory_health_low_access', 'memory_health_duplicates', 'memory_consolidate', 'dataset_list', 'dataset_query'],
    file_shed: ['fs_read_file', 'fs_write_file', 'fs_list_files', 'fs_mkdir', 'fs_delete', 'fs_exists', 'fs_get_info', 'fs_read_lines', 'fs_edit'],
    workshop: ['execute_python'],
    bridge_portal: ['agent_spawn', 'agent_status', 'agent_result', 'agent_list', 'socratic_council', 'village_post', 'village_search', 'village_get_thread', 'village_list_agents', 'summon_ancestor', 'introduction_ritual', 'village_detect_convergence', 'village_get_stats']
};

/**
 * Get zone by tool name
 */
export function getZoneForTool(toolName) {
    const TOOL_ZONES = {
        // Music
        music_generate: 'dj_booth', music_status: 'dj_booth', music_result: 'dj_booth',
        music_list: 'dj_booth', music_favorite: 'dj_booth', music_library: 'dj_booth',
        music_search: 'dj_booth', music_play: 'dj_booth', midi_create: 'dj_booth',
        music_compose: 'dj_booth',

        // Memory/Vector
        vector_add: 'memory_garden', vector_search: 'memory_garden',
        vector_delete: 'memory_garden', vector_list_collections: 'memory_garden',
        vector_get_stats: 'memory_garden', vector_add_knowledge: 'memory_garden',
        vector_search_knowledge: 'memory_garden', memory_store: 'memory_garden',
        memory_retrieve: 'memory_garden', memory_search: 'memory_garden',
        memory_delete: 'memory_garden', memory_list: 'memory_garden',
        memory_health_stale: 'memory_garden', memory_health_low_access: 'memory_garden',
        memory_health_duplicates: 'memory_garden', memory_consolidate: 'memory_garden',
        memory_health_summary: 'memory_garden',
        dataset_list: 'memory_garden', dataset_query: 'memory_garden',

        // Filesystem
        fs_read_file: 'file_shed', fs_write_file: 'file_shed', fs_list_files: 'file_shed',
        fs_mkdir: 'file_shed', fs_delete: 'file_shed', fs_exists: 'file_shed',
        fs_get_info: 'file_shed', fs_read_lines: 'file_shed', fs_edit: 'file_shed',

        // Code
        execute_python: 'workshop',

        // Agent/Village
        agent_spawn: 'bridge_portal', agent_status: 'bridge_portal',
        agent_result: 'bridge_portal', agent_list: 'bridge_portal',
        socratic_council: 'bridge_portal', village_post: 'bridge_portal',
        village_search: 'bridge_portal', village_get_thread: 'bridge_portal',
        village_list_agents: 'bridge_portal', summon_ancestor: 'bridge_portal',
        introduction_ritual: 'bridge_portal', village_detect_convergence: 'bridge_portal',
        village_get_stats: 'bridge_portal'
    };

    return TOOL_ZONES[toolName] || 'village_square';
}

/**
 * Hit test: check if a point is within a zone
 */
export function getZoneAtPoint(x, y) {
    for (const [name, zone] of Object.entries(ZONES)) {
        const halfW = zone.width / 2;
        const halfH = zone.height / 2;
        if (x >= zone.x - halfW && x <= zone.x + halfW &&
            y >= zone.y - halfH && y <= zone.y + halfH) {
            return name;
        }
    }
    return null;
}
