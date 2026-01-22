/**
 * Village Sound Manager
 *
 * Web Audio API integration for Village GUI.
 * Handles sound loading, playback, volume control, and event mapping.
 *
 * Phase 5.1: Core sound system
 */

// Sound categories
const SOUND_CATEGORIES = {
    UI: 'ui',           // Tool feedback sounds
    AMBIENT: 'ambient', // Background loops
    WEATHER: 'weather', // Weather effects
    AGENT: 'agent'      // Agent actions
};

// Sound definitions - maps sound names to files
const SOUND_LIBRARY = {
    // UI Sounds
    'tool_success': { file: 'tool_chime.mp3', category: 'ui', volume: 0.7 },
    'tool_error': { file: 'tool_error.mp3', category: 'ui', volume: 0.6 },
    'tool_start': { file: 'tool_start.mp3', category: 'ui', volume: 0.4 },

    // Agent Sounds
    'thinking': { file: 'thinking.mp3', category: 'agent', volume: 0.3, loop: true },
    'footsteps': { file: 'footsteps.mp3', category: 'agent', volume: 0.4 },
    'success_fanfare': { file: 'success_fanfare.mp3', category: 'agent', volume: 0.6 },

    // Ambient Sounds
    'ambient_day': { file: 'ambient_day.mp3', category: 'ambient', volume: 0.2, loop: true },
    'ambient_night': { file: 'night_ambient.mp3', category: 'ambient', volume: 0.25, loop: true },
    'ambient_dawn': { file: 'dawn.mp3', category: 'ambient', volume: 0.3 },

    // Weather Sounds
    'rain': { file: 'rain.mp3', category: 'weather', volume: 0.4, loop: true },
    'thunder': { file: 'thunder.mp3', category: 'weather', volume: 0.7 },
    'wind': { file: 'wind_snow.mp3', category: 'weather', volume: 0.35, loop: true }
};

// Tool to sound mapping
const TOOL_SOUNDS = {
    // Success sounds by zone
    'dj_booth': 'tool_success',
    'memory_garden': 'tool_success',
    'workshop': 'tool_success',
    'file_shed': 'tool_success',
    'bridge_portal': 'tool_success',
    'campfire': 'tool_success',

    // Specific tool overrides
    'music_generate': 'success_fanfare',
    'agent_spawn': 'success_fanfare',
    'socratic_council': 'success_fanfare'
};


class SoundManager {
    constructor() {
        // Audio context (created on first user interaction)
        this.audioContext = null;
        this.initialized = false;

        // Loaded audio buffers
        this.buffers = new Map();

        // Currently playing sounds
        this.playing = new Map();

        // Volume controls (0-1)
        this.masterVolume = 0.7;
        this.categoryVolumes = {
            [SOUND_CATEGORIES.UI]: 1.0,
            [SOUND_CATEGORIES.AMBIENT]: 0.5,
            [SOUND_CATEGORIES.WEATHER]: 0.6,
            [SOUND_CATEGORIES.AGENT]: 0.8
        };

        // Mute state
        this.muted = false;

        // Sound base path
        this.basePath = '/static/village/sounds/';

        // Ambient state
        this.currentAmbient = null;
        this.currentWeather = null;

        // Load state from localStorage
        this.loadSettings();
    }

    /**
     * Initialize audio context (must be called from user gesture)
     */
    async init() {
        if (this.initialized) return true;

        try {
            // Create audio context
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();

            // Create master gain node
            this.masterGain = this.audioContext.createGain();
            this.masterGain.connect(this.audioContext.destination);
            this.masterGain.gain.value = this.muted ? 0 : this.masterVolume;

            // Create category gain nodes
            this.categoryGains = {};
            for (const [category, volume] of Object.entries(this.categoryVolumes)) {
                const gain = this.audioContext.createGain();
                gain.connect(this.masterGain);
                gain.gain.value = volume;
                this.categoryGains[category] = gain;
            }

            this.initialized = true;
            console.log('[SoundManager] Initialized');

            // Preload essential sounds
            await this.preloadEssential();

            return true;
        } catch (e) {
            console.error('[SoundManager] Failed to initialize:', e);
            return false;
        }
    }

    /**
     * Preload essential sounds (UI feedback)
     */
    async preloadEssential() {
        const essential = ['tool_success', 'tool_error', 'tool_start'];
        const promises = essential.map(name => this.loadSound(name));

        try {
            await Promise.all(promises);
            console.log('[SoundManager] Essential sounds loaded');
        } catch (e) {
            console.warn('[SoundManager] Some essential sounds failed to load:', e);
        }
    }

    /**
     * Load a sound into buffer
     */
    async loadSound(name) {
        if (this.buffers.has(name)) {
            return this.buffers.get(name);
        }

        const def = SOUND_LIBRARY[name];
        if (!def) {
            console.warn(`[SoundManager] Unknown sound: ${name}`);
            return null;
        }

        try {
            const response = await fetch(this.basePath + def.file);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const arrayBuffer = await response.arrayBuffer();
            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);

            this.buffers.set(name, audioBuffer);
            console.log(`[SoundManager] Loaded: ${name}`);

            return audioBuffer;
        } catch (e) {
            console.warn(`[SoundManager] Failed to load ${name}:`, e.message);
            return null;
        }
    }

    /**
     * Play a sound
     * @param {string} name - Sound name from SOUND_LIBRARY
     * @param {object} options - Override options (volume, loop)
     * @returns {string|null} - Play ID for stopping, or null if failed
     */
    play(name, options = {}) {
        if (!this.initialized || this.muted) return null;

        const def = SOUND_LIBRARY[name];
        if (!def) {
            console.warn(`[SoundManager] Unknown sound: ${name}`);
            return null;
        }

        const buffer = this.buffers.get(name);
        if (!buffer) {
            // Try to load and play async
            this.loadSound(name).then(buf => {
                if (buf) this.play(name, options);
            });
            return null;
        }

        try {
            // Create source
            const source = this.audioContext.createBufferSource();
            source.buffer = buffer;
            source.loop = options.loop ?? def.loop ?? false;

            // Create gain for this sound
            const gain = this.audioContext.createGain();
            gain.gain.value = options.volume ?? def.volume ?? 1.0;

            // Connect: source -> gain -> category gain -> master
            const categoryGain = this.categoryGains[def.category] || this.masterGain;
            source.connect(gain);
            gain.connect(categoryGain);

            // Generate play ID
            const playId = `${name}_${Date.now()}`;

            // Track playing sound
            this.playing.set(playId, { source, gain, name });

            // Clean up when done
            source.onended = () => {
                this.playing.delete(playId);
            };

            // Play
            source.start(0);

            return playId;
        } catch (e) {
            console.error(`[SoundManager] Error playing ${name}:`, e);
            return null;
        }
    }

    /**
     * Stop a playing sound
     */
    stop(playId) {
        const sound = this.playing.get(playId);
        if (sound) {
            try {
                sound.source.stop();
            } catch (e) {
                // Already stopped
            }
            this.playing.delete(playId);
        }
    }

    /**
     * Stop all sounds in a category
     */
    stopCategory(category) {
        for (const [playId, sound] of this.playing.entries()) {
            const def = SOUND_LIBRARY[sound.name];
            if (def && def.category === category) {
                this.stop(playId);
            }
        }
    }

    /**
     * Fade out a sound
     */
    fadeOut(playId, duration = 1.0) {
        const sound = this.playing.get(playId);
        if (sound) {
            const now = this.audioContext.currentTime;
            sound.gain.gain.setValueAtTime(sound.gain.gain.value, now);
            sound.gain.gain.linearRampToValueAtTime(0, now + duration);

            setTimeout(() => this.stop(playId), duration * 1000);
        }
    }

    /**
     * Set master volume
     */
    setMasterVolume(volume) {
        this.masterVolume = Math.max(0, Math.min(1, volume));
        if (this.masterGain && !this.muted) {
            this.masterGain.gain.value = this.masterVolume;
        }
        this.saveSettings();
    }

    /**
     * Set category volume
     */
    setCategoryVolume(category, volume) {
        this.categoryVolumes[category] = Math.max(0, Math.min(1, volume));
        if (this.categoryGains[category]) {
            this.categoryGains[category].gain.value = this.categoryVolumes[category];
        }
        this.saveSettings();
    }

    /**
     * Toggle mute
     */
    toggleMute() {
        this.muted = !this.muted;
        if (this.masterGain) {
            this.masterGain.gain.value = this.muted ? 0 : this.masterVolume;
        }
        this.saveSettings();
        return this.muted;
    }

    /**
     * Play sound for tool event
     */
    playToolSound(toolName, eventType, zone) {
        if (eventType === 'tool_start') {
            this.play('tool_start');
        } else if (eventType === 'tool_complete') {
            // Check for specific tool override
            const soundName = TOOL_SOUNDS[toolName] || TOOL_SOUNDS[zone] || 'tool_success';
            this.play(soundName);
        } else if (eventType === 'tool_error') {
            this.play('tool_error');
        }
    }

    /**
     * Set ambient sound based on time of day
     */
    setAmbient(timeOfDay) {
        // Fade out current ambient
        if (this.currentAmbient) {
            this.fadeOut(this.currentAmbient, 2.0);
        }

        // Select new ambient
        let ambientName;
        if (timeOfDay === 'night') {
            ambientName = 'ambient_night';
        } else if (timeOfDay === 'dawn' || timeOfDay === 'dusk') {
            ambientName = 'ambient_dawn';
        } else {
            ambientName = 'ambient_day';
        }

        // Play new ambient
        this.loadSound(ambientName).then(() => {
            this.currentAmbient = this.play(ambientName, { loop: true });
        });
    }

    /**
     * Set weather sound
     */
    setWeather(weather) {
        // Fade out current weather sound
        if (this.currentWeather) {
            this.fadeOut(this.currentWeather, 1.5);
            this.currentWeather = null;
        }

        // No sound for clear weather
        if (!weather || weather === 'clear') {
            return;
        }

        // Map weather to sound
        let soundName;
        if (weather === 'rain' || weather === 'storm') {
            soundName = 'rain';
        } else if (weather === 'snow') {
            soundName = 'wind';
        }

        if (soundName) {
            this.loadSound(soundName).then(() => {
                this.currentWeather = this.play(soundName, { loop: true });
            });
        }
    }

    /**
     * Play thunder (for storms)
     */
    playThunder() {
        this.loadSound('thunder').then(() => {
            // Random delay for realism
            setTimeout(() => {
                this.play('thunder');
            }, Math.random() * 500);
        });
    }

    /**
     * Play agent thinking sound
     */
    startThinking() {
        if (this.thinkingSound) return;

        this.loadSound('thinking').then(() => {
            this.thinkingSound = this.play('thinking', { loop: true });
        });
    }

    /**
     * Stop agent thinking sound
     */
    stopThinking() {
        if (this.thinkingSound) {
            this.fadeOut(this.thinkingSound, 0.5);
            this.thinkingSound = null;
        }
    }

    /**
     * Save settings to localStorage
     */
    saveSettings() {
        localStorage.setItem('village_sound_settings', JSON.stringify({
            masterVolume: this.masterVolume,
            categoryVolumes: this.categoryVolumes,
            muted: this.muted
        }));
    }

    /**
     * Load settings from localStorage
     */
    loadSettings() {
        try {
            const saved = localStorage.getItem('village_sound_settings');
            if (saved) {
                const settings = JSON.parse(saved);
                this.masterVolume = settings.masterVolume ?? 0.7;
                this.categoryVolumes = { ...this.categoryVolumes, ...settings.categoryVolumes };
                this.muted = settings.muted ?? false;
            }
        } catch (e) {
            console.warn('[SoundManager] Failed to load settings');
        }
    }

    /**
     * Get current status for UI
     */
    getStatus() {
        return {
            initialized: this.initialized,
            muted: this.muted,
            masterVolume: this.masterVolume,
            categoryVolumes: { ...this.categoryVolumes },
            playingCount: this.playing.size,
            loadedCount: this.buffers.size
        };
    }
}

// Export singleton
export const soundManager = new SoundManager();
export { SOUND_LIBRARY, SOUND_CATEGORIES, TOOL_SOUNDS };
