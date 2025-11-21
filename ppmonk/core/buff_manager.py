"""Buff and damage-over-time tracking for PPMonk."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class Buff:
    """Represents a buff or debuff with duration and remaining ticks."""

    name: str
    duration: float
    ticks: int


class BuffManager:
    """Tracks active buffs and their durations."""

    def __init__(self) -> None:
        self.active_buffs: Dict[str, Buff] = {}

    def add_buff(self, buff: Buff) -> None:
        """Register a new buff or refresh an existing one."""

        self.active_buffs[buff.name] = buff

    def expire_buff(self, name: str) -> None:
        """Remove a buff if it exists."""

        self.active_buffs.pop(name, None)

    def clear(self) -> None:
        """Remove all tracked buffs."""

        self.active_buffs.clear()
