"""Observation encoding utilities for PPMonk environments."""

from __future__ import annotations

from typing import Any

from ppmonk.core import Player


class ObservationEncoder:
    """Convert complex combat state into RL-friendly observations."""

    def encode(self, player: Player) -> Any:
        """Return a simplified observation of player state."""

        return {
            "health": player.health,
            "energy": player.energy,
            "chi": player.chi,
        }
