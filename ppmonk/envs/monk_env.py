"""Gym-compatible environment for PPMonk."""

from __future__ import annotations

from typing import Any, Tuple

from ppmonk.core import Player, SpellBook, BuffManager, Timeline
from ppmonk.envs.observation import ObservationEncoder


class MonkEnv:
    """Stub for the main training environment."""

    def __init__(self) -> None:
        self.player = Player()
        self.spells = SpellBook()
        self.buffs = BuffManager()
        self.timeline = Timeline()
        self.encoder = ObservationEncoder()

    def reset(self) -> Any:
        """Reset environment state and return initial observation."""

        self.player.reset()
        self.buffs.clear()
        self.timeline.clear()
        return self.encoder.encode(self.player)

    def step(self, action: Any) -> Tuple[Any, float, bool, dict]:
        """Perform an action. This is a placeholder for RL integration."""

        observation = self.encoder.encode(self.player)
        reward = 0.0
        done = not self.player.is_alive()
        info: dict = {}
        return observation, reward, done, info
