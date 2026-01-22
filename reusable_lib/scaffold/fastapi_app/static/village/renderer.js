/**
 * Canvas Renderer - Enhanced with visual effects
 *
 * Handles drawing the village, zones, and UI elements.
 * Now with Day/Night cycle!
 */

import { ZONES, CANVAS_WIDTH, CANVAS_HEIGHT } from './zones.js';

// Sky color palettes for different times of day
const SKY_COLORS = {
    // Night (0-5, 21-24)
    night: {
        top: '#0a0a12',
        mid: '#12121f',
        bottom: '#0a0a12',
        starOpacity: 0.8
    },
    // Dawn (5-7)
    dawn: {
        top: '#1a1a2e',
        mid: '#4a3f6b',
        bottom: '#ff7b54',
        starOpacity: 0.2
    },
    // Morning (7-10)
    morning: {
        top: '#4a90c2',
        mid: '#87ceeb',
        bottom: '#ffecd2',
        starOpacity: 0
    },
    // Day (10-17)
    day: {
        top: '#2d6aa5',
        mid: '#5da5d4',
        bottom: '#87ceeb',
        starOpacity: 0
    },
    // Dusk (17-19)
    dusk: {
        top: '#2d3a5a',
        mid: '#b06e4f',
        bottom: '#ff6b35',
        starOpacity: 0.1
    },
    // Evening (19-21)
    evening: {
        top: '#1a1a2e',
        mid: '#3d3d6b',
        bottom: '#5a4a6b',
        starOpacity: 0.5
    }
};

export class Renderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');

        // Set canvas size
        canvas.width = CANVAS_WIDTH;
        canvas.height = CANVAS_HEIGHT;

        // Animation state
        this.time = 0;
        this.starField = this.generateStarField(80);  // More stars for night sky

        // Day/Night cycle - use real time by default
        this.useRealTime = true;
        this.manualHour = 12;  // For manual override
        this.timeSpeed = 1;    // 1 = real time, 60 = 1 hour per minute

        // Weather system (Phase 4.2)
        this.weather = 'clear';  // clear, rain, storm, snow, fog
        this.weatherIntensity = 0.5;  // 0-1
        this.weatherParticles = [];
        this.lightningFlash = 0;  // Flash intensity (decays)
        this.lastLightning = 0;
        this.initWeatherParticles();
    }

    /**
     * Initialize weather particle pool
     */
    initWeatherParticles() {
        this.weatherParticles = [];
        for (let i = 0; i < 200; i++) {
            this.weatherParticles.push({
                x: Math.random() * CANVAS_WIDTH,
                y: Math.random() * CANVAS_HEIGHT,
                speed: Math.random() * 2 + 1,
                size: Math.random() * 2 + 1,
                wobble: Math.random() * Math.PI * 2
            });
        }
    }

    /**
     * Set weather state
     */
    setWeather(type, intensity = 0.5) {
        this.weather = type;
        this.weatherIntensity = Math.max(0, Math.min(1, intensity));
        if (type === 'storm') {
            this.lastLightning = this.time;
        }
    }

    /**
     * Get current hour (0-24) based on settings
     */
    getCurrentHour() {
        if (this.useRealTime) {
            const now = new Date();
            return now.getHours() + now.getMinutes() / 60;
        }
        return this.manualHour;
    }

    /**
     * Get time of day category for sound system
     * @returns {'night'|'dawn'|'day'|'dusk'}
     */
    getTimeOfDay() {
        const hour = this.getCurrentHour();
        if (hour >= 21 || hour < 5) return 'night';
        if (hour >= 5 && hour < 7) return 'dawn';
        if (hour >= 19 && hour < 21) return 'dusk';
        return 'day';
    }

    /**
     * Get sky palette for current time
     */
    getSkyPalette(hour) {
        // Determine time period and blend between palettes
        let palette1, palette2, blend;

        if (hour >= 21 || hour < 5) {
            // Night
            return SKY_COLORS.night;
        } else if (hour >= 5 && hour < 7) {
            // Dawn transition
            blend = (hour - 5) / 2;
            palette1 = SKY_COLORS.night;
            palette2 = SKY_COLORS.dawn;
        } else if (hour >= 7 && hour < 10) {
            // Morning transition
            blend = (hour - 7) / 3;
            palette1 = SKY_COLORS.dawn;
            palette2 = SKY_COLORS.morning;
        } else if (hour >= 10 && hour < 17) {
            // Full day
            return SKY_COLORS.day;
        } else if (hour >= 17 && hour < 19) {
            // Dusk transition
            blend = (hour - 17) / 2;
            palette1 = SKY_COLORS.day;
            palette2 = SKY_COLORS.dusk;
        } else if (hour >= 19 && hour < 21) {
            // Evening transition
            blend = (hour - 19) / 2;
            palette1 = SKY_COLORS.dusk;
            palette2 = SKY_COLORS.evening;
        }

        // Blend colors
        return this.blendPalettes(palette1, palette2, blend);
    }

    /**
     * Blend two color palettes
     */
    blendPalettes(p1, p2, t) {
        return {
            top: this.lerpColor(p1.top, p2.top, t),
            mid: this.lerpColor(p1.mid, p2.mid, t),
            bottom: this.lerpColor(p1.bottom, p2.bottom, t),
            starOpacity: p1.starOpacity + (p2.starOpacity - p1.starOpacity) * t
        };
    }

    /**
     * Linear interpolate between two hex colors
     */
    lerpColor(c1, c2, t) {
        const r1 = parseInt(c1.slice(1, 3), 16);
        const g1 = parseInt(c1.slice(3, 5), 16);
        const b1 = parseInt(c1.slice(5, 7), 16);
        const r2 = parseInt(c2.slice(1, 3), 16);
        const g2 = parseInt(c2.slice(3, 5), 16);
        const b2 = parseInt(c2.slice(5, 7), 16);

        const r = Math.round(r1 + (r2 - r1) * t);
        const g = Math.round(g1 + (g2 - g1) * t);
        const b = Math.round(b1 + (b2 - b1) * t);

        return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
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
     * Clear canvas with dynamic sky based on time of day
     */
    clear() {
        const hour = this.getCurrentHour();
        const palette = this.getSkyPalette(hour);

        // Create gradient background
        const gradient = this.ctx.createLinearGradient(0, 0, 0, CANVAS_HEIGHT);
        gradient.addColorStop(0, palette.top);
        gradient.addColorStop(0.5, palette.mid);
        gradient.addColorStop(1, palette.bottom);

        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw sun or moon
        this.drawCelestialBody(hour);

        // Draw twinkling stars (only visible at night)
        this.time += 0.016;
        if (palette.starOpacity > 0) {
            this.starField.forEach(star => {
                const twinkle = 0.3 + Math.sin(this.time * star.twinkleSpeed * 60 + star.phase) * 0.7;
                this.ctx.fillStyle = `rgba(255, 255, 255, ${twinkle * palette.starOpacity})`;
                this.ctx.beginPath();
                this.ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
                this.ctx.fill();
            });
        }

        // Store current brightness for zone rendering
        this.currentBrightness = this.getBrightness(hour);

        // Draw weather effects (rain, snow fall behind zones)
        if (this.weather === 'rain' || this.weather === 'storm' || this.weather === 'snow') {
            this.drawWeather();
        }
    }

    /**
     * Draw weather overlay (fog, lightning flash - drawn after zones)
     */
    drawWeatherOverlay() {
        if (this.weather === 'fog') {
            this.drawFog(this.ctx, this.weatherIntensity);
        }
        if (this.weather === 'storm' && this.lightningFlash > 0) {
            this.ctx.fillStyle = `rgba(255, 255, 255, ${this.lightningFlash * 0.3})`;
            this.ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
            this.lightningFlash -= 0.05;
        }
    }

    /**
     * Draw sun or moon based on time
     */
    drawCelestialBody(hour) {
        const ctx = this.ctx;

        // Calculate position along an arc
        // Sun rises at 6, peaks at 12, sets at 18
        // Moon rises at 18, peaks at 0, sets at 6

        const isSun = hour >= 6 && hour < 20;
        let progress;

        if (isSun) {
            // Sun path (6-20)
            progress = (hour - 6) / 14;
        } else {
            // Moon path (20-6)
            if (hour >= 20) {
                progress = (hour - 20) / 10;
            } else {
                progress = (hour + 4) / 10;
            }
        }

        // Arc path from left to right
        const x = 50 + progress * (CANVAS_WIDTH - 100);
        const arcHeight = 120;
        const y = 80 + Math.sin(progress * Math.PI) * -arcHeight + arcHeight;

        ctx.save();

        if (isSun) {
            // Draw sun
            const sunGlow = ctx.createRadialGradient(x, y, 0, x, y, 40);
            sunGlow.addColorStop(0, 'rgba(255, 220, 100, 0.9)');
            sunGlow.addColorStop(0.3, 'rgba(255, 180, 50, 0.5)');
            sunGlow.addColorStop(1, 'rgba(255, 150, 50, 0)');

            ctx.fillStyle = sunGlow;
            ctx.beginPath();
            ctx.arc(x, y, 40, 0, Math.PI * 2);
            ctx.fill();

            // Sun core
            ctx.fillStyle = '#ffdd66';
            ctx.beginPath();
            ctx.arc(x, y, 15, 0, Math.PI * 2);
            ctx.fill();
        } else {
            // Draw moon
            const moonGlow = ctx.createRadialGradient(x, y, 0, x, y, 30);
            moonGlow.addColorStop(0, 'rgba(230, 230, 255, 0.8)');
            moonGlow.addColorStop(0.5, 'rgba(200, 200, 230, 0.3)');
            moonGlow.addColorStop(1, 'rgba(150, 150, 200, 0)');

            ctx.fillStyle = moonGlow;
            ctx.beginPath();
            ctx.arc(x, y, 30, 0, Math.PI * 2);
            ctx.fill();

            // Moon core
            ctx.fillStyle = '#e8e8f0';
            ctx.beginPath();
            ctx.arc(x, y, 12, 0, Math.PI * 2);
            ctx.fill();

            // Moon craters (subtle)
            ctx.fillStyle = 'rgba(200, 200, 210, 0.5)';
            ctx.beginPath();
            ctx.arc(x - 3, y - 2, 3, 0, Math.PI * 2);
            ctx.fill();
            ctx.beginPath();
            ctx.arc(x + 4, y + 3, 2, 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.restore();
    }

    /**
     * Get brightness multiplier for current time (affects zone rendering)
     */
    getBrightness(hour) {
        if (hour >= 10 && hour < 17) return 1.0;      // Full day
        if (hour >= 7 && hour < 10) return 0.85;       // Morning
        if (hour >= 17 && hour < 19) return 0.75;      // Dusk
        if (hour >= 19 && hour < 21) return 0.5;       // Evening
        if (hour >= 5 && hour < 7) return 0.4;         // Dawn
        return 0.3;                                     // Night
    }

    /**
     * Draw weather effects
     */
    drawWeather() {
        if (this.weather === 'clear') return;

        const ctx = this.ctx;
        const intensity = this.weatherIntensity;
        const particleCount = Math.floor(this.weatherParticles.length * intensity);

        ctx.save();

        switch (this.weather) {
            case 'rain':
                this.drawRain(ctx, particleCount);
                break;
            case 'storm':
                this.drawRain(ctx, particleCount);
                this.drawLightning(ctx);
                break;
            case 'snow':
                this.drawSnow(ctx, particleCount);
                break;
            case 'fog':
                this.drawFog(ctx, intensity);
                break;
        }

        ctx.restore();
    }

    /**
     * Draw rain particles
     */
    drawRain(ctx, count) {
        ctx.strokeStyle = 'rgba(150, 180, 255, 0.6)';
        ctx.lineWidth = 1;

        for (let i = 0; i < count; i++) {
            const p = this.weatherParticles[i];

            // Update position
            p.y += p.speed * 8;
            p.x += 2;  // Wind

            // Reset if off screen
            if (p.y > CANVAS_HEIGHT) {
                p.y = -10;
                p.x = Math.random() * (CANVAS_WIDTH + 100) - 50;
            }
            if (p.x > CANVAS_WIDTH + 50) {
                p.x = -50;
            }

            // Draw raindrop as a short line
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p.x + 3, p.y + 10 + p.speed * 3);
            ctx.stroke();
        }
    }

    /**
     * Draw lightning flash
     */
    drawLightning(ctx) {
        // Random lightning strikes
        if (Math.random() < 0.005 * this.weatherIntensity) {
            this.lightningFlash = 1;
            this.lastLightning = this.time;
        }

        // Decay flash
        if (this.lightningFlash > 0) {
            ctx.fillStyle = `rgba(255, 255, 255, ${this.lightningFlash * 0.7})`;
            ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

            // Draw lightning bolt occasionally
            if (this.lightningFlash > 0.8) {
                this.drawLightningBolt(ctx);
            }

            this.lightningFlash -= 0.08;
        }
    }

    /**
     * Draw a lightning bolt
     */
    drawLightningBolt(ctx) {
        const startX = Math.random() * CANVAS_WIDTH * 0.6 + CANVAS_WIDTH * 0.2;
        let x = startX;
        let y = 0;

        ctx.strokeStyle = 'rgba(255, 255, 200, 0.9)';
        ctx.lineWidth = 2;
        ctx.shadowColor = '#ffffff';
        ctx.shadowBlur = 20;

        ctx.beginPath();
        ctx.moveTo(x, y);

        // Jagged path down
        while (y < CANVAS_HEIGHT * 0.7) {
            x += (Math.random() - 0.5) * 60;
            y += Math.random() * 40 + 20;
            ctx.lineTo(x, y);

            // Branch occasionally
            if (Math.random() < 0.3) {
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(x, y);
                const branchX = x + (Math.random() - 0.5) * 80;
                const branchY = y + Math.random() * 50 + 20;
                ctx.lineTo(branchX, branchY);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(x, y);
            }
        }
        ctx.stroke();
        ctx.shadowBlur = 0;
    }

    /**
     * Draw snow particles
     */
    drawSnow(ctx, count) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';

        for (let i = 0; i < count; i++) {
            const p = this.weatherParticles[i];

            // Update position - snow drifts and falls slowly
            p.y += p.speed * 1.5;
            p.x += Math.sin(this.time * 2 + p.wobble) * 0.5;

            // Reset if off screen
            if (p.y > CANVAS_HEIGHT) {
                p.y = -5;
                p.x = Math.random() * CANVAS_WIDTH;
            }

            // Draw snowflake
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    /**
     * Draw fog overlay
     */
    drawFog(ctx, intensity) {
        // Multiple fog layers for depth
        const layers = [
            { y: CANVAS_HEIGHT * 0.3, alpha: 0.15 * intensity },
            { y: CANVAS_HEIGHT * 0.5, alpha: 0.25 * intensity },
            { y: CANVAS_HEIGHT * 0.7, alpha: 0.35 * intensity },
        ];

        for (const layer of layers) {
            const gradient = ctx.createLinearGradient(0, layer.y - 100, 0, layer.y + 100);
            gradient.addColorStop(0, `rgba(180, 180, 200, 0)`);
            gradient.addColorStop(0.5, `rgba(180, 180, 200, ${layer.alpha})`);
            gradient.addColorStop(1, `rgba(180, 180, 200, 0)`);

            ctx.fillStyle = gradient;
            ctx.fillRect(0, layer.y - 100, CANVAS_WIDTH, 200);
        }

        // Drifting fog wisps
        const wispCount = Math.floor(5 * intensity);
        ctx.fillStyle = `rgba(200, 200, 220, ${0.1 * intensity})`;

        for (let i = 0; i < wispCount; i++) {
            const x = (this.time * 20 + i * 200) % (CANVAS_WIDTH + 200) - 100;
            const y = CANVAS_HEIGHT * 0.4 + Math.sin(this.time + i) * 50 + i * 40;

            ctx.beginPath();
            ctx.ellipse(x, y, 100 + i * 20, 30 + i * 5, 0, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    /**
     * Draw all zones
     */
    drawZones(activeZone = null, hoveredZone = null, selectedZone = null) {
        for (const [name, zone] of Object.entries(ZONES)) {
            const isActive = name === activeZone;
            const isHovered = name === hoveredZone;
            const isSelected = name === selectedZone;
            this.drawZone(name, zone, isActive, isHovered, isSelected);
        }
    }

    /**
     * Draw a single zone with enhanced visuals
     */
    drawZone(name, zone, isActive = false, isHovered = false, isSelected = false) {
        const ctx = this.ctx;
        const halfW = zone.width / 2;
        const halfH = zone.height / 2;

        ctx.save();

        // Determine visual state
        const isHighlighted = isActive || isHovered || isSelected;

        // Active zone pulse effect
        let pulseSize = 0;
        if (isActive) {
            pulseSize = Math.sin(this.time * 4) * 3;
            ctx.shadowColor = zone.color;
            ctx.shadowBlur = 25 + Math.sin(this.time * 4) * 10;
        } else if (isSelected) {
            // Selected zone: steady glow
            ctx.shadowColor = zone.color;
            ctx.shadowBlur = 15;
        } else if (isHovered) {
            // Hovered zone: subtle glow
            ctx.shadowColor = zone.color;
            ctx.shadowBlur = 10;
        }

        // Zone background with gradient
        const gradient = ctx.createRadialGradient(
            zone.x, zone.y, 0,
            zone.x, zone.y, Math.max(zone.width, zone.height) * 0.7
        );

        // Adjust alpha based on state and time of day
        let baseAlpha = 0x55;
        if (isActive) baseAlpha = 0xaa;
        else if (isSelected) baseAlpha = 0x88;
        else if (isHovered) baseAlpha = 0x77;

        // Apply brightness from time of day
        const brightness = this.currentBrightness || 1.0;
        const adjustedAlpha = Math.round(baseAlpha * (0.5 + brightness * 0.5));
        const alpha = adjustedAlpha.toString(16).padStart(2, '0');
        const alphaLow = Math.round(0x22 * brightness).toString(16).padStart(2, '0');

        gradient.addColorStop(0, zone.color + alpha);
        gradient.addColorStop(1, zone.color + alphaLow);

        ctx.fillStyle = gradient;
        ctx.strokeStyle = zone.color;
        ctx.lineWidth = isActive ? 3 : (isHighlighted ? 2.5 : 2);

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

        ctx.fillStyle = isHighlighted ? '#ffffff' : '#aaaaaa';
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

    /**
     * Draw time and weather indicator
     */
    drawTimeIndicator() {
        const ctx = this.ctx;
        const hour = this.getCurrentHour();

        ctx.save();

        // Position top-right
        const x = CANVAS_WIDTH - 75;
        const y = 15;

        // Background panel (taller to fit weather)
        ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        ctx.beginPath();
        ctx.roundRect(x - 5, y - 5, 70, this.weather !== 'clear' ? 45 : 25, 5);
        ctx.fill();

        // Time icon based on period
        let timeIcon;
        if (hour >= 21 || hour < 5) timeIcon = '🌙';
        else if (hour >= 5 && hour < 7) timeIcon = '🌅';
        else if (hour >= 7 && hour < 10) timeIcon = '🌤️';
        else if (hour >= 10 && hour < 17) timeIcon = '☀️';
        else if (hour >= 17 && hour < 19) timeIcon = '🌇';
        else timeIcon = '🌆';

        ctx.font = '14px serif';
        ctx.textAlign = 'left';
        ctx.fillText(timeIcon, x, y + 12);

        // Time text
        const hours = Math.floor(hour);
        const mins = Math.floor((hour % 1) * 60);
        const timeStr = `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;

        ctx.fillStyle = '#cccccc';
        ctx.font = '12px monospace';
        ctx.fillText(timeStr, x + 22, y + 12);

        // Weather indicator (if not clear)
        if (this.weather !== 'clear') {
            const weatherIcons = {
                rain: '🌧️',
                storm: '⛈️',
                snow: '❄️',
                fog: '🌫️'
            };
            ctx.font = '12px serif';
            ctx.fillText(weatherIcons[this.weather] || '☁️', x, y + 32);

            ctx.fillStyle = '#888888';
            ctx.font = '10px monospace';
            ctx.fillText(this.weather.toUpperCase(), x + 18, y + 32);
        }

        ctx.restore();
    }

    /**
     * Set manual time (for testing or fast-forward)
     */
    setTime(hour) {
        this.useRealTime = false;
        this.manualHour = hour % 24;
    }

    /**
     * Resume real time
     */
    useRealTimeMode() {
        this.useRealTime = true;
    }

    /**
     * Fast forward time (for demos)
     */
    advanceTime(hours = 1) {
        if (!this.useRealTime) {
            this.manualHour = (this.manualHour + hours) % 24;
        }
    }
}
