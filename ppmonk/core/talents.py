class Talent:
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
    def __init__(self, name, stat_name, value, is_percentage=False):
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
                if self.is_percentage:
                    setattr(spell, self.attr_name, base * (1.0 + self.value))
                else:
                    setattr(spell, self.attr_name, base + self.value)
                if self.attr_name == 'ap_coeff':
                    spell.update_tick_coeff()


# --- 新天赋实现 ---
class SharpReflexesTalent(Talent):
    def apply(self, player, spell_book):
        player.has_sharp_reflexes = True


class FerociousnessTalent(Talent):
    def __init__(self, name, rank=1):
        super().__init__(name)
        self.rank = max(1, min(rank, 2)) if rank is not None else 1

    def apply(self, player, spell_book):
        player.ferociousness_rank = max(getattr(player, 'ferociousness_rank', 0), self.rank)
        player.update_stats()


class HardenedSolesTalent(Talent):
    def __init__(self, name, rank=1):
        super().__init__(name)
        self.rank = max(1, min(rank, 2)) if rank is not None else 1

    def apply(self, player, spell_book):
        if 'BOK' not in spell_book.spells:
            return
        bok = spell_book.spells['BOK']
        crit_bonus = 0.06 if self.rank == 1 else 0.12
        dmg_bonus = 0.10 if self.rank == 1 else 0.20
        bok.bonus_crit_chance = max(getattr(bok, 'bonus_crit_chance', 0.0), crit_bonus)
        bok.crit_damage_bonus = max(getattr(bok, 'crit_damage_bonus', 0.0), dmg_bonus)


class AscensionTalent(Talent):
    def apply(self, player, spell_book):
        player.max_energy += 20.0
        player.energy = min(player.energy, player.max_energy)
        player.max_chi += 1
        player.chi = min(player.chi, player.max_chi)
        player.energy_regen_mult *= 1.10


class TouchOfTheTigerTalent(Talent):
    def apply(self, player, spell_book):
        if 'TP' in spell_book.spells:
            tp = spell_book.spells['TP']
            tp.ap_coeff *= 1.15
            tp.update_tick_coeff()


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


# --- TALENT_DB (含 Choice Node 映射) ---
TALENT_DB = {
    # Row 1
    '1-1': lambda rank=None: UnlockSpellTalent('Fists of Fury', 'FOF'),

    # Row 2
    '2-1': lambda rank=None: MomentumBoostTalent('Momentum Boost'),
    '2-2': lambda rank=None: CombatWisdomTalent('Combat Wisdom'),
    '2-3': lambda rank=None: SharpReflexesTalent('Sharp Reflexes'),

    # Row 3
    '3-1': lambda rank=None: TouchOfTheTigerTalent('Touch of the Tiger'),
    '3-2': lambda rank=None: FerociousnessTalent('Ferociousness', rank=rank or 1),
    '3-3': lambda rank=None: HardenedSolesTalent('Hardened Soles', rank=rank or 1),
    '3-4': lambda rank=None: AscensionTalent('Ascension'),

    # Row 4
    '4-1': lambda rank=None: PlaceholderTalent('Dual Threat'),
    '4-2': lambda rank=None: PlaceholderTalent('Teachings of the Monastery'),
    '4-3': lambda rank=None: PlaceholderTalent('Glory of the Dawn'),

    # Row 5
    '5-1': lambda rank=None: PlaceholderTalent('Crane Vortex'),
    '5-2': lambda rank=None: PlaceholderTalent('Meridian Strikes'),
    '5-3': lambda rank=None: PlaceholderTalent('Rising Star'),
    '5-4': lambda rank=None: PlaceholderTalent('Zenith'),
    '5-5': lambda rank=None: PlaceholderTalent('Hit Combo'),
    '5-6': lambda rank=None: PlaceholderTalent('Brawler Intensity'),

    # Row 6 (Choice Nodes)
    '6-1': lambda rank=None: PlaceholderTalent('Jade Ignition'),
    '6-2': lambda rank=None: PlaceholderTalent('Cyclone Drift'),
    '6-2_b': lambda rank=None: PlaceholderTalent('Crashing Fists'),

    '6-3': lambda rank=None: PlaceholderTalent('Spiritual Focus'),
    '6-3_b': lambda rank=None: PlaceholderTalent('Drinking Horn Cover'),

    '6-4': lambda rank=None: PlaceholderTalent('Obsidian Spiral'),
    '6-5': lambda rank=None: PlaceholderTalent('Combo Breaker'),

    # Row 7 (Choice Nodes)
    '7-1': lambda rank=None: PlaceholderTalent('Dance of Chi-Ji'),
    '7-2': lambda rank=None: PlaceholderTalent('Shadowboxing Treads'),

    # [重点] WDP vs SOTWL
    '7-3': lambda rank=None: UnlockSpellTalent('Whirling Dragon Punch', 'WDP'),
    '7-3_b': lambda rank=None: UnlockSpellTalent('Strike of the Windlord', 'SOTWL'),

    '7-4': lambda rank=None: PlaceholderTalent('Energy Burst'),
    '7-5': lambda rank=None: PlaceholderTalent('Inner Peace'),

    # Row 8 (Choice Nodes)
    '8-1': lambda rank=None: PlaceholderTalent('Tiger Eye Brew'),
    '8-2': lambda rank=None: PlaceholderTalent('Sequenced Strikes'),
    '8-3': lambda rank=None: PlaceholderTalent('Sunfire Spiral'),
    '8-4': lambda rank=None: PlaceholderTalent('Communion with Wind'),

    '8-5': lambda rank=None: PlaceholderTalent('Echo Technique'),
    '8-5_b': lambda rank=None: PlaceholderTalent('Revolving Whirl'),

    '8-6': lambda rank=None: PlaceholderTalent('Universal Energy'),
    '8-7': lambda rank=None: PlaceholderTalent('Memory of Monastery'),

    # Row 9
    '9-1': lambda rank=None: PlaceholderTalent('TEB Buff'),
    '9-2': lambda rank=None: PlaceholderTalent('Rushing Jade Wind'),
    '9-3': lambda rank=None: PlaceholderTalent('Xuens Battlegear'),
    '9-4': lambda rank=None: PlaceholderTalent('Thunderfist'),
    '9-5': lambda rank=None: PlaceholderTalent('Weapon of Wind'),
    '9-6': lambda rank=None: PlaceholderTalent('Knowledge'),
    '9-7': lambda rank=None: UnlockSpellTalent('Slicing Winds', 'SW'),
    '9-8': lambda rank=None: PlaceholderTalent('Jadefire Stomp'),

    # Row 10 (Choice Nodes)
    '10-1': lambda rank=None: PlaceholderTalent('TEB Final'),
    '10-2': lambda rank=None: PlaceholderTalent('Skyfire Heel'),
    '10-3': lambda rank=None: PlaceholderTalent('Harmonic Combo'),
    '10-4': lambda rank=None: PlaceholderTalent('Flurry of Xuen'),
    '10-5': lambda rank=None: PlaceholderTalent('Martial Agility'),

    '10-6': lambda rank=None: PlaceholderTalent('Airborne Rhythm'),
    '10-6_b': lambda rank=None: PlaceholderTalent('Hurricane Vault'),

    '10-7': lambda rank=None: PlaceholderTalent('Path of Jade'),
    '10-7_b': lambda rank=None: PlaceholderTalent('Singularly Focused'),

    # Legacy
    'WDP': lambda rank=None: UnlockSpellTalent('Whirling Dragon Punch', 'WDP'),
    'SW': lambda rank=None: UnlockSpellTalent('Slicing Winds', 'SW'),
    'SOTWL': lambda rank=None: UnlockSpellTalent('Strike of the Windlord', 'SOTWL'),
}


class TalentManager:
    def apply_talents(self, talent_ids, player, spell_book):
        for tid in talent_ids:
            rank = None
            talent_key = tid
            if isinstance(tid, (list, tuple)) and len(tid) == 2:
                talent_key, rank = tid
            talent_factory = TALENT_DB.get(talent_key)
            if talent_factory:
                talent = talent_factory(rank=rank)
                talent.apply(player, spell_book)
