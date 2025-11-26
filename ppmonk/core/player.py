class PlayerState:
    def __init__(self, rating_crit=2000, rating_haste=1500, rating_mastery=1000, rating_vers=500):
        self.rating_crit = rating_crit
        self.rating_haste = rating_haste
        self.rating_mastery = rating_mastery
        self.rating_vers = rating_vers
        
        self.base_mastery = 0.19
        self.base_crit = 0.10

        self.max_energy = 120.0
        self.energy_regen_mult = 1.0
        self.energy = 120.0

        self.max_chi = 6 # 默认6，Ascension 会改为 7
        self.chi = 2

        # [新] 雪怒状态追踪 (Ferociousness)
        self.xuen_active = False
        self.xuen_duration = 0.0

        # [新] 天赋带来的额外面板暴击 (Ferociousness)
        self.talent_crit_bonus = 0.0
        # 如果点了2级 Ferociousness，这里存 0.04；Xuen 期间翻倍逻辑在 update_stats 处理

        # 战斗智慧 (Combat Wisdom)
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
        
        self.crit = 0.0
        self.versatility = 0.0
        self.haste = 0.0
        self.mastery = 0.0
        self.update_stats()

    def update_stats(self):
        # 基础暴击
        raw_crit = (self.rating_crit / 4600.0) + self.base_crit

        # [新] Ferociousness 逻辑：Xuen 激活时，天赋暴击加成翻倍
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

    def advance_time(self, duration):
        total_damage = 0
        dt = 0.01
        elapsed = 0.0

        # 动态计算回能 (Ascension 可能修改了 energy_regen_mult)
        regen_rate = 10.0 * (1.0 + self.haste) * self.energy_regen_mult

        while elapsed < duration:
            step = min(dt, duration - elapsed)
            self.energy = min(self.max_energy, self.energy + regen_rate * step)

            if self.gcd_remaining > 0:
                self.gcd_remaining = max(0, self.gcd_remaining - step)

            # Combat Wisdom CD
            if not self.combat_wisdom_ready:
                self.combat_wisdom_timer -= step
                if self.combat_wisdom_timer <= 0:
                    self.combat_wisdom_ready = True
                    self.combat_wisdom_timer = 0

            # [新] 雪怒持续时间倒计时
            if self.xuen_active:
                self.xuen_duration -= step
                if self.xuen_duration <= 0:
                    self.xuen_active = False
                    self.update_stats() # 状态结束，刷新暴击率

            if self.is_channeling:
                self.channel_time_remaining -= step
                self.time_until_next_tick -= step
                if self.time_until_next_tick <= 1e-6:
                    if self.channel_ticks_remaining > 0:
                        spell = self.current_channel_spell
                        tick_idx = spell.total_ticks - self.channel_ticks_remaining
                        tick_dmg = spell.calculate_tick_damage(self, tick_idx=tick_idx)
                        total_damage += tick_dmg
                        self.channel_ticks_remaining -= 1
                        self.time_until_next_tick += self.channel_tick_interval
                if self.channel_time_remaining <= 1e-6 or self.channel_ticks_remaining <= 0:
                    self.is_channeling = False
                    self.current_channel_spell = None
                    self.channel_mastery_snapshot = False
            elapsed += step
        return total_damage