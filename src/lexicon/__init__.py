"""
FFXIV装备自动标注工具包
"""

from .labeler import FFXIVAutoLabeler
from .label_system import get_prompt_template, get_all_labels

__version__ = "0.1.0"
__all__ = ["FFXIVAutoLabeler", "get_prompt_template", "get_all_labels"]

