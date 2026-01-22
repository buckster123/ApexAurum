/**
 * Village Zone Definitions
 *
 * Each zone has:
 * - position (x, y) - center point
 * - size (width, height)
 * - color - fill color
 * - label - display name
 */

export const CANVAS_WIDTH = 800;
export const CANVAS_HEIGHT = 600;

export const ZONES = {
    village_square: {
        x: 400, y: 300,
        width: 120, height: 120,
        color: '#2d3436',
        label: 'Village Square'
    },
    dj_booth: {
        x: 100, y: 300,
        width: 100, height: 80,
        color: '#6c5ce7',
        label: 'DJ Booth'
    },
    memory_garden: {
        x: 400, y: 80,
        width: 140, height: 80,
        color: '#00b894',
        label: 'Memory Garden'
    },
    file_shed: {
        x: 700, y: 300,
        width: 100, height: 80,
        color: '#fdcb6e',
        label: 'File Shed'
    },
    workshop: {
        x: 400, y: 520,
        width: 120, height: 80,
        color: '#e17055',
        label: 'Workshop'
    },
    bridge_portal: {
        x: 700, y: 80,
        width: 100, height: 80,
        color: '#a29bfe',
        label: 'Bridge Portal'
    }
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
