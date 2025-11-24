"""Talent definitions and registry for PPMonk.

This module centralises all talent logic, making it easier for the UI to
refer to coordinate-style IDs (e.g. "1-1", "2-1").  Every coordinate from
``1-1`` through ``10-10`` resolves to a valid Talent instance so the backend
never crashes when the UI sends an unexpected ID.  Legacy English IDs remain
available for backward compatibility.
"""

from __future__ import annotations

from typing import Dict, Iterable


class Talent:
    """Base class for all talents."""

    def __init__(self, name: str):
        self.name = name

    def apply(self, player, spell_book):
        """Apply the talent effect to the given player/spellbook."""
        return None


class UnlockSpellTalent(Talent):
    """Talent that marks a spell as learned/known."""

    def __init__(self, name: str, spell_abbr: str):
        super().__init__(name)
        self.spell_abbr = spell_abbr

    def apply(self, player, spell_book):
        if self.spell_abbr in spell_book.spells:
            spell_book.spells[self.spell_abbr].is_known = True


class StatModTalent(Talent):
    """Talent that adjusts a player stat."""

    def __init__(self, name: str, stat_name: str, value: float, is_percentage: bool = False):
        super().__init__(name)
        self.stat_name = stat_name
        self.value = value
        self.is_percentage = is_percentage

    def apply(self, player, spell_book):
        if hasattr(player, self.stat_name):
            base = getattr(player, self.stat_name)
            if self.is_percentage:
                setattr(player, self.stat_name, base * (1.0 + self.value))
            else:
                setattr(player, self.stat_name, base + self.value)


class SpellModTalent(Talent):
    """Talent that adjusts a spell attribute."""

    def __init__(self, name: str, spell_abbr: str, attr_name: str, value: float, is_percentage: bool = False):
        super().__init__(name)
        self.spell_abbr = spell_abbr
        self.attr_name = attr_name
        self.value = value
        self.is_percentage = is_percentage

    def apply(self, player, spell_book):
        if self.spell_abbr in spell_book.spells:
            spell = spell_book.spells[self.spell_abbr]
            if hasattr(spell, self.attr_name):
                base = getattr(spell, self.attr_name)
                if self.is_percentage:
                    setattr(spell, self.attr_name, base * (1.0 + self.value))
                else:
                    setattr(spell, self.attr_name, base + self.value)
                if self.attr_name == "ap_coeff":
                    spell.update_tick_coeff()


# --- 机制类天赋 ---
class MomentumBoostTalent(Talent):
    def apply(self, player, spell_book):
        if "FOF" in spell_book.spells:
            fof = spell_book.spells["FOF"]
            if hasattr(fof, "haste_dmg_scaling"):
                fof.haste_dmg_scaling = True
            if hasattr(fof, "tick_dmg_ramp"):
                fof.tick_dmg_ramp = 0.10


class CombatWisdomTalent(Talent):
    def apply(self, player, spell_book):
        if hasattr(player, "combat_wisdom_ready"):
            player.combat_wisdom_ready = True
            player.combat_wisdom_timer = 0.0


class PlaceholderTalent(Talent):
    def apply(self, player, spell_book):
        return None


# --- Talent registry helpers -------------------------------------------------
# Explicit entries with gameplay effects.
_BASE_ENTRIES: Dict[str, Talent] = {
    "1-1": UnlockSpellTalent("Fists of Fury", "FOF"),

    "2-1": MomentumBoostTalent("Momentum Boost"),
    "2-2": CombatWisdomTalent("Combat Wisdom"),
    "2-3": PlaceholderTalent("Sharp Reflexes"),

    "3-1": PlaceholderTalent("Touch of the Tiger"),
    "3-2": PlaceholderTalent("Ferociousness"),
    "3-3": PlaceholderTalent("Hardened Soles"),
    "3-4": StatModTalent("Ascension", "max_energy", 20.0),

    "4-1": PlaceholderTalent("Dual Threat"),
    "4-2": PlaceholderTalent("Teachings of the Monastery"),
    "4-3": PlaceholderTalent("Glory of the Dawn"),

    "5-1": PlaceholderTalent("Crane Vortex"),
    "5-2": PlaceholderTalent("Meridian Strikes"),
    "5-3": PlaceholderTalent("Rising Star"),
    "5-4": PlaceholderTalent("Zenith"),
    "5-5": PlaceholderTalent("Hit Combo"),
    "5-6": PlaceholderTalent("Brawler Intensity"),

    "6-1": PlaceholderTalent("Jade Ignition"),
    "6-2": PlaceholderTalent("Cyclone Choice"),
    "6-3": PlaceholderTalent("Horn Choice"),
    "6-4": PlaceholderTalent("Obsidian Spiral"),
    "6-5": PlaceholderTalent("Combo Breaker"),

    "7-1": PlaceholderTalent("Dance of Chi-Ji"),
    "7-2": PlaceholderTalent("Shadowboxing Treads"),
    "7-3": UnlockSpellTalent("Whirling Dragon Punch", "WDP"),
    "7-4": PlaceholderTalent("Energy Burst"),
    "7-5": PlaceholderTalent("Inner Peace"),

    "8-1": PlaceholderTalent("Tiger Eye Brew"),
    "8-2": PlaceholderTalent("Sequenced Strikes"),
    "8-3": PlaceholderTalent("Sunfire Spiral"),
    "8-4": PlaceholderTalent("Communion with Wind"),
    "8-5": PlaceholderTalent("Revolving Choice"),
    "8-6": PlaceholderTalent("Universal Energy"),
    "8-7": PlaceholderTalent("Memory of Monastery"),

    "9-1": PlaceholderTalent("TEB Buff"),
    "9-2": PlaceholderTalent("RJW"),
    "9-3": PlaceholderTalent("Xuens Battlegear"),
    "9-4": PlaceholderTalent("Thunderfist"),
    "9-5": PlaceholderTalent("Weapon of Wind"),
    "9-6": PlaceholderTalent("Knowledge"),
    "9-7": UnlockSpellTalent("Slicing Winds", "SW"),
    "9-8": PlaceholderTalent("Jadefire Stomp"),

    "10-1": PlaceholderTalent("TEB Final"),
    "10-2": PlaceholderTalent("Skyfire Heel"),
    "10-3": PlaceholderTalent("Harmonic Combo"),
    "10-4": PlaceholderTalent("Flurry of Xuen"),
    "10-5": PlaceholderTalent("Martial Agility"),
    "10-6": PlaceholderTalent("Airborne Rhythm"),
    "10-7": PlaceholderTalent("Path of Jade"),
}

_COMPATIBILITY_ENTRIES: Dict[str, Talent] = {
    "WDP": UnlockSpellTalent("Whirling Dragon Punch", "WDP"),
    "SW": UnlockSpellTalent("Slicing Winds", "SW"),
    "SOTWL": UnlockSpellTalent("Strike of the Windlord", "SOTWL"),
    "Ascension": StatModTalent("Ascension", "max_energy", 20.0),
}


def _build_talent_db(max_columns: int = 10) -> Dict[str, Talent]:
    """Build a fully populated talent DB covering 10 rows and ``max_columns`` columns.

    Any coordinate not explicitly defined in ``_BASE_ENTRIES`` will map to a
    :class:`PlaceholderTalent` so lookups are always safe.
    """

    talent_db: Dict[str, Talent] = {}

    # Fill all coordinates with placeholders first to guarantee coverage.
    for row in range(1, 11):
        for col in range(1, max_columns + 1):
            coord = f"{row}-{col}"
            talent_db[coord] = PlaceholderTalent(f"Placeholder {coord}")

    # Overlay real entries.
    talent_db.update(_BASE_ENTRIES)

    # Add legacy aliases.
    talent_db.update(_COMPATIBILITY_ENTRIES)

    return talent_db


# --- Public API --------------------------------------------------------------
TALENT_DB: Dict[str, Talent] = _build_talent_db()


class TalentManager:
    def apply_talents(self, talent_ids: Iterable[str], player, spell_book):
        for tid in talent_ids:
            talent = TALENT_DB.get(tid)
            if talent:
                talent.apply(player, spell_book)
