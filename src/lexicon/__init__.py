"""
FFXIV Equipment Auto-labeling Package
"""

from .labeler import FFXIVAutoLabeler
from .label_system import get_prompt_template, get_all_labels
from .app import app

__version__ = "0.1.0"
__all__ = ["FFXIVAutoLabeler", "get_prompt_template", "get_all_labels", "app"]

