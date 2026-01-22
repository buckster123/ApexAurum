/**
 * Village GUI - Main Application
 *
 * Coordinates WebSocket events, agents, and rendering.
 * Phase 3: Integrated with HTML UI panels
 */

import { ZONES, getZoneForTool } from './zones.js';
import { Agent, AGENT_COLORS } from './agent.js';
import { Renderer } from './renderer.js';

class VillageApp {
    constructor() {
        // Canvas and renderer
        this.canvas = document.getElementById('village-canvas');
        this.renderer = new Renderer(this.canvas);

        // Agents - restore from localStorage or default
        this.agents = new Map();
        this.currentAgentId = localStorage.getItem('village_agent') || 'CLAUDE';
        this.ensureAgent(this.currentAgentId);

        // State
        this.status = {
            connection: 'disconnected',
            eventCount: 0,
            lastTool: null
        };

        // Active zone (for highlighting)
        this.activeZone = null;

        // WebSocket
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.connectWebSocket();

        // Start render loop
        this.animate();

        // Export to window for UI interaction
        window.villageApp = this;

        console.log('Village GUI initialized');
    }

    /**
     * Set current agent (called from UI selector)
     */
    setCurrentAgent(agentId) {
        this.currentAgentId = agentId;
        this.ensureAgent(agentId);
        console.log(`Active agent: ${agentId}`);
    }

    /**
     * Ensure an agent exists, create if not
     */
    ensureAgent(agentId) {
        if (!this.agents.has(agentId)) {
            const color = AGENT_COLORS[agentId] || AGENT_COLORS.default;
            const agent = new Agent(agentId, agentId, color);
            this.agents.set(agentId, agent);
            console.log(`Created agent: ${agentId} (${color})`);
        }
        return this.agents.get(agentId);
    }

    /**
     * Connect to WebSocket
     */
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/village`;

        console.log(`Connecting to ${wsUrl}`);
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.status.connection = 'connected';
            this.reconnectAttempts = 0;
            this.updateUI();

            // Log to activity panel
            if (window.addLogEntry) {
                addLogEntry('system', 'SYSTEM', 'connect', 'WebSocket connected');
            }
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.status.connection = 'disconnected';
            this.updateUI();

            // Reconnect with backoff
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
                this.reconnectAttempts++;
                console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
                setTimeout(() => this.connectWebSocket(), delay);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.status.connection = 'error';
            this.updateUI();
        };

        this.ws.onmessage = (event) => {
            this.handleEvent(JSON.parse(event.data));
        };
    }

    /**
     * Handle incoming event from backend
     */
    handleEvent(event) {
        console.log('Event:', event);
        this.status.eventCount++;

        switch (event.type) {
            case 'tool_start':
                this.handleToolStart(event);
                break;

            case 'tool_complete':
            case 'tool_error':
                this.handleToolComplete(event);
                break;

            case 'connection':
                console.log('Connection confirmed');
                break;

            default:
                console.log('Unknown event type:', event.type);
        }

        this.updateUI();
    }

    /**
     * Handle tool start event
     */
    handleToolStart(event) {
        const agentId = event.agent_id || this.currentAgentId;
        const agent = this.ensureAgent(agentId);
        const zone = event.zone || getZoneForTool(event.tool);

        agent.moveTo(zone, ZONES);
        agent.startTool(event.tool);

        this.activeZone = zone;
        this.status.lastTool = event.tool;

        // Update activity log
        if (window.addLogEntry) {
            addLogEntry('start', agentId, event.tool, null, zone);
        }
    }

    /**
     * Handle tool complete event
     */
    handleToolComplete(event) {
        const agentId = event.agent_id || this.currentAgentId;
        const agent = this.agents.get(agentId);
        const zone = event.zone || getZoneForTool(event.tool);

        if (agent) {
            agent.finishTool();
        }

        // Update activity log
        const type = event.success ? 'complete' : 'error';
        if (window.addLogEntry) {
            addLogEntry(type, agentId, event.tool, event.result_preview, zone);
        }

        // Clear active zone after brief delay
        setTimeout(() => {
            this.activeZone = null;
        }, 500);
    }

    /**
     * Update UI panels (stats, etc.)
     */
    updateUI() {
        if (window.updateStats) {
            updateStats(this.status);
        }
    }

    /**
     * Animation loop
     */
    animate() {
        // Update all agents
        for (const agent of this.agents.values()) {
            agent.update();
        }

        // Render
        this.renderer.clear();
        this.renderer.drawConnections();
        this.renderer.drawZones(this.activeZone);

        // Draw all agents
        for (const agent of this.agents.values()) {
            agent.draw(this.renderer.ctx);
        }

        // Continue loop
        requestAnimationFrame(() => this.animate());
    }
}

// Start app when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.villageApp = new VillageApp();
});
