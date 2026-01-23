"""
pages/music_visualizer.py
Advanced Visualizer Studio for Pi 5 - Phase 5.1 (Complete Waveform Polishing)
"""

import streamlit as st
import librosa
import soundfile as sf
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
from PIL import Image, ImageFilter, ImageEnhance
import subprocess
import os
from pathlib import Path
import gc
import time
import json
import warnings
from dataclasses import dataclass, field, fields
from typing import Optional, Callable, Dict, Any, Tuple, List
import sys
import logging
import io
import threading
from enum import Enum

# =============================================================================
# PATH INTEGRATION & LOGGER
# =============================================================================
# Resolve paths relative to this file's location or use ApexAurum sandbox
_THIS_DIR = Path(__file__).parent.resolve()
_PROJECT_ROOT = _THIS_DIR.parent.parent  # sandbox/music_viz -> sandbox -> ApexAurum

# Try to find sandbox in project structure, fallback to local
if (_PROJECT_ROOT / "sandbox").exists():
    SANDBOX_ROOT = _PROJECT_ROOT / "sandbox"
elif (_THIS_DIR.parent / "music").exists():
    SANDBOX_ROOT = _THIS_DIR.parent  # We're already in sandbox
else:
    SANDBOX_ROOT = Path(st.session_state.get("sandbox_dir", "./sandbox")).resolve()

MUSIC_ROOT = SANDBOX_ROOT / "music"
PRESETS_DIR = SANDBOX_ROOT / "visualizer_presets"  # Keep presets in sandbox root
PRESETS_DIR.mkdir(exist_ok=True)
MUSIC_ROOT.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')

DEBUG_MODE = False

# =============================================================================
# ENUMS & DATACLASSES
# =============================================================================

class ColorScheme(Enum):
    CYAN = "Cyan Plasma"
    FIRE = "Fire (Red/Orange)"
    NEON = "Neon (Green/Pink)"
    OCEAN = "Ocean (Blue/Cyan)"
    PSYCHEDELIC = "Psychedelic (Rainbow)"

class PositionOption(Enum):
    TOP = "Top Edge"
    BOTTOM = "Bottom Edge"
    LEFT = "Left Edge"
    RIGHT = "Right Edge"
    CENTER = "Center"

class AnchorOption(Enum):
    START = "Start (Near Edge)"
    CENTER = "Center"
    END = "End (Far Edge)"

class WaveformBandMode(Enum):
    SINGLE = "Single Band (Classic)"
    DUAL = "Dual Band (Bass/Treble)"
    TRIPLE = "Triple Band (Bass/Mid/Treble)"

class WaveformFreqPreset(Enum):
    CUSTOM = "Custom Manual"
    BASS_ONLY = "Bass Only (20-250Hz)"
    BASS_MID = "Bass & Mid (20-4000Hz)"
    FULL_RANGE = "Full Separation"

class WaveformRenderMode(Enum):
    OVERLAPPED = "Overlapped (Centered)"
    STACKED = "Stacked (Separated)"
    PARALLEL = "Parallel (Side-by-Side)"

@dataclass
class EffectSettings:
    # VERSION CONTROL - increment when adding fields
    config_version: int = 7
    
    # Particle system
    particle_count: int = 60
    particle_speed: float = 1.0
    particle_size_range: tuple = (1.0, 4.0)
    particle_color_scheme: ColorScheme = ColorScheme.CYAN
    
    # Spectrum bars
    bar_count: int = 48
    bar_width: float = 0.9
    bar_color_scheme: ColorScheme = ColorScheme.CYAN
    bar_smoothness: float = 0.7
    
    # Bar layout
    bar_position: PositionOption = PositionOption.BOTTOM
    bar_anchor: AnchorOption = AnchorOption.CENTER
    bar_thickness_pct: float = 15
    bar_length_pct: float = 80
    bar_offset_pct: float = 5
    
    # Bar enhancements
    bar_mirror: bool = False
    bar_gradient: bool = True
    
    # Multi-Band Waveform
    enable_waveform: bool = True
    waveform_band_mode: WaveformBandMode = WaveformBandMode.SINGLE
    waveform_thickness: float = 2.0
    waveform_position: PositionOption = PositionOption.TOP
    waveform_anchor: AnchorOption = AnchorOption.CENTER
    waveform_thickness_pct: float = 10
    waveform_length_pct: float = 80
    waveform_offset_pct: float = 5
    
    # NEW: Waveform amplitude & clipping controls
    waveform_amplitude: float = 1.0
    waveform_pad_pct: float = 10
    waveform_autogain: bool = True
    
    # NEW: Waveform dynamics
    waveform_speed: float = 1.0
    waveform_logfreq: bool = False
    waveform_oversample: int = 2
    
    # NEW: Frequency & rendering controls
    waveform_freq_preset: WaveformFreqPreset = WaveformFreqPreset.CUSTOM
    waveform_render_mode: WaveformRenderMode = WaveformRenderMode.OVERLAPPED
    waveform_band_freq_splits: List[int] = field(default_factory=lambda: [250, 4000])
    waveform_band_gain: List[float] = field(default_factory=lambda: [1.0, 0.8, 0.6])
    
    # Waveform colors (3 bands max)
    waveform_band_colors: List[str] = field(default_factory=lambda: ["#00FF88", "#FF8800", "#8800FF"])
    
    # Waveform enhancements
    waveform_fill: bool = False
    waveform_mirror: bool = False
    
    # Cover effects
    cover_pulse: bool = True
    cover_rotation: bool = False
    cover_rotation_speed: float = 0.5
    cover_zoom_on_beat: bool = True
    cover_zoom_intensity: float = 0.05
    
    # Background
    background_blur: int = 25
    background_brightness: float = 0.7
    
    # Beat effects
    beat_flash: bool = True
    beat_flash_intensity: float = 0.3
    beat_particle_burst: bool = True
    
    # Performance
    quality_preset: str = "medium"
    fps: int = 30
    width: int = 1280
    height: int = 720
    chunk_duration: int = 15
    bitrate: str = "6M"

@dataclass
class VisualizerConfig:
    effects: EffectSettings = field(default_factory=EffectSettings)
    
    def __post_init__(self):
        if self.effects.quality_preset == "low":
            self.effects.particle_count = 30
            self.effects.bar_count = 32
            self.effects.bitrate = "3M"
        elif self.effects.quality_preset == "high":
            self.effects.particle_count = 90
            self.effects.bar_count = 64
            self.effects.bitrate = "8M"

# =============================================================================
# CONFIG MIGRATION UTILITY
# =============================================================================
def migrate_config(old_config: Any) -> VisualizerConfig:
    """Migrate old configs to current schema"""
    new_config = VisualizerConfig()
    
    if isinstance(old_config, VisualizerConfig):
        # Copy over existing fields
        for field in fields(old_config.effects):
            if hasattr(old_config.effects, field.name):
                setattr(new_config.effects, field.name, getattr(old_config.effects, field.name))
        
        # Ensure new fields have defaults
        for field in fields(new_config.effects):
            if not hasattr(new_config.effects, field.name):
                setattr(new_config.effects, field.name, field.default)
    
    return new_config

# =============================================================================
# CORE SYSTEMS (Particles, Audio, Engine)
# =============================================================================

class ParticleSystem:
    def __init__(self, config: EffectSettings):
        self.config = config
        count = config.particle_count
        self.positions = np.random.rand(count, 2)
        self.velocities = np.random.randn(count, 2) * 0.002 * config.particle_speed
        self.lifetimes = np.random.rand(count)
        self.sizes = np.random.uniform(*config.particle_size_range, count)
        self.colors = self._generate_colors()
        
    def _generate_colors(self):
        if self.config.particle_color_scheme == ColorScheme.FIRE:
            return np.random.rand(self.config.particle_count, 3) * [1, 0.3, 0]
        elif self.config.particle_color_scheme == ColorScheme.NEON:
            return np.random.rand(self.config.particle_count, 3) * [0, 1, 0.5]
        elif self.config.particle_color_scheme == ColorScheme.OCEAN:
            return np.random.rand(self.config.particle_count, 3) * [0, 0.5, 1]
        else:
            return np.random.rand(self.config.particle_count, 3)
        
    def update(self, beat_strength: float, onset: float, burst: bool = False):
        center_force = (0.5 - self.positions) * beat_strength * 0.01
        self.velocities += center_force
        
        if burst:
            turbulence = np.random.randn(*self.velocities.shape) * 0.01
        else:
            turbulence = np.random.randn(*self.velocities.shape) * onset * 0.005
        self.velocities += turbulence
        
        self.velocities *= 0.98
        self.positions += self.velocities
        
        bounce_mask = (self.positions < 0) | (self.positions > 1)
        self.velocities[bounce_mask] *= -0.8
        self.positions = np.clip(self.positions, 0, 1)
        
        self.lifetimes -= 0.008
        respawn_mask = self.lifetimes <= 0
        self.lifetimes[respawn_mask] = 1.0
        self.positions[respawn_mask] = np.random.rand(np.sum(respawn_mask), 2)
        
    def get_draw_data(self):
        if len(self.positions) == 0:
            return np.array([[0.5, 0.5]]), np.array([1.0]), np.array([[1.0, 1.0, 1.0]]), np.array([0.5])
        alphas = self.lifetimes ** 0.5
        if hasattr(self.config, 'beat_flash_intensity'):
            alphas *= (1 + self.config.beat_flash_intensity)
        return self.positions, self.sizes, self.colors, alphas

class AudioAnalyzer:
    def __init__(self, audio_path: Path, sr: int = 22050, smooth_factor: float = 0.7):
        self.sr = sr
        self.smooth_factor = smooth_factor
        try:
            self.y, self.sr = librosa.load(audio_path, sr=sr, mono=True, duration=600)
        except Exception as e:
            st.error(f"Failed to load audio: {e}")
            raise
        
        self.duration = librosa.get_duration(y=self.y, sr=sr)
        if self.duration < 0.1:
            raise ValueError("Audio too short (< 0.1s)")
        
        self.onset_env = librosa.onset.onset_strength(y=self.y, sr=sr)
        self.rms = librosa.feature.rms(y=self.y)[0]
        self.tempo, self.beat_frames = librosa.beat.beat_track(y=self.y, sr=sr)
        
        if len(self.beat_frames) == 0:
            self.beat_frames = np.array([0, len(self.onset_env) // 2])
        
        # Store raw audio for waveform processing
        self.stft = np.abs(librosa.stft(self.y, n_fft=2048))
        self.times = librosa.times_like(self.stft, sr=sr)
        self.beat_interp = self._interpolate_beats()
        
        # Use raw audio for bandpass
        self.audio_raw = self.y
        self.audio_normalized = (self.audio_raw - np.mean(self.audio_raw)) / (np.std(self.audio_raw) + 1e-6)
        
    def _interpolate_beats(self):
        beat_env = np.zeros_like(self.onset_env)
        beat_env[self.beat_frames] = 1.0
        return np.convolve(beat_env, np.ones(10)/10, mode='same')
    
    def get_frame_features(self, time: float, config: EffectSettings):
        onset_idx = min(int(time * self.sr // 512), len(self.onset_env)-1)
        rms_idx = min(int(time * self.sr // 2048), len(self.rms)-1)
        
        return {
            'onset': self.onset_env[onset_idx],
            'rms': self.rms[rms_idx],
            'beat_strength': self.beat_interp[onset_idx],
            'spectrum': self._get_spectrum_at(time),
            'waveform': self._get_waveform_at(time, config.waveform_speed),
            'waveform_bands': self._get_waveform_bands_at(time, config)
        }
    
    def _get_spectrum_at(self, time: float):
        time_idx = min(int(time * self.sr // 512), self.stft.shape[1]-1)
        spectrum = self.stft[:, time_idx]
        bins = np.array_split(spectrum, 48)
        return np.array([np.mean(bin) for bin in bins])
    
    def _get_waveform_at(self, time: float, speed_factor: float = 1.0):
        """Get waveform with speed control"""
        sample_pos = int(time * self.sr)
        # Longer window for slower movement
        window = int(self.sr // (10 * max(speed_factor, 0.1)))  # Prevent division by zero
        start = max(0, sample_pos - window // 2)
        end = min(len(self.audio_normalized), start + window)
        waveform = self.audio_normalized[start:end]
        
        # Apply speed control via resampling
        if speed_factor != 1.0:
            target_len = int(len(waveform) * speed_factor)
            if target_len > 0:
                waveform = np.interp(
                    np.linspace(0, len(waveform)-1, target_len),
                    np.arange(len(waveform)),
                    waveform
                )
        
        return waveform
    
    def _get_waveform_bands_at(self, time: float, config: EffectSettings) -> Dict[str, np.ndarray]:
        """Extract multi-band waveforms based on config with presets"""
        sample_pos = int(time * self.sr)
        window = int(self.sr // 10)  # Constant window for consistency
        start = max(0, sample_pos - window // 2)
        end = min(len(self.audio_raw), start + window)
        audio_window = self.audio_raw[start:end]
        
        if len(audio_window) < 100:
            return {'bass': np.array([]), 'mid': np.array([]), 'treble': np.array([])}
        
        bands = {}
        mode = config.waveform_band_mode
        preset = config.waveform_freq_preset
        
        # Handle preset modes
        if preset == WaveformFreqPreset.BASS_ONLY:
            # Bass only
            bands['bass'] = self._filter_band(audio_window, 20, 250)
            bands['mid'] = np.zeros_like(audio_window) * 0.01  # Silent
            bands['treble'] = np.zeros_like(audio_window) * 0.01
        elif preset == WaveformFreqPreset.BASS_MID:
            # Bass + Mid only
            bands['bass'] = self._filter_band(audio_window, 20, 250)
            bands['mid'] = self._filter_band(audio_window, 250, 4000)
            bands['treble'] = np.zeros_like(audio_window) * 0.01
        else:
            # Full custom mode
            splits = config.waveform_band_freq_splits
            if mode == WaveformBandMode.DUAL:
                # Dual = Bass/Treble split at first split point
                bands['bass'] = self._filter_band(audio_window, 20, splits[0])
                bands['treble'] = self._filter_band(audio_window, splits[0], min(8000, self.sr // 2))
                bands['mid'] = np.zeros_like(audio_window) * 0.01
            else:
                # Triple = full separation
                bands['bass'] = self._filter_band(audio_window, 20, splits[0])
                bands['mid'] = self._filter_band(audio_window, splits[0], splits[1])
                bands['treble'] = self._filter_band(audio_window, splits[1], min(8000, self.sr // 2))
        
        # Apply per-band gain, normalize, and respect autogain
        band_names = ['bass', 'mid', 'treble']
        for i, band_name in enumerate([b for b in band_names if b in bands]):
            if band_name in bands and len(bands[band_name]) > 0:
                # Apply gain
                gain = config.waveform_band_gain[i] if i < len(config.waveform_band_gain) else 1.0
                bands[band_name] *= gain
                
                # Auto-gain if enabled
                if config.waveform_autogain:
                    max_val = np.max(np.abs(bands[band_name]))
                    if max_val > 0.1:
                        bands[band_name] = bands[band_name] * (0.8 / max_val)
                
                # Normalize
                if np.std(bands[band_name]) > 1e-6:
                    bands[band_name] = (bands[band_name] - np.mean(bands[band_name])) / (np.std(bands[band_name]) + 1e-6)
        
        return bands
    
    def _filter_band(self, audio: np.ndarray, low_freq: float, high_freq: float) -> np.ndarray:
        """Apply bandpass filter to extract frequency band"""
        nyquist = self.sr / 2
        low = low_freq / nyquist
        high = high_freq / nyquist
        
        # Use scipy butterworth filter
        from scipy import signal
        sos = signal.butter(4, [low, high], btype='band', output='sos')
        return signal.sosfilt(sos, audio)

class VisualizerEngine:
    def __init__(self, config: VisualizerConfig):
        self.config = config
        self.particles = ParticleSystem(config.effects)
        
    @staticmethod
    def _log_debug(msg: str):
        if DEBUG_MODE:
            st.sidebar.text(f"🔍 {msg}")
    
    def _is_vertical_orientation(self, position: PositionOption) -> bool:
        """Check if position requires vertical rendering"""
        return position in [PositionOption.LEFT, PositionOption.RIGHT]
    
    def _get_bar_color(self, index: int, total: int):
        """Generate bar color based on selected scheme"""
        scheme = self.config.effects.bar_color_scheme
        
        if scheme == ColorScheme.FIRE:
            return plt.cm.Reds(index / total * 0.5 + 0.3)
        elif scheme == ColorScheme.NEON:
            # Alternate green/pink for neon effect
            return (0, 1, 0, 0.6) if index % 2 == 0 else (1, 0, 0.5, 0.6)
        elif scheme == ColorScheme.OCEAN:
            return plt.cm.Blues(index / total * 0.5 + 0.5)
        elif scheme == ColorScheme.CYAN:
            return (0, 1, 0.8, 0.6)  # Cyan with alpha
        else:  # PSYCHEDELIC
            return plt.cm.hsv(index / total)
        
    def _calculate_smart_bounds(self, position: PositionOption, anchor: AnchorOption,
                               length_pct: float, thickness_pct: float, offset_pct: float,
                               is_vertical: bool) -> Tuple[float, float, float, float]:
        """Calculate bounds that swap dimensions for vertical orientation and respect anchor"""
        
        # Swap dimensions for vertical orientation
        if is_vertical:
            width = thickness_pct / 100.0
            height = length_pct / 100.0
        else:
            width = length_pct / 100.0
            height = thickness_pct / 100.0
            
        offset = offset_pct / 100.0
        
        # Calculate base position
        if position == PositionOption.TOP:
            left = (1 - width) / 2
            bottom = 1 - height - offset
        elif position == PositionOption.BOTTOM:
            left = (1 - width) / 2
            bottom = offset
        elif position == PositionOption.LEFT:
            left = offset
            bottom = (1 - height) / 2
        elif position == PositionOption.RIGHT:
            left = 1 - width - offset
            bottom = (1 - height) / 2
        elif position == PositionOption.CENTER:
            left = (1 - width) / 2
            bottom = (1 - height) / 2
        else:
            left = (1 - width) / 2
            bottom = offset
        
        # Apply anchor adjustments
        if anchor == AnchorOption.START:
            if position == PositionOption.TOP:
                bottom = 1 - height - offset  # Already at start
            elif position == PositionOption.BOTTOM:
                bottom = offset  # Already at start
            elif position == PositionOption.LEFT:
                left = offset  # Already at start
            elif position == PositionOption.RIGHT:
                left = 1 - width - offset  # Already at start
        elif anchor == AnchorOption.END:
            if position == PositionOption.TOP:
                bottom = 1 - offset  # Push to far edge
            elif position == PositionOption.BOTTOM:
                bottom = 1 - height - offset  # Push to far edge
            elif position == PositionOption.LEFT:
                left = 1 - width - offset  # Push to far edge
            elif position == PositionOption.RIGHT:
                left = offset  # Push to far edge
        
        return [left, bottom, width, height]
        
    def generate_video(self, audio_path: Path, cover_path: Path, 
                      output_path: Path, progress_callback: Optional[Callable] = None):
        self._log_debug("Starting video generation...")
        
        try:
            analyzer = AudioAnalyzer(audio_path, smooth_factor=self.config.effects.bar_smoothness)
        except Exception as e:
            st.error(f"Audio analysis failed: {e}")
            return False
            
        cover_bg, cover_fg = self._prepare_images(cover_path)
        total_frames = int(analyzer.duration * self.config.effects.fps)
        
        hw_encoder_available = self._check_hw_encoder_device()
        codec = 'h264_v4l2m2m' if hw_encoder_available else 'libx264'
        
        if not hw_encoder_available:
            st.warning("⚠️ Hardware encoder unavailable. Using CPU-based software encoding")
        
        cmd = [
            'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
            '-s', f'{self.config.effects.width}x{self.config.effects.height}', '-pix_fmt', 'rgb24',
            '-r', str(self.config.effects.fps), '-i', '-', '-i', str(audio_path),
            '-c:v', codec, '-c:a', 'aac', '-b:v', self.config.effects.bitrate,
            '-b:a', '192k', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
        ]
        
        if not hw_encoder_available:
            cmd.extend(['-preset', 'ultrafast'])
        
        cmd.append(str(output_path))
        
        fig, ax_dict = self._create_figure_template(cover_bg, cover_fg, analyzer)
        ffmpeg_proc = None
        
        try:
            ffmpeg_proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10**8)
            
            try:
                ret = ffmpeg_proc.wait(timeout=5)
                if ret is not None and ret != 0:
                    raise subprocess.CalledProcessError(ret, cmd)
            except subprocess.TimeoutExpired:
                pass
            
            chunk_frames = int(self.config.effects.chunk_duration * self.config.effects.fps)
            for chunk_start in range(0, total_frames, chunk_frames):
                self._process_chunk(chunk_start, chunk_frames, total_frames,
                                  analyzer, cover_fg, fig, ax_dict, ffmpeg_proc, progress_callback)
                gc.collect()
            
            try:
                ffmpeg_proc.stdin.close()
            except:
                pass
            
            ret = ffmpeg_proc.wait()
            
            if ret != 0:
                stderr_output = ffmpeg_proc.stderr.read().decode() if ffmpeg_proc.stderr else "No stderr"
                raise subprocess.CalledProcessError(ret, cmd, stderr_output)
            
            if not output_path.exists() or output_path.stat().st_size < 1024:
                raise ValueError(f"Incomplete output file: {output_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Generation failed: {e}", exc_info=True)
            return False
            
        finally:
            plt.close(fig)
            if ffmpeg_proc and ffmpeg_proc.poll() is None:
                ffmpeg_proc.kill()
    
    def _check_hw_encoder_device(self) -> bool:
        # Pi 5 uses software encoding for reliability
        return False
        
    def _prepare_images(self, cover_path: Path):
        self._log_debug(f"Processing cover: {cover_path.name}")
        try:
            cover = Image.open(cover_path).convert('RGB')
        except Exception as e:
            st.error(f"Cannot open cover image: {e}")
            raise
            
        if cover.width > 4000 or cover.height > 4000:
            cover = cover.resize((2000, 2000), Image.Resampling.LANCZOS)
            
        fg_max_w, fg_max_h = int(self.config.effects.width * 0.6), int(self.config.effects.height * 0.6)
        fg_ratio = min(fg_max_w / cover.width, fg_max_h / cover.height)
        fg_size = (int(cover.width * fg_ratio), int(cover.height * fg_ratio))
        cover_fg = cover.resize(fg_size, Image.Resampling.LANCZOS)
        
        bg_ratio = max(self.config.effects.width / cover.width, self.config.effects.height / cover.height)
        bg_size = (int(cover.width * bg_ratio), int(cover.height * cover.height // cover.width))
        cover_bg = cover.resize(bg_size, Image.Resampling.BILINEAR)
        cover_bg = cover_bg.filter(ImageFilter.GaussianBlur(radius=self.config.effects.background_blur))
        
        left = (cover_bg.width - self.config.effects.width) // 2
        top = (cover_bg.height - self.config.effects.height) // 2
        cover_bg = cover_bg.crop((left, top, left + self.config.effects.width, top + self.config.effects.height))
        return cover_bg, cover_fg
    
    def _create_figure_template(self, bg_img, fg_img, analyzer):
        fig = plt.figure(figsize=(self.config.effects.width/100, self.config.effects.height/100), dpi=100)
        fig.patch.set_facecolor('black')
        
        # Background
        ax_bg = fig.add_axes([0, 0, 1, 1])
        bg_display = ImageEnhance.Brightness(bg_img).enhance(self.config.effects.background_brightness)
        ax_bg.imshow(bg_display, aspect='auto')
        ax_bg.axis('off')
        
        # Cover (centered)
        fg_w, fg_h = fg_img.size
        ax_cover = fig.add_axes([
            0.5 - (fg_w/self.config.effects.width)/2,
            0.5 - (fg_h/self.config.effects.height)/2,
            fg_w/self.config.effects.width,
            fg_h/self.config.effects.height
        ])
        ax_cover_img = ax_cover.imshow(fg_img, aspect='auto')
        ax_cover.axis('off')
        
        # Dynamic Spectrum Bars positioning
        bar_is_vertical = self._is_vertical_orientation(self.config.effects.bar_position)
        bar_bounds = self._calculate_smart_bounds(
            self.config.effects.bar_position,
            self.config.effects.bar_anchor,
            self.config.effects.bar_length_pct,
            self.config.effects.bar_thickness_pct,
            self.config.effects.bar_offset_pct,
            bar_is_vertical
        )
        ax_bars = fig.add_axes(bar_bounds, facecolor='none')
        
        # Set orientation based on position
        if bar_is_vertical:
            ax_bars.set_xlim(0, 1)
            ax_bars.set_ylim(0, self.config.effects.bar_count)
        else:
            ax_bars.set_xlim(0, self.config.effects.bar_count)
            ax_bars.set_ylim(0, 1)
        ax_bars.axis('off')
        
        # Create bars with correct orientation
        bar_rects = []
        for i in range(self.config.effects.bar_count):
            if bar_is_vertical:
                # Vertical bars (portrait mode) - grow horizontally
                rect = Rectangle((0, i), 0, self.config.effects.bar_width, 
                                facecolor='cyan', alpha=0.6)
            else:
                # Horizontal bars (landscape mode) - grow vertically
                rect = Rectangle((i, 0), self.config.effects.bar_width, 0, 
                                facecolor='cyan', alpha=0.6)
            bar_rects.append(rect)
            ax_bars.add_patch(rect)
        
        # Multi-Band Waveform setup with padding
        waveform_lines = []
        ax_waveform = None
        
        if self.config.effects.enable_waveform:
            wf_is_vertical = self._is_vertical_orientation(self.config.effects.waveform_position)
            waveform_bounds = self._calculate_smart_bounds(
                self.config.effects.waveform_position,
                self.config.effects.waveform_anchor,
                self.config.effects.waveform_length_pct,
                self.config.effects.waveform_thickness_pct,
                self.config.effects.waveform_offset_pct,
                wf_is_vertical
            )
            ax_waveform = fig.add_axes(waveform_bounds, facecolor='none')
            
            # Set waveform orientation and add padding
            pad_pct = self.config.effects.waveform_pad_pct / 100.0
            if wf_is_vertical:
                ax_waveform.set_xlim(-1 - pad_pct, 1 + pad_pct)
                ax_waveform.set_ylim(0, 1)
            else:
                ax_waveform.set_xlim(0, 1)
                ax_waveform.set_ylim(-1 - pad_pct, 1 + pad_pct)
                
            ax_waveform.axis('off')
            
            # Create multiple lines for multi-band mode
            if self.config.effects.waveform_band_mode == WaveformBandMode.SINGLE:
                # Single line (classic mode)
                if self.config.effects.waveform_fill:
                    # Use Polygon patch for fill mode (supports set_xy)
                    poly = Polygon([[0, 0]], closed=True,
                                   facecolor=self.config.effects.waveform_band_colors[0],
                                   alpha=0.3, edgecolor=self.config.effects.waveform_band_colors[0],
                                   linewidth=0.5)
                    ax_waveform.add_patch(poly)
                    waveform_lines = [poly]
                else:
                    line, = ax_waveform.plot([], [], color=self.config.effects.waveform_band_colors[0],
                                            linewidth=self.config.effects.waveform_thickness)
                    waveform_lines = [line]
            else:
                # Multi-band mode - create lines for each band
                n_bands = 2 if self.config.effects.waveform_band_mode == WaveformBandMode.DUAL else 3
                colors = self.config.effects.waveform_band_colors[:n_bands]

                for i, color in enumerate(colors):
                    if self.config.effects.waveform_fill:
                        alpha = 0.4 - (i * 0.1)  # Slight transparency gradient
                        # Use Polygon patch for fill mode (supports set_xy)
                        poly = Polygon([[0, 0]], closed=True,
                                       facecolor=color, alpha=alpha,
                                       edgecolor=color, linewidth=0.5)
                        ax_waveform.add_patch(poly)
                        waveform_lines.append(poly)
                    else:
                        line, = ax_waveform.plot([], [], color=color,
                                                linewidth=self.config.effects.waveform_thickness)
                        waveform_lines.append(line)
        else:
            waveform_lines = []
        
        # Particles
        ax_particles = fig.add_axes([0, 0, 1, 1], facecolor='none')
        scatter = ax_particles.scatter([], [], s=[], c=[], cmap='plasma')
        ax_particles.set_xlim(0, 1)
        ax_particles.set_ylim(0, 1)
        ax_particles.axis('off')
        
        # Beat flash overlay
        ax_flash = fig.add_axes([0, 0, 1, 1], facecolor='none')
        flash_rect = Rectangle((0, 0), 1, 1, facecolor='white', alpha=0, transform=fig.transFigure)
        ax_flash.add_patch(flash_rect)
        ax_flash.axis('off')
        
        return fig, {
            'ax_cover_img': ax_cover_img,
            'bar_rects': bar_rects,
            'scatter': scatter,
            'flash_rect': flash_rect,
            'waveform_lines': waveform_lines,  # Changed to list
            'ax_waveform': ax_waveform,
            'ax_cover': ax_cover,
            'ax_bars': ax_bars,
        }
    
    def _process_chunk(self, chunk_start, chunk_frames, total_frames,
                      analyzer, cover_fg, fig, ax_dict, proc, callback):
        for frame_idx in range(chunk_start, min(chunk_start + chunk_frames, total_frames)):
            current_time = frame_idx / self.config.effects.fps
            features = analyzer.get_frame_features(current_time, self.config.effects)
            
            beat_burst = features['beat_strength'] > 0.8 and self.config.effects.beat_particle_burst
            self.particles.update(features['beat_strength'], features['onset'], burst=beat_burst)
            pos, sizes, colors, alphas = self.particles.get_draw_data()
            
            self._update_frame(fig, ax_dict, features, pos, sizes, colors, alphas, cover_fg, current_time)
            
            fig.canvas.draw()
            
            if hasattr(fig.canvas, 'buffer_rgba'):
                buf = fig.canvas.buffer_rgba()
                frame_data = np.frombuffer(buf, dtype='uint8').reshape((self.config.effects.height, self.config.effects.width, 4))
                frame_data = frame_data[:, :, :3]
            elif hasattr(fig.canvas, 'tostring_rgb'):
                frame_data = np.frombuffer(fig.canvas.tostring_rgb(), dtype='uint8')
                frame_data = frame_data.reshape((self.config.effects.height, self.config.effects.width, 3))
            else:
                raise RuntimeError("No compatible canvas buffer method found")
            
            try:
                proc.stdin.write(frame_data.tobytes())
            except BrokenPipeError:
                raise RuntimeError("FFmpeg encoder crashed during frame write")
            
            if callback and frame_idx % self.config.effects.fps == 0:
                callback(frame_idx / total_frames)
    
    def _update_frame(self, fig, ax_dict, features, pos, sizes, colors, alphas, cover_fg, current_time):
        spectrum = features['spectrum']
        spectrum_norm = np.log1p(spectrum) / np.log1p(spectrum.max() + 1e-6)
        
        # Apply mirroring if enabled
        if self.config.effects.bar_mirror and len(spectrum_norm) > 1:
            # Create symmetrical mirrored spectrum
            mirrored = np.concatenate([spectrum_norm[::-1], spectrum_norm])
            spectrum_norm = mirrored[:len(ax_dict['bar_rects'])]
        
        # Update bars with orientation awareness
        is_vertical = self._is_vertical_orientation(self.config.effects.bar_position)
        
        for i, rect in enumerate(ax_dict['bar_rects']):
            if i >= len(spectrum_norm):
                break
            amplitude = spectrum_norm[i]
            
            if is_vertical:
                # Vertical bars (grow horizontally from left)
                rect.set_width(amplitude)
                rect.set_height(self.config.effects.bar_width)
                rect.set_xy((0, i))
            else:
                # Horizontal bars (grow vertically from bottom)
                rect.set_height(amplitude)
                rect.set_width(self.config.effects.bar_width)
                rect.set_xy((i, 0))
            
            # Set color based on scheme
            rect.set_facecolor(self._get_bar_color(i, min(len(spectrum_norm), len(ax_dict['bar_rects']))))
        
        # Update multi-band waveform with all new features
        if self.config.effects.enable_waveform and ax_dict.get('ax_waveform'):
            wf_is_vertical = self._is_vertical_orientation(self.config.effects.waveform_position)
            waveform_bands = features.get('waveform_bands', {})
            
            if self.config.effects.waveform_band_mode == WaveformBandMode.SINGLE:
                # Single band mode (classic)
                waveform = features['waveform']
                if len(waveform) > 0:
                    # Apply amplitude scaling
                    waveform = waveform * self.config.effects.waveform_amplitude

                    # Auto-gain if enabled
                    if self.config.effects.waveform_autogain and len(waveform) > 0:
                        max_val = np.max(np.abs(waveform))
                        if max_val > 0.9:
                            waveform = waveform * (0.8 / max_val)

                    # Apply speed (already handled in get_waveform_at)

                    if self.config.effects.waveform_mirror:
                        waveform = np.concatenate([waveform, -waveform[::-1]])

                    if wf_is_vertical:
                        y_data = np.linspace(0, 1, len(waveform))
                        if self.config.effects.waveform_fill:
                            # Create closed polygon: waveform -> baseline -> back
                            x_verts = np.concatenate([waveform, np.zeros_like(waveform)[::-1]])
                            y_verts = np.concatenate([y_data, y_data[::-1]])
                            ax_dict['waveform_lines'][0].set_xy(np.column_stack([x_verts, y_verts]))
                        else:
                            ax_dict['waveform_lines'][0].set_data(waveform, y_data)
                    else:
                        x_data = np.linspace(0, 1, len(waveform))
                        if self.config.effects.waveform_fill:
                            # Create closed polygon: waveform -> baseline -> back
                            x_verts = np.concatenate([x_data, x_data[::-1]])
                            y_verts = np.concatenate([waveform, np.zeros_like(waveform)[::-1]])
                            ax_dict['waveform_lines'][0].set_xy(np.column_stack([x_verts, y_verts]))
                        else:
                            ax_dict['waveform_lines'][0].set_data(x_data, waveform)
            else:
                # Multi-band mode
                n_bands = len(ax_dict['waveform_lines'])
                band_names = ['bass', 'treble'] if n_bands == 2 else ['bass', 'mid', 'treble']
                wf_render_mode = self.config.effects.waveform_render_mode

                for i, (line, band_name) in enumerate(zip(ax_dict['waveform_lines'], band_names)):
                    if band_name in waveform_bands and len(waveform_bands[band_name]) > 0:
                        waveform = waveform_bands[band_name].copy()

                        # Apply amplitude scaling
                        waveform = waveform * self.config.effects.waveform_amplitude

                        if self.config.effects.waveform_mirror:
                            waveform = np.concatenate([waveform, -waveform[::-1]])

                        if wf_is_vertical:
                            y_data = np.linspace(0, 1, len(waveform))

                            # Apply rendering mode offsets
                            if wf_render_mode == WaveformRenderMode.STACKED:
                                offset = (i - (n_bands-1)/2) * 0.3
                                y_data = y_data + offset
                            elif wf_render_mode == WaveformRenderMode.PARALLEL:
                                offset = (i - (n_bands-1)/2) * 0.2
                                waveform = waveform + offset

                            if self.config.effects.waveform_fill:
                                # Create closed polygon: waveform -> baseline -> back
                                baseline = np.zeros_like(waveform) if wf_render_mode != WaveformRenderMode.PARALLEL else np.full_like(waveform, offset if 'offset' in dir() else 0)
                                x_verts = np.concatenate([waveform, baseline[::-1]])
                                y_verts = np.concatenate([y_data, y_data[::-1]])
                                line.set_xy(np.column_stack([x_verts, y_verts]))
                            else:
                                line.set_data(waveform, y_data)
                        else:
                            x_data = np.linspace(0, 1, len(waveform))

                            # Apply rendering mode offsets
                            wf_offset = 0
                            if wf_render_mode == WaveformRenderMode.STACKED:
                                wf_offset = (i - (n_bands-1)/2) * 0.5
                                waveform = waveform + wf_offset
                            elif wf_render_mode == WaveformRenderMode.PARALLEL:
                                # Side-by-side would require different handling
                                pass

                            if self.config.effects.waveform_fill:
                                # Create closed polygon: waveform -> baseline -> back
                                baseline = np.full_like(waveform, wf_offset)
                                x_verts = np.concatenate([x_data, x_data[::-1]])
                                y_verts = np.concatenate([waveform, baseline[::-1]])
                                line.set_xy(np.column_stack([x_verts, y_verts]))
                            else:
                                line.set_data(x_data, waveform)
        
        scatter = ax_dict['scatter']
        if len(pos) > 0:
            scatter.set_offsets(pos)
            scatter.set_sizes(sizes * (1 + features['beat_strength'] * 3))
            scatter.set_array(alphas)
        
        if self.config.effects.cover_pulse:
            scale = 1 + features['beat_strength'] * self.config.effects.cover_zoom_intensity
            ax_dict['ax_cover_img'].set_data(
                cover_fg.resize((int(cover_fg.width * scale), int(cover_fg.height * scale)), Image.Resampling.LANCZOS)
            )
        
        flash_intensity = features['beat_strength'] ** 2 * self.config.effects.beat_flash_intensity
        ax_dict['flash_rect'].set_alpha(flash_intensity)

# =============================================================================
# PRESET MANAGEMENT
# =============================================================================

def save_preset(name: str, config: EffectSettings):
    preset_path = PRESETS_DIR / f"{name}.json"
    with open(preset_path, 'w') as f:
        # Convert dataclass to dict, handling lists and enums
        config_dict = {}
        for field in fields(config):
            value = getattr(config, field.name)
            if isinstance(value, (ColorScheme, PositionOption, AnchorOption, 
                                WaveformBandMode, WaveformFreqPreset, WaveformRenderMode)):
                config_dict[field.name] = value.value
            elif isinstance(value, list):
                config_dict[field.name] = value
            elif isinstance(value, tuple):
                config_dict[field.name] = value
            else:
                config_dict[field.name] = value
        json.dump(config_dict, f, indent=2)
    st.success(f"✅ Preset '{name}' saved!")

def load_preset(name: str) -> EffectSettings:
    preset_path = PRESETS_DIR / f"{name}.json"
    if not preset_path.exists():
        return EffectSettings()
    
    with open(preset_path, 'r') as f:
        data = json.load(f)
    
    # Convert string enums back to objects
    enum_mappings = {
        'particle_color_scheme': ColorScheme,
        'bar_color_scheme': ColorScheme,
        'bar_position': PositionOption,
        'waveform_position': PositionOption,
        'bar_anchor': AnchorOption,
        'waveform_anchor': AnchorOption,
        'waveform_band_mode': WaveformBandMode,
        'waveform_freq_preset': WaveformFreqPreset,
        'waveform_render_mode': WaveformRenderMode
    }
    
    for key, enum_class in enum_mappings.items():
        if key in data and data[key]:
            data[key] = enum_class(data[key])
    
    return EffectSettings(**data)

def list_presets() -> list[str]:
    return [p.stem for p in PRESETS_DIR.glob("*.json")]

def apply_layout_preset(preset_name: str, config: EffectSettings):
    """Apply common layout patterns"""
    if preset_name == "Classic Bottom":
        config.bar_position = PositionOption.BOTTOM
        config.bar_length_pct = 80
        config.bar_thickness_pct = 15
        config.bar_offset_pct = 5
        config.waveform_position = PositionOption.TOP
        config.waveform_length_pct = 80
        config.waveform_thickness_pct = 10
    elif preset_name == "Side by Side":
        config.bar_position = PositionOption.LEFT
        config.bar_length_pct = 40
        config.bar_thickness_pct = 15
        config.bar_offset_pct = 10
        config.waveform_position = PositionOption.RIGHT
        config.waveform_length_pct = 40
        config.waveform_thickness_pct = 15
        config.waveform_offset_pct = 10
    elif preset_name == "Vertical Full":
        config.bar_position = PositionOption.LEFT
        config.bar_length_pct = 90
        config.bar_thickness_pct = 20
        config.bar_offset_pct = 3
        config.waveform_position = PositionOption.LEFT
        config.waveform_length_pct = 90
        config.waveform_thickness_pct = 8
        config.waveform_offset_pct = 3
    elif preset_name == "Minimal Center":
        config.bar_position = PositionOption.CENTER
        config.bar_length_pct = 60
        config.bar_thickness_pct = 10
        config.bar_offset_pct = 0
        config.waveform_position = PositionOption.CENTER
        config.waveform_length_pct = 60
        config.waveform_thickness_pct = 5
        config.waveform_offset_pct = 0

def apply_genre_preset(genre: str, config: EffectSettings):
    """Apply genre-optimized settings"""
    if genre == "Electronic":
        config.waveform_band_mode = WaveformBandMode.TRIPLE
        config.waveform_freq_preset = WaveformFreqPreset.FULL_RANGE
        config.waveform_band_colors = ["#FF0080", "#00FF00", "#00FFFF"]
        config.waveform_speed = 1.5
        config.particle_color_scheme = ColorScheme.NEON
        config.bar_color_scheme = ColorScheme.PSYCHEDELIC
        config.beat_flash_intensity = 0.4
    elif genre == "Acoustic":
        config.waveform_band_mode = WaveformBandMode.DUAL
        config.waveform_freq_preset = WaveformFreqPreset.BASS_MID
        config.waveform_band_colors = ["#8B4513", "#FFD700"]
        config.waveform_speed = 0.7
        config.particle_color_scheme = ColorScheme.FIRE
        config.bar_color_scheme = ColorScheme.FIRE
        config.beat_flash_intensity = 0.2
        config.bar_smoothness = 0.8
    elif genre == "Hip-Hop":
        config.waveform_band_mode = WaveformBandMode.DUAL
        config.waveform_freq_preset = WaveformFreqPreset.BASS_ONLY
        config.waveform_band_colors = ["#8B0000", "#FFFFFF"]
        config.waveform_band_gain = [1.2, 0.6]
        config.waveform_speed = 1.0
        config.particle_color_scheme = ColorScheme.NEON
        config.bar_color_scheme = ColorScheme.CYAN
        config.beat_flash_intensity = 0.5
    elif genre == "Ambient":
        config.waveform_band_mode = WaveformBandMode.TRIPLE
        config.waveform_freq_preset = WaveformFreqPreset.FULL_RANGE
        config.waveform_band_colors = ["#000080", "#00CED1", "#E0FFFF"]
        config.waveform_speed = 0.5
        config.waveform_thickness = 1.5
        config.particle_color_scheme = ColorScheme.OCEAN
        config.bar_color_scheme = ColorScheme.OCEAN
        config.beat_flash_intensity = 0.1
        config.particle_speed = 0.5

# =============================================================================
# POSITION PREVIEW RENDERER
# =============================================================================

def render_position_preview(config: EffectSettings, preview_placeholder):
    """Renders a live preview of element positioning with orientation indicators"""
    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
    fig.patch.set_facecolor('#1E1E1E')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_facecolor('#2D2D2D')
    
    # Draw screen border
    screen_rect = Rectangle((5, 5), 90, 90, linewidth=2, edgecolor='white', facecolor='none')
    ax.add_patch(screen_rect)
    
    # Draw bars with actual orientation
    bar_is_vertical = config.bar_position in [PositionOption.LEFT, PositionOption.RIGHT]
    bar_length = config.bar_length_pct
    bar_thickness = config.bar_thickness_pct
    
    if config.bar_position == PositionOption.TOP:
        bar_x = (100 - bar_length) / 2
        bar_y = 100 - bar_thickness - config.bar_offset_pct
    elif config.bar_position == PositionOption.BOTTOM:
        bar_x = (100 - bar_length) / 2
        bar_y = config.bar_offset_pct
    elif config.bar_position == PositionOption.LEFT:
        bar_x = config.bar_offset_pct
        bar_y = (100 - bar_length) / 2
    elif config.bar_position == PositionOption.RIGHT:
        bar_x = 100 - bar_thickness - config.bar_offset_pct
        bar_y = (100 - bar_length) / 2
    elif config.bar_position == PositionOption.CENTER:
        bar_x = (100 - bar_length) / 2
        bar_y = (100 - bar_thickness) / 2
    
    # Show actual bar visualization
    n_bars_preview = 8
    if bar_is_vertical:
        # Draw vertical bars (growing right)
        for i in range(n_bars_preview):
            x_pos = bar_x + i * (bar_thickness / n_bars_preview)
            height = (i / n_bars_preview) * bar_length  # Mock amplitude
            rect = Rectangle((x_pos, bar_y + (bar_length - height)/2), 
                           bar_thickness / n_bars_preview, height, 
                           facecolor='cyan', alpha=0.7, label='Spectrum Bars' if i == 0 else "")
            ax.add_patch(rect)
    else:
        # Draw horizontal bars (growing up)
        for i in range(n_bars_preview):
            y_pos = bar_y + i * (bar_thickness / n_bars_preview)
            width = (i / n_bars_preview) * bar_length  # Mock amplitude
            rect = Rectangle((bar_x + (bar_length - width)/2, y_pos), 
                           width, bar_thickness / n_bars_preview, 
                           facecolor='cyan', alpha=0.7, label='Spectrum Bars' if i == 0 else "")
            ax.add_patch(rect)
    
    # Draw multi-band waveform with orientation
    wf_is_vertical = config.waveform_position in [PositionOption.LEFT, PositionOption.RIGHT]
    wf_length = config.waveform_length_pct
    wf_thickness = config.waveform_thickness_pct
    
    if config.waveform_position == PositionOption.TOP:
        wf_x = (100 - wf_length) / 2
        wf_y = 100 - wf_thickness - config.waveform_offset_pct
    elif config.waveform_position == PositionOption.BOTTOM:
        wf_x = (100 - wf_length) / 2
        wf_y = config.waveform_offset_pct
    elif config.waveform_position == PositionOption.LEFT:
        wf_x = config.waveform_offset_pct
        wf_y = (100 - wf_length) / 2
    elif config.waveform_position == PositionOption.RIGHT:
        wf_x = 100 - wf_thickness - config.waveform_offset_pct
        wf_y = (100 - wf_length) / 2
    elif config.waveform_position == PositionOption.CENTER:
        wf_x = (100 - wf_length) / 2
        wf_y = (100 - wf_thickness) / 2
    
    if config.enable_waveform:
        if wf_is_vertical:
            # Vertical waveform line(s)
            if config.waveform_band_mode == WaveformBandMode.SINGLE:
                ax.plot([wf_x + wf_thickness/2] * 2, [wf_y, wf_y + wf_length], 
                       color=config.waveform_band_colors[0], linewidth=3, label='Waveform')
            else:
                # Multi-band vertical
                n_bands = 2 if config.waveform_band_mode == WaveformBandMode.DUAL else 3
                for i in range(n_bands):
                    x_pos = wf_x + (i + 0.5) * (wf_thickness / n_bands)
                    ax.plot([x_pos] * 2, [wf_y, wf_y + wf_length], 
                           color=config.waveform_band_colors[i], linewidth=2, 
                           label=f'Band {i+1}' if i == 0 else "")
        else:
            # Horizontal waveform line(s)
            if config.waveform_band_mode == WaveformBandMode.SINGLE:
                ax.plot([wf_x, wf_x + wf_length], [wf_y + wf_thickness/2] * 2, 
                       color=config.waveform_band_colors[0], linewidth=3, label='Waveform')
            else:
                # Multi-band horizontal - stacked preview
                n_bands = 2 if config.waveform_band_mode == WaveformBandMode.DUAL else 3
                band_height = wf_thickness / n_bands
                for i in range(n_bands):
                    y_pos = wf_y + i * band_height + band_height/2
                    ax.plot([wf_x, wf_x + wf_length], [y_pos] * 2, 
                           color=config.waveform_band_colors[i], linewidth=2,
                           label=f'Band {i+1}' if i == 0 else "")
    
    # Add orientation indicator
    band_text = f" | {config.waveform_band_mode.value}" if config.enable_waveform else ""
    orientation_text = f"Bars: {'Vertical' if bar_is_vertical else 'Horizontal'} | Wave: {'Vertical' if wf_is_vertical else 'Horizontal'}{band_text}"
    ax.text(50, 95, orientation_text, ha='center', va='top', color='yellow', fontsize=8, 
           bbox=dict(boxstyle="round,pad=0.3", facecolor='#2D2D2D', edgecolor='yellow'))
    
    # Add labels and legend
    ax.text(50, 2, "🎨 Live Preview", ha='center', va='bottom', color='white', fontsize=10, weight='bold')
    ax.legend(loc='upper right', fontsize=8, facecolor='#2D2D2D', edgecolor='white')
    ax.axis('off')
    
    # Render to placeholder
    preview_placeholder.pyplot(fig)
    plt.close(fig)

# =============================================================================
# STREAMLIT UI - Multi-Tab Professional Interface
# =============================================================================

def music_visualizer_page():
    st.title("🎵 Music Visualizer Studio Pro")
    st.caption("Advanced hardware-accelerated music video generator")
    
    # INITIALIZE OR MIGRATE CONFIG
    if "viz_config" not in st.session_state:
        st.session_state.viz_config = VisualizerConfig()
    else:
        # Check if config needs migration
        current_effects = st.session_state.viz_config.effects
        if not hasattr(current_effects, 'config_version') or current_effects.config_version < 7:
            st.session_state.viz_config = migrate_config(st.session_state.viz_config)
            st.info("✅ Configuration migrated to new version with complete waveform controls!")
    # Load layout preset if requested
    if "layout_preset" in st.session_state:
        apply_layout_preset(st.session_state.layout_preset, st.session_state.viz_config.effects)
        del st.session_state.layout_preset
        st.rerun()
    
    with st.sidebar:
        st.header("📐 Quick Layouts")
        
        layout_presets = {
            "Classic Bottom": "Traditional horizontal bars at bottom",
            "Side by Side": "Vertical bars left, waveform right",
            "Vertical Full": "Full-height vertical bars left edge",
            "Minimal Center": "Centered, subtle elements"
        }
        
        selected_layout = st.selectbox("Apply Layout", [""] + list(layout_presets.keys()), 
                                      format_func=lambda x: x if x else "Select a preset...")
        if selected_layout:
            if st.button(f"Apply '{selected_layout}'"):
                st.session_state.layout_preset = selected_layout
                st.rerun()
        
        st.divider()
        
        st.header("🎵 Genre Presets")
        
        genre_presets = {
            "Electronic": "Bright, fast, punchy",
            "Acoustic": "Warm, natural, subtle",
            "Hip-Hop": "Heavy bass, crisp highs",
            "Ambient": "Slow, smooth, atmospheric"
        }
        
        selected_genre = st.selectbox("Apply Genre", [""] + list(genre_presets.keys()),
                                     format_func=lambda x: x if x else "Select genre...")
        if selected_genre:
            if st.button(f"Apply {selected_genre}"):
                apply_genre_preset(selected_genre, st.session_state.viz_config.effects)
                st.success(f"✅ Applied {selected_genre} preset!")
                st.rerun()
        
        st.divider()
        
        st.header("Quick Actions")
        if st.button("🎬 Quick Render (Low/30fps)"):
            st.session_state.viz_config.effects.quality_preset = "low"
            st.session_state.viz_config.effects.fps = 30
            st.success("Quick render settings applied!")
        
        if st.button("✨ High Quality (Medium/60fps)"):
            st.session_state.viz_config.effects.quality_preset = "high"
            st.session_state.viz_config.effects.fps = 60
            st.success("High quality settings applied!")
        
        st.divider()
        
        if DEBUG_MODE:
            st.subheader("Performance")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Particles", st.session_state.viz_config.effects.particle_count)
            with col2:
                st.metric("Bars", st.session_state.viz_config.effects.bar_count)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📁 Files", "🎨 Visual Design", "⚙️ Performance", "▶️ Generate"])
    
    with tab1:
        st.header("File Selection")
        
        try:
            audio_files = list(MUSIC_ROOT.rglob("*.mp3")) + list(MUSIC_ROOT.rglob("*.wav"))
        except:
            audio_files = []
            
        if not audio_files:
            st.error(f"No audio files in `{MUSIC_ROOT.relative_to(SANDBOX_ROOT)}`")
            return
        
        selected_audio = st.selectbox(
            "Select Audio",
            options=audio_files,
            format_func=lambda p: str(p.relative_to(MUSIC_ROOT))
        )
        
        cover_path = None
        for ext in ['.jpg', '.png', '.jpeg']:
            candidate = selected_audio.with_suffix(ext)
            if candidate.exists():
                cover_path = candidate
                break
        
        if cover_path:
            st.success(f"Found cover: {cover_path.name}")
            st.image(str(cover_path), width=300)
        else:
            st.warning("No cover image found")
    
    with tab2:
        st.header("🎨 Visual Design")
        
        st.info("🎯 **Tip:** The live preview below shows exactly how elements will appear. **Orange = growing direction**")
        
        preview_placeholder = st.empty()
        
        # ==================== SPECTRUM BARS SECTION ====================
        st.subheader("📊 Spectrum Bars", divider="blue")
        
        bar_col1, bar_col2 = st.columns(2)
        
        with bar_col1:
            st.markdown("#### 📍 Position & Size")
            
            # Position with visual diagram
            pos_options = [p.value for p in PositionOption]
            current_pos_idx = pos_options.index(st.session_state.viz_config.effects.bar_position.value)
            
            st.session_state.viz_config.effects.bar_position = PositionOption(
                st.selectbox(
                    "Edge Position",
                    options=pos_options,
                    index=current_pos_idx,
                    key="bar_pos_select",
                    help="Which screen edge to attach to. LEFT/RIGHT = vertical bars, TOP/BOTTOM = horizontal"
                )
            )
            
            # Anchor control
            anchor_options = [a.value for a in AnchorOption]
            current_anchor_idx = anchor_options.index(st.session_state.viz_config.effects.bar_anchor.value)
            st.session_state.viz_config.effects.bar_anchor = AnchorOption(
                st.selectbox(
                    "Alignment",
                    options=anchor_options,
                    index=current_anchor_idx,
                    key="bar_anchor_select",
                    help="How element aligns within its container"
                )
            )
            
            # Swap labels based on orientation
            bar_is_vertical = st.session_state.viz_config.effects.bar_position in [PositionOption.LEFT, PositionOption.RIGHT]
            
            st.session_state.viz_config.effects.bar_length_pct = st.slider(
                f"Length ({'Vertical' if bar_is_vertical else 'Horizontal'} Span)",
                min_value=20, max_value=100, 
                value=st.session_state.viz_config.effects.bar_length_pct,
                help="How far the bars stretch along the screen"
            )
            
            st.session_state.viz_config.effects.bar_thickness_pct = st.slider(
                f"Thickness ({'Horizontal' if bar_is_vertical else 'Vertical'} Size)",
                min_value=5, max_value=40, 
                value=st.session_state.viz_config.effects.bar_thickness_pct,
                help="How thick the bar area is"
            )
            
            st.session_state.viz_config.effects.bar_offset_pct = st.slider(
                "Distance from Edge", 0, 20, st.session_state.viz_config.effects.bar_offset_pct,
                help="Space between element and screen edge"
            )
        
        with bar_col2:
            st.markdown("#### 🎨 Style & Effects")
            
            st.session_state.viz_config.effects.bar_count = st.slider(
                "Bar Count", 16, 128, st.session_state.viz_config.effects.bar_count,
                help="Number of frequency bands"
            )
            
            st.session_state.viz_config.effects.bar_width = st.slider(
                "Bar Separation", 0.5, 1.5, st.session_state.viz_config.effects.bar_width, step=0.1,
                help="How close bars are to each other (1.0 = touching)"
            )
            
            st.session_state.viz_config.effects.bar_smoothness = st.slider(
                "Smoothness", 0.0, 1.0, st.session_state.viz_config.effects.bar_smoothness,
                help="How much to smooth audio spikes"
            )
            
            current_bar_color = st.session_state.viz_config.effects.bar_color_scheme.value
            bar_color_options = [e.value for e in ColorScheme]
            selected_bar_color = st.selectbox(
                "Color Scheme", bar_color_options,
                index=bar_color_options.index(current_bar_color),
                key="bar_color_select"
            )
            st.session_state.viz_config.effects.bar_color_scheme = ColorScheme(selected_bar_color)
            
            col_mirror, col_gradient = st.columns(2)
            with col_mirror:
                st.session_state.viz_config.effects.bar_mirror = st.checkbox(
                    "Mirror Effect", st.session_state.viz_config.effects.bar_mirror,
                    help="Creates symmetrical copy (best with CENTER position)"
                )
            with col_gradient:
                st.session_state.viz_config.effects.bar_gradient = st.checkbox(
                    "Gradient Fill", st.session_state.viz_config.effects.bar_gradient,
                    help="Gradient from dark to bright"
                )
        
        # ==================== MULTI-BAND WAVEFORM SECTION ====================
        st.subheader("〰️ Multi-Band Waveform", divider="green")
        
        wf_col1, wf_col2 = st.columns(2)
        
        with wf_col1:
            st.markdown("#### 📍 Position & Size")
            
            wf_pos_options = [p.value for p in PositionOption]
            current_wf_pos_idx = wf_pos_options.index(st.session_state.viz_config.effects.waveform_position.value)
            
            st.session_state.viz_config.effects.waveform_position = PositionOption(
                st.selectbox(
                    "Edge Position",
                    options=wf_pos_options,
                    index=current_wf_pos_idx,
                    key="wf_pos_select",
                    help="Which screen edge to attach to. LEFT/RIGHT = sideways waveform"
                )
            )
            
            wf_anchor_options = [a.value for a in AnchorOption]
            current_wf_anchor_idx = wf_anchor_options.index(st.session_state.viz_config.effects.waveform_anchor.value)
            st.session_state.viz_config.effects.waveform_anchor = AnchorOption(
                st.selectbox(
                    "Alignment",
                    options=wf_anchor_options,
                    index=current_wf_anchor_idx,
                    key="wf_anchor_select",
                    help="How waveform aligns within its container"
                )
            )
            
            wf_is_vertical = st.session_state.viz_config.effects.waveform_position in [PositionOption.LEFT, PositionOption.RIGHT]
            
            st.session_state.viz_config.effects.waveform_length_pct = st.slider(
                f"Length ({'Vertical' if wf_is_vertical else 'Horizontal'} Span)",
                min_value=20, max_value=100, 
                value=st.session_state.viz_config.effects.waveform_length_pct,
                help="How far the waveform stretches"
            )
            
            st.session_state.viz_config.effects.waveform_thickness_pct = st.slider(
                f"Thickness ({'Horizontal' if wf_is_vertical else 'Vertical'} Size)",
                min_value=5, max_value=30, 
                value=st.session_state.viz_config.effects.waveform_thickness_pct,
                help="Waveform display height"
            )
            
            st.session_state.viz_config.effects.waveform_offset_pct = st.slider(
                "Distance from Edge", 0, 20, st.session_state.viz_config.effects.waveform_offset_pct,
                help="Space from screen edge"
            )
        
        with wf_col2:
            st.markdown("#### 🎨 Multi-Band Mode")
            
            st.session_state.viz_config.effects.enable_waveform = st.checkbox(
                "Enable Waveform", st.session_state.viz_config.effects.enable_waveform,
                key="enable_wf"
            )
            
            if st.session_state.viz_config.effects.enable_waveform:
                # Multi-band mode selector
                band_options = [m.value for m in WaveformBandMode]
                current_band_idx = band_options.index(st.session_state.viz_config.effects.waveform_band_mode.value)
                
                st.session_state.viz_config.effects.waveform_band_mode = WaveformBandMode(
                    st.selectbox(
                        "Waveform Mode",
                        options=band_options,
                        index=current_band_idx,
                        key="wf_band_mode",
                        help="Single = classic, Dual = Bass/Treble, Triple = Bass/Mid/Treble"
                    )
                )
                
                # Frequency preset selector
                freq_preset_options = [p.value for p in WaveformFreqPreset]
                current_preset_idx = freq_preset_options.index(st.session_state.viz_config.effects.waveform_freq_preset.value)
                st.session_state.viz_config.effects.waveform_freq_preset = WaveformFreqPreset(
                    st.selectbox(
                        "Frequency Preset",
                        options=freq_preset_options,
                        index=current_preset_idx,
                        key="wf_freq_preset",
                        help="Pre-configured frequency ranges"
                    )
                )
                
                # Show color controls based on mode
                n_bands = 2 if st.session_state.viz_config.effects.waveform_band_mode == WaveformBandMode.DUAL else 3
                
                st.markdown("**Band Colors**")
                band_names = ['Bass (Low)', 'Treble (High)'] if n_bands == 2 else ['Bass', 'Mid', 'Treble']
                
                for i in range(n_bands):
                    current_color = st.session_state.viz_config.effects.waveform_band_colors[i]
                    new_color = st.color_picker(
                        f"{band_names[i]} Color",
                        current_color,
                        key=f"wf_color_{i}"
                    )
                    if new_color != current_color:
                        st.session_state.viz_config.effects.waveform_band_colors[i] = new_color
                
                # Amplitude and clipping controls
                st.markdown("**Amplitude & Clipping**")
                st.session_state.viz_config.effects.waveform_amplitude = st.slider(
                    "Amplitude Scale", 0.1, 2.0, st.session_state.viz_config.effects.waveform_amplitude, 0.1,
                    help="Waveform gain (use <1.0 to reduce clipping)"
                )
                st.session_state.viz_config.effects.waveform_pad_pct = st.slider(
                    "Container Padding", 0, 30, st.session_state.viz_config.effects.waveform_pad_pct, 5,
                    help="Space inside waveform container"
                )
                st.session_state.viz_config.effects.waveform_autogain = st.checkbox(
                    "Auto-Gain (Prevents Clipping)", st.session_state.viz_config.effects.waveform_autogain,
                    help="Automatically scales down if clipping detected"
                )
                
                # Dynamics controls
                st.markdown("**Dynamics**")
                st.session_state.viz_config.effects.waveform_speed = st.slider(
                    "Waveform Speed", 0.1, 3.0, st.session_state.viz_config.effects.waveform_speed, 0.1,
                    help="Slower = <1.0, Faster = >1.0"
                )
                st.session_state.viz_config.effects.waveform_band_gain = [
                    st.slider(f"{band_names[i]} Gain", 0.1, 2.0, 
                             st.session_state.viz_config.effects.waveform_band_gain[i] if i < len(st.session_state.viz_config.effects.waveform_band_gain) else 1.0, 0.1,
                             key=f"wf_gain_{i}")
                    for i in range(n_bands)
                ]
                
                # Rendering options
                render_options = [m.value for m in WaveformRenderMode]
                current_render_idx = render_options.index(st.session_state.viz_config.effects.waveform_render_mode.value)
                st.session_state.viz_config.effects.waveform_render_mode = WaveformRenderMode(
                    st.selectbox(
                        "Rendering Mode",
                        options=render_options,
                        index=current_render_idx,
                        key="wf_render_mode",
                        help="How multi-bands are positioned"
                    )
                )
                
                col_fill, col_mirror = st.columns(2)
                with col_fill:
                    st.session_state.viz_config.effects.waveform_fill = st.checkbox(
                        "Fill Area", st.session_state.viz_config.effects.waveform_fill,
                        help="Fills area under curve - great for stacked look"
                    )
                with col_mirror:
                    st.session_state.viz_config.effects.waveform_mirror = st.checkbox(
                        "Mirror Effect", st.session_state.viz_config.effects.waveform_mirror,
                        help="Creates symmetrical waveform"
                    )
        
        # ==================== PARTICLES & COVER ====================
        st.subheader("✨ Particles & Cover Effects", divider="violet")
        
        fx_col1, fx_col2 = st.columns(2)
        
        with fx_col1:
            st.markdown("#### Particles")
            st.session_state.viz_config.effects.particle_count = st.slider(
                "Particle Count", 10, 200, st.session_state.viz_config.effects.particle_count
            )
            st.session_state.viz_config.effects.particle_speed = st.slider(
                "Particle Speed", 0.1, 3.0, st.session_state.viz_config.effects.particle_speed
            )
            st.session_state.viz_config.effects.particle_size_range = st.slider(
                "Size Range", 0.5, 5.0, st.session_state.viz_config.effects.particle_size_range, step=0.1
            )
            
            current_color = st.session_state.viz_config.effects.particle_color_scheme.value
            color_options = [e.value for e in ColorScheme]
            selected_color = st.selectbox(
                "Particle Color", color_options,
                index=color_options.index(current_color),
                key="particle_color"
            )
            st.session_state.viz_config.effects.particle_color_scheme = ColorScheme(selected_color)
            
            st.session_state.viz_config.effects.beat_particle_burst = st.checkbox(
                "Burst on Beat", st.session_state.viz_config.effects.beat_particle_burst
            )
        
        with fx_col2:
            st.markdown("#### Cover Effects")
            st.session_state.viz_config.effects.cover_pulse = st.checkbox(
                "Pulse on Beat", st.session_state.viz_config.effects.cover_pulse
            )
            if st.session_state.viz_config.effects.cover_pulse:
                st.session_state.viz_config.effects.cover_zoom_intensity = st.slider(
                    "Pulse Intensity", 0.01, 0.1, st.session_state.viz_config.effects.cover_zoom_intensity
                )
            
            st.session_state.viz_config.effects.beat_flash = st.checkbox(
                "Screen Flash on Beat", st.session_state.viz_config.effects.beat_flash
            )
            if st.session_state.viz_config.effects.beat_flash:
                st.session_state.viz_config.effects.beat_flash_intensity = st.slider(
                    "Flash Intensity", 0.1, 0.8, st.session_state.viz_config.effects.beat_flash_intensity
                )
        
        # ==================== PREVIEW & PRESETS ====================
        st.subheader("👁️ Live Preview", divider="blue")
        render_position_preview(st.session_state.viz_config.effects, preview_placeholder)
        
        # Preset Management
        st.subheader("💾 Presets", divider="gray")
        preset_col1, preset_col2 = st.columns([3, 1])
        
        with preset_col1:
            preset_name = st.text_input("Save Current Settings As", placeholder="e.g., My Vertical Layout")
        with preset_col2:
            if st.button("💾 Save Preset"):
                if preset_name:
                    save_preset(preset_name, st.session_state.viz_config.effects)
                else:
                    st.error("Enter a preset name")
        
        presets = list_presets()
        if presets:
            col_load, col_btn = st.columns([3, 1])
            with col_load:
                selected_preset = st.selectbox("Load Preset", [""] + presets)
            with col_btn:
                if st.button("📂 Load") and selected_preset:
                    st.session_state.viz_config.effects = load_preset(selected_preset)
                    st.success(f"✅ Loaded: {selected_preset}")
                    st.rerun()
    
    with tab3:
        st.header("⚙️ Performance & Quality")
        
        col_perf1, col_perf2 = st.columns(2)
        
        with col_perf1:
            st.subheader("Quality")
            st.session_state.viz_config.effects.quality_preset = st.select_slider(
                "Preset", ["low", "medium", "high"], st.session_state.viz_config.effects.quality_preset,
                help="Affects particles, bars, and bitrate"
            )
            
            st.subheader("Resolution")
            res_options = ["960x540", "1280x720", "1920x1080"]
            current_res = f"{st.session_state.viz_config.effects.width}x{st.session_state.viz_config.effects.height}"
            selected_res = st.selectbox("Screen Size", res_options, 
                                      index=res_options.index(current_res) if current_res in res_options else 1)
            w, h = map(int, selected_res.split('x'))
            st.session_state.viz_config.effects.width = w
            st.session_state.viz_config.effects.height = h
            
            st.subheader("Frame Rate")
            st.session_state.viz_config.effects.fps = st.select_slider(
                "FPS", [24, 30, 60], st.session_state.viz_config.effects.fps
            )
        
        with col_perf2:
            st.subheader("Advanced")
            st.session_state.viz_config.effects.chunk_duration = st.slider(
                "Chunk Duration (seconds)", 5, 30, st.session_state.viz_config.effects.chunk_duration,
                help="Process video in chunks to manage memory"
            )
            st.session_state.viz_config.effects.bitrate = st.text_input(
                "Video Bitrate", st.session_state.viz_config.effects.bitrate,
                help="Higher = better quality, larger file"
            )
            
            st.subheader("Background")
            st.session_state.viz_config.effects.background_blur = st.slider(
                "Background Blur", 0, 50, st.session_state.viz_config.effects.background_blur
            )
            st.session_state.viz_config.effects.background_brightness = st.slider(
                "Background Brightness", 0.3, 1.0, st.session_state.viz_config.effects.background_brightness
            )
    
    with tab4:
        st.header("▶️ Generate Video")
        
        if st.button("👁️ Generate 5s Preview"):
            preview_path = selected_audio.with_suffix('.preview.mp4')
            preview_config = st.session_state.viz_config
            preview_config.effects.chunk_duration = 5
            
            engine = VisualizerEngine(preview_config)
            with st.spinner("Generating preview..."):
                success = engine.generate_video(
                    selected_audio, cover_path, preview_path,
                    progress_callback=lambda p: st.progress(p)
                )
            
            if success and preview_path.exists():
                st.success("✅ Preview ready!")
                st.video(str(preview_path))
                if st.button("🗑️ Delete Preview"):
                    preview_path.unlink(missing_ok=True)
                    st.rerun()
            else:
                st.error("❌ Preview generation failed")
        
        st.divider()
        
        output_path = selected_audio.with_suffix('.visualizer.mp4')
        if output_path.exists():
            st.info(f"Output: `{output_path.name}`")
            if st.checkbox("Overwrite existing file"):
                st.warning("⚠️ Will replace existing file")
        
        if st.button("🎬 Generate Full Video", type="primary", use_container_width=True):
            engine = VisualizerEngine(st.session_state.viz_config)
            progress_bar = st.progress(0)
            status = st.empty()
            
            start_time = time.time()
            
            def update_progress(p):
                progress_bar.progress(p)
                elapsed = time.time() - start_time
                if p > 0:
                    eta = elapsed / p - elapsed
                    status.text(f"⏱️ ETA: {int(eta//60)}m {int(eta%60)}s")
            
            try:
                status.info("Starting generation...")
                success = engine.generate_video(selected_audio, cover_path, output_path, update_progress)
                
                if success and output_path.exists():
                    status.success("✅ Complete!")
                    st.video(str(output_path))
                    
                    filesize = output_path.stat().st_size / (1024*1024)
                    duration = librosa.get_duration(filename=str(selected_audio))
                    st.info(f"📊 {output_path.name} | {duration:.1f}s | {filesize:.1f}MB")
                else:
                    status.error("❌ Generation failed")
                    
            except Exception as e:
                st.exception(e)
                logger.error("Unhandled generation error", exc_info=True)
            finally:
                gc.collect()

# =============================================================================
# PI 5 SETUP INSTRUCTIONS
# =============================================================================

def show_setup_instructions():
    with st.expander("🔧 Pi 5 Setup & Performance Tips", expanded=False):
        st.markdown("""
        ### **Pi 5 Software Encoding Mode**
        
        This visualizer uses **CPU-based encoding** optimized for Pi 5's performance:
        
        - ✅ Software encoding (`libx264`) with `ultrafast` preset
        - ✅ Handles 720p/30fps comfortably
        - ✅ Progressive rendering in chunks to manage memory
        
        ### **Best Performance Settings:**
        
        - **Quality**: Medium (default)
        - **Resolution**: 1280x720
        - **FPS**: 30
        - **Chunk Duration**: 15 seconds
        
        ### **Temperature Monitoring:**
        
        ```bash
        watch -n 2 vcgencmd measure_temp
        ```
        
        Add cooling if sustained > 75°C
        """)

# =============================================================================
# AUTO-EXECUTE
# =============================================================================
if __name__ in ["__page__", "__main__"]:
    try:
        show_setup_instructions()
        music_visualizer_page()
    except Exception as e:
        st.error("Unhandled error in visualizer page")
        st.exception(e)
