/**
 * Village GUI - Main Application
 *
 * Coordinates WebSocket events, agents, and rendering.
 */

import { ZONES, getZoneForTool } from './zones.js';
import { Agent, AGENT_COLORS } from './agent.js';
import { Renderer } from './renderer.js';

class VillageApp {
    constructor() {
        // Canvas and renderer
        this.canvas = document.getElementById('village-canvas');
        this.renderer = new Renderer(this.canvas);

        // Agents
        this.agents = new Map();
        this.ensureAgent('CLAUDE');  // Default agent

        // State
        this.status = {
            connection: 'disconnected',
            eventCount: 0,
            lastTool: null
        };

        // Active zone (for highlighting)
        this.activeZone = null;

        // Event log
        this.eventLog = [];
        this.maxLogEntries = 50;

        // WebSocket
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.connectWebSocket();

        // Start render loop
        this.animate();

        console.log('Village GUI initialized');
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
            this.addLog('system', 'Connected to Village GUI');
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.status.connection = 'disconnected';
            this.addLog('system', 'Disconnected from server');

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
                this.addLog('system', 'Connection confirmed');
                break;

            default:
                console.log('Unknown event type:', event.type);
        }
    }

    /**
     * Handle tool start event
     */
    handleToolStart(event) {
        const agent = this.ensureAgent(event.agent_id);
        const zone = event.zone || getZoneForTool(event.tool);

        agent.moveTo(zone, ZONES);
        agent.startTool(event.tool);

        this.activeZone = zone;
        this.status.lastTool = event.tool;

        this.addLog('tool_start', `${event.agent_id} -> ${event.tool} @ ${zone}`);
    }

    /**
     * Handle tool complete event
     */
    handleToolComplete(event) {
        const agent = this.agents.get(event.agent_id);
        if (agent) {
            agent.finishTool();
        }

        const status = event.success ? 'OK' : 'FAIL';
        const duration = event.duration_ms ? ` (${event.duration_ms}ms)` : '';
        this.addLog('tool_complete', `${event.agent_id} <- ${event.tool} ${status}${duration}`);

        // Clear active zone after brief delay
        setTimeout(() => {
            this.activeZone = null;
        }, 500);
    }

    /**
     * Add entry to event log
     */
    addLog(type, message) {
        const timestamp = new Date().toLocaleTimeString();
        this.eventLog.unshift({ type, message, timestamp });

        // Trim log
        if (this.eventLog.length > this.maxLogEntries) {
            this.eventLog.pop();
        }

        // Update DOM log
        this.updateLogDisplay();
    }

    /**
     * Update the log display in DOM
     */
    updateLogDisplay() {
        const logEl = document.getElementById('event-log');
        if (!logEl) return;

        const entries = this.eventLog.slice(0, 10).map(entry => {
            const icon = entry.type === 'tool_start' ? '>' :
                         entry.type === 'tool_complete' ? '<' : '*';
            return `${entry.timestamp} ${icon} ${entry.message}`;
        });

        logEl.textContent = entries.join('\n');
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
        this.renderer.drawHeader();
        this.renderer.drawConnections();
        this.renderer.drawZones(this.activeZone);

        // Draw all agents
        for (const agent of this.agents.values()) {
            agent.draw(this.renderer.ctx);
        }

        this.renderer.drawStatus(this.status);

        // Continue loop
        requestAnimationFrame(() => this.animate());
    }
}

// Start app when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.villageApp = new VillageApp();
});
