/**
 * Canvas Renderer - Enhanced with visual effects
 *
 * Handles drawing the village, zones, and UI elements.
 */

import { ZONES, CANVAS_WIDTH, CANVAS_HEIGHT } from './zones.js';

export class Renderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');

        // Set canvas size
        canvas.width = CANVAS_WIDTH;
        canvas.height = CANVAS_HEIGHT;

        // Animation state
        this.time = 0;
        this.starField = this.generateStarField(50);
    }

    /**
     * Generate background star field
     */
    generateStarField(count) {
        const stars = [];
        for (let i = 0; i < count; i++) {
            stars.push({
                x: Math.random() * CANVAS_WIDTH,
                y: Math.random() * CANVAS_HEIGHT,
                size: Math.random() * 1.5 + 0.5,
                twinkleSpeed: Math.random() * 0.05 + 0.02,
                phase: Math.random() * Math.PI * 2
            });
        }
        return stars;
    }

    /**
     * Clear canvas with gradient background
     */
    clear() {
        // Create gradient background
        const gradient = this.ctx.createLinearGradient(0, 0, 0, CANVAS_HEIGHT);
        gradient.addColorStop(0, '#0a0a12');
        gradient.addColorStop(0.5, '#12121f');
        gradient.addColorStop(1, '#0a0a12');

        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw twinkling stars
        this.time += 0.016;
        this.starField.forEach(star => {
            const twinkle = 0.3 + Math.sin(this.time * star.twinkleSpeed * 60 + star.phase) * 0.7;
            this.ctx.fillStyle = `rgba(255, 255, 255, ${twinkle * 0.5})`;
            this.ctx.beginPath();
            this.ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
            this.ctx.fill();
        });
    }

    /**
     * Draw all zones
     */
    drawZones(activeZone = null) {
        for (const [name, zone] of Object.entries(ZONES)) {
            this.drawZone(name, zone, name === activeZone);
        }
    }

    /**
     * Draw a single zone with enhanced visuals
     */
    drawZone(name, zone, isActive = false) {
        const ctx = this.ctx;
        const halfW = zone.width / 2;
        const halfH = zone.height / 2;

        ctx.save();

        // Active zone pulse effect
        let pulseSize = 0;
        if (isActive) {
            pulseSize = Math.sin(this.time * 4) * 3;
            ctx.shadowColor = zone.color;
            ctx.shadowBlur = 25 + Math.sin(this.time * 4) * 10;
        }

        // Zone background with gradient
        const gradient = ctx.createRadialGradient(
            zone.x, zone.y, 0,
            zone.x, zone.y, Math.max(zone.width, zone.height) * 0.7
        );

        const alpha = isActive ? 'aa' : '55';
        gradient.addColorStop(0, zone.color + alpha);
        gradient.addColorStop(1, zone.color + '22');

        ctx.fillStyle = gradient;
        ctx.strokeStyle = zone.color;
        ctx.lineWidth = isActive ? 3 : 2;

        // Draw rounded rectangle
        const x = zone.x - halfW - pulseSize;
        const y = zone.y - halfH - pulseSize;
        const w = zone.width + pulseSize * 2;
        const h = zone.height + pulseSize * 2;

        ctx.beginPath();
        ctx.roundRect(x, y, w, h, 12);
        ctx.fill();
        ctx.stroke();

        // Inner glow for active zones
        if (isActive) {
            ctx.strokeStyle = zone.color + '66';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.roundRect(x + 4, y + 4, w - 8, h - 8, 8);
            ctx.stroke();
        }

        // Zone icon (emoji-based for simplicity)
        const icons = {
            village_square: '🏠',
            dj_booth: '🎵',
            memory_garden: '🌿',
            file_shed: '📁',
            workshop: '⚙️',
            bridge_portal: '🌉'
        };

        ctx.font = '20px serif';
        ctx.textAlign = 'center';
        ctx.fillText(icons[name] || '⭐', zone.x, zone.y + 6);

        // Label with better styling
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 11px monospace';
        ctx.textAlign = 'center';

        // Label background
        const labelY = zone.y + halfH + 18;
        const labelWidth = ctx.measureText(zone.label).width + 10;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        ctx.fillRect(zone.x - labelWidth/2, labelY - 10, labelWidth, 14);

        ctx.fillStyle = isActive ? '#ffffff' : '#aaaaaa';
        ctx.fillText(zone.label, zone.x, labelY);

        ctx.restore();
    }

    /**
     * Draw connection lines between zones (paths)
     */
    drawConnections() {
        const ctx = this.ctx;
        ctx.save();

        // Draw paths from village square to other zones
        const center = ZONES.village_square;

        for (const [name, zone] of Object.entries(ZONES)) {
            if (name === 'village_square') continue;

            // Animated dashed line
            const dashOffset = this.time * 20;

            ctx.strokeStyle = 'rgba(212, 175, 55, 0.15)';
            ctx.lineWidth = 1;
            ctx.setLineDash([5, 10]);
            ctx.lineDashOffset = -dashOffset;

            ctx.beginPath();
            ctx.moveTo(center.x, center.y);
            ctx.lineTo(zone.x, zone.y);
            ctx.stroke();
        }

        ctx.setLineDash([]);
        ctx.restore();
    }

    /**
     * Draw status bar with better styling
     */
    drawStatus(status) {
        const ctx = this.ctx;
        ctx.save();

        // Status panel background
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.fillRect(5, 5, 150, 55);
        ctx.strokeStyle = '#D4AF37';
        ctx.lineWidth = 1;
        ctx.strokeRect(5, 5, 150, 55);

        // Connection status with color
        ctx.font = '11px monospace';
        ctx.fillStyle = status.connection === 'connected' ? '#00ff88' : '#ff4444';
        ctx.textAlign = 'left';
        ctx.fillText(`● ${status.connection.toUpperCase()}`, 12, 22);

        // Event count
        ctx.fillStyle = '#aaaaaa';
        ctx.fillText(`Events: ${status.eventCount}`, 12, 38);

        // Last tool
        if (status.lastTool) {
            ctx.fillStyle = '#D4AF37';
            ctx.fillText(`Last: ${status.lastTool}`, 12, 54);
        }

        ctx.restore();
    }

    /**
     * Draw the title/header
     */
    drawHeader() {
        const ctx = this.ctx;
        ctx.save();

        // Title with glow
        ctx.shadowColor = '#D4AF37';
        ctx.shadowBlur = 10;
        ctx.fillStyle = '#D4AF37';
        ctx.font = 'bold 18px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('⚗ VILLAGE GUI ⚗', CANVAS_WIDTH / 2, 28);

        ctx.shadowBlur = 0;
        ctx.fillStyle = '#666';
        ctx.font = '10px monospace';
        ctx.fillText('Agent Activity Visualization', CANVAS_WIDTH / 2, 44);

        ctx.restore();
    }

    /**
     * Draw a notification popup
     */
    drawNotification(message, type = 'info') {
        const ctx = this.ctx;
        ctx.save();

        const colors = {
            info: '#00aaff',
            success: '#00ff88',
            error: '#ff4444',
            warning: '#ffaa00'
        };

        const color = colors[type] || colors.info;

        // Position at bottom center
        const y = CANVAS_HEIGHT - 50;
        const padding = 15;
        ctx.font = '12px monospace';
        const width = ctx.measureText(message).width + padding * 2;

        // Background
        ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;

        ctx.beginPath();
        ctx.roundRect(CANVAS_WIDTH/2 - width/2, y, width, 30, 5);
        ctx.fill();
        ctx.stroke();

        // Text
        ctx.fillStyle = color;
        ctx.textAlign = 'center';
        ctx.fillText(message, CANVAS_WIDTH/2, y + 19);

        ctx.restore();
    }

    /**
     * Draw FPS counter (debug)
     */
    drawFPS(fps) {
        const ctx = this.ctx;
        ctx.save();
        ctx.fillStyle = '#444';
        ctx.font = '10px monospace';
        ctx.textAlign = 'right';
        ctx.fillText(`${fps} FPS`, CANVAS_WIDTH - 10, CANVAS_HEIGHT - 10);
        ctx.restore();
    }
}
