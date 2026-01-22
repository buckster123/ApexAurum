/**
 * Village GUI - Main Application
 *
 * Coordinates WebSocket events, agents, and rendering.
 * Phase 3: Integrated with HTML UI panels
 */

import { ZONES, ZONE_TOOLS, getZoneForTool, getZoneAtPoint } from './zones.js';
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

        // Zone history - tracks recent tool executions per zone
        this.zoneHistory = {};
        for (const zoneName of Object.keys(ZONES)) {
            this.zoneHistory[zoneName] = [];
        }

        // Selected zone (for detail panel)
        this.selectedZone = null;

        // Hovered zone (for visual feedback)
        this.hoveredZone = null;

        // Set up canvas click handler
        this.canvas.addEventListener('click', (e) => this.handleCanvasClick(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleCanvasHover(e));
        this.canvas.addEventListener('mouseleave', () => { this.hoveredZone = null; });

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

        console.log(`Village GUI: Connecting to ${wsUrl}`);
        console.log(`Village GUI: location.host = ${window.location.host}`);
        console.log(`Village GUI: location.protocol = ${window.location.protocol}`);

        try {
            this.ws = new WebSocket(wsUrl);
        } catch (e) {
            console.error('Village GUI: WebSocket creation failed:', e);
            this.status.connection = 'error';
            this.updateUI();
            return;
        }

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

        // Track in zone history
        this.addToZoneHistory(zone, {
            tool: event.tool,
            agent: agentId,
            success: event.success,
            result_preview: event.result_preview,
            timestamp: Date.now()
        });

        // Update activity log
        const type = event.success ? 'complete' : 'error';
        if (window.addLogEntry) {
            addLogEntry(type, agentId, event.tool, event.result_preview, zone);
        }

        // Clear active zone after brief delay
        setTimeout(() => {
            this.activeZone = null;
        }, 500);

        // Update zone detail if this zone is selected
        if (this.selectedZone === zone) {
            this.showZoneDetail(zone);
        }
    }

    /**
     * Add entry to zone history (keep last 20 per zone)
     */
    addToZoneHistory(zoneName, entry) {
        if (!this.zoneHistory[zoneName]) {
            this.zoneHistory[zoneName] = [];
        }
        this.zoneHistory[zoneName].unshift(entry);
        if (this.zoneHistory[zoneName].length > 20) {
            this.zoneHistory[zoneName].pop();
        }
    }

    /**
     * Handle canvas click - detect zone
     */
    handleCanvasClick(event) {
        const rect = this.canvas.getBoundingClientRect();
        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;
        const x = (event.clientX - rect.left) * scaleX;
        const y = (event.clientY - rect.top) * scaleY;

        const zoneName = getZoneAtPoint(x, y);
        if (zoneName) {
            this.selectedZone = zoneName;
            this.showZoneDetail(zoneName);
        } else {
            this.hideZoneDetail();
        }
    }

    /**
     * Handle canvas hover - change cursor and highlight zone
     */
    handleCanvasHover(event) {
        const rect = this.canvas.getBoundingClientRect();
        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;
        const x = (event.clientX - rect.left) * scaleX;
        const y = (event.clientY - rect.top) * scaleY;

        const zoneName = getZoneAtPoint(x, y);
        this.hoveredZone = zoneName;
        this.canvas.style.cursor = zoneName ? 'pointer' : 'default';
    }

    /**
     * Show zone detail panel
     */
    showZoneDetail(zoneName) {
        const zone = ZONES[zoneName];
        const tools = ZONE_TOOLS[zoneName] || [];
        const history = this.zoneHistory[zoneName] || [];

        const panel = document.getElementById('zone-detail-panel');
        if (!panel) return;

        // Build HTML
        let html = `
            <div class="zone-detail-header" style="border-left-color: ${zone.color}">
                <span class="zone-icon">${zone.icon}</span>
                <h4>${zone.label}</h4>
                <button onclick="window.villageApp.hideZoneDetail()" class="close-btn">&times;</button>
            </div>
            <p class="zone-description">${zone.description}</p>
            <div class="zone-section">
                <h5>Available Tools (${tools.length})</h5>
                <div class="zone-tools">
                    ${tools.slice(0, 8).map(t => `<span class="tool-tag">${t}</span>`).join('')}
                    ${tools.length > 8 ? `<span class="tool-more">+${tools.length - 8} more</span>` : ''}
                </div>
            </div>
            <div class="zone-section">
                <h5>Recent Activity</h5>
                <div class="zone-history">
        `;

        if (history.length === 0) {
            html += '<div class="no-history">No activity yet</div>';
        } else {
            history.slice(0, 5).forEach(entry => {
                const time = new Date(entry.timestamp).toLocaleTimeString('en-US', {hour12: false});
                const icon = entry.success ? '✓' : '✗';
                const statusClass = entry.success ? 'success' : 'error';
                html += `
                    <div class="history-entry ${statusClass}">
                        <span class="history-icon">${icon}</span>
                        <span class="history-tool">${entry.tool}</span>
                        <span class="history-agent">${entry.agent}</span>
                        <span class="history-time">${time}</span>
                    </div>
                `;
            });
        }

        html += '</div></div>';

        panel.innerHTML = html;
        panel.classList.add('visible');
    }

    /**
     * Hide zone detail panel
     */
    hideZoneDetail() {
        this.selectedZone = null;
        const panel = document.getElementById('zone-detail-panel');
        if (panel) {
            panel.classList.remove('visible');
        }
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
        this.renderer.drawZones(this.activeZone, this.hoveredZone, this.selectedZone);

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
    console.log('Village GUI: DOM ready, creating app...');
    try {
        window.villageApp = new VillageApp();
        console.log('Village GUI: App created successfully');
    } catch (e) {
        console.error('Village GUI: Failed to create app:', e);
        const statusEl = document.getElementById('stat-connection');
        if (statusEl) {
            statusEl.textContent = 'INIT ERROR: ' + e.message;
            statusEl.className = 'stat-value disconnected';
        }
    }
});

// Mark module as loaded
console.log('Village GUI: Module loaded');
