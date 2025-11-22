"""Player state management for PPMonk."""

class PlayerState:
    def __init__(self,
                 attack_power=5000,
                 rating_crit=2000,
                 rating_haste=1500,
                 rating_mastery=1000,
                 rating_vers=500):
        # --- 输入属性 (Ratings) ---
        self.attack_power = attack_power
        self.rating_crit = rating_crit
        self.rating_haste = rating_haste
        self.rating_mastery = rating_mastery
        self.rating_vers = rating_vers

        # --- 转化率常量 ---
        self.RATING_PER_CRIT = 46.0
        self.RATING_PER_HASTE = 44.0
        self.RATING_PER_VERS = 54.0
        self.RATING_PER_MASTERY = 20.0

        # --- 基础百分比 ---
        self.base_crit_pct = 0.10  # 10%
        self.base_mastery_pct = 0.19  # 19%

        # --- 实时面板属性 (0.0 - 1.0) ---
        self.crit = 0.0
        self.haste = 0.0
        self.mastery = 0.0
        self.versatility = 0.0
        self.update_secondary_stats()

        # --- 资源状态 ---
        self.max_energy = 120.0
        self.energy_regen_mult = 1.0  # 能量回复倍率 (默认为1.0)
        self.energy = 120.0
        self.max_chi = 6
        self.chi = 2  # 起手2豆

        # --- 战斗状态机 ---
        self.last_spell_name = None
        self.gcd_remaining = 0.0

        # 引导状态 (FOF, SCK)
        self.is_channeling = False
        self.current_channel_spell = None
        self.channel_time_remaining = 0.0
        self.channel_ticks_remaining = 0
        self.time_until_next_tick = 0.0
        self.channel_tick_interval = 0.0

        # 引导技能的精通快照 (组合拳判定)
        self.channel_mastery_snapshot = False

    def update_secondary_stats(self):
        """根据 Rating 计算最终百分比，包含递减效应 (DR)。"""
        # 1. Haste / Vers / Crit
        self.crit = (self.rating_crit / self.RATING_PER_CRIT / 100.0) + self.base_crit_pct
        self.versatility = (self.rating_vers / self.RATING_PER_VERS / 100.0)
        self.haste = (self.rating_haste / self.RATING_PER_HASTE / 100.0)

        # 2. Mastery (特殊递减逻辑)
        dr_threshold = 30.0 * self.RATING_PER_CRIT  # 1380
        if self.rating_mastery <= dr_threshold:
            effective_mastery_rating = self.rating_mastery
        else:
            excess = self.rating_mastery - dr_threshold
            effective_mastery_rating = dr_threshold + (excess * 0.9)
        self.mastery = (effective_mastery_rating / self.RATING_PER_MASTERY / 100.0) + self.base_mastery_pct

    def advance_time(self, duration):
        """推进时间轴，处理资源回复与引导伤害。"""
        total_damage = 0
        dt = 0.01
        elapsed = 0.0
        regen_rate = 10.0 * (1.0 + self.haste) * self.energy_regen_mult

        while elapsed < duration:
            step = min(dt, duration - elapsed)
            if self.energy < self.max_energy:
                self.energy = min(self.max_energy, self.energy + regen_rate * step)

            if self.gcd_remaining > 0:
                self.gcd_remaining = max(0, self.gcd_remaining - step)

            if self.is_channeling:
                self.channel_time_remaining -= step
                self.time_until_next_tick -= step

                if self.time_until_next_tick <= 1e-6 and self.channel_ticks_remaining > 0:
                    spell = self.current_channel_spell
                    tick_dmg = spell.calculate_tick_damage(self)
                    total_damage += tick_dmg
                    self.channel_ticks_remaining -= 1
                    self.time_until_next_tick += self.channel_tick_interval

                if self.channel_time_remaining <= 1e-6 or self.channel_ticks_remaining <= 0:
                    self.is_channeling = False
                    self.current_channel_spell = None
                    self.channel_mastery_snapshot = False

            elapsed += step

        return total_damage

    def get_current_ap(self):
        """返回当前攻击强度，供以后扩展 buff 使用。"""
        return self.attack_power
