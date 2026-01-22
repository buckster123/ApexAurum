/**
 * Agent Avatar - Enhanced with smooth easing and particle effects
 *
 * Represents an agent in the village with position, movement, and visual effects.
 */

// Easing functions
const Easing = {
    // Smooth deceleration
    easeOutCubic: (t) => 1 - Math.pow(1 - t, 3),
    // Smooth acceleration and deceleration
    easeInOutCubic: (t) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2,
    // Bouncy finish
    easeOutBack: (t) => {
        const c1 = 1.70158;
        const c3 = c1 + 1;
        return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
    },
    // Elastic bounce
    easeOutElastic: (t) => {
        if (t === 0 || t === 1) return t;
        return Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * (2 * Math.PI) / 3) + 1;
    }
};

// Particle class for visual effects
class Particle {
    constructor(x, y, color) {
        this.x = x;
        this.y = y;
        this.color = color;
        this.vx = (Math.random() - 0.5) * 4;
        this.vy = (Math.random() - 0.5) * 4;
        this.life = 1.0;
        this.decay = 0.02 + Math.random() * 0.02;
        this.size = 2 + Math.random() * 3;
    }

    update() {
        this.x += this.vx;
        this.y += this.vy;
        this.life -= this.decay;
        this.vx *= 0.98;
        this.vy *= 0.98;
    }

    draw(ctx) {
        if (this.life <= 0) return;
        ctx.save();
        ctx.globalAlpha = this.life * 0.8;
        ctx.fillStyle = this.color;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size * this.life, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }

    isDead() {
        return this.life <= 0;
    }
}

export class Agent {
    constructor(id, name, color = '#00ffaa') {
        this.id = id;
        this.name = name;
        this.color = color;
        this.radius = 22;

        // Position
        this.x = 400;
        this.y = 300;

        // Movement with easing
        this.startX = this.x;
        this.startY = this.y;
        this.targetX = this.x;
        this.targetY = this.y;
        this.moveProgress = 1;  // 0 to 1
        this.moveDuration = 60; // frames (1 second at 60fps)
        this.moveFrame = 0;

        // State
        this.state = 'idle';  // idle, moving, working, returning
        this.currentZone = 'village_square';
        this.currentTool = null;
        this.lastResult = null;

        // Animation
        this.pulsePhase = Math.random() * Math.PI * 2;
        this.rotationPhase = 0;
        this.breathPhase = Math.random() * Math.PI * 2;

        // Particles
        this.particles = [];
        this.particleTimer = 0;

        // Trail effect
        this.trail = [];
        this.maxTrailLength = 15;
    }

    /**
     * Move agent to a zone with smooth easing
     */
    moveTo(zoneName, zones) {
        const zone = zones[zoneName];
        if (!zone) {
            console.warn(`Unknown zone: ${zoneName}`);
            return;
        }

        // Store start position
        this.startX = this.x;
        this.startY = this.y;
        this.targetX = zone.x;
        this.targetY = zone.y;

        // Reset movement
        this.moveProgress = 0;
        this.moveFrame = 0;

        // Calculate duration based on distance
        const dx = this.targetX - this.startX;
        const dy = this.targetY - this.startY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        this.moveDuration = Math.max(30, Math.min(90, distance / 5));

        this.currentZone = zoneName;
        this.state = 'moving';
    }

    /**
     * Start working on a tool
     */
    startTool(toolName) {
        this.currentTool = toolName;
        this.state = 'working';
        // Burst of particles when starting work
        this.emitParticleBurst(20);
    }

    /**
     * Finish working
     */
    finishTool(result = null) {
        this.lastResult = result;
        this.currentTool = null;

        // Emit celebration particles
        this.emitParticleBurst(30);

        // Return to village square
        this.startX = this.x;
        this.startY = this.y;
        this.targetX = 400;
        this.targetY = 300;
        this.moveProgress = 0;
        this.moveFrame = 0;
        this.moveDuration = 45;
        this.currentZone = 'village_square';
        this.state = 'returning';
    }

    /**
     * Emit a burst of particles
     */
    emitParticleBurst(count) {
        for (let i = 0; i < count; i++) {
            this.particles.push(new Particle(this.x, this.y, this.color));
        }
    }

    /**
     * Update position and effects (call each frame)
     */
    update() {
        // Update movement with easing
        if (this.moveProgress < 1) {
            this.moveFrame++;
            this.moveProgress = Math.min(1, this.moveFrame / this.moveDuration);

            // Apply easing
            const easedProgress = Easing.easeOutCubic(this.moveProgress);

            this.x = this.startX + (this.targetX - this.startX) * easedProgress;
            this.y = this.startY + (this.targetY - this.startY) * easedProgress;

            // Add to trail while moving
            if (this.moveFrame % 3 === 0) {
                this.trail.push({ x: this.x, y: this.y, alpha: 1 });
                if (this.trail.length > this.maxTrailLength) {
                    this.trail.shift();
                }
            }
        } else {
            // Arrived
            this.x = this.targetX;
            this.y = this.targetY;
            if (this.state === 'moving') {
                this.state = 'working';
            } else if (this.state === 'returning') {
                this.state = 'idle';
            }
        }

        // Update animation phases
        this.pulsePhase += 0.08;
        this.rotationPhase += 0.03;
        this.breathPhase += 0.02;

        // Emit particles while working
        if (this.state === 'working') {
            this.particleTimer++;
            if (this.particleTimer % 5 === 0) {
                this.particles.push(new Particle(
                    this.x + (Math.random() - 0.5) * 30,
                    this.y + (Math.random() - 0.5) * 30,
                    this.color
                ));
            }
        }

        // Update particles
        this.particles.forEach(p => p.update());
        this.particles = this.particles.filter(p => !p.isDead());

        // Fade trail
        this.trail.forEach(t => t.alpha *= 0.92);
        this.trail = this.trail.filter(t => t.alpha > 0.05);
    }

    /**
     * Draw agent on canvas
     */
    draw(ctx) {
        ctx.save();

        // Draw trail
        this.trail.forEach((t, i) => {
            ctx.beginPath();
            ctx.arc(t.x, t.y, 4, 0, Math.PI * 2);
            ctx.fillStyle = this.color + Math.floor(t.alpha * 50).toString(16).padStart(2, '0');
            ctx.fill();
        });

        // Draw particles
        this.particles.forEach(p => p.draw(ctx));

        // Breathing effect
        const breathScale = 1 + Math.sin(this.breathPhase) * 0.03;

        // Pulse effect when working
        let radius = this.radius * breathScale;
        let glowIntensity = 0;

        if (this.state === 'working') {
            radius += Math.sin(this.pulsePhase) * 4;
            glowIntensity = 0.5 + Math.sin(this.pulsePhase) * 0.3;
        } else if (this.state === 'moving' || this.state === 'returning') {
            glowIntensity = 0.3;
        }

        // Outer glow
        if (glowIntensity > 0) {
            const gradient = ctx.createRadialGradient(
                this.x, this.y, radius,
                this.x, this.y, radius + 25
            );
            gradient.addColorStop(0, this.color + Math.floor(glowIntensity * 99).toString(16).padStart(2, '0'));
            gradient.addColorStop(1, this.color + '00');
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(this.x, this.y, radius + 25, 0, Math.PI * 2);
            ctx.fill();
        }

        // Rotating ring when working
        if (this.state === 'working') {
            ctx.save();
            ctx.translate(this.x, this.y);
            ctx.rotate(this.rotationPhase);
            ctx.strokeStyle = this.color + '66';
            ctx.lineWidth = 2;
            ctx.setLineDash([8, 8]);
            ctx.beginPath();
            ctx.arc(0, 0, radius + 12, 0, Math.PI * 2);
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.restore();
        }

        // Main circle with gradient
        const mainGradient = ctx.createRadialGradient(
            this.x - radius * 0.3, this.y - radius * 0.3, 0,
            this.x, this.y, radius
        );
        mainGradient.addColorStop(0, this.lightenColor(this.color, 40));
        mainGradient.addColorStop(0.7, this.color);
        mainGradient.addColorStop(1, this.darkenColor(this.color, 30));

        ctx.beginPath();
        ctx.arc(this.x, this.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = mainGradient;
        ctx.fill();

        // Border
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Inner highlight
        ctx.beginPath();
        ctx.arc(this.x - radius * 0.25, this.y - radius * 0.25, radius * 0.3, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.fill();

        // Name label with background
        ctx.font = 'bold 12px monospace';
        ctx.textAlign = 'center';
        const textWidth = ctx.measureText(this.name).width;

        // Label background
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.fillRect(this.x - textWidth/2 - 4, this.y + radius + 6, textWidth + 8, 16);

        // Label text
        ctx.fillStyle = '#ffffff';
        ctx.fillText(this.name, this.x, this.y + radius + 18);

        // Tool label when working
        if (this.currentTool) {
            ctx.font = '10px monospace';
            const toolWidth = ctx.measureText(this.currentTool).width;

            // Tool label background
            ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            ctx.fillRect(this.x - toolWidth/2 - 4, this.y - radius - 20, toolWidth + 8, 14);

            // Tool label text
            ctx.fillStyle = '#D4AF37';
            ctx.fillText(this.currentTool, this.x, this.y - radius - 9);
        }

        ctx.restore();
    }

    // Color utility functions
    lightenColor(color, percent) {
        const num = parseInt(color.replace('#', ''), 16);
        const amt = Math.round(2.55 * percent);
        const R = Math.min(255, (num >> 16) + amt);
        const G = Math.min(255, ((num >> 8) & 0x00FF) + amt);
        const B = Math.min(255, (num & 0x0000FF) + amt);
        return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
    }

    darkenColor(color, percent) {
        const num = parseInt(color.replace('#', ''), 16);
        const amt = Math.round(2.55 * percent);
        const R = Math.max(0, (num >> 16) - amt);
        const G = Math.max(0, ((num >> 8) & 0x00FF) - amt);
        const B = Math.max(0, (num & 0x0000FF) - amt);
        return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
    }
}

// Agent color presets - vibrant colors for each agent
export const AGENT_COLORS = {
    AZOTH: '#00ffaa',      // Emerald green - The First
    ELYSIAN: '#ff69b4',    // Pink - The Harmonist
    VAJRA: '#ffd700',      // Gold - The Diamond Cutter
    KETHER: '#9370db',     // Purple - The Crown
    CLAUDE: '#00aaff',     // Blue - Default
    SYSTEM: '#888888',     // Gray - System
    default: '#00aaff'
};
