import random


class PlayerState:
    def __init__(self, rating_crit=2000, rating_haste=1500, rating_mastery=1000, rating_vers=500, weapon_type='dw'):
        self.rating_crit = rating_crit
        self.rating_haste = rating_haste
        self.rating_mastery = rating_mastery
        self.rating_vers = rating_vers

        # [新] 武器与攻击强度
        self.weapon_type = weapon_type  # '2h' or 'dw'
        self.attack_power = 1000.0  # 基础 AP，可根据装备调整

        self.base_mastery = 0.19
        self.base_crit = 0.10

        self.max_energy = 130.0
        self.energy_regen_mult = 1.0
        self.energy = 130.0

        self.max_chi = 5
        self.chi = 2

        # 状态追踪
        self.xuen_active = False
        self.xuen_duration = 0.0
        self.zenith_active = False
        self.zenith_duration = 0.0
        self.talent_crit_bonus = 0.0
        self.combat_wisdom_ready = False
        self.combat_wisdom_timer = 0.0

        self.last_spell_name = None
        self.gcd_remaining = 0.0
        self.is_channeling = False
        self.current_channel_spell = None
        self.channel_time_remaining = 0.0
        self.channel_ticks_remaining = 0
        self.time_until_next_tick = 0.0
        self.channel_tick_interval = 0.0
        self.channel_mastery_snapshot = False

        # 面板属性
        self.crit = 0.0
        self.versatility = 0.0
        self.haste = 0.0
        self.mastery = 0.0

        # [新] 天赋开关
        self.has_dual_threat = False
        self.has_totm = False
        self.has_glory_of_the_dawn = False

        # [新] 禅院教诲层数
        self.totm_stacks = 0

        # [新] 自动攻击计时器
        self.swing_timer = 0.0
        # 基础攻速
        if self.weapon_type == '2h':
            self.base_swing_time = 3.5
        else:  # dw
            self.base_swing_time = 2.6

        self.update_stats()

    def update_stats(self):
        raw_crit = (self.rating_crit / 4600.0) + self.base_crit
        crit_bonus = self.talent_crit_bonus
        if self.xuen_active:
            crit_bonus *= 2.0
        self.crit = raw_crit + crit_bonus

        self.versatility = (self.rating_vers / 5400.0)
        self.haste = (self.rating_haste / 4400.0)

        dr_threshold = 1380
        eff_mast_rating = self.rating_mastery
        if self.rating_mastery > dr_threshold:
            excess = self.rating_mastery - dr_threshold
            eff_mast_rating = dr_threshold + (excess * 0.9)
        self.mastery = (eff_mast_rating / 2000.0) + self.base_mastery

    def advance_time(self, duration, damage_meter=None):
        total_damage = 0
        dt = 0.01
        elapsed = 0.0
        regen_rate = 10.0 * (1.0 + self.haste) * self.energy_regen_mult

        while elapsed < duration:
            step = min(dt, duration - elapsed)
            self.energy = min(self.max_energy, self.energy + regen_rate * step)

            if self.gcd_remaining > 0:
                self.gcd_remaining = max(0, self.gcd_remaining - step)

            if not self.combat_wisdom_ready:
                self.combat_wisdom_timer -= step
                if self.combat_wisdom_timer <= 0:
                    self.combat_wisdom_ready = True
                    self.combat_wisdom_timer = 0

            if self.xuen_active:
                self.xuen_duration -= step
                if self.xuen_duration <= 0:
                    self.xuen_active = False
                    self.update_stats()

            if self.zenith_active:
                self.zenith_duration -= step
                if self.zenith_duration <= 0:
                    self.zenith_active = False

            # --- [新] 自动攻击逻辑 ---
            self.swing_timer -= step
            if self.swing_timer <= 0:
                # 重置计时器 (受急速缩减)
                self.swing_timer += self.base_swing_time / (1.0 + self.haste)

                # 判定 Dual Threat (30% 概率)
                is_dual_threat = False
                if self.has_dual_threat and random.random() < 0.30:
                    is_dual_threat = True
                    print("[DEBUG] Dual Threat Triggered!")

                damage = 0.0
                if is_dual_threat:
                    # Dual Threat: 372.6% AP 自然伤害
                    damage = 3.726 * self.attack_power
                    # 自然伤害享受全能、暴击，不享受护甲减免(模拟器暂未模拟护甲)
                    # 这里假设享受通用增伤
                else:
                    # 普通平砍: 物理伤害
                    if self.weapon_type == '2h':
                        damage = 2.40 * self.attack_power
                    else:  # dw: 主手+副手 (120% + 60% = 180%)
                        damage = 1.80 * self.attack_power

                # 结算平砍伤害 (含全能/暴击)
                # 注意：Way of the Cobra (眼镜蛇之道) 可能会加平砍暴击，这里暂用面板暴击
                is_crit = random.random() < self.crit
                crit_mult = 2.0 if is_crit else 1.0

                final_dmg = damage * (1.0 + self.versatility) * crit_mult

                total_damage += final_dmg

                if damage_meter is not None:
                    key = "Dual Threat" if is_dual_threat else "Auto Attack"
                    damage_meter[key] = damage_meter.get(key, 0) + final_dmg

            # --- 通道法术逻辑 ---
            if self.is_channeling:
                self.channel_time_remaining -= step
                self.time_until_next_tick -= step
                if self.time_until_next_tick <= 1e-6:
                    if self.channel_ticks_remaining > 0:
                        spell = self.current_channel_spell
                        tick_idx = spell.total_ticks - self.channel_ticks_remaining
                        tick_dmg, _ = spell.calculate_tick_damage(self, tick_idx=tick_idx)
                        total_damage += tick_dmg

                        # 记录通道伤害
                        if damage_meter is not None and spell:
                            damage_meter[spell.abbr] = damage_meter.get(spell.abbr, 0) + tick_dmg

                        self.channel_ticks_remaining -= 1
                        self.time_until_next_tick += self.channel_tick_interval
                if self.channel_time_remaining <= 1e-6 or self.channel_ticks_remaining <= 0:
                    self.is_channeling = False
                    self.current_channel_spell = None
                    self.channel_mastery_snapshot = False

            elapsed += step

        return total_damage