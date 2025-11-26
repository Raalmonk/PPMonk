import random
from .talents import TalentManager


class Spell:
    def __init__(self, abbr, ap_coeff, energy=0, chi_cost=0, chi_gen=0, cd=0, cd_haste=False,
                 cast_time=0, cast_haste=False, is_channeled=False, ticks=1, req_talent=False, gcd_override=None):
        self.abbr = abbr
        self.ap_coeff = ap_coeff
        self.energy_cost = energy
        self.chi_cost = chi_cost
        self.chi_gen = chi_gen
        self.base_cd = cd
        self.cd_haste = cd_haste
        self.base_cast_time = cast_time
        self.cast_haste = cast_haste
        self.is_channeled = is_channeled
        self.total_ticks = ticks
        self.tick_coeff = ap_coeff / ticks if ticks > 0 else ap_coeff
        self.req_talent = req_talent
        self.gcd_override = gcd_override
        self.is_known = not req_talent
        self.current_cd = 0.0
        self.is_combo_strike = True

        # 机制属性
        self.haste_dmg_scaling = False
        self.tick_dmg_ramp = 0.0
        self.triggers_combat_wisdom = False
        self.triggers_sharp_reflexes = False

        # 伤害/暴击修正
        self.damage_multiplier = 1.0
        self.bonus_crit_chance = 0.0
        self.crit_damage_bonus = 0.0

    def update_tick_coeff(self):
        self.tick_coeff = self.ap_coeff / self.total_ticks if self.total_ticks > 0 else self.ap_coeff

    def get_effective_cd(self, player):
        if self.cd_haste: return self.base_cd / (1.0 + player.haste)
        return self.base_cd

    def get_effective_cast_time(self, player):
        if self.cast_haste: return self.base_cast_time / (1.0 + player.haste)
        return self.base_cast_time

    def get_tick_interval(self, player):
        if not self.is_channeled or self.total_ticks <= 0: return 0
        return self.get_effective_cast_time(player) / self.total_ticks

    def is_usable(self, player, other_spells=None):
        if not self.is_known: return False
        if self.current_cd > 0.01: return False
        if player.energy < self.energy_cost: return False
        if player.chi < self.chi_cost: return False
        return True

    def cast(self, player, other_spells=None, damage_meter=None):
        player.energy -= self.energy_cost
        player.chi = max(0, player.chi - self.chi_cost)
        player.chi = min(player.max_chi, player.chi + self.chi_gen)
        self.current_cd = self.get_effective_cd(player)

        if self.gcd_override is not None:
            player.gcd_remaining = self.gcd_override
        else:
            player.gcd_remaining = 1.0

        # 1. Sharp Reflexes
        if self.triggers_sharp_reflexes and other_spells:
            if 'RSK' in other_spells:
                other_spells['RSK'].current_cd = max(0, other_spells['RSK'].current_cd - 1.0)
            if 'FOF' in other_spells:
                other_spells['FOF'].current_cd = max(0, other_spells['FOF'].current_cd - 1.0)

        # 2. Teachings of the Monastery
        if self.abbr == 'TP' and player.has_totm:
            player.totm_stacks = min(4, player.totm_stacks + 1)

        extra_damage = 0.0

        if self.abbr == 'BOK' and player.has_totm:
            if player.totm_stacks > 0:
                extra_hits = player.totm_stacks
                dmg_per_hit = 0.847 * player.attack_power
                is_crit = random.random() < (player.crit + self.bonus_crit_chance)
                crit_m = (2.0 + self.crit_damage_bonus) if is_crit else 1.0
                total_extra = extra_hits * dmg_per_hit * (1 + player.versatility) * crit_m
                extra_damage += total_extra

                if damage_meter is not None:
                    damage_meter['TotM'] = damage_meter.get('TotM', 0) + total_extra

                player.totm_stacks = 0

            if random.random() < 0.12 and other_spells and 'RSK' in other_spells:
                other_spells['RSK'].current_cd = 0.0

        # 3. Glory of the Dawn
        if self.abbr == 'RSK' and player.has_glory_of_the_dawn:
            if random.random() < player.haste:
                glory_dmg = 1.0 * player.attack_power
                is_crit = random.random() < (player.crit + self.bonus_crit_chance)
                crit_m = (2.0 + self.crit_damage_bonus) if is_crit else 1.0
                final_glory = glory_dmg * (1 + player.versatility) * crit_m
                extra_damage += final_glory
                player.chi = min(player.max_chi, player.chi + 1)
                if damage_meter is not None:
                    damage_meter['Glory of Dawn'] = damage_meter.get('Glory of Dawn', 0) + final_glory

        # 4. Zenith (特质实装)
        # 效果: 1000% AP 自然伤害 AOE
        if self.abbr == 'Zenith':
            zenith_dmg = 10.0 * player.attack_power
            # 自然伤害不享受物理易伤(Balanced Stratagem), 但享受 Ferocity of Xuen
            # 假设基础面板已包含 Ferocity of Xuen
            final_zenith = zenith_dmg * (1.0 + player.versatility) * (2.0 if random.random() < player.crit else 1.0)
            extra_damage += final_zenith
            if damage_meter is not None:
                damage_meter['Zenith (Blast)'] = damage_meter.get('Zenith (Blast)', 0) + final_zenith

        # 雪怒 & Combat Wisdom
        if self.abbr == 'Xuen':
            player.xuen_active = True
            player.xuen_duration = 24.0
            player.update_stats()

        if self.triggers_combat_wisdom and getattr(player, 'combat_wisdom_ready', False):
            player.combat_wisdom_ready = False
            player.combat_wisdom_timer = 15.0
            eh_base = 1.2 * player.attack_power
            # [实装] Strength of Spirit: EH 暴击 +15%
            eh_crit_chance = player.crit + 0.15
            is_crit_eh = random.random() < eh_crit_chance
            eh_dmg = eh_base * (1.0 + player.versatility) * (2.0 if is_crit_eh else 1.0)
            extra_damage += eh_dmg

        triggers_mastery = self.is_combo_strike and (player.last_spell_name is not None) and (
                    player.last_spell_name != self.abbr)
        player.last_spell_name = self.abbr

        if self.is_channeled:
            cast_t = self.get_effective_cast_time(player)
            player.is_channeling = True
            player.current_channel_spell = self
            player.channel_time_remaining = cast_t
            player.channel_ticks_remaining = self.total_ticks
            player.channel_tick_interval = self.get_tick_interval(player)
            player.time_until_next_tick = player.channel_tick_interval
            player.channel_mastery_snapshot = triggers_mastery
            return 0.0
        else:
            base_dmg = self.calculate_tick_damage(player, mastery_override=triggers_mastery)
            if extra_damage > 0: base_dmg *= 1.30  # Combat Wisdom 仅增幅 TP
            return base_dmg + extra_damage

    def calculate_tick_damage(self, player, mastery_override=None, tick_idx=0):
        dmg = self.tick_coeff * self.damage_multiplier

        # [实装] Base Traits 硬编码
        # Fast Feet: RSK +70%, SCK +10%
        if self.abbr == 'RSK': dmg *= 1.70
        if self.abbr == 'SCK': dmg *= 1.10

        # Ferocity of Xuen: 全局 +4%
        dmg *= 1.04

        # Balanced Stratagem: 物理伤害 +4% (绝大部分技能是物理)
        if self.abbr in ['TP', 'BOK', 'RSK', 'SCK', 'FOF', 'WDP', 'SOTWL']:
            dmg *= 1.04

        if self.haste_dmg_scaling: dmg *= (1.0 + player.haste)
        if self.tick_dmg_ramp > 0: dmg *= (1.0 + (tick_idx + 1) * self.tick_dmg_ramp)

        apply_mastery = False
        if mastery_override is not None:
            apply_mastery = mastery_override
        elif self.is_channeled:
            apply_mastery = player.channel_mastery_snapshot

        if apply_mastery: dmg *= (1.0 + player.mastery)
        dmg *= (1.0 + player.versatility)

        eff_crit = min(1.0, player.crit + self.bonus_crit_chance)
        crit_mult = 2.0 + self.crit_damage_bonus
        dmg *= (1.0 + eff_crit * (crit_mult - 1.0))

        return dmg

    def tick_cd(self, dt):
        if self.current_cd > 0: self.current_cd = max(0, self.current_cd - dt)


class SpellWDP(Spell):
    def is_usable(self, player, other_spells):
        if not super().is_usable(player): return False
        rsk = other_spells['RSK'];
        fof = other_spells['FOF']
        return rsk.current_cd > 0 and fof.current_cd > 0


class SpellBook:
    def __init__(self, active_talents=None, talents=None):
        if active_talents is not None and talents is not None:
            merged = list(dict.fromkeys([*active_talents, *talents]))
            active_talents = merged
        elif active_talents is None and talents is not None:
            active_talents = talents

        # 基础伤害系数需按实际修改，此处简化
        # 注意：Zenith 在此被定义，彻底解决 KeyError
        self.spells = {
            'TP': Spell('TP', 0.88 * 1000, energy=50, chi_gen=2),
            'BOK': Spell('BOK', 3.56 * 1000, chi_cost=1),
            'RSK': Spell('RSK', 4.228 * 1000, chi_cost=2, cd=10.0, cd_haste=True),
            'SCK': Spell('SCK', 3.52 * 1000, chi_cost=2, is_channeled=True, ticks=4, cast_time=1.5, cast_haste=True),
            'FOF': Spell('FOF', 2.07 * 5 * 1000, chi_cost=3, cd=24.0, cd_haste=True, is_channeled=True, ticks=5,
                         cast_time=4.0, cast_haste=True, req_talent=True),
            'WDP': SpellWDP('WDP', 5.40 * 1000, cd=30.0, req_talent=True),
            'SOTWL': Spell('SOTWL', 15.12 * 1000, chi_cost=2, cd=30.0, req_talent=True),
            'SW': Spell('SW', 8.96 * 1000, cd=30.0, cast_time=0.4, req_talent=True, gcd_override=0.4),
            'Xuen': Spell('Xuen', 0.0, cd=120.0, req_talent=True, gcd_override=0.0),

            # [核心修复] 定义 Zenith
            # 假设 Zenith 是个大招，90秒CD，无需能量但可能需要天赋解锁
            # 这里 req_talent=False 暂时让它可用，或者你需要添加 5-4 天赋解锁
            'Zenith': Spell('Zenith', 0.0, cd=90.0, req_talent=True)
        }
        self.spells['TP'].triggers_combat_wisdom = True
        self.active_talents = active_talents if active_talents else []
        self.talent_manager = TalentManager()

    def apply_talents(self, player):
        self.talent_manager.apply_talents(self.active_talents, player, self)

    def tick(self, dt):
        for s in self.spells.values(): s.tick_cd(dt)