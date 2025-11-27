class Talent:
    """天赋基类"""
    def __init__(self, name):
        self.name = name

    def apply(self, player, spell_book):
        pass

class PlaceholderTalent(Talent):
    """占位天赋"""
    def apply(self, player, spell_book):
        pass

class UnlockSpellTalent(Talent):
    def __init__(self, name, spell_abbr):
        super().__init__(name)
        self.spell_abbr = spell_abbr
    def apply(self, player, spell_book):
        if self.spell_abbr in spell_book.spells:
            spell_book.spells[self.spell_abbr].is_known = True

class StatModTalent(Talent):
    """修改基础属性"""
    def __init__(self, name, stat_name, value, is_percentage=False):
        super().__init__(name)
        self.stat_name = stat_name
        self.value = value
        self.is_percentage = is_percentage

    def apply(self, player, spell_book):
        if hasattr(player, self.stat_name):
            base_val = getattr(player, self.stat_name)
            if self.is_percentage:
                setattr(player, self.stat_name, base_val * (1.0 + self.value))
            else:
                setattr(player, self.stat_name, base_val + self.value)

class SpellModTalent(Talent):
    """修改技能属性"""
    def __init__(self, name, spell_abbr, attr_name, value, is_percentage=False):
        super().__init__(name)
        self.spell_abbr = spell_abbr
        self.attr_name = attr_name
        self.value = value
        self.is_percentage = is_percentage

    def apply(self, player, spell_book):
        if self.spell_abbr in spell_book.spells:
            spell = spell_book.spells[self.spell_abbr]
            if hasattr(spell, self.attr_name):
                base_val = getattr(spell, self.attr_name)
                if self.is_percentage:
                    setattr(spell, self.attr_name, base_val * (1.0 + self.value))
                else:
                    setattr(spell, self.attr_name, base_val + self.value)
                if self.attr_name == 'ap_coeff':
                    spell.update_tick_coeff()

# --- Row 2 & 3 (核心机制天赋) ---

class MomentumBoostTalent(Talent):
    def apply(self, player, spell_book):
        player.has_momentum_boost = True
        if 'FOF' in spell_book.spells:
            fof = spell_book.spells['FOF']
            fof.haste_dmg_scaling = True
            fof.tick_dmg_ramp = 0.10

class CombatWisdomTalent(Talent):
    def apply(self, player, spell_book):
        player.combat_wisdom_ready = True
        player.combat_wisdom_timer = 0.0

class SharpReflexesTalent(Talent):
    def apply(self, player, spell_book):
        if 'BOK' in spell_book.spells:
            spell_book.spells['BOK'].triggers_sharp_reflexes = True

class FerociousnessTalent(Talent):
    def __init__(self, name, rank=2):
        super().__init__(name)
        self.rank = rank
    def apply(self, player, spell_book):
        bonus = 0.02 * self.rank
        player.talent_crit_bonus += bonus
        player.update_stats()

class HardenedSolesTalent(Talent):
    def __init__(self, name, rank=2):
        super().__init__(name)
        self.rank = rank
    def apply(self, player, spell_book):
        if 'BOK' in spell_book.spells:
            bok = spell_book.spells['BOK']
            bok.bonus_crit_chance += 0.06 * self.rank
            bok.crit_damage_bonus += 0.10 * self.rank

class AscensionTalent(Talent):
    def apply(self, player, spell_book):
        player.max_energy += 20.0
        player.max_chi += 1
        player.energy_regen_mult *= 1.10
        player.energy = player.max_energy

class TouchOfTheTigerTalent(Talent):
    def apply(self, player, spell_book):
        if 'TP' in spell_book.spells:
            spell_book.spells['TP'].damage_multiplier *= 1.15

# --- Row 4 ---

class DualThreatTalent(Talent):
    """4-1: Dual Threat (自动攻击强化)"""
    def apply(self, player, spell_book):
        player.has_dual_threat = True

class TeachingsOfTheMonasteryTalent(Talent):
    """4-2: Teachings of the Monastery (禅院教诲)"""
    def apply(self, player, spell_book):
        player.has_totm = True

class GloryOfTheDawnTalent(Talent):
    """4-3: Glory of the Dawn (旭日峥嵘)"""
    def apply(self, player, spell_book):
        player.has_glory_of_the_dawn = True

# --- Row 5 ---

class CraneVortexTalent(Talent):
    """5-1: Crane Vortex (SCK +15%)"""
    def apply(self, player, spell_book):
        if 'SCK' in spell_book.spells:
            spell_book.spells['SCK'].ap_coeff *= 1.15
            spell_book.spells['SCK'].update_tick_coeff()

class MeridianStrikesTalent(Talent):
    """5-2: Meridian Strikes (ToD CD -45s, Dmg +15%)"""
    def apply(self, player, spell_book):
        if 'ToD' in spell_book.spells:
            tod = spell_book.spells['ToD']
            tod.base_cd = 45.0
            tod.damage_multiplier *= 1.15

class RisingStarTalent(Talent):
    """5-3: Rising Star (RSK +15% Dmg, +12% Crit Dmg)"""
    def apply(self, player, spell_book):
        if 'RSK' in spell_book.spells:
            rsk = spell_book.spells['RSK']
            rsk.damage_multiplier *= 1.15
            rsk.crit_damage_bonus += 0.12

class HitComboTalent(Talent):
    """5-5: Hit Combo"""
    def apply(self, player, spell_book):
        player.has_hit_combo = True

class BrawlerIntensityTalent(Talent):
    """5-6: Brawler's Intensity (RSK CD -1s, BOK Dmg +12%)"""
    def apply(self, player, spell_book):
        if 'RSK' in spell_book.spells:
            spell_book.spells['RSK'].base_cd -= 1.0
        if 'BOK' in spell_book.spells:
            spell_book.spells['BOK'].damage_multiplier *= 1.12

# --- Row 6 (Task 2 & 3) ---

class JadeIgnitionTalent(Talent):
    """6-1: Jade Ignition"""
    def apply(self, player, spell_book):
        player.has_jade_ignition = True

class CyclonesDriftTalent(Talent):
    """6-2: Cyclone's Drift (Haste 10% Multi)"""
    def apply(self, player, spell_book):
        player.has_cyclones_drift = True
        player.update_stats()

class CrashingStrikesTalent(Talent):
    """6-2_b: Crashing Strikes (FOF 5s, 6 Ticks)"""
    def apply(self, player, spell_book):
        if 'FOF' in spell_book.spells:
            fof = spell_book.spells['FOF']
            fof.base_cast_time = 5.0
            fof.total_ticks = 6
            fof.update_tick_coeff()

class DrinkingHornCoverTalent(Talent):
    """6-3_b: Drinking Horn Cover (Zenith Duration +5s)"""
    def apply(self, player, spell_book):
        player.has_drinking_horn_cover = True

class SpiritualFocusTalent(Talent):
    """6-3: Spiritual Focus (Zenith CD 90->70)"""
    def apply(self, player, spell_book):
        if 'Zenith' in spell_book.spells:
            spell_book.spells['Zenith'].base_cd = 70.0

class ObsidianSpiralTalent(Talent):
    """6-4: Obsidian Spiral (BOK +1 Chi during Zenith)"""
    def apply(self, player, spell_book):
        player.has_obsidian_spiral = True

class ComboBreakerTalent(Talent):
    """6-5: Combo Breaker (TP proc free BOK)"""
    def apply(self, player, spell_book):
        player.has_combo_breaker = True

# --- Row 7 (Task 3) ---

class DanceOfChiJiTalent(Talent):
    """7-1: Dance of Chi-Ji"""
    def apply(self, player, spell_book):
        player.has_dance_of_chiji = True

class ShadowboxingTreadsTalent(Talent):
    """7-2: Shadowboxing Treads (BOK +5% dmg, Cleave)"""
    def apply(self, player, spell_book):
        player.has_shadowboxing = True

class EnergyBurstTalent(Talent):
    """7-4: Energy Burst (Consume Combo Breaker -> +1 Chi)"""
    def apply(self, player, spell_book):
        player.has_energy_burst = True

class InnerPeaceTalent(Talent):
    """7-5: Inner Peace (Max Energy +30, TP Cost -5)"""
    def apply(self, player, spell_book):
        player.max_energy += 30.0
        # Re-top energy if just initialized
        if player.energy > player.max_energy - 35.0: # Heuristic
             player.energy = player.max_energy

        if 'TP' in spell_book.spells:
            spell_book.spells['TP'].energy_cost = 45 # 50 -> 45


# --- 完整数据库 ---
TALENT_DB = {
    # Row 1
    '1-1': UnlockSpellTalent('Fists of Fury', 'FOF'),

    # Row 2
    '2-1': MomentumBoostTalent('Momentum Boost'),
    '2-2': CombatWisdomTalent('Combat Wisdom'),
    '2-3': SharpReflexesTalent('Sharp Reflexes'),

    # Row 3
    '3-1': TouchOfTheTigerTalent('Touch of the Tiger'),
    '3-2': FerociousnessTalent('Ferociousness', rank=2),
    '3-3': HardenedSolesTalent('Hardened Soles', rank=2),
    '3-4': AscensionTalent('Ascension'),

    # Row 4
    '4-1': DualThreatTalent('Dual Threat'),
    '4-2': TeachingsOfTheMonasteryTalent('Teachings of the Monastery'),
    '4-3': GloryOfTheDawnTalent('Glory of the Dawn'),

    # Row 5
    '5-1': CraneVortexTalent('Crane Vortex'),
    '5-2': MeridianStrikesTalent('Meridian Strikes'),
    '5-3': RisingStarTalent('Rising Star'),
    '5-4': UnlockSpellTalent('Zenith', 'Zenith'),
    '5-5': HitComboTalent('Hit Combo'),
    '5-6': BrawlerIntensityTalent('Brawler Intensity'),

    # Row 6
    '6-1': JadeIgnitionTalent('Jade Ignition'),
    '6-2': CyclonesDriftTalent('Cyclone\'s Drift'),
    '6-2_b': CrashingStrikesTalent('Crashing Strikes'),
    '6-3': SpiritualFocusTalent('Spiritual Focus'),
    '6-3_b': DrinkingHornCoverTalent('Drinking Horn Cover'),
    '6-4': ObsidianSpiralTalent('Obsidian Spiral'),
    '6-5': ComboBreakerTalent('Combo Breaker'),

    # Row 7
    '7-1': DanceOfChiJiTalent('Dance of Chi-Ji'),
    '7-2': ShadowboxingTreadsTalent('Shadowboxing Treads'),
    '7-3': UnlockSpellTalent('Whirling Dragon Punch', 'WDP'),
    '7-3_b': UnlockSpellTalent('Strike of the Windlord', 'SOTWL'),
    '7-4': EnergyBurstTalent('Energy Burst'),
    '7-5': InnerPeaceTalent('Inner Peace'),

    # Placeholders for future
    '8-1': PlaceholderTalent('Tiger Eye Brew'),
    '8-2': PlaceholderTalent('Sequenced Strikes'),
    '8-3': PlaceholderTalent('Sunfire Spiral'),
    '8-4': PlaceholderTalent('Communion with Wind'),
    '8-5': PlaceholderTalent('Revolving Choice'),
    '8-6': PlaceholderTalent('Universal Energy'),
    '8-7': PlaceholderTalent('Memory of Monastery'),
    '9-1': PlaceholderTalent('TEB Buff'),
    '9-2': PlaceholderTalent('Rushing Jade Wind'),
    '9-3': UnlockSpellTalent('Invoke Xuen', 'Xuen'),
    '9-4': PlaceholderTalent('Thunderfist'),
    '9-5': PlaceholderTalent('Weapon of Wind'),
    '9-6': PlaceholderTalent('Knowledge'),
    '9-7': UnlockSpellTalent('Slicing Winds', 'SW'),
    '9-8': PlaceholderTalent('Jadefire Stomp'),
    '10-1': PlaceholderTalent('TEB Final'),
    '10-2': PlaceholderTalent('Skyfire Heel'),
    '10-3': PlaceholderTalent('Harmonic Combo'),
    '10-4': PlaceholderTalent('Flurry of Xuen'),
    '10-5': PlaceholderTalent('Martial Agility'),
    '10-6': PlaceholderTalent('Airborne Rhythm'),
    '10-7': PlaceholderTalent('Path of Jade'),

    # 兼容旧 ID / Shortcuts
    'WDP': UnlockSpellTalent('Whirling Dragon Punch', 'WDP'),
    'SW': UnlockSpellTalent('Slicing Winds', 'SW'),
    'SOTWL': UnlockSpellTalent('Strike of the Windlord', 'SOTWL'),
    'Ascension': AscensionTalent('Ascension'),
}

class TalentManager:
    def apply_talents(self, talent_ids, player, spell_book):
        for tid in talent_ids:
            if tid in TALENT_DB:
                TALENT_DB[tid].apply(player, spell_book)
