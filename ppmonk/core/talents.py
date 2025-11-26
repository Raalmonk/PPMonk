class Talent:
    """天赋基类"""
    def __init__(self, name):
        self.name = name

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

class TouchOfTheTigerTalent(Talent):
    def apply(self, player, spell_book):
        if 'TP' in spell_book.spells:
            spell_book.spells['TP'].damage_multiplier *= 1.15

# --- Row 4 (新实装天赋) ---

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

class PlaceholderTalent(Talent):
    def apply(self, player, spell_book): pass

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

    # Row 4 (已实装)
    '4-1': DualThreatTalent('Dual Threat'),
    '4-2': TeachingsOfTheMonasteryTalent('Teachings of the Monastery'),
    '4-3': GloryOfTheDawnTalent('Glory of the Dawn'),

    # Row 5 - 10 (占位符)
    '5-1': PlaceholderTalent('Crane Vortex'),
    '5-2': PlaceholderTalent('Meridian Strikes'),
    '5-3': PlaceholderTalent('Rising Star'),
    '5-4': UnlockSpellTalent('Zenith', 'Zenith'),
    '5-5': PlaceholderTalent('Hit Combo'),
    '5-6': PlaceholderTalent('Brawler Intensity'),
    '6-1': PlaceholderTalent('Jade Ignition'),
    '6-2': PlaceholderTalent('Cyclone Choice'),
    '6-3': PlaceholderTalent('Horn Choice'),
    '6-4': PlaceholderTalent('Obsidian Spiral'),
    '6-5': PlaceholderTalent('Combo Breaker'),
    '7-1': PlaceholderTalent('Dance of Chi-Ji'),
    '7-2': PlaceholderTalent('Shadowboxing Treads'),
    '7-3': UnlockSpellTalent('Whirling Dragon Punch', 'WDP'),
    '7-4': PlaceholderTalent('Energy Burst'),
    '7-5': PlaceholderTalent('Inner Peace'),
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

    # 兼容旧 ID
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