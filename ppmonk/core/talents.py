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
            if self.attr_name == 'damage_multiplier':
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

# --- Rows 8 & 9 ---

class SequencedStrikesTalent(Talent):
    def apply(self, player, spell_book):
        player.has_sequenced_strikes = True

class SunfireSpiralTalent(Talent):
    def apply(self, player, spell_book):
        player.has_sunfire_spiral = True

class CommunionWithWindTalent(Talent):
    def apply(self, player, spell_book):
        player.has_communion_with_wind = True

class RevolvingWhirlTalent(Talent):
    def apply(self, player, spell_book):
        player.has_revolving_whirl = True

class EchoTechniqueTalent(Talent):
    def apply(self, player, spell_book):
        player.has_echo_technique = True

class UniversalEnergyTalent(Talent):
    def apply(self, player, spell_book):
        player.has_universal_energy = True

class MemoryOfMonasteryTalent(Talent):
    def apply(self, player, spell_book):
        player.has_memory_of_monastery = True

class RushingWindKickTalent(Talent):
    def apply(self, player, spell_book):
        player.has_rushing_wind_kick = True

class XuensBattlegearTalent(Talent):
    def apply(self, player, spell_book):
        player.has_xuens_battlegear = True

class ThunderfistTalent(Talent):
    def apply(self, player, spell_book):
        player.has_thunderfist = True

class WeaponOfTheWindTalent(Talent):
    def apply(self, player, spell_book):
        player.has_weapon_of_wind = True

class KnowledgeBrokenTempleTalent(Talent):
    def apply(self, player, spell_book):
        player.has_knowledge_of_broken_temple = True
        player.max_totm_stacks = 8

class JadefireStompTalent(Talent):
    def apply(self, player, spell_book):
        player.has_jadefire_stomp = True

class TigereyeBrewTalent(Talent):
    def apply(self, player, spell_book):
        player.has_teb_stacking = True

class TigereyeBrewDamageTalent(Talent):
    def __init__(self, name, rank=2):
        super().__init__(name)
        self.rank = rank
    def apply(self, player, spell_book):
        player.teb_crit_dmg_bonus += 0.10 * self.rank

class SkyfireHeelTalent(Talent):
    def apply(self, player, spell_book):
        player.has_skyfire_heel = True

class HarmonicComboTalent(Talent):
    def apply(self, player, spell_book):
        if 'FOF' in spell_book.spells:
            fof = spell_book.spells['FOF']
            fof.add_modifier(self.name, 0.90)
            fof.chi_cost = 2

class FlurryOfXuenTalent(Talent):
    def apply(self, player, spell_book):
        player.has_flurry_of_xuen = True

class MartialAgilityTalent(Talent):
    def apply(self, player, spell_book):
        player.has_martial_agility = True

class AirborneRhythmTalent(Talent):
    def apply(self, player, spell_book):
        if 'SW' in spell_book.spells:
            sw = spell_book.spells['SW']
            sw.chi_gen = 2

class HurricanesVaultTalent(Talent):
    def apply(self, player, spell_book):
        if 'SW' in spell_book.spells:
            sw = spell_book.spells['SW']
            sw.chi_cost = 2
            sw.chi_gen = 0
            sw.add_modifier(self.name, 2.0)

class PathOfJadeTalent(Talent):
    def apply(self, player, spell_book):
        player.has_path_of_jade = True

class SingularlyFocusedJadeTalent(Talent):
    def apply(self, player, spell_book):
        player.has_singularly_focused_jade = True

# --- Shado-Pan Hero Talents ---

class PrideOfPandariaTalent(Talent):
    def apply(self, player, spell_book):
        player.has_pride_of_pandaria = True

class HighImpactTalent(Talent):
    def apply(self, player, spell_book):
        player.has_high_impact = True

class VeteransEyeTalent(Talent):
    def apply(self, player, spell_book):
        player.has_veterans_eye = True

class MartialPrecisionTalent(Talent):
    def apply(self, player, spell_book):
        player.armor_pen += 0.12

class ShadoOverTheBattlefieldTalent(Talent):
    def apply(self, player, spell_book):
        player.has_shado_over_battlefield = True

class OneVersusManyTalent(Talent):
    def apply(self, player, spell_book):
        player.has_one_versus_many = True
        if 'FOF' in spell_book.spells:
            spell_book.spells['FOF'].add_modifier(self.name, 1.20)

class StandReadyTalent(Talent):
    def apply(self, player, spell_book):
        player.has_stand_ready = True

class AgainstAllOddsTalent(Talent):
    def apply(self, player, spell_book):
        player.agility *= 1.04

class EfficientTrainingTalent(Talent):
    def apply(self, player, spell_book):
        if 'TP' in spell_book.spells:
            spell_book.spells['TP'].add_modifier(self.name, 1.20)
        if 'Zenith' in spell_book.spells:
            spell_book.spells['Zenith'].base_cd -= 10.0

class VigilantWatchTalent(Talent):
    def apply(self, player, spell_book):
        if 'BOK' in spell_book.spells:
            spell_book.spells['BOK'].crit_damage_bonus += 0.30

class WeaponsOfTheWallTalent(Talent):
    def apply(self, player, spell_book):
        player.has_weapons_of_the_wall = True

class WisdomOfTheWallTalent(Talent):
    def apply(self, player, spell_book):
        player.has_wisdom_of_the_wall = True

class ShadoPanBaseTalent(Talent):
    def apply(self, player, spell_book):
        player.has_shado_pan_base = True
        player.flurry_charges = 0
        # Automatically apply all non-choice passives for Shado-Pan
        VeteransEyeTalent('Auto').apply(player, spell_book)
        MartialPrecisionTalent('Auto').apply(player, spell_book)
        ShadoOverTheBattlefieldTalent('Auto').apply(player, spell_book)
        OneVersusManyTalent('Auto').apply(player, spell_book)
        StandReadyTalent('Auto').apply(player, spell_book)
        AgainstAllOddsTalent('Auto').apply(player, spell_book)
        EfficientTrainingTalent('Auto').apply(player, spell_book)
        VigilantWatchTalent('Auto').apply(player, spell_book)
        WeaponsOfTheWallTalent('Auto').apply(player, spell_book)
        WisdomOfTheWallTalent('Auto').apply(player, spell_book)


# --- Conduit of the Celestials (COTC) Hero Talents ---

class CelestialConduitTalent(Talent):
    def apply(self, player, spell_book):
        player.has_celestial_conduit = True
        if 'Conduit' in spell_book.spells:
            spell_book.spells['Conduit'].is_known = True

class XuensBondTalent(Talent):
    def apply(self, player, spell_book):
        player.has_xuens_bond = True

class HeartOfJadeSerpentTalent(Talent):
    def apply(self, player, spell_book):
        player.has_heart_of_jade_serpent = True

class StrengthOfBlackOxTalent(Talent):
    def apply(self, player, spell_book):
        player.has_strength_of_black_ox = True

class InnerCompassTalent(Talent):
    def apply(self, player, spell_book):
        player.has_inner_compass = True

class CourageOfWhiteTigerTalent(Talent):
    def apply(self, player, spell_book):
        player.has_courage_of_white_tiger = True

class XuensGuidanceTalent(Talent):
    def apply(self, player, spell_book):
        player.has_xuens_guidance = True

class TempleTrainingTalent(Talent):
    def apply(self, player, spell_book):
        player.has_temple_training = True
        if 'FOF' in spell_book.spells:
            spell_book.spells['FOF'].add_modifier(self.name, 1.10)
        if 'SCK' in spell_book.spells:
            spell_book.spells['SCK'].add_modifier(self.name, 1.10)

class RestoreBalanceTalent(Talent):
    def apply(self, player, spell_book):
        player.has_restore_balance = True

class PathOfFallingStarTalent(Talent):
    def apply(self, player, spell_book):
        player.has_path_of_falling_star = True

class UnityWithinTalent(Talent):
    def apply(self, player, spell_book):
        player.has_unity_within = True

class COTCBaseTalent(Talent):
    def apply(self, player, spell_book):
        player.has_cotc_base = True
        # Unlock Xuen features
        # Automatically apply all non-choice passives for COTC
        CelestialConduitTalent('Auto').apply(player, spell_book)
        HeartOfJadeSerpentTalent('Auto').apply(player, spell_book)
        StrengthOfBlackOxTalent('Auto').apply(player, spell_book)
        InnerCompassTalent('Auto').apply(player, spell_book)
        CourageOfWhiteTigerTalent('Auto').apply(player, spell_book)
        PathOfFallingStarTalent('Auto').apply(player, spell_book)
        UnityWithinTalent('Auto').apply(player, spell_book)

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
    '8-1': TigereyeBrewTalent('Tiger Eye Brew'),
    '8-2': SequencedStrikesTalent('Sequenced Strikes'),
    '8-3': SunfireSpiralTalent('Sunfire Spiral'),
    '8-4': CommunionWithWindTalent('Communion with Wind'),
    '8-5': RevolvingWhirlTalent('Revolving Whirl'),
    '8-5_b': EchoTechniqueTalent('Echo Technique'),
    '8-6': UniversalEnergyTalent('Universal Energy'),
    '8-7': MemoryOfMonasteryTalent('Memory of Monastery'),

    # Row 9
    '9-1': TigereyeBrewDamageTalent('TEB Damage'),
    '9-2': RushingWindKickTalent('Rushing Wind Kick'),
    '9-3': XuensBattlegearTalent('Xuens Battlegear'),
    '9-4': ThunderfistTalent('Thunderfist'),
    '9-5': WeaponOfTheWindTalent('Weapon of Wind'),
    '9-6': KnowledgeBrokenTempleTalent('Knowledge of Broken Temple'),
    '9-7': UnlockSpellTalent('Slicing Winds', 'SW'),
    '9-8': JadefireStompTalent('Jadefire Stomp'),

    # Row 10
    '10-1': PlaceholderTalent('TEB Final'),
    '10-2': SkyfireHeelTalent('Skyfire Heel'),
    '10-3': HarmonicComboTalent('Harmonic Combo'),
    '10-4': FlurryOfXuenTalent('Flurry of Xuen'),
    '10-5': MartialAgilityTalent('Martial Agility'),
    '10-6': AirborneRhythmTalent('Airborne Rhythm'),
    '10-6_b': HurricanesVaultTalent('Hurricane\'s Vault'),
    '10-7': PathOfJadeTalent('Path of Jade'),
    '10-7_b': SingularlyFocusedJadeTalent('Singularly Focused Jade'),

    # Shado-Pan (Hero Talents)
    'ShadoPanBase': ShadoPanBaseTalent('Shado-Pan'),
    'PrideOfPandaria': PrideOfPandariaTalent('Pride of Pandaria'),
    'HighImpact': HighImpactTalent('High Impact'),
    # Individual passives kept for reference, but applied by Base now
    'VeteransEye': VeteransEyeTalent('Veterans Eye'),
    'MartialPrecision': MartialPrecisionTalent('Martial Precision'),
    'ShadoOverTheBattlefield': ShadoOverTheBattlefieldTalent('Shado Over the Battlefield'),
    'OneVersusMany': OneVersusManyTalent('One Versus Many'),
    'StandReady': StandReadyTalent('Stand Ready'),
    'AgainstAllOdds': AgainstAllOddsTalent('Against All Odds'),
    'EfficientTraining': EfficientTrainingTalent('Efficient Training'),
    'VigilantWatch': VigilantWatchTalent('Vigilant Watch'),
    'WeaponsOfTheWall': WeaponsOfTheWallTalent('Weapons of the Wall'),
    'WisdomOfTheWall': WisdomOfTheWallTalent('Wisdom of the Wall'),

    # Conduit of the Celestials (COTC Hero Talents)
    'COTCBase': COTCBaseTalent('Conduit of the Celestials (Base)'),
    'CelestialConduit': CelestialConduitTalent('Celestial Conduit'),
    'XuensBond': XuensBondTalent('Xuen\'s Bond'),
    'HeartOfJadeSerpent': HeartOfJadeSerpentTalent('Heart of the Jade Serpent'),
    'StrengthOfBlackOx': StrengthOfBlackOxTalent('Strength of the Black Ox'),
    'InnerCompass': InnerCompassTalent('Inner Compass'),
    'CourageOfWhiteTiger': CourageOfWhiteTigerTalent('Courage of the White Tiger'),
    'XuensGuidance': XuensGuidanceTalent('Xuen\'s Guidance'),
    'TempleTraining': TempleTrainingTalent('Temple Training'),
    'RestoreBalance': RestoreBalanceTalent('Restore Balance'),
    'PathOfFallingStar': PathOfFallingStarTalent('Path of the Falling Star'),
    'UnityWithin': UnityWithinTalent('Unity Within'),

    # Shortcuts
    'WDP': UnlockSpellTalent('Whirling Dragon Punch', 'WDP'),
    'SW': UnlockSpellTalent('Slicing Winds', 'SW'),
    'SOTWL': UnlockSpellTalent('Strike of the Windlord', 'SOTWL'),
    'Ascension': AscensionTalent('Ascension'),
    'hero-sp-header': ShadoPanBaseTalent('Shado-Pan'),
    'hero-cotc-header': COTCBaseTalent('Conduit of the Celestials (Base)')
}

class TalentManager:
    def apply_talents(self, talent_ids, player, spell_book):
        for tid in talent_ids:
            if tid in TALENT_DB:
                TALENT_DB[tid].apply(player, spell_book)
