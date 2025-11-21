"""Spell book module for PPMonk.

This file defines a simple container for spell definitions. Real damage,
cooldown, and cost calculations can be implemented alongside the
configuration files in future work.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class Spell:
    """Represents a single spell and its properties."""

    name: str
    damage_coefficient: float
    cooldown: float
    cost: float


class SpellBook:
    """Stores and retrieves available spells."""

    def __init__(self) -> None:
        self.spells: Dict[str, Spell] = {}

    def add_spell(self, spell: Spell) -> None:
        """Add a spell to the collection."""

        self.spells[spell.name] = spell

    def get_spell(self, name: str) -> Spell:
        """Return a spell by name, raising KeyError if missing."""

        return self.spells[name]
