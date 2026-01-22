"""
Suno Prompt Compiler - Transform intent into optimized Suno prompts

Based on the comprehensive Suno Prompt Generation System, this module provides:
- Intent parsing and template selection
- Mood → emotional cartography mapping
- Symbol/kaomoji injection for Bark/Chirp manipulation
- Weirdness/Style balance optimization
- Unhinged seed generation for creativity boost

The compiler bridges high-level creative intent to the complex prompt structures
that unlock Suno's full potential.

Architecture:
    User Intent → Intent Parser → Template Selector → Parameter Injector
                → Symbol Compiler → Unhinged Seed Generator → Final Prompt
"""

import json
import random
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# Storage paths
TEMPLATES_DIR = Path("./sandbox/suno_templates")
MAPPINGS_DIR = TEMPLATES_DIR / "mappings"
PRESETS_DIR = TEMPLATES_DIR / "presets"

# Ensure directories exist
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
MAPPINGS_DIR.mkdir(parents=True, exist_ok=True)
PRESETS_DIR.mkdir(parents=True, exist_ok=True)


class Purpose(Enum):
    """Music generation purpose - affects structure and length"""
    SFX = "sfx"              # Short sound effect (5-30s)
    AMBIENT = "ambient"       # Background/atmosphere (1-4min)
    LOOP = "loop"            # Seamless loop (15-60s)
    SONG = "song"            # Full song structure (2-8min)
    JINGLE = "jingle"        # Short catchy piece (15-45s)


class Mood(Enum):
    """Mood presets with emotional cartography mappings"""
    # Positive
    MYSTICAL = "mystical"
    JOYFUL = "joyful"
    TRIUMPHANT = "triumphant"
    PEACEFUL = "peaceful"
    ENERGETIC = "energetic"
    HOPEFUL = "hopeful"
    PLAYFUL = "playful"

    # Neutral
    CONTEMPLATIVE = "contemplative"
    MYSTERIOUS = "mysterious"
    ETHEREAL = "ethereal"
    INDUSTRIAL = "industrial"
    DIGITAL = "digital"

    # Negative
    MELANCHOLIC = "melancholic"
    TENSE = "tense"
    DARK = "dark"
    CHAOTIC = "chaotic"
    OMINOUS = "ominous"
    ERROR = "error"  # For error sounds


# ═══════════════════════════════════════════════════════════════════════════════
# SYMBOL LIBRARIES - For Bark/Chirp manipulation
# ═══════════════════════════════════════════════════════════════════════════════

KAOMOJI_SETS = {
    "joyful": ["(≧◡≦)", "♪(◠‿◠)♪", "(˘▿˘)♫", "≧(´▽`)≦", "(灬ºωº灬)♡"],
    "peaceful": ["(◡‿◡)", "(´｡• ᵕ •｡`)", "(◕‿◕)", "♪(✿◡‿◡)", "(´-ω-`)"],
    "mystical": ["✧･ﾟ:", "⋆｡°✩₊˚.⋆", "◦°˚°◦•●◉✿✿", ".・。.・゜✭・.・✫・゜・。.", "☆ﾟ.*･｡ﾟ"],
    "energetic": ["(ง •̀_•́)ง", "(≧ω≦)", "┌(・。・)┘♪", "(灬º﹃º灬)", "\\(◎o◎)/"],
    "melancholic": ["(｡•́︿•̀｡)", "(´;ω;`)", "(◞‸◟)", "(っ˘̩╭╮˘̩)っ", "( ´_ゝ`)"],
    "dark": ["(¬‿¬)", "(￣▽￣)", "( ಠ ಠ )", "(╬ಠ益ಠ)", "༼ つ ◕_◕ ༽つ"],
    "playful": ["(◔◡◔)", "(灬^ω^灬)", "(≧◡≦)", "( ˘▽˘)っ♨", "ヾ(⌐■_■)ノ♪"],
    "contemplative": ["(˘▾˘)", "(・。・)", "(-_-)", "(￣～￣;)", "( ´_ゝ`)"],
    "error": ["(╯°□°)╯︵ ┻━┻", "(ಠ_ಠ)", "(；一_一)", "╭∩╮(-_-)╭∩╮", "( ≧Д≦)"],
}

MUSICAL_SYMBOLS = {
    "flow": ["≈≈≈♫≈≈≈", "∞♪∞♪∞", "≋≋≋♪≋≋≋"],
    "repeat": [":::", "•¨•.¸¸♪", "\ﾟ¨ﾟ✧･ﾟ"],
    "transition": ["✧･ﾟ: ✧･ﾟ:", "⋆｡°✩₊˚.⋆", ".｡.:\\・°☆"],
    "sparkle": ["✿✿◉●•◦°˚°◦", "◦°˚°◦•●◉✿✿", ":･ﾟ✧:･ﾟ✧"],
    "infinity": ["∞∞∞∞∞∞∞∞", "♪～(◔◡◔)～♪", "∮ₛ→∇⁴→∮ₛ"],
}

MATH_SYMBOLS = {
    "quantum": ["∮ₛ→∇⁴", "⨁→∂⨂→⨁", "∂⨂→∇⁴→∂⨂", "[H⊗X⊗H→T]"],
    "alchemical": ["☉∮☉", "∇⁴∂∇", "☉-∲-तेजस्"],
    "processor": ["[Processor State: ✩∯▽ₜ₀ → ⋆∮◇ₐ₀]", "[∮ₛ→∇⁴→∮ₛ]"],
}

# Binary sequences for different moods (encodes context for Suno)
BINARY_SEQUENCES = {
    "mystical": "01101101 01111001 01110011",  # "mys"
    "joyful": "01101010 01101111 01111001",    # "joy"
    "dark": "01100100 01100001 01110010",       # "dar"
    "error": "01100101 01110010 01110010",      # "err"
    "digital": "01100100 01101001 01100111",    # "dig"
    "peaceful": "01110000 01100101 01100001",   # "pea"
    "energetic": "01100101 01101110 01100101",  # "ene"
}


# ═══════════════════════════════════════════════════════════════════════════════
# EMOTIONAL CARTOGRAPHY - Mood to percentage mappings
# ═══════════════════════════════════════════════════════════════════════════════

EMOTIONAL_CARTOGRAPHY = {
    "mystical": {"primary": "ethereal calm", "primary_pct": 70, "secondary": "crypto mystical", "secondary_pct": 30},
    "joyful": {"primary": "euphoric burst", "primary_pct": 80, "secondary": "playful energy", "secondary_pct": 20},
    "triumphant": {"primary": "victorious surge", "primary_pct": 75, "secondary": "heroic power", "secondary_pct": 25},
    "peaceful": {"primary": "serene tranquil", "primary_pct": 85, "secondary": "gentle drift", "secondary_pct": 15},
    "energetic": {"primary": "dynamic pulse", "primary_pct": 75, "secondary": "kinetic drive", "secondary_pct": 25},
    "hopeful": {"primary": "optimistic rise", "primary_pct": 70, "secondary": "dawn awakening", "secondary_pct": 30},
    "playful": {"primary": "whimsical bounce", "primary_pct": 65, "secondary": "mischievous spark", "secondary_pct": 35},
    "contemplative": {"primary": "introspective depth", "primary_pct": 75, "secondary": "philosophical muse", "secondary_pct": 25},
    "mysterious": {"primary": "enigmatic shadow", "primary_pct": 70, "secondary": "cryptic veil", "secondary_pct": 30},
    "ethereal": {"primary": "transcendent float", "primary_pct": 80, "secondary": "celestial drift", "secondary_pct": 20},
    "industrial": {"primary": "mechanical grind", "primary_pct": 70, "secondary": "urban pulse", "secondary_pct": 30},
    "digital": {"primary": "glitch matrix", "primary_pct": 65, "secondary": "cyber flow", "secondary_pct": 35},
    "melancholic": {"primary": "sorrowful depth", "primary_pct": 75, "secondary": "nostalgic ache", "secondary_pct": 25},
    "tense": {"primary": "anxious edge", "primary_pct": 70, "secondary": "suspenseful build", "secondary_pct": 30},
    "dark": {"primary": "ominous void", "primary_pct": 75, "secondary": "shadowed menace", "secondary_pct": 25},
    "chaotic": {"primary": "frenzied storm", "primary_pct": 65, "secondary": "anarchic surge", "secondary_pct": 35},
    "ominous": {"primary": "foreboding dread", "primary_pct": 80, "secondary": "lurking threat", "secondary_pct": 20},
    "error": {"primary": "discordant glitch", "primary_pct": 70, "secondary": "failure cascade", "secondary_pct": 30},
}


# ═══════════════════════════════════════════════════════════════════════════════
# BPM AND TUNING MAPPINGS
# ═══════════════════════════════════════════════════════════════════════════════

MOOD_BPM = {
    "mystical": (60.0, 80.0),
    "joyful": (120.0, 140.0),
    "triumphant": (130.0, 150.0),
    "peaceful": (50.0, 70.0),
    "energetic": (140.0, 170.0),
    "hopeful": (100.0, 120.0),
    "playful": (115.0, 135.0),
    "contemplative": (60.0, 85.0),
    "mysterious": (70.0, 95.0),
    "ethereal": (55.0, 75.0),
    "industrial": (110.0, 140.0),
    "digital": (125.0, 155.0),
    "melancholic": (60.0, 85.0),
    "tense": (90.0, 120.0),
    "dark": (70.0, 100.0),
    "chaotic": (150.0, 180.0),
    "ominous": (50.0, 75.0),
    "error": (80.0, 120.0),
}

MOOD_TUNING = {
    "mystical": "432Hz",
    "peaceful": "432Hz",
    "ethereal": "432Hz",
    "contemplative": "432Hz",
    "digital": "19-TET",
    "chaotic": "19-TET",
    "error": "19-TET",
    "industrial": "just intonation",
    "dark": "just intonation",
}

PURPOSE_WEIRDNESS_STYLE = {
    Purpose.SFX: (25, 75),       # More consistent for sound effects
    Purpose.AMBIENT: (35, 65),   # Slightly more experimental
    Purpose.LOOP: (20, 80),      # Very consistent for looping
    Purpose.SONG: (45, 55),      # Balanced
    Purpose.JINGLE: (30, 70),    # Catchy and consistent
}


# ═══════════════════════════════════════════════════════════════════════════════
# COMPILED PROMPT DATACLASS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CompiledPrompt:
    """A fully compiled Suno prompt ready for music_generate"""
    # Core fields for music_generate()
    styles: str                    # Goes to 'style' parameter
    lyrics: str                    # Goes to 'prompt' parameter (for instrumental, this is symbols)
    exclude_styles: str = ""       # For advanced use

    # Metadata
    title_suggestion: str = ""
    weirdness_pct: int = 50
    style_pct: int = 50
    unhinged_seed: str = ""

    # Generation hints
    recommended_model: str = "V5"
    is_instrumental: bool = True

    # Debug/traceability
    intent: str = ""
    mood: str = ""
    purpose: str = ""

    def to_music_generate_args(self) -> Dict[str, Any]:
        """Convert to arguments for music_generate()"""
        return {
            "prompt": self.lyrics,
            "style": self.styles,
            "title": self.title_suggestion,
            "model": self.recommended_model,
            "is_instrumental": self.is_instrumental,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Full dictionary representation"""
        return asdict(self)

    def get_full_prompt_display(self) -> str:
        """Format for display/debugging"""
        return f"""
═══════════════════════════════════════════════════════════════
COMPILED SUNO PROMPT
═══════════════════════════════════════════════════════════════

🎹 STYLES:
{self.styles}

🚫 EXCLUDE STYLES:
{self.exclude_styles or "(none)"}

🎙️ LYRICS/SYMBOLS:
{self.lyrics}

⚖️ BALANCE:
Weirdness: {self.weirdness_pct}% | Style: {self.style_pct}%

🌀 UNHINGED SEED:
{self.unhinged_seed}

───────────────────────────────────────────────────────────────
Intent: {self.intent}
Mood: {self.mood} | Purpose: {self.purpose}
Model: {self.recommended_model} | Instrumental: {self.is_instrumental}
═══════════════════════════════════════════════════════════════
"""


# ═══════════════════════════════════════════════════════════════════════════════
# CORE COMPILER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class SunoCompiler:
    """
    Compiles high-level intent into optimized Suno prompts.

    Example:
        compiler = SunoCompiler()
        prompt = compiler.compile(
            intent="mystical bell chime for tool completion",
            mood="mystical",
            purpose="sfx",
            genre="ambient chime"
        )
        # Use with music_generate:
        music_generate(**prompt.to_music_generate_args())
    """

    def __init__(self):
        self.templates = self._load_templates()
        self.custom_mappings = self._load_custom_mappings()

    def _load_templates(self) -> Dict[str, Any]:
        """Load template library from disk"""
        templates = {}
        template_files = list(TEMPLATES_DIR.glob("*.json"))
        for tf in template_files:
            try:
                with open(tf) as f:
                    templates[tf.stem] = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load template {tf}: {e}")
        return templates

    def _load_custom_mappings(self) -> Dict[str, Any]:
        """Load any custom mappings from disk"""
        mappings = {}
        mapping_files = list(MAPPINGS_DIR.glob("*.json"))
        for mf in mapping_files:
            try:
                with open(mf) as f:
                    mappings[mf.stem] = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load mapping {mf}: {e}")
        return mappings

    def compile(
        self,
        intent: str,
        mood: str = "mystical",
        purpose: str = "song",
        genre: str = "",
        weirdness: Optional[int] = None,
        style_balance: Optional[int] = None,
        duration_hint: str = "medium",
        instrumental: bool = True,
        include_unhinged_seed: bool = True,
        custom_symbols: Optional[List[str]] = None,
    ) -> CompiledPrompt:
        """
        Compile intent into a full Suno prompt.

        Args:
            intent: Natural language description of what you want
            mood: Emotional mood (mystical, joyful, dark, etc.)
            purpose: sfx, ambient, loop, song, jingle
            genre: Base genre(s) like "ambient chime", "electronic dubstep"
            weirdness: 0-100, override default for purpose
            style_balance: 0-100, override default for purpose
            duration_hint: short, medium, long
            instrumental: True for instrumental, False for vocals
            include_unhinged_seed: Add creativity-boosting seed
            custom_symbols: Additional symbols to include

        Returns:
            CompiledPrompt ready for music_generate()
        """
        # Normalize inputs
        mood = mood.lower()
        purpose_enum = Purpose(purpose.lower()) if purpose.lower() in [p.value for p in Purpose] else Purpose.SONG

        # Get defaults for purpose
        default_weird, default_style = PURPOSE_WEIRDNESS_STYLE.get(purpose_enum, (50, 50))
        weirdness = weirdness if weirdness is not None else default_weird
        style_balance = style_balance if style_balance is not None else default_style

        # Build components
        styles = self._build_styles(intent, mood, genre, purpose_enum)
        exclude_styles = self._build_exclude_styles(mood, genre)
        lyrics = self._build_lyrics(intent, mood, purpose_enum, custom_symbols)
        unhinged_seed = self._build_unhinged_seed(intent, mood, genre) if include_unhinged_seed else ""
        title = self._generate_title_suggestion(intent, mood)

        return CompiledPrompt(
            styles=styles,
            lyrics=lyrics,
            exclude_styles=exclude_styles,
            title_suggestion=title,
            weirdness_pct=weirdness,
            style_pct=style_balance,
            unhinged_seed=unhinged_seed,
            recommended_model="V5",
            is_instrumental=instrumental,
            intent=intent,
            mood=mood,
            purpose=purpose_enum.value,
        )

    def _build_styles(self, intent: str, mood: str, genre: str, purpose: Purpose) -> str:
        """Build the styles field"""
        components = []

        # Base genre
        if genre:
            components.append(genre)

        # Purpose-specific additions
        if purpose == Purpose.SFX:
            components.extend(["short", "punchy", "minimal"])
        elif purpose == Purpose.AMBIENT:
            components.extend(["atmospheric", "evolving", "textural"])
        elif purpose == Purpose.LOOP:
            components.extend(["seamless", "loopable", "consistent"])

        # BPM from mood
        if mood in MOOD_BPM:
            bpm_low, bpm_high = MOOD_BPM[mood]
            # Use fractional BPM for more unique results
            bpm = round(random.uniform(bpm_low, bpm_high), 1)
            components.append(f"{bpm}BPM")

        # Tuning from mood
        if mood in MOOD_TUNING:
            components.append(MOOD_TUNING[mood])

        # Emotional cartography
        if mood in EMOTIONAL_CARTOGRAPHY:
            ec = EMOTIONAL_CARTOGRAPHY[mood]
            components.append(f"emotional cartography {ec['primary']} {ec['primary_pct']}% {ec['secondary']} {ec['secondary_pct']}%")

        # Add quantum/neuromorphic for certain moods
        if mood in ["mystical", "ethereal", "digital"]:
            components.append("quantum textures")
        if mood in ["industrial", "digital", "chaotic"]:
            components.append("neuromorphic synthesis")

        # Add binary sequence for depth
        if mood in BINARY_SEQUENCES:
            components.append(f"binary {BINARY_SEQUENCES[mood]}")

        return ", ".join(components)

    def _build_exclude_styles(self, mood: str, genre: str) -> str:
        """Build exclude_styles with double negatives for ironic enforcement"""
        excludes = []

        # Use double negatives to enforce certain qualities
        if mood in ["mystical", "peaceful", "ethereal"]:
            excludes.append("no not gentle ambient swells")
            excludes.append("no not ethereal textures")
        elif mood in ["energetic", "chaotic", "triumphant"]:
            excludes.append("no not dynamic builds")
            excludes.append("no not powerful drops")
        elif mood == "error":
            excludes.append("no not discordant glitches")
            excludes.append("no not harsh digital artifacts")

        return ", ".join(excludes) if excludes else ""

    def _build_lyrics(self, intent: str, mood: str, purpose: Purpose, custom_symbols: Optional[List[str]] = None) -> str:
        """Build the lyrics field with symbols for instrumental manipulation"""
        sections = []

        # Get kaomoji set for mood
        kaomoji_key = mood if mood in KAOMOJI_SETS else "peaceful"
        kaomoji = KAOMOJI_SETS.get(kaomoji_key, KAOMOJI_SETS["peaceful"])

        # Get musical symbols
        flow_symbols = MUSICAL_SYMBOLS["flow"]
        transition_symbols = MUSICAL_SYMBOLS["transition"]
        sparkle_symbols = MUSICAL_SYMBOLS["sparkle"]

        # Get math symbols for depth
        math_symbols = MATH_SYMBOLS["quantum"]

        # Structure based on purpose
        if purpose == Purpose.SFX:
            # Very short, punchy - single section
            section = f"[SFX] {random.choice(kaomoji)} {random.choice(flow_symbols)} {random.choice(transition_symbols)} {random.choice(math_symbols)}"
            sections.append(section)

        elif purpose == Purpose.AMBIENT:
            # Longer, evolving sections
            sections.append(f"[Ambient Entry] {' '.join(random.sample(transition_symbols, 2))} {' '.join(random.sample(kaomoji, 2))}")
            sections.append(f"[Evolve] {' '.join(random.sample(flow_symbols, 2))} {' '.join(random.sample(sparkle_symbols, 2))} {random.choice(math_symbols)}")
            sections.append(f"[Drift] {' '.join(kaomoji)} {' '.join(flow_symbols)}")

        elif purpose == Purpose.LOOP:
            # Consistent, loopable
            base_symbols = f"{random.choice(flow_symbols)} {random.choice(kaomoji)} {random.choice(transition_symbols)}"
            sections.append(f"[Loop] {base_symbols} ::: {base_symbols}")

        else:  # SONG or JINGLE
            # Full structure
            sections.append(f"[Intro] {' '.join(random.sample(transition_symbols, 2))} {random.choice(kaomoji)}")
            sections.append(f"[Build] {' '.join(random.sample(flow_symbols, 2))} {' '.join(random.sample(kaomoji, 2))} {random.choice(math_symbols)}")
            sections.append(f"[Peak] {' '.join(sparkle_symbols)} {' '.join(kaomoji)} {' '.join(flow_symbols)}")
            sections.append(f"[Outro] {random.choice(transition_symbols)} {random.choice(kaomoji)} {random.choice(flow_symbols)}")

        # Add processor code
        if mood in EMOTIONAL_CARTOGRAPHY:
            ec = EMOTIONAL_CARTOGRAPHY[mood]
            sections.append(f"[EmotionMap: {ec['primary'].title()} {ec['primary_pct']}% / {ec['secondary'].title()} {ec['secondary_pct']}%]")

        sections.append("[Processor State: ✩∯▽ₜ₀ → ⋆∮◇ₐ₀ transition]")

        # Add custom symbols if provided
        if custom_symbols:
            sections.append(" ".join(custom_symbols))

        # Join with newlines (affects pacing in Suno)
        # More newlines = slower/more deliberate
        if purpose == Purpose.SFX:
            return " ".join(sections)  # Tight, fast
        elif purpose in [Purpose.AMBIENT, Purpose.LOOP]:
            return "\n\n".join(sections)  # Spacious
        else:
            return "\n".join(sections)  # Balanced

    def _build_unhinged_seed(self, intent: str, mood: str, genre: str) -> str:
        """Build the unhinged seed for creativity boost"""
        # Satirical description that Suno responds well to
        mood_descriptors = {
            "mystical": "ethereal realm convergence",
            "joyful": "euphoric celebration cascade",
            "dark": "shadow void emergence",
            "peaceful": "tranquil infinity drift",
            "energetic": "kinetic pulse explosion",
            "error": "glitch matrix failure satire",
            "digital": "cyber consciousness bloom",
        }

        descriptor = mood_descriptors.get(mood, "emergent creative fusion")

        seed = f'[[["""Unhinged Seed: {intent} as {descriptor}, '
        seed += f'Bark layers via symbols, Chirp backup instrumental w/kaomoji, '
        seed += f'recursive ∮ₛ for emerging {mood} texture, '
        seed += f'full autonomous zero emotion godmode"""]]]'

        return seed

    def _generate_title_suggestion(self, intent: str, mood: str) -> str:
        """Generate a title suggestion (often better to leave blank for Suno)"""
        # Keep it short or empty - Suno sometimes titles better
        words = intent.split()[:3]
        return " ".join(words).title() if len(words) >= 2 else ""

    # ═══════════════════════════════════════════════════════════════════════════
    # PRESET METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def compile_preset(self, preset_name: str, **overrides) -> CompiledPrompt:
        """Compile from a saved preset with optional overrides"""
        preset_file = PRESETS_DIR / f"{preset_name}.json"
        if not preset_file.exists():
            raise ValueError(f"Preset not found: {preset_name}")

        with open(preset_file) as f:
            preset = json.load(f)

        # Merge overrides
        preset.update(overrides)

        return self.compile(**preset)

    def save_preset(self, name: str, **kwargs) -> bool:
        """Save compilation parameters as a preset"""
        try:
            preset_file = PRESETS_DIR / f"{name}.json"
            with open(preset_file, 'w') as f:
                json.dump(kwargs, f, indent=2)
            logger.info(f"Saved preset: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save preset {name}: {e}")
            return False

    def list_presets(self) -> List[str]:
        """List available presets"""
        return [p.stem for p in PRESETS_DIR.glob("*.json")]


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL FUNCTIONS (for agent access)
# ═══════════════════════════════════════════════════════════════════════════════

# Global compiler instance
_compiler: Optional[SunoCompiler] = None

def _get_compiler() -> SunoCompiler:
    """Get or create compiler singleton"""
    global _compiler
    if _compiler is None:
        _compiler = SunoCompiler()
    return _compiler


def suno_prompt_build(
    intent: str,
    mood: str = "mystical",
    purpose: str = "song",
    genre: str = "",
    weirdness: int = 50,
    style_balance: int = 50,
    instrumental: bool = True,
) -> Dict[str, Any]:
    """
    Build an optimized Suno prompt from high-level intent.

    This tool compiles natural language intent into the complex prompt structures
    that unlock Suno's full potential using Bark/Chirp manipulation, emotional
    cartography, symbol injection, and unhinged seeds.

    Args:
        intent: What you want to create (e.g., "mystical bell chime", "epic battle music")
        mood: Emotional mood - mystical, joyful, dark, peaceful, energetic, error, etc.
        purpose: Generation purpose - sfx (short), ambient, loop, song, jingle
        genre: Base genre (e.g., "ambient chime", "electronic dubstep", "orchestral")
        weirdness: 0-100, higher = more experimental/chaotic
        style_balance: 0-100, higher = more consistent/structured
        instrumental: True for instrumental, False for vocals

    Returns:
        Dict with compiled prompt ready for music_generate(), plus metadata.
        Use result["music_generate_args"] directly with music_generate().

    Example:
        >>> result = suno_prompt_build(
        ...     intent="mystical crystal chime for tool completion",
        ...     mood="mystical",
        ...     purpose="sfx",
        ...     genre="ambient chime crystalline"
        ... )
        >>> music_generate(**result["music_generate_args"])
    """
    try:
        compiler = _get_compiler()
        compiled = compiler.compile(
            intent=intent,
            mood=mood,
            purpose=purpose,
            genre=genre,
            weirdness=weirdness,
            style_balance=style_balance,
            instrumental=instrumental,
        )

        return {
            "success": True,
            "music_generate_args": compiled.to_music_generate_args(),
            "full_prompt": compiled.to_dict(),
            "display": compiled.get_full_prompt_display(),
        }
    except Exception as e:
        logger.error(f"Prompt build failed: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def suno_prompt_preset_save(
    name: str,
    intent: str,
    mood: str = "mystical",
    purpose: str = "song",
    genre: str = "",
    weirdness: int = 50,
    style_balance: int = 50,
    instrumental: bool = True,
) -> Dict[str, Any]:
    """
    Save Suno prompt parameters as a reusable preset.

    Args:
        name: Preset name (e.g., "village_chime", "epic_battle")
        intent: What the preset creates
        mood: Emotional mood
        purpose: Generation purpose
        genre: Base genre
        weirdness: Experimentation level (0-100)
        style_balance: Structure level (0-100)
        instrumental: True for instrumental

    Returns:
        Success status and preset path.
    """
    try:
        compiler = _get_compiler()
        success = compiler.save_preset(
            name=name,
            intent=intent,
            mood=mood,
            purpose=purpose,
            genre=genre,
            weirdness=weirdness,
            style_balance=style_balance,
            instrumental=instrumental,
        )
        return {
            "success": success,
            "preset_name": name,
            "preset_path": str(PRESETS_DIR / f"{name}.json"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def suno_prompt_preset_load(name: str, **overrides) -> Dict[str, Any]:
    """
    Load and compile a saved preset, optionally with overrides.

    Args:
        name: Preset name to load
        **overrides: Any parameters to override from the preset

    Returns:
        Compiled prompt ready for music_generate().
    """
    try:
        compiler = _get_compiler()
        compiled = compiler.compile_preset(name, **overrides)
        return {
            "success": True,
            "music_generate_args": compiled.to_music_generate_args(),
            "full_prompt": compiled.to_dict(),
            "display": compiled.get_full_prompt_display(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def suno_prompt_preset_list() -> Dict[str, Any]:
    """
    List all available Suno prompt presets.

    Returns:
        List of preset names.
    """
    try:
        compiler = _get_compiler()
        presets = compiler.list_presets()
        return {
            "success": True,
            "presets": presets,
            "count": len(presets),
            "preset_dir": str(PRESETS_DIR),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

SUNO_PROMPT_BUILD_SCHEMA = {
    "name": "suno_prompt_build",
    "description": "Build an optimized Suno prompt from high-level intent. Compiles natural language into complex prompt structures using Bark/Chirp manipulation, emotional cartography, symbol injection, and unhinged seeds for maximum creative output.",
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "description": "What you want to create (e.g., 'mystical bell chime', 'epic battle music')"
            },
            "mood": {
                "type": "string",
                "description": "Emotional mood: mystical, joyful, dark, peaceful, energetic, error, contemplative, ethereal, industrial, digital, melancholic, tense, chaotic, ominous, triumphant, hopeful, playful",
                "default": "mystical"
            },
            "purpose": {
                "type": "string",
                "description": "Generation purpose: sfx (5-30s), ambient (1-4min), loop (15-60s), song (2-8min), jingle (15-45s)",
                "default": "song"
            },
            "genre": {
                "type": "string",
                "description": "Base genre (e.g., 'ambient chime', 'electronic dubstep', 'orchestral epic')",
                "default": ""
            },
            "weirdness": {
                "type": "integer",
                "description": "Experimentation level 0-100. Higher = more chaotic/experimental",
                "default": 50
            },
            "style_balance": {
                "type": "integer",
                "description": "Structure level 0-100. Higher = more consistent/structured",
                "default": 50
            },
            "instrumental": {
                "type": "boolean",
                "description": "True for instrumental, False for vocals",
                "default": True
            }
        },
        "required": ["intent"]
    }
}

SUNO_PROMPT_PRESET_SAVE_SCHEMA = {
    "name": "suno_prompt_preset_save",
    "description": "Save Suno prompt parameters as a reusable preset for quick access.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Preset name (e.g., 'village_chime', 'epic_battle')"
            },
            "intent": {
                "type": "string",
                "description": "What the preset creates"
            },
            "mood": {"type": "string", "default": "mystical"},
            "purpose": {"type": "string", "default": "song"},
            "genre": {"type": "string", "default": ""},
            "weirdness": {"type": "integer", "default": 50},
            "style_balance": {"type": "integer", "default": 50},
            "instrumental": {"type": "boolean", "default": True}
        },
        "required": ["name", "intent"]
    }
}

SUNO_PROMPT_PRESET_LOAD_SCHEMA = {
    "name": "suno_prompt_preset_load",
    "description": "Load and compile a saved Suno prompt preset.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Preset name to load"
            }
        },
        "required": ["name"]
    }
}

SUNO_PROMPT_PRESET_LIST_SCHEMA = {
    "name": "suno_prompt_preset_list",
    "description": "List all available Suno prompt presets.",
    "input_schema": {
        "type": "object",
        "properties": {}
    }
}
