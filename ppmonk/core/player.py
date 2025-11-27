import random


class PlayerState:
    def __init__(self, agility=2000.0, rating_crit=2000, rating_haste=1500, rating_mastery=1000, rating_vers=500, weapon_type='dw', max_health=100000.0, target_count=1):
        self.rating_crit = rating_crit
        self.rating_haste = rating_haste
        self.rating_mastery = rating_mastery
        self.rating_vers = rating_vers
        self.agility = agility

        # [新] 武器与攻击强度
        self.weapon_type = weapon_type  # '2h' or 'dw'
        self.attack_power = agility  # 基础 AP = 敏捷

        # [新] 生命值与目标 (Task 2 & 5)
        self.max_health = max_health
        self.target_health_pct = 1.0
        self.target_count = max(1, target_count)

        self.base_mastery = 0.19
        self.base_crit = 0.10

        # [Task 1: Base Energy Adjustment]
        self.max_energy = 100.0
        self.energy_regen_mult = 1.0
        self.energy = 100.0

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

        # [新] Momentum Boost State (Task 3)
        self.momentum_buff_active = False
        self.momentum_buff_duration = 0.0

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
        self.has_momentum_boost = False
        self.has_cyclones_drift = False
        self.has_hit_combo = False
        self.has_jade_ignition = False # Task 2

        # [Task 2/3: Row 6 & 7 Flags]
        self.has_shadowboxing = False
        self.has_dance_of_chiji = False
        self.has_energy_burst = False

        # [新] 禅院教诲层数
        self.totm_stacks = 0

        # [新] Hit Combo Stacks (Task 2)
        self.hit_combo_stacks = 0

        # [新] Buff Stacks (Task 2 & 3)
        self.combo_breaker_stacks = 0
        self.dance_of_chiji_stacks = 0
        self.dance_of_chiji_duration = 0.0 # Track duration for DocJ

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

        # [新] Cyclone's Drift (Task 4)
        raw_haste = (self.rating_haste / 4400.0)
        if self.has_cyclones_drift:
            self.haste = raw_haste * 1.10
        else:
            self.haste = raw_haste

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
        log_entries = []

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

            # [新] Momentum Boost Buff Tracking
            if self.momentum_buff_active:
                self.momentum_buff_duration -= step
                if self.momentum_buff_duration <= 0:
                    self.momentum_buff_active = False

            # [新] Dance of Chi-Ji Tracking
            if self.dance_of_chiji_stacks > 0:
                self.dance_of_chiji_duration -= step
                if self.dance_of_chiji_duration <= 0:
                    self.dance_of_chiji_stacks = 0
                    self.dance_of_chiji_duration = 0.0

            self.swing_timer -= step
            if self.swing_timer <= 0:
                # [新] Momentum Boost Attack Speed Logic
                swing_speed_mod = 1.0 + self.haste
                if self.momentum_buff_active:
                    swing_speed_mod *= 1.6 # "Attack speed increased by 60%" -> Interval / 1.6

                self.swing_timer += self.base_swing_time / swing_speed_mod

                is_dual_threat = self.has_dual_threat and random.random() < 0.30

                # Base Damage Calculation
                coeff = 1.0
                if is_dual_threat:
                    coeff = 3.726
                elif self.weapon_type == '2h':
                    coeff = 2.40
                else:
                    coeff = 1.80

                base_dmg = coeff * self.attack_power

                crit_chance = self.crit
                crit_mult = 2.0
                dmg_mod = 1.0 + self.versatility

                expected_dmg = (base_dmg * dmg_mod) * (1 + (crit_chance * (crit_mult - 1)))
                total_damage += expected_dmg

                key = "Dual Threat" if is_dual_threat else "Auto Attack"
                if damage_meter is not None:
                    damage_meter[key] = damage_meter.get(key, 0) + expected_dmg

                breakdown = {
                    'base': int(base_dmg),
                    'modifiers': {'Versatility': 1.0 + self.versatility},
                    'flags': ['Dual Threat'] if is_dual_threat else [],
                    'crit_chance': crit_chance,
                    'crit_mult': crit_mult,
                    'final_mod': dmg_mod
                }

                log_entries.append({
                    "Action": key,
                    "Expected DMG": expected_dmg,
                    "Breakdown": breakdown,
                    "source": "passive",
                    "offset": elapsed  # Time relative to the start of this advance_time call
                })

            if self.is_channeling:
                self.channel_time_remaining -= step
                self.time_until_next_tick -= step
                if self.time_until_next_tick <= 1e-6:
                    if self.channel_ticks_remaining > 0:
                        spell = self.current_channel_spell
                        tick_idx = spell.total_ticks - self.channel_ticks_remaining
                        # [Modified for Task 6 AOE]
                        # Spell.calculate_tick_damage returns single target damage
                        # We need to handle AOE here if it's an active tick
                        # However, Spell.cast handles initial burst, but ticks are here.
                        # Wait, Spell.calculate_tick_damage is used here.
                        # If the spell is AOE (FOF, SCK), we need to multiply by targets (with soft cap).
                        # I should modify calculate_tick_damage to handle AOE OR handle it here.
                        # I'll let Spell.calculate_tick_damage handle it if I pass 'player' which has target_count,
                        # BUT calculate_tick_damage is usually "per target".
                        # Let's see what I implemented in SpellBook.
                        # I will modify SpellBook to handle AOE inside calculate_tick_damage or return a breakdown that indicates it.
                        # For now, I assume calculate_tick_damage returns TOTAL damage across all targets if I implement it that way.
                        # See SpellBook plan.

                        tick_dmg, breakdown = spell.calculate_tick_damage(self, tick_idx=tick_idx)
                        total_damage += tick_dmg
                        if damage_meter is not None and spell:
                            damage_meter[spell.abbr] = damage_meter.get(spell.abbr, 0) + tick_dmg
                        self.channel_ticks_remaining -= 1
                        self.time_until_next_tick += self.channel_tick_interval

                        # Log tick
                        log_entries.append({
                            "Action": f"{spell.abbr} (Tick)",
                            "Expected DMG": tick_dmg,
                            "Breakdown": breakdown,
                            "source": "active",
                            "offset": elapsed
                        })

                if self.channel_time_remaining <= 1e-6 or self.channel_ticks_remaining <= 0:
                    # [新] Momentum Boost Trigger
                    # "When FOF channel completes (or ends)..."
                    if self.current_channel_spell.abbr == 'FOF' and self.has_momentum_boost:
                        self.momentum_buff_active = True
                        self.momentum_buff_duration = 8.0

                    self.is_channeling = False
                    self.current_channel_spell = None
                    self.channel_mastery_snapshot = False
            elapsed += step
        return total_damage, log_entries
