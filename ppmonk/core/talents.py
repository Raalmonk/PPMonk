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
            # Use specific methods if attr_name matches new list system
            if self.attr_name == 'damage_multiplier':
                # Map to add_modifier
                 val = 1.0 + self.value if self.is_percentage else self.value
                 spell.add_modifier(self.name, val)
            elif self.attr_name == 'bonus_crit_chance':
                 spell.add_crit_modifier(self.name, self.value)
            elif hasattr(spell, self.attr_name):
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
            bok.add_crit_modifier(self.name, 0.06 * self.rank)
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
            spell_book.spells['TP'].add_modifier(self.name, 1.15)

# --- Row 4 ---

class DualThreatTalent(Talent):
    def apply(self, player, spell_book):
        player.has_dual_threat = True

class TeachingsOfTheMonasteryTalent(Talent):
    def apply(self, player, spell_book):
        player.has_totm = True

class GloryOfTheDawnTalent(Talent):
    def apply(self, player, spell_book):
        player.has_glory_of_the_dawn = True

# --- Row 5 ---

class CraneVortexTalent(Talent):
    def apply(self, player, spell_book):
        if 'SCK' in spell_book.spells:
            spell_book.spells['SCK'].ap_coeff *= 1.15
            spell_book.spells['SCK'].update_tick_coeff()

class MeridianStrikesTalent(Talent):
    def apply(self, player, spell_book):
        if 'ToD' in spell_book.spells:
            tod = spell_book.spells['ToD']
            tod.base_cd = 45.0
            tod.add_modifier(self.name, 1.15)

class RisingStarTalent(Talent):
    def apply(self, player, spell_book):
        if 'RSK' in spell_book.spells:
            rsk = spell_book.spells['RSK']
            rsk.add_modifier(self.name, 1.15)
            rsk.crit_damage_bonus += 0.12

class HitComboTalent(Talent):
    def apply(self, player, spell_book):
        player.has_hit_combo = True

class BrawlerIntensityTalent(Talent):
    def apply(self, player, spell_book):
        if 'RSK' in spell_book.spells:
            spell_book.spells['RSK'].base_cd -= 1.0
        if 'BOK' in spell_book.spells:
            spell_book.spells['BOK'].add_modifier(self.name, 1.12)

# --- Row 6 ---

class JadeIgnitionTalent(Talent):
    def apply(self, player, spell_book):
        player.has_jade_ignition = True

class CyclonesDriftTalent(Talent):
    def apply(self, player, spell_book):
        player.has_cyclones_drift = True
        player.update_stats()

class CrashingStrikesTalent(Talent):
    def apply(self, player, spell_book):
        if 'FOF' in spell_book.spells:
            fof = spell_book.spells['FOF']
            fof.base_cast_time = 5.0
            fof.total_ticks = 6
            fof.update_tick_coeff()

class DrinkingHornCoverTalent(Talent):
    def apply(self, player, spell_book):
        player.has_drinking_horn_cover = True

class SpiritualFocusTalent(Talent):
    def apply(self, player, spell_book):
        if 'Zenith' in spell_book.spells:
            spell_book.spells['Zenith'].base_cd = 70.0

class ObsidianSpiralTalent(Talent):
    def apply(self, player, spell_book):
        player.has_obsidian_spiral = True

class ComboBreakerTalent(Talent):
    def apply(self, player, spell_book):
        player.has_combo_breaker = True

# --- Row 7 ---

class DanceOfChiJiTalent(Talent):
    def apply(self, player, spell_book):
        player.has_dance_of_chiji = True

class ShadowboxingTreadsTalent(Talent):
    def apply(self, player, spell_book):
        player.has_shadowboxing = True

class EnergyBurstTalent(Talent):
    def apply(self, player, spell_book):
        player.has_energy_burst = True

class InnerPeaceTalent(Talent):
    def apply(self, player, spell_book):
        player.max_energy += 30.0
        if player.energy > player.max_energy - 35.0:
             player.energy = player.max_energy

        if 'TP' in spell_book.spells:
            spell_book.spells['TP'].energy_cost = 45

# --- Rows 8 & 9 (New Talents) ---

class SequencedStrikesTalent(Talent):
    """8-2: Sequenced Strikes"""
    def apply(self, player, spell_book):
        player.has_sequenced_strikes = True

class SunfireSpiralTalent(Talent):
    """8-3: Sunfire Spiral (RSK Mastery +20%)"""
    def apply(self, player, spell_book):
        player.has_sunfire_spiral = True

class CommunionWithWindTalent(Talent):
    """8-4: Communion with Wind"""
    def apply(self, player, spell_book):
        player.has_communion_with_wind = True

class RevolvingWhirlTalent(Talent):
    """8-5 (Choice 1): Revolving Whirl"""
    def apply(self, player, spell_book):
        player.has_revolving_whirl = True

class EchoTechniqueTalent(Talent):
    """8-5 (Choice 2): Echo Technique"""
    def apply(self, player, spell_book):
        player.has_echo_technique = True

class UniversalEnergyTalent(Talent):
    """8-6: Universal Energy"""
    def apply(self, player, spell_book):
        player.has_universal_energy = True

class MemoryOfMonasteryTalent(Talent):
    """8-7: Memory of the Monastery"""
    def apply(self, player, spell_book):
        player.has_memory_of_monastery = True
        # TP damage +15% is handled in Spell logic or here.
        # Better handled in Spell.calculate_tick_damage via flag or just add modifier here?
        # The prompt says "TP Dmg +15%", "Proc 10%".
        # I added flag 'has_memory_of_monastery' and logic in SpellBook.

class RushingWindKickTalent(Talent):
    """9-2: Rushing Wind Kick"""
    def apply(self, player, spell_book):
        player.has_rushing_wind_kick = True

class XuensBattlegearTalent(Talent):
    """9-3: Xuen's Battlegear"""
    def apply(self, player, spell_book):
        player.has_xuens_battlegear = True

class ThunderfistTalent(Talent):
    """9-4: Thunderfist"""
    def apply(self, player, spell_book):
        player.has_thunderfist = True

class WeaponOfTheWindTalent(Talent):
    """9-5: Weapon of the Wind"""
    def apply(self, player, spell_book):
        player.has_weapon_of_wind = True

class KnowledgeBrokenTempleTalent(Talent):
    """9-6: Knowledge of the Broken Temple"""
    def apply(self, player, spell_book):
        player.has_knowledge_of_broken_temple = True
        player.max_totm_stacks = 8

class JadefireStompTalent(Talent):
    """9-8: Jadefire Stomp"""
    def apply(self, player, spell_book):
        player.has_jadefire_stomp = True


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

    # Row 8
    '8-1': PlaceholderTalent('Tiger Eye Brew'),
    '8-2': SequencedStrikesTalent('Sequenced Strikes'),
    '8-3': SunfireSpiralTalent('Sunfire Spiral'),
    '8-4': CommunionWithWindTalent('Communion with Wind'),
    '8-5': RevolvingWhirlTalent('Revolving Whirl'), # Default choice
    '8-5_b': EchoTechniqueTalent('Echo Technique'),
    '8-6': UniversalEnergyTalent('Universal Energy'),
    '8-7': MemoryOfMonasteryTalent('Memory of Monastery'),

    # Row 9
    '9-1': PlaceholderTalent('TEB Buff'),
    '9-2': RushingWindKickTalent('Rushing Wind Kick'),
    '9-3': XuensBattlegearTalent('Xuens Battlegear'),
    '9-4': ThunderfistTalent('Thunderfist'),
    '9-5': WeaponOfTheWindTalent('Weapon of Wind'),
    '9-6': KnowledgeBrokenTempleTalent('Knowledge of Broken Temple'),
    '9-7': UnlockSpellTalent('Slicing Winds', 'SW'),
    '9-8': JadefireStompTalent('Jadefire Stomp'),

    # Row 10
    '10-1': PlaceholderTalent('TEB Final'),
    '10-2': PlaceholderTalent('Skyfire Heel'),
    '10-3': PlaceholderTalent('Harmonic Combo'),
    '10-4': PlaceholderTalent('Flurry of Xuen'),
    '10-5': PlaceholderTalent('Martial Agility'),
    '10-6': PlaceholderTalent('Airborne Rhythm'),
    '10-7': PlaceholderTalent('Path of Jade'),

    # Shortcuts
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
