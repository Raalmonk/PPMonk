class Talent:
    """天赋基类"""

    def __init__(self, name):
        self.name = name

    def apply(self, player, spell_book):
        """应用天赋效果"""
        pass


class UnlockSpellTalent(Talent):
    """主动天赋：解锁某个技能"""

    def __init__(self, name, spell_abbr):
        super().__init__(name)
        self.spell_abbr = spell_abbr

    def apply(self, player, spell_book):
        if self.spell_abbr in spell_book.spells:
            # 将技能标记为已学会
            spell_book.spells[self.spell_abbr].is_known = True


class StatModTalent(Talent):
    """被动天赋：修改玩家属性 (如能量上限、回复速度)"""

    def __init__(self, name, stat_name, value, is_percentage=False):
        super().__init__(name)
        self.stat_name = stat_name
        self.value = value
        self.is_percentage = is_percentage

    def apply(self, player, spell_book):
        if hasattr(player, self.stat_name):
            base_val = getattr(player, self.stat_name)
            if self.is_percentage:
                # 例如：回复速度 * 1.1
                setattr(player, self.stat_name, base_val * (1.0 + self.value))
            else:
                # 例如：能量上限 + 20
                setattr(player, self.stat_name, base_val + self.value)


class SpellModTalent(Talent):
    """被动天赋：修改技能属性 (如伤害系数、冷却时间)"""

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

                # 如果修改了 AP 系数，重新计算单跳伤害
                if self.attr_name == 'ap_coeff':
                    spell.update_tick_coeff()


# --- 天赋数据库 ---
TALENT_DB = {
    # 主动技能
    'WDP': UnlockSpellTalent('Whirling Dragon Punch', 'WDP'),
    'SW': UnlockSpellTalent('Slicing Winds', 'SW'),
    'SOTWL': UnlockSpellTalent('Strike of the Windlord', 'SOTWL'),

    # 被动天赋
    'Ascension': StatModTalent('Ascension', 'max_energy', 20.0),
    'Ascension_Regen': StatModTalent('Ascension', 'energy_regen_mult', 0.1, is_percentage=True),
    'Improved_RSK': SpellModTalent('Improved_RSK', 'RSK', 'ap_coeff', 0.1, is_percentage=True),
}


class TalentManager:
    def apply_talents(self, talent_names, player, spell_book):
        for name in talent_names:
            if name == 'Ascension':
                TALENT_DB['Ascension'].apply(player, spell_book)
                TALENT_DB['Ascension_Regen'].apply(player, spell_book)
            elif name in TALENT_DB:
                TALENT_DB[name].apply(player, spell_book)
