# ppmonk/core/__init__.py
"""Core combat logic for PPMonk."""

# [关键修复] 导入 PlayerState 并给它起个别名 Player，防止报错
from .player import PlayerState as Player  
from .spell_book import SpellBook
from .buff_manager import BuffManager
from .timeline import Timeline
from .talents import TalentManager, TALENT_DB # 建议把新模块也加上

__all__ = [
    "Player",
    "SpellBook",
    "BuffManager",
    "Timeline",
    "TalentManager",
    "TALENT_DB"
]