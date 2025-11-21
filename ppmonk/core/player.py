"""Player state representation for PPMonk.

This module defines the Player class, which tracks resource values and
the status of the combatant. The implementation is intentionally minimal
and can be expanded with full combat logic in future iterations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Player:
    """Represents a player with basic combat resources."""

    health: float = 100.0
    energy: float = 100.0
    chi: float = 0.0
    stats: Dict[str, float] = field(default_factory=dict)

    def reset(self) -> None:
        """Reset dynamic resources to their default values."""

        self.energy = 100.0
        self.chi = 0.0

    def apply_damage(self, amount: float) -> None:
        """Apply incoming damage to the player."""

        self.health = max(self.health - amount, 0.0)

    def is_alive(self) -> bool:
        """Return whether the player is still alive."""

        return self.health > 0
