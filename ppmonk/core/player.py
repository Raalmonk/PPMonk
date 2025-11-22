# ppmonk/core/player.py

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
        # 初始化时计算一次
        self.crit = 0.0
        self.haste = 0.0
        self.mastery = 0.0
        self.versatility = 0.0
        self.update_secondary_stats()

        # --- 资源状态 ---
        self.max_energy = 120.0
        self.energy = 120.0
        self.max_chi = 6
        self.chi = 0  # 初始通常为0，或者根据战斗配置设为1-2

        # --- 战斗状态机 ---
        self.last_spell_name = None  # 用于组合拳判定

        self.gcd_remaining = 0.0

        # 引导状态 (FOF, SCK)
        self.is_channeling = False
        self.current_channel_spell = None  # 记录正在引导哪个 Spell 对象
        self.channel_time_remaining = 0.0  # 引导剩余总时间
        self.channel_tick_interval = 0.0  # 每跳间隔
        self.time_until_next_tick = 0.0  # 距离下一跳还有多久
        self.channel_ticks_remaining = 0  # 剩余跳数

        # 引导技能的精通快照 (组合拳判定)
        self.channel_mastery_snapshot = False

    def update_secondary_stats(self):
        """
        根据 Rating 计算最终百分比，包含递减效应 (DR)。
        """
        # 1. Haste / Vers / Crit (假设遵循标准DR，阈值通常是 rating 换算出的 30%)
        # 这里为了简化，先按线性计算，如果需要这些属性的DR，可以在这里加
        # 暴击 = Rating / 46 + 10%
        self.crit = (self.rating_crit / self.RATING_PER_CRIT / 100.0) + self.base_crit_pct

        # 全能 = Rating / 54
        self.versatility = (self.rating_vers / self.RATING_PER_VERS / 100.0)

        # 急速 = Rating / 44
        self.haste = (self.rating_haste / self.RATING_PER_HASTE / 100.0)

        # 2. Mastery (特殊递减逻辑)
        # 阈值 = 30 * 46 = 1380 Rating
        dr_threshold = 30.0 * self.RATING_PER_CRIT  # 1380
        effective_mastery_rating = 0.0

        if self.rating_mastery <= dr_threshold:
            effective_mastery_rating = self.rating_mastery
        else:
            # 第一档递减: 超过部分只生效 90% (WoW 标准是 10% penalty)
            excess = self.rating_mastery - dr_threshold
            effective_mastery_rating = dr_threshold + (excess * 0.9)

            # 如果数值极大，可能还有第二档(通常是39% stats)，暂不展开

        # 精通 = 有效Rating / 20 + 19%
        self.mastery = (effective_mastery_rating / self.RATING_PER_MASTERY / 100.0) + self.base_mastery_pct

    def tick(self, delta_time):
        """
        物理引擎核心跳动
        """
        # 1. 能量回复 (Energy Regen)
        # 公式: Base(10) * (1 + Haste)
        regen_rate = 10.0 * (1.0 + self.haste)
        # 即使在引导时，能量通常也是回复的
        if self.energy < self.max_energy:
            self.energy = min(self.max_energy, self.energy + regen_rate * delta_time)

        # 2. GCD 冷却
        if self.gcd_remaining > 0:
            self.gcd_remaining = max(0, self.gcd_remaining - delta_time)

        # 3. 引导处理 (Channeling Logic)
        tick_damage = 0

        if self.is_channeling:
            self.channel_time_remaining -= delta_time
            self.time_until_next_tick -= delta_time

            # 判定跳伤害
            if self.time_until_next_tick <= 0:
                if self.channel_ticks_remaining > 0:
                    spell = self.current_channel_spell
                    tick_damage = spell.calculate_tick_damage(self)
                    self.channel_ticks_remaining -= 1

                    # 重置下一跳计时器 (加上剩余的负值以保持时间精确)
                    self.time_until_next_tick += self.channel_tick_interval

            # 判定引导结束
            if self.channel_time_remaining <= 0 or self.channel_ticks_remaining <= 0:
                self.break_channel()

        return 0, tick_damage

    def break_channel(self):
        """打断或结束引导"""
        self.is_channeling = False
        self.current_channel_spell = None
        self.channel_time_remaining = 0
        self.channel_ticks_remaining = 0
        self.channel_mastery_snapshot = False

    # 辅助：获取当前快照属性 (Snapshot) 用于 DoT/HoT
    # 如果以后需要动态属性 (如饰品触发)，在这个类里加一个 buffs_stats_modifier
    def get_current_ap(self):
        return self.attack_power  # 以后加上 * (1 + ap_buff_pct)