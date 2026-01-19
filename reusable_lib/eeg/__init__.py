# EEG - Neural Interface for Emotional Response Detection
# Extracted from ApexAurum - Claude Edition
#
# Supports OpenBCI hardware (Cyton, Ganglion) and mock mode for testing.
# Translates brain activity into AI-readable "felt experience" format.
#
# Requirements (optional):
#   pip install brainflow numpy scipy
#
# Works without brainflow using mock board and scipy fallback.

from .connection import EEGConnection, MockBoard, BRAINFLOW_AVAILABLE
from .processor import EEGProcessor, BandPower
from .experience import EmotionMapper, MomentExperience, ListeningSession

__all__ = [
    # Connection
    'EEGConnection',
    'MockBoard',
    'BRAINFLOW_AVAILABLE',
    # Processing
    'EEGProcessor',
    'BandPower',
    # Experience mapping
    'EmotionMapper',
    'MomentExperience',
    'ListeningSession',
]
