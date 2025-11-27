import random

class PlayerState:
    def __init__(self, agility=2000.0, rating_crit=2000, rating_haste=1500, rating_mastery=1000, rating_vers=500, weapon_type='dw', max_health=100000.0, target_count=1):
        self.rating_crit = rating_crit
        self.rating_haste = rating_haste
        self.rating_mastery = rating_mastery
        self.rating_vers = rating_vers
        self.agility = agility

        # [Task 4] 基础 AP = 敏捷
        self.weapon_type = weapon_type  # '2h' or 'dw'
        self.attack_power = agility

        # [Task 2] 生命值与目标
        self.max_health = max_health
        self.target_health_pct = 1.0
        self.target_count = max(1, target_count)

        self.base_mastery = 0.19
        self.base_crit = 0.10

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

        # 天赋开关
        self.has_dual_threat = False
        self.has_totm = False
        self.has_glory_of_the_dawn = False
        self.has_momentum_boost = False
        self.has_cyclones_drift = False
        self.has_hit_combo = False
        self.has_jade_ignition = False
        self.has_shadowboxing = False
        self.has_dance_of_chiji = False
        self.has_energy_burst = False
        self.has_obsidian_spiral = False # Added missing flag init
        self.has_combo_breaker = False
        self.has_drinking_horn_cover = False

        # Missing from refactor pass 1 but needed for checks
        self.has_universal_energy = False
        self.has_weapon_of_wind = False
        self.has_jadefire_stomp = False

        # [Task 2] Core Buffs
        self.totm_stacks = 0
        self.max_totm_stacks = 4 # Default 4

        self.hit_combo_stacks = 0

        self.combo_breaker_stacks = 0 # BOK! Buff

        self.dance_of_chiji_stacks = 0
        self.dance_of_chiji_duration = 0.0

        self.thunderfist_stacks = 0
        self.thunderfist_icd_timer = 0.0 # Initialized here as requested

        self.rwk_ready = False # Rushing Wind Kick Ready

        # 自动攻击计时器
        self.swing_timer = 0.0
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

            # ICD Timers
            if self.thunderfist_icd_timer > 0:
                self.thunderfist_icd_timer -= step

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

            if self.momentum_buff_active:
                self.momentum_buff_duration -= step
                if self.momentum_buff_duration <= 0:
                    self.momentum_buff_active = False

            if self.dance_of_chiji_stacks > 0:
                self.dance_of_chiji_duration -= step
                if self.dance_of_chiji_duration <= 0:
                    self.dance_of_chiji_stacks = 0
                    self.dance_of_chiji_duration = 0.0

            self.swing_timer -= step
            if self.swing_timer <= 0:
                swing_speed_mod = 1.0 + self.haste
                if self.momentum_buff_active:
                    swing_speed_mod *= 1.6

                self.swing_timer += self.base_swing_time / swing_speed_mod

                # [Task 3 & 2] Thunderfist Consumption on Auto Attack
                # "如果 stacks > 0 且 now - last_consume > 1.5" -> Using timer approach
                thunderfist_dmg = 0.0
                thunderfist_proc = False

                if self.thunderfist_stacks > 0 and self.thunderfist_icd_timer <= 0:
                    self.thunderfist_stacks -= 1
                    self.thunderfist_icd_timer = 1.5
                    thunderfist_proc = True

                    # Thunderfist Damage: 1.61 * AP * Agility (Nature)
                    # Task 4: All damage * Agility
                    tf_base = 1.61 * self.attack_power * self.agility


                is_dual_threat = self.has_dual_threat and random.random() < 0.30

                coeff = 1.0
                if is_dual_threat:
                    coeff = 3.726
                elif self.weapon_type == '2h':
                    coeff = 2.40
                else:
                    coeff = 1.80

                # [Task 4] Apply Agility Multiplier
                base_dmg = coeff * self.attack_power * self.agility

                crit_chance = self.crit
                crit_mult = 2.0
                dmg_mod = 1.0 + self.versatility

                # Weapon of the Wind (9-5): +10% all dmg if zenith_active
                if self.zenith_active and getattr(self, 'has_weapon_of_wind', False):
                    dmg_mod *= 1.10

                expected_dmg = (base_dmg * dmg_mod) * (1 + (crit_chance * (crit_mult - 1)))
                total_damage += expected_dmg

                key = "Dual Threat" if is_dual_threat else "Auto Attack"
                if damage_meter is not None:
                    damage_meter[key] = damage_meter.get(key, 0) + expected_dmg

                breakdown = {
                    'base': int(base_dmg),
                    'modifiers': ['Versatility: x%.2f' % (1.0 + self.versatility)],
                    'crit_sources': ['Base: %.1f%%' % (crit_chance*100)],
                    'final_crit': crit_chance,
                    'crit_mult': crit_mult
                }

                if self.zenith_active and getattr(self, 'has_weapon_of_wind', False):
                    breakdown['modifiers'].append('WeaponOfWind: x1.10')

                log_entries.append({
                    "Action": key,
                    "Expected DMG": expected_dmg,
                    "Breakdown": breakdown,
                    "source": "passive",
                    "offset": elapsed
                })

                # Handle Thunderfist Event
                if thunderfist_proc:
                    # Thunderfist Logic
                    # Nature Damage
                    tf_mod = 1.0 + self.versatility
                    if self.zenith_active and getattr(self, 'has_weapon_of_wind', False):
                        tf_mod *= 1.10

                    # Universal Energy (8-6): Magic dmg +15%
                    if getattr(self, 'has_universal_energy', False):
                        tf_mod *= 1.15

                    tf_crit = self.crit
                    tf_expected = (tf_base * tf_mod) * (1 + (tf_crit * (crit_mult - 1)))
                    total_damage += tf_expected

                    if damage_meter is not None:
                        damage_meter['Thunderfist'] = damage_meter.get('Thunderfist', 0) + tf_expected

                    tf_breakdown = {
                        'base': int(tf_base),
                        'modifiers': ['Versatility: x%.2f' % (1.0 + self.versatility)],
                        'crit_sources': ['Base: %.1f%%' % (tf_crit*100)],
                        'final_crit': tf_crit,
                        'crit_mult': crit_mult
                    }
                    if getattr(self, 'has_universal_energy', False):
                        tf_breakdown['modifiers'].append('UniversalEnergy: x1.15')

                    log_entries.append({
                        "Action": "Thunderfist",
                        "Expected DMG": tf_expected,
                        "Breakdown": tf_breakdown,
                        "source": "passive",
                        "offset": elapsed
                    })

            if self.is_channeling:
                self.channel_time_remaining -= step
                self.time_until_next_tick -= step
                if self.time_until_next_tick <= 1e-6:
                    if self.channel_ticks_remaining > 0:
                        spell = self.current_channel_spell
                        tick_idx = spell.total_ticks - self.channel_ticks_remaining
                        tick_dmg, breakdown = spell.calculate_tick_damage(self, tick_idx=tick_idx)
                        total_damage += tick_dmg
                        if damage_meter is not None and spell:
                            damage_meter[spell.abbr] = damage_meter.get(spell.abbr, 0) + tick_dmg
                        self.channel_ticks_remaining -= 1
                        self.time_until_next_tick += self.channel_tick_interval

                        log_entries.append({
                            "Action": f"{spell.abbr} (Tick)",
                            "Expected DMG": tick_dmg,
                            "Breakdown": breakdown,
                            "source": "active",
                            "offset": elapsed
                        })

                if self.channel_time_remaining <= 1e-6 or self.channel_ticks_remaining <= 0:
                    if self.current_channel_spell.abbr == 'FOF':
                         # Momentum Boost
                        if self.has_momentum_boost:
                            self.momentum_buff_active = True
                            self.momentum_buff_duration = 8.0

                        # [Task 3] Jadefire Stomp (9-8)
                        if getattr(self, 'has_jadefire_stomp', False):
                            # Trigger AOE: 0.4 * AP * Agility, Soft Cap 5
                            # This is a one-off event at end of channel
                            jf_base = 0.4 * self.attack_power * self.agility

                            # Mods
                            jf_mod = 1.0 + self.versatility
                            if self.zenith_active and getattr(self, 'has_weapon_of_wind', False):
                                jf_mod *= 1.10
                            if getattr(self, 'has_universal_energy', False):
                                jf_mod *= 1.15 # Nature

                            # Soft Cap
                            # To avoid duplicating logic, I'll implement soft cap inline here or use a helper if available.
                            # Since this is inside PlayerState, I don't have easy access to Spell methods unless I pass 'spell' which I have.
                            # But Spell._apply_aoe_scaling is internal. I should have made it static or public.
                            # I'll replicate simple soft cap here:
                            # dmg = base * sqrt(5/count) if count > 5
                            count = self.target_count
                            scale = 1.0
                            if count > 5:
                                scale = (5.0 / count) ** 0.5

                            jf_total = jf_base * jf_mod * count * scale * (1 + (self.crit * (crit_mult - 1)))

                            total_damage += jf_total
                            if damage_meter is not None:
                                damage_meter['Jadefire Stomp'] = damage_meter.get('Jadefire Stomp', 0) + jf_total

                            log_entries.append({
                                "Action": "Jadefire Stomp",
                                "Expected DMG": jf_total,
                                "Breakdown": {
                                    "base": int(jf_base),
                                    "targets": count,
                                    "modifiers": ["SoftCap" if count>5 else "Uncapped"]
                                },
                                "source": "passive",
                                "offset": elapsed
                            })

                    self.is_channeling = False
                    self.current_channel_spell = None
                    self.channel_mastery_snapshot = False
            elapsed += step
        return total_damage, log_entries
