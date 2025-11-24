# ppmonk/core/__init__.py

# [修复] 使用绝对路径导入，彻底解决 "no known parent package" 问题
from ppmonk.core.player import PlayerState as Player
from ppmonk.core.spell_book import SpellBook
from ppmonk.core.buff_manager import BuffManager
from ppmonk.core.timeline import Timeline
from ppmonk.core.talents import TalentManager, TALENT_DB

__all__ = [
    "Player",
    "SpellBook",
    "BuffManager",
    "Timeline",
    "TalentManager",
    "TALENT_DB"
]