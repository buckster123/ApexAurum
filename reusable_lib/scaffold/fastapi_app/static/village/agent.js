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

        // Emotional state (Phase 4.4)
        this.mood = 'idle';  // idle, happy, stressed, thinking, energized
        this.moodIntensity = 0.5;  // 0-1
        this.successHistory = [];  // Recent success/failure records
        this.maxHistoryLength = 10;
        this.thoughtBubble = null;  // Current thought (emoji or text)
        this.thoughtTimer = 0;
        this.lastMoodChange = 0;

        // DJ Mode (Phase 6.4)
        this.djMode = false;
        this.djRecordAngle = 0;
        this.djRecordSpeed = 0;
        this.danceMode = false;
        this.danceTimer = 0;
        this.dancePhase = 0;
        this.musicalNotes = [];  // Floating music note particles
    }

    /**
     * Check if current tool is a DJ booth tool
     */
    isDJTool(toolName) {
        const djTools = [
            'music_generate', 'music_compose', 'midi_create', 'music_play',
            'suno_prompt_build', 'suno_prompt_preset_load',
            'audio_trim', 'audio_fade', 'audio_normalize', 'audio_loop'
        ];
        return djTools.includes(toolName);
    }

    /**
     * Start dance mode (called when music completes successfully)
     */
    startDancing(duration = 180) {
        this.danceMode = true;
        this.danceTimer = duration;
        this.dancePhase = 0;
        this.setMood('energized', 0.9);
        this.thoughtBubble = '🎵';
        this.thoughtTimer = duration;
        // Burst of musical notes
        this.emitMusicalNotes(15);
    }

    /**
     * Emit floating musical note particles
     */
    emitMusicalNotes(count) {
        const notes = ['🎵', '🎶', '♪', '♫', '🎼'];
        for (let i = 0; i < count; i++) {
            this.musicalNotes.push({
                x: this.x + (Math.random() - 0.5) * 40,
                y: this.y - 10,
                vx: (Math.random() - 0.5) * 2,
                vy: -1 - Math.random() * 2,
                note: notes[Math.floor(Math.random() * notes.length)],
                life: 1.0,
                decay: 0.01 + Math.random() * 0.01,
                size: 12 + Math.random() * 8,
                rotation: Math.random() * 0.5 - 0.25
            });
        }
    }

    /**
     * Record a task result for mood calculation
     */
    recordResult(success) {
        this.successHistory.push(success);
        if (this.successHistory.length > this.maxHistoryLength) {
            this.successHistory.shift();
        }
        this.updateMood();
    }

    /**
     * Update mood based on recent activity
     */
    updateMood() {
        const now = Date.now();

        // Calculate success rate
        if (this.successHistory.length === 0) {
            this.mood = 'idle';
            this.moodIntensity = 0.3;
            return;
        }

        const successCount = this.successHistory.filter(s => s).length;
        const successRate = successCount / this.successHistory.length;
        const activityLevel = this.successHistory.length / this.maxHistoryLength;

        // Determine mood
        if (this.state === 'working') {
            this.mood = 'thinking';
            this.moodIntensity = 0.7;
            this.thoughtBubble = '💭';
        } else if (successRate >= 0.8 && activityLevel > 0.5) {
            this.mood = 'energized';
            this.moodIntensity = 0.9;
            this.thoughtBubble = '⚡';
        } else if (successRate >= 0.6) {
            this.mood = 'happy';
            this.moodIntensity = 0.6 + successRate * 0.3;
            this.thoughtBubble = '😊';
        } else if (successRate < 0.4 && this.successHistory.length >= 3) {
            this.mood = 'stressed';
            this.moodIntensity = 0.8;
            this.thoughtBubble = '😰';
        } else {
            this.mood = 'idle';
            this.moodIntensity = 0.4;
            this.thoughtBubble = null;
        }

        this.lastMoodChange = now;
        this.thoughtTimer = 120;  // Show thought for 2 seconds
    }

    /**
     * Set mood directly (for external control)
     */
    setMood(mood, intensity = 0.7) {
        this.mood = mood;
        this.moodIntensity = intensity;

        const moodEmojis = {
            happy: '😊',
            stressed: '😰',
            thinking: '💭',
            idle: '😴',
            energized: '⚡'
        };
        this.thoughtBubble = moodEmojis[mood] || null;
        this.thoughtTimer = 120;
    }

    /**
     * Get mood color overlay
     */
    getMoodColor() {
        const moodColors = {
            happy: '#44ff88',      // Bright green
            stressed: '#ff6666',   // Red tint
            thinking: '#6699ff',   // Blue
            idle: '#888888',       // Gray
            energized: '#ffdd00'   // Bright yellow
        };
        return moodColors[this.mood] || this.color;
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

        // Check if DJ tool
        if (this.isDJTool(toolName)) {
            this.djMode = true;
            this.djRecordSpeed = 0.05;  // Start spinning
            this.emitMusicalNotes(5);
        } else {
            this.djMode = false;
        }

        // Burst of particles when starting work
        this.emitParticleBurst(20);
    }

    /**
     * Finish working
     */
    finishTool(result = null, success = true) {
        const wasDJ = this.djMode;
        const wasMusicGenerate = this.currentTool === 'music_generate' || this.currentTool === 'music_compose';

        this.lastResult = result;
        this.currentTool = null;

        // Record result for mood tracking
        this.recordResult(success);

        // DJ mode: dance on success, stop record on failure
        if (wasDJ) {
            if (success && wasMusicGenerate) {
                this.startDancing(180);  // Dance for 3 seconds
                this.djRecordSpeed = 0.1;  // Speed up record
            } else {
                this.djRecordSpeed = 0;  // Stop record
                this.djMode = false;
            }
        }

        // Emit particles - different colors based on success
        if (success) {
            this.emitParticleBurst(30);
        } else {
            // Red particles for errors
            for (let i = 0; i < 20; i++) {
                this.particles.push(new Particle(this.x, this.y, '#ff4444'));
            }
        }

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

        // Update thought bubble timer
        if (this.thoughtTimer > 0) {
            this.thoughtTimer--;
        }

        // Update mood when working
        if (this.state === 'working' && this.mood !== 'thinking') {
            this.setMood('thinking');
        }

        // DJ Mode updates
        if (this.djMode) {
            this.djRecordAngle += this.djRecordSpeed;
            // Emit musical notes periodically while DJing
            if (this.state === 'working' && Math.random() < 0.02) {
                this.emitMusicalNotes(1);
            }
        }

        // Dance mode updates
        if (this.danceMode) {
            this.dancePhase += 0.15;
            this.danceTimer--;
            if (this.danceTimer <= 0) {
                this.danceMode = false;
                this.djMode = false;
                this.djRecordSpeed = 0;
            }
            // Emit notes while dancing
            if (Math.random() < 0.05) {
                this.emitMusicalNotes(1);
            }
        }

        // Update musical notes
        this.musicalNotes.forEach(note => {
            note.x += note.vx;
            note.y += note.vy;
            note.vy += 0.02;  // Slight gravity
            note.life -= note.decay;
            note.vx *= 0.99;
        });
        this.musicalNotes = this.musicalNotes.filter(n => n.life > 0);
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

        // Draw musical notes
        this.musicalNotes.forEach(note => {
            ctx.save();
            ctx.globalAlpha = note.life;
            ctx.font = `${note.size}px serif`;
            ctx.textAlign = 'center';
            ctx.translate(note.x, note.y);
            ctx.rotate(note.rotation);
            ctx.fillText(note.note, 0, 0);
            ctx.restore();
        });

        // DJ Mode: Draw vinyl record behind agent
        if (this.djMode) {
            ctx.save();
            ctx.translate(drawX, drawY);
            ctx.rotate(this.djRecordAngle);

            // Vinyl record
            ctx.beginPath();
            ctx.arc(0, 0, this.radius + 15, 0, Math.PI * 2);
            ctx.fillStyle = '#1a1a1a';
            ctx.fill();

            // Record grooves (concentric circles)
            ctx.strokeStyle = '#333333';
            ctx.lineWidth = 1;
            for (let r = 8; r < this.radius + 12; r += 4) {
                ctx.beginPath();
                ctx.arc(0, 0, r, 0, Math.PI * 2);
                ctx.stroke();
            }

            // Center label
            ctx.beginPath();
            ctx.arc(0, 0, 8, 0, Math.PI * 2);
            ctx.fillStyle = '#cc66ff';  // Purple label
            ctx.fill();

            // Label detail
            ctx.beginPath();
            ctx.arc(0, 0, 3, 0, Math.PI * 2);
            ctx.fillStyle = '#ffffff';
            ctx.fill();

            ctx.restore();
        }

        // Dance mode: Apply body bounce and sway
        let danceOffsetY = 0;
        let danceOffsetX = 0;
        if (this.danceMode) {
            // Bounce up and down
            danceOffsetY = Math.sin(this.dancePhase) * 6;
            // Slight horizontal sway
            danceOffsetX = Math.sin(this.dancePhase * 0.5) * 4;
        }

        // Calculate final draw position
        const drawX = this.x + danceOffsetX;
        const drawY = this.y + danceOffsetY;

        // Breathing effect
        const breathScale = 1 + Math.sin(this.breathPhase) * 0.03;

        // Pulse effect based on mood
        let radius = this.radius * breathScale;
        let glowIntensity = 0;
        let glowColor = this.color;

        // Mood-based effects
        const moodColor = this.getMoodColor();

        if (this.state === 'working') {
            radius += Math.sin(this.pulsePhase) * 4;
            glowIntensity = 0.5 + Math.sin(this.pulsePhase) * 0.3;
            glowColor = '#6699ff';  // Blue thinking glow
        } else if (this.state === 'moving' || this.state === 'returning') {
            glowIntensity = 0.3;
        } else {
            // Mood-based glow when idle
            glowIntensity = this.moodIntensity * 0.4;
            glowColor = moodColor;

            // Stressed agents pulse faster
            if (this.mood === 'stressed') {
                radius += Math.sin(this.pulsePhase * 2) * 3;
                glowIntensity = 0.4 + Math.sin(this.pulsePhase * 2) * 0.3;
            }
            // Energized agents have brighter glow
            if (this.mood === 'energized') {
                glowIntensity = 0.6 + Math.sin(this.pulsePhase) * 0.2;
            }
        }

        // Outer glow (mood-colored)
        if (glowIntensity > 0) {
            const gradient = ctx.createRadialGradient(
                drawX, drawY, radius,
                drawX, drawY, radius + 25
            );
            gradient.addColorStop(0, glowColor + Math.floor(glowIntensity * 99).toString(16).padStart(2, '0'));
            gradient.addColorStop(1, glowColor + '00');
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(drawX, drawY, radius + 25, 0, Math.PI * 2);
            ctx.fill();
        }

        // Rotating ring when working (or DJ record spinning effect)
        if (this.state === 'working' && !this.djMode) {
            ctx.save();
            ctx.translate(drawX, drawY);
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
            drawX - radius * 0.3, drawY - radius * 0.3, 0,
            drawX, drawY, radius
        );
        mainGradient.addColorStop(0, this.lightenColor(this.color, 40));
        mainGradient.addColorStop(0.7, this.color);
        mainGradient.addColorStop(1, this.darkenColor(this.color, 30));

        ctx.beginPath();
        ctx.arc(drawX, drawY, radius, 0, Math.PI * 2);
        ctx.fillStyle = mainGradient;
        ctx.fill();

        // Border - extra glow when dancing
        if (this.danceMode) {
            ctx.strokeStyle = '#ffff00';  // Yellow glow
            ctx.lineWidth = 3;
            ctx.shadowColor = '#ffff00';
            ctx.shadowBlur = 10;
        } else {
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
        }
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Inner highlight
        ctx.beginPath();
        ctx.arc(drawX - radius * 0.25, drawY - radius * 0.25, radius * 0.3, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.fill();

        // Name label with background
        ctx.font = 'bold 12px monospace';
        ctx.textAlign = 'center';
        const textWidth = ctx.measureText(this.name).width;

        // Label background
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.fillRect(drawX - textWidth/2 - 4, drawY + radius + 6, textWidth + 8, 16);

        // Label text
        ctx.fillStyle = '#ffffff';
        ctx.fillText(this.name, drawX, drawY + radius + 18);

        // Tool label when working
        if (this.currentTool) {
            ctx.font = '10px monospace';
            const toolWidth = ctx.measureText(this.currentTool).width;

            // Tool label background
            ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            ctx.fillRect(drawX - toolWidth/2 - 4, drawY - radius - 20, toolWidth + 8, 14);

            // Tool label text
            ctx.fillStyle = '#D4AF37';
            ctx.fillText(this.currentTool, drawX, drawY - radius - 9);
        }

        // Thought bubble (mood indicator)
        if (this.thoughtBubble && this.thoughtTimer > 0) {
            const bubbleAlpha = Math.min(1, this.thoughtTimer / 30);  // Fade out
            const bobOffset = Math.sin(this.breathPhase * 2) * 3;

            // Bubble background
            ctx.save();
            ctx.globalAlpha = bubbleAlpha;

            const bubbleX = drawX + radius + 10;
            const bubbleY = drawY - radius - 10 + bobOffset;

            // Draw bubble shape
            ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
            ctx.beginPath();
            ctx.arc(bubbleX, bubbleY, 14, 0, Math.PI * 2);
            ctx.fill();

            // Small circles leading to agent
            ctx.beginPath();
            ctx.arc(bubbleX - 12, bubbleY + 8, 5, 0, Math.PI * 2);
            ctx.fill();
            ctx.beginPath();
            ctx.arc(bubbleX - 16, bubbleY + 14, 3, 0, Math.PI * 2);
            ctx.fill();

            // Emoji
            ctx.font = '14px serif';
            ctx.textAlign = 'center';
            ctx.fillStyle = '#000000';
            ctx.fillText(this.thoughtBubble, bubbleX, bubbleY + 5);

            ctx.restore();
        }

        // Mood indicator bar (small bar under name)
        if (this.mood !== 'idle' || this.moodIntensity > 0.5) {
            const barWidth = 30;
            const barHeight = 3;
            const barX = drawX - barWidth / 2;
            const barY = drawY + radius + 24;

            // Background
            ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
            ctx.fillRect(barX, barY, barWidth, barHeight);

            // Mood fill
            ctx.fillStyle = this.getMoodColor();
            ctx.fillRect(barX, barY, barWidth * this.moodIntensity, barHeight);
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
