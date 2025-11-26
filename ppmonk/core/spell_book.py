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

        # --- 机制属性 ---
        self.haste_dmg_scaling = False
        self.tick_dmg_ramp = 0.0
        self.triggers_combat_wisdom = False

        # [新] Sharp Reflexes: 施放该技能是否会减少其他技能CD
        self.triggers_sharp_reflexes = False

        # [新] Hardened Soles / Touch of Tiger 属性
        self.bonus_crit_chance = 0.0 # 技能独立的额外暴击率 (0.0 ~ 1.0)
        self.crit_damage_bonus = 0.0 # 技能独立的额外爆伤 (如 0.2 表示 +20%)
        self.damage_multiplier = 1.0 # 独立增伤倍率 (如 Touch of Tiger = 1.15)

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

    def cast(self, player, other_spells=None):
        # 注意：这里需要传入 other_spells 字典才能做减 CD 逻辑
        # 如果调用方没传，尝试从外部获取引用 (通常在 env.step 里调用)

        player.energy -= self.energy_cost
        player.chi = max(0, player.chi - self.chi_cost)
        player.chi = min(player.max_chi, player.chi + self.chi_gen)
        self.current_cd = self.get_effective_cd(player)

        if self.gcd_override is not None:
            player.gcd_remaining = self.gcd_override
        else:
            player.gcd_remaining = 1.0

        # --- [新] Sharp Reflexes 触发逻辑 ---
        if self.triggers_sharp_reflexes and other_spells:
            # 减少 RSK 和 FOF 的 CD 1秒
            if 'RSK' in other_spells:
                other_spells['RSK'].current_cd = max(0, other_spells['RSK'].current_cd - 1.0)
            if 'FOF' in other_spells:
                other_spells['FOF'].current_cd = max(0, other_spells['FOF'].current_cd - 1.0)
            # print(f"[DEBUG] Sharp Reflexes! Reduced CD of RSK/FOF")

        # --- [新] 雪怒激活逻辑 ---
        if self.abbr == 'Xuen':
            player.xuen_active = True
            player.xuen_duration = 24.0 # 持续 24 秒
            player.update_stats()
            # print(f"[DEBUG] Xuen Activated! Crit increased.")

        # Combat Wisdom 触发
        extra_damage = 0.0
        if self.triggers_combat_wisdom and getattr(player, 'combat_wisdom_ready', False):
            player.combat_wisdom_ready = False
            player.combat_wisdom_timer = 15.0
            eh_dmg = 1.2 * (1.0 + player.versatility)
            extra_damage += eh_dmg

        triggers_mastery = self.is_combo_strike and (player.last_spell_name is not None) and (player.last_spell_name != self.abbr)
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
            if extra_damage > 0: base_dmg *= 1.30
            return base_dmg + extra_damage

    def calculate_tick_damage(self, player, mastery_override=None, tick_idx=0):
        # 基础伤害 * 独立增伤 (Touch of Tiger)
        dmg = self.tick_coeff * self.damage_multiplier

        if self.haste_dmg_scaling: dmg *= (1.0 + player.haste)
        if self.tick_dmg_ramp > 0: dmg *= (1.0 + (tick_idx + 1) * self.tick_dmg_ramp)

        apply_mastery = False
        if mastery_override is not None: apply_mastery = mastery_override
        elif self.is_channeled: apply_mastery = player.channel_mastery_snapshot

        if apply_mastery: dmg *= (1.0 + player.mastery)
        dmg *= (1.0 + player.versatility)

        # [新] 暴击期望计算 (含 Hardened Soles 爆伤加成)
        # 实际暴击率 = 面板 + 技能独立加成 (如 Hardened Soles 加 BOK 暴击)
        eff_crit_chance = min(1.0, player.crit + self.bonus_crit_chance)

        # 暴击倍率 = 2.0 (基础) + 爆伤加成
        crit_mult = 2.0 + self.crit_damage_bonus

        # 期望倍数 = 1 + 暴击率 * (倍率 - 1)
        dmg *= (1.0 + eff_crit_chance * (crit_mult - 1.0))

        return dmg

    def tick_cd(self, dt):
        if self.current_cd > 0: self.current_cd = max(0, self.current_cd - dt)

class SpellWDP(Spell):
    def is_usable(self, player, other_spells):
        if not super().is_usable(player): return False
        rsk = other_spells['RSK']; fof = other_spells['FOF']
        return rsk.current_cd > 0 and fof.current_cd > 0

class SpellBook:
    def __init__(self, active_talents=None, talents=None):
        if active_talents is not None and talents is not None:
            merged = list(dict.fromkeys([*active_talents, *talents]))
            active_talents = merged
        elif active_talents is None and talents is not None:
            active_talents = talents

        self.spells = {
            'TP': Spell('TP', 0.88, energy=50, chi_gen=2),
            'BOK': Spell('BOK', 3.56, chi_cost=1),
            'RSK': Spell('RSK', 4.228, chi_cost=2, cd=10.0, cd_haste=True),
            'SCK': Spell('SCK', 3.52, chi_cost=2, is_channeled=True, ticks=4, cast_time=1.5, cast_haste=True),
            'FOF': Spell('FOF', 2.07 * 5, chi_cost=3, cd=24.0, cd_haste=True, is_channeled=True, ticks=5, cast_time=4.0, cast_haste=True, req_talent=True),
            'WDP': SpellWDP('WDP', 5.40, cd=30.0, req_talent=True),
            'SOTWL': Spell('SOTWL', 15.12, chi_cost=2, cd=30.0, req_talent=True),
            'SW': Spell('SW', 8.96, cd=30.0, cast_time=0.4, req_talent=True, gcd_override=0.4),

            # [新] Xuen 技能定义
            'Xuen': Spell('Xuen', 0.0, cd=120.0, req_talent=True, gcd_override=0.0) # 不占GCD? 暂时设为0或1
        }
        self.spells['TP'].triggers_combat_wisdom = True
        self.active_talents = active_talents if active_talents else []
        self.talent_manager = TalentManager()

    def apply_talents(self, player):
        self.talent_manager.apply_talents(self.active_talents, player, self)

    def tick(self, dt):
        for s in self.spells.values(): s.tick_cd(dt)