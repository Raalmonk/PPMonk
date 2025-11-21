"""Timeline management for PPMonk encounters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class TimelineEvent:
    """Represents a scheduled encounter event."""

    time: float
    name: str
    description: str = ""


class Timeline:
    """Manages a sequence of encounter events."""

    def __init__(self) -> None:
        self.events: List[TimelineEvent] = []

    def add_event(self, event: TimelineEvent) -> None:
        """Add an event to the timeline."""

        self.events.append(event)
        self.events.sort(key=lambda evt: evt.time)

    def clear(self) -> None:
        """Remove all scheduled events."""

        self.events.clear()
