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

# --- 核心机制天赋 ---
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

class PlaceholderTalent(Talent):
    def apply(self, player, spell_book): pass

# --- 天赋数据库 ---
TALENT_DB = {
    # [必须] 这是解锁 FOF 的唯一钥匙
    '1-1': UnlockSpellTalent('Fists of Fury', 'FOF'),

    # 机制天赋
    '2-1': MomentumBoostTalent('Momentum Boost'),
    '2-2': CombatWisdomTalent('Combat Wisdom'),
    '2-3': PlaceholderTalent('Sharp Reflexes'),

    # 占位符 (保持结构完整)
    '3-1': PlaceholderTalent('Touch of the Tiger'),
    '3-2': PlaceholderTalent('Ferociousness'),
    '3-3': PlaceholderTalent('Hardened Soles'),
    '3-4': StatModTalent('Ascension', 'max_energy', 20.0),
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
    '9-2': PlaceholderTalent('RJW'),
    '9-3': PlaceholderTalent('Xuens Battlegear'),
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

    # 兼容旧代码
    'WDP': UnlockSpellTalent('Whirling Dragon Punch', 'WDP'),
    'SW': UnlockSpellTalent('Slicing Winds', 'SW'),
    'SOTWL': UnlockSpellTalent('Strike of the Windlord', 'SOTWL'),
    'Ascension': StatModTalent('Ascension', 'max_energy', 20.0),
}

class TalentManager:
    def apply_talents(self, talent_names, player, spell_book):
        for name in talent_names:
            if name in TALENT_DB:
                TALENT_DB[name].apply(player, spell_book)