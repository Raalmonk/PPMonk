class Talent:
    def __init__(self, name): self.name = name
    def apply(self, player, spell_book): pass

class UnlockSpellTalent(Talent):
    def __init__(self, name, spell_abbr):
        super().__init__(name)
        self.spell_abbr = spell_abbr
    def apply(self, player, spell_book):
        if self.spell_abbr in spell_book.spells:
            spell_book.spells[self.spell_abbr].is_known = True

class StatModTalent(Talent):
    def __init__(self, name, stat_name, value, is_percentage=False):
        super().__init__(name)
        self.stat_name = stat_name
        self.value = value
        self.is_percentage = is_percentage
    def apply(self, player, spell_book):
        if hasattr(player, self.stat_name):
            base = getattr(player, self.stat_name)
            if self.is_percentage: setattr(player, self.stat_name, base * (1.0 + self.value))
            else: setattr(player, self.stat_name, base + self.value)

class SpellModTalent(Talent):
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
                base = getattr(spell, self.attr_name)
                if self.is_percentage: setattr(spell, self.attr_name, base * (1.0 + self.value))
                else: setattr(spell, self.attr_name, base + self.value)
                if self.attr_name == 'ap_coeff': spell.update_tick_coeff()

# --- 核心天赋实现 ---

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

# [新] Sharp Reflexes: 幻灭踢减CD
class SharpReflexesTalent(Talent):
    def apply(self, player, spell_book):
        if 'BOK' in spell_book.spells:
            # 标记 BOK 拥有触发能力
            spell_book.spells['BOK'].triggers_sharp_reflexes = True

# [新] Ferociousness: 暴击加成 (Rank支持在构造函数处理，这里简化为 Rank 1/2 逻辑)
class FerociousnessTalent(Talent):
    def __init__(self, name, rank=1):
        super().__init__(name)
        self.rank = rank
    def apply(self, player, spell_book):
        # Rank 1: +2%, Rank 2: +4%
        bonus = 0.02 * self.rank
        player.talent_crit_bonus += bonus
        player.update_stats()

# [新] Hardened Soles: BOK 暴击/爆伤
class HardenedSolesTalent(Talent):
    def __init__(self, name, rank=1):
        super().__init__(name)
        self.rank = rank
    def apply(self, player, spell_book):
        if 'BOK' in spell_book.spells:
            bok = spell_book.spells['BOK']
            # Rank 1: +6% Crit, +10% Dmg
            # Rank 2: +12% Crit, +20% Dmg
            bok.bonus_crit_chance += 0.06 * self.rank
            bok.crit_damage_bonus += 0.10 * self.rank

# [新] Ascension: 能量/真气/回复
class AscensionTalent(Talent):
    def apply(self, player, spell_book):
        player.max_energy += 20.0
        player.max_chi += 1 # 变成 7 气
        player.energy_regen_mult *= 1.10 # +10% regen

# [新] Touch of the Tiger: TP 增伤
class TouchOfTheTigerTalent(Talent):
    def apply(self, player, spell_book):
        if 'TP' in spell_book.spells:
            # +15% 伤害 (multiplier * 1.15)
            spell_book.spells['TP'].damage_multiplier *= 1.15

class PlaceholderTalent(Talent):
    def apply(self, player, spell_book): pass

# --- 数据库 ---
TALENT_DB = {
    '1-1': UnlockSpellTalent('Fists of Fury', 'FOF'),

    '2-1': MomentumBoostTalent('Momentum Boost'),
    '2-2': CombatWisdomTalent('Combat Wisdom'),
    '2-3': SharpReflexesTalent('Sharp Reflexes'),

    '3-1': TouchOfTheTigerTalent('Touch of the Tiger'),
    '3-2': FerociousnessTalent('Ferociousness', rank=2), # 假设默认满级，或根据 rank 参数调整
    '3-3': HardenedSolesTalent('Hardened Soles', rank=2), # 假设默认满级
    '3-4': AscensionTalent('Ascension'),

    '4-1': PlaceholderTalent('Dual Threat'),
    '4-2': PlaceholderTalent('Teachings of the Monastery'),
    '4-3': PlaceholderTalent('Glory of the Dawn'),
    '5-1': PlaceholderTalent('Crane Vortex'),
    '5-2': PlaceholderTalent('Meridian Strikes'),
    '5-3': PlaceholderTalent('Rising Star'),
    '5-4': PlaceholderTalent('Zenith'),
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
    '9-3': UnlockSpellTalent('Invoke Xuen', 'Xuen'), # [新] 9-3 解锁雪怒
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
    def apply_talents(self, talent_names, player, spell_book):
        for name in talent_names:
            if name in TALENT_DB:
                TALENT_DB[name].apply(player, spell_book)