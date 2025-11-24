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
            base_val = getattr(player, self.stat_name)
            if self.is_percentage: setattr(player, self.stat_name, base_val * (1.0 + self.value))
            else: setattr(player, self.stat_name, base_val + self.value)

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
                base_val = getattr(spell, self.attr_name)
                if self.is_percentage: setattr(spell, self.attr_name, base_val * (1.0 + self.value))
                else: setattr(spell, self.attr_name, base_val + self.value)
                if self.attr_name == 'ap_coeff': spell.update_tick_coeff()

# [新增] 特殊天赋类
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
        if not hasattr(player, 'talents_procs'):
            player.talents_procs = {}
        pass


class PlaceholderTalent(Talent):
    def apply(self, player, spell_book):
        # Placeholder for yet-to-be-implemented talent effects
        pass

# --- 天赋数据库 ---
TALENT_DB = {
    # --- 第一层 ---
    # 关键：1-1 必须解锁 FOF，否则你永远放不出来
    '1-1': UnlockSpellTalent('Fists of Fury', 'FOF'),

    # --- 第二层 ---
    '2-1': MomentumBoostTalent('Momentum Boost'),
    '2-2': CombatWisdomTalent('Combat Wisdom'),
    '2-3': SharpReflexesTalent('Sharp Reflexes'),

    # Row 3
    '3-1': PlaceholderTalent('Touch of the Tiger'),
    '3-2': PlaceholderTalent('Ferociousness'),  # Rank 2 logic handled internally?
    '3-3': PlaceholderTalent('Hardened Soles'),
    '3-4': StatModTalent('Ascension', 'max_energy', 20.0),

    # Row 4
    '4-1': PlaceholderTalent('Dual Threat'),
    '4-2': PlaceholderTalent('Teachings of the Monastery'),  # TOTM usually buffs blackout kick
    '4-3': PlaceholderTalent('Glory of the Dawn'),

    # Row 5
    '5-1': PlaceholderTalent('Crane Vortex'),
    '5-2': PlaceholderTalent('Meridian Strikes'),
    '5-3': PlaceholderTalent('Rising Star'),  # Usually buffs RSK
    '5-4': PlaceholderTalent('Zenith'),
    '5-5': PlaceholderTalent('Hit Combo'),  # Needs buff tracking logic
    '5-6': PlaceholderTalent('Brawler Intensity'),

    # Row 6
    '6-1': PlaceholderTalent('Jade Ignition'),
    '6-2': PlaceholderTalent('Cyclone/Crashing Choice'),
    '6-3': PlaceholderTalent('Horn/Focus Choice'),
    '6-4': PlaceholderTalent('Obsidian Spiral'),
    '6-5': PlaceholderTalent('Combo Breaker'),

    # Row 7
    '7-1': PlaceholderTalent('Dance of Chi-Ji'),
    '7-2': PlaceholderTalent('Shadowboxing Treads'),
    # 7-3 是核心二选一: WDP 或 SOTWL. 
    # UI 上这是一个节点，逻辑上我们暂且让它解锁 WDP (或者你需要更复杂的 Choice 逻辑)
    # 临时方案：解锁 WDP 和 SOTWL 两个，或者默认给 WDP。
    '7-3': UnlockSpellTalent('Whirling Dragon Punch', 'WDP'),
    '7-4': PlaceholderTalent('Energy Burst'),
    '7-5': PlaceholderTalent('Inner Peace'),

    # Row 8
    '8-1': PlaceholderTalent('Tiger Eye Brew Base'),
    '8-2': PlaceholderTalent('Sequenced Strikes'),
    '8-3': PlaceholderTalent('Sunfire Spiral'),
    '8-4': PlaceholderTalent('Communion with Wind'),
    '8-5': PlaceholderTalent('Revolving/Echo Choice'),
    '8-6': PlaceholderTalent('Universal Energy'),
    '8-7': PlaceholderTalent('Memory of Monastery'),

    # Row 9
    '9-1': PlaceholderTalent('Tiger Eye Buff'),
    '9-2': PlaceholderTalent('Rushing Jade Wind'),
    '9-3': PlaceholderTalent('Xuens Battlegear'),
    '9-4': PlaceholderTalent('Thunderfist'),
    '9-5': PlaceholderTalent('Weapon of Wind'),
    '9-6': PlaceholderTalent('Knowl. Broken Temple'),
    '9-7': UnlockSpellTalent('Slicing Winds', 'SW'),
    '9-8': PlaceholderTalent('Jadefire Stomp'),

    # Row 10
    '10-1': PlaceholderTalent('TEB Final'),
    '10-2': PlaceholderTalent('Skyfire Heel'),
    '10-3': PlaceholderTalent('Harmonic Combo'),
    '10-4': PlaceholderTalent('Flurry of Xuen'),
    '10-5': PlaceholderTalent('Martial Agility'),
    '10-6': PlaceholderTalent('Airborne Rhythm'),
    '10-7': PlaceholderTalent('Path of Jade'),

    # --- 原有保留 (如果 UI 还在传这些旧 ID) ---
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
