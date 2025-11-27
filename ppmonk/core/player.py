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
        self.has_obsidian_spiral = False
        self.has_combo_breaker = False
        self.has_drinking_horn_cover = False

        self.has_universal_energy = False
        self.has_weapon_of_wind = False
        self.has_jadefire_stomp = False

        # [Task 1] TEB & Martial Agility
        self.teb_stacks = 10
        self.teb_timer = 8.0
        self.teb_active_bonus = 0.0
        self.teb_crit_dmg_bonus = 0.0
        self.has_teb_stacking = False
        self.has_martial_agility = False

        # [Task 2] New Talent Flags
        self.has_path_of_jade = False
        self.has_singularly_focused_jade = False
        self.has_flurry_of_xuen = False

        # [Shado-Pan] Flags & Stats
        self.armor_pen = 0.0
        self.flurry_charges = 0
        # self.max_flurry_charges = 10  # Removed upper limit
        self.stand_ready_active = False

        self.has_shado_pan_base = False
        self.has_pride_of_pandaria = False
        self.has_high_impact = False
        self.has_shado_over_battlefield = False
        self.has_one_versus_many = False
        self.has_stand_ready = False
        self.has_weapons_of_the_wall = False
        self.has_wisdom_of_the_wall = False
        self.has_veterans_eye = False

        # [Task 2] Core Buffs
        self.totm_stacks = 0
        self.max_totm_stacks = 4

        self.hit_combo_stacks = 0

        self.combo_breaker_stacks = 0

        self.dance_of_chiji_stacks = 0
        self.dance_of_chiji_duration = 0.0

        self.thunderfist_stacks = 0
        self.thunderfist_icd_timer = 0.0

        self.rwk_ready = False

        # 自动攻击计时器
        self.swing_timer = 0.0
        if self.weapon_type == '2h':
            self.base_swing_time = 3.5
        else:  # dw
            self.base_swing_time = 2.6

        self.update_stats()

    def get_physical_mitigation(self):
        # Boss physical DR = 30%
        # Effective DR = 0.30 * (1 - armor_pen)
        effective_dr = 0.30 * (1.0 - self.armor_pen)
        return 1.0 - effective_dr

    def update_stats(self):
        raw_crit = (self.rating_crit / 4600.0) + self.base_crit
        crit_bonus = self.talent_crit_bonus
        if self.xuen_active:
            crit_bonus *= 2.0
        self.crit = raw_crit + crit_bonus

        self.versatility = (self.rating_vers / 5400.0)

        raw_haste = (self.rating_haste / 4400.0)

        if self.has_cyclones_drift:
            # Cyclones Drift logic from previous code
            self.haste = raw_haste * 1.10
        else:
            self.haste = raw_haste

        # Veterans Eye
        if self.has_veterans_eye:
             self.haste += 0.05

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

            # [Task 1] TEB Stacking
            if self.has_teb_stacking:
                self.teb_timer -= step
                if self.teb_timer <= 0:
                    self.teb_stacks = min(20, self.teb_stacks + 1)
                    self.teb_timer += 8.0

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

                # [Task 1] Martial Agility
                if self.has_martial_agility:
                    ma_mod = 1.3
                    if self.zenith_active:
                        ma_mod = 1.6
                    swing_speed_mod *= ma_mod

                self.swing_timer += self.base_swing_time / swing_speed_mod

                # [Task 3 & 2] Thunderfist Consumption on Auto Attack
                thunderfist_dmg = 0.0
                thunderfist_proc = False

                if self.thunderfist_stacks > 0 and self.thunderfist_icd_timer <= 0:
                    self.thunderfist_stacks -= 1
                    self.thunderfist_icd_timer = 1.5
                    thunderfist_proc = True
                    # Thunderfist Damage: 1.61 * AP * Agility (Nature)
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

                # [Shado-Pan] Flurry Strikes Stacking
                if self.has_shado_pan_base:
                    proc_chance = 1.0
                    if self.weapon_type == 'dw':
                        # 17.14 * 2.6 / 60 = 0.7427
                        proc_chance = (17.14 * 2.6) / 60.0

                    if random.random() < proc_chance:
                        stacks_to_add = 1
                        # One Versus Many: Crit AA gives 2 stacks
                        # We use 'crit_chance' as probability for this
                        if self.has_one_versus_many and random.random() < crit_chance:
                            stacks_to_add = 2

                        # Removed limit check: min(self.max_flurry_charges, ...)
                        self.flurry_charges += stacks_to_add

                # [Shado-Pan] Stand Ready Trigger
                if self.stand_ready_active:
                    self.stand_ready_active = False
                    # Trigger Flurry Logic: 0.7 * (0.6 * AP)
                    # Flurry Base per stack = 0.6 * AP * Agility
                    # Scale = 0.7
                    # This consumes ALL stacks. Wait, "Consume all stacks" is part of FOF.
                    # Stand Ready says: "Immediate trigger Flurry Strikes logic (consume all stacks cause damage)".
                    # So we use current stacks.

                    stacks = self.flurry_charges
                    self.flurry_charges = 0

                    if stacks > 0:
                        # Logic duplicated from SpellBook implementation plan to avoid circular import
                        # Flurry Base: 0.6 * AP
                        flurry_coeff = 0.6
                        flurry_base = flurry_coeff * self.attack_power * self.agility * stacks

                        # Apply Physical Mitigation
                        mitigation = self.get_physical_mitigation()
                        flurry_base *= mitigation

                        # Modifiers
                        f_mod = 1.0 + self.versatility

                        # Stand Ready Scale: 0.7
                        f_mod *= 0.7

                        # Pride of Pandaria
                        flurry_crit = self.crit
                        if self.has_pride_of_pandaria:
                            flurry_crit += 0.15

                        flurry_dmg = flurry_base * f_mod * (1 + (flurry_crit * (crit_mult - 1)))
                        total_damage += flurry_dmg

                        if damage_meter is not None:
                            damage_meter['Flurry Strikes'] = damage_meter.get('Flurry Strikes', 0) + flurry_dmg

                        log_entries.append({
                            "Action": f"Flurry Strikes (Stand Ready) x{stacks}",
                            "Expected DMG": flurry_dmg,
                            "Breakdown": {
                                "base": int(flurry_base),
                                "modifiers": ["StandReady: x0.7", f"Mitigation: x{mitigation:.2f}"],
                                "final_crit": flurry_crit
                            },
                            "source": "passive",
                            "offset": elapsed
                        })

                        # Shado Over Battlefield (Nature AOE)
                        if self.has_shado_over_battlefield:
                            # 0.52 * AP * Agility per stack? No, "Attach to Flurry Strikes".
                            # Usually procs per event or per stack? "Every time Flurry Strikes deals damage".
                            # Usually means 1 proc per "Flurry Strikes" event. But FOF deals it per stack?
                            # Prompt: "每当 Flurry Strikes 造成伤害时... 额外造成 0.52 * AP".
                            # Does it mean per stack?
                            # FOF says: "Trigger Flurry Strikes damage: per stack 0.6 * AP".
                            # So if I have 10 stacks, I do 10x (0.6 AP).
                            # Does Shado Over Battlefield trigger 10x? Or 1x?
                            # "Attach to Flurry Strikes... additional 0.52 AP".
                            # If it's attached to the *Strike*, and we do 10 Strikes (one per charge), then yes, 10x.
                            # So effectively, it makes Flurry 0.6 Physical + 0.52 Nature.

                            sob_coeff = 0.52
                            sob_base = sob_coeff * self.attack_power * self.agility * stacks
                            # Nature -> No Armor Pen, but Universal Energy applies
                            sob_mod = 1.0 + self.versatility
                            if getattr(self, 'has_universal_energy', False):
                                sob_mod *= 1.15

                            # Soft Cap 8
                            eff_targets = self.target_count
                            scale = 1.0
                            if eff_targets > 8:
                                scale = (8.0 / eff_targets) ** 0.5

                            sob_total = sob_base * sob_mod * eff_targets * scale * (1 + (flurry_crit * (crit_mult - 1)))

                            total_damage += sob_total
                            if damage_meter is not None:
                                damage_meter['Shado Over Battlefield'] = damage_meter.get('Shado Over Battlefield', 0) + sob_total

                            log_entries.append({
                                "Action": "Shado Over Battlefield",
                                "Expected DMG": sob_total,
                                "source": "passive",
                                "offset": elapsed
                            })

                        # High Impact (Physical AOE)
                        if self.has_high_impact:
                            # 1.0 * AP * Agility (Explosion)
                            # Per stack? Or per event?
                            # "When Flurry Strikes triggers, extra 1.0 AP (Explosion)".
                            # Assuming per stack for now as it makes sense if Flurry is a stack-based attack.
                            hi_coeff = 1.0
                            hi_base = hi_coeff * self.attack_power * self.agility * stacks

                            hi_mod = 1.0 + self.versatility

                            # Soft Cap 8
                            eff_targets = self.target_count
                            scale = 1.0
                            if eff_targets > 8:
                                scale = (8.0 / eff_targets) ** 0.5

                            hi_total = hi_base * hi_mod * eff_targets * scale * (1 + (flurry_crit * (crit_mult - 1)))
                            total_damage += hi_total
                            if damage_meter is not None:
                                damage_meter['High Impact'] = damage_meter.get('High Impact', 0) + hi_total


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

                            # [Task 2] Path of Jade / Singularly Focused Jade
                            eff_target_count = self.target_count
                            poj_bonus = 0.0
                            if getattr(self, 'has_path_of_jade', False):
                                poj_bonus = min(0.50, 0.10 * eff_target_count)
                                jf_mod *= (1.0 + poj_bonus)

                            if getattr(self, 'has_singularly_focused_jade', False):
                                jf_mod *= 4.0 # Base + 300%
                                eff_target_count = 1

                            # Soft Cap (Manual Imp)
                            scale = 1.0
                            if eff_target_count > 5:
                                scale = (5.0 / eff_target_count) ** 0.5

                            jf_total = jf_base * jf_mod * eff_target_count * scale * (1 + (self.crit * (crit_mult - 1)))

                            total_damage += jf_total
                            if damage_meter is not None:
                                damage_meter['Jadefire Stomp'] = damage_meter.get('Jadefire Stomp', 0) + jf_total

                            log_entries.append({
                                "Action": "Jadefire Stomp",
                                "Expected DMG": jf_total,
                                "Breakdown": {
                                    "base": int(jf_base),
                                    "targets": eff_target_count,
                                    "modifiers": ["SoftCap" if eff_target_count>5 else "Uncapped", f"PathJade:{poj_bonus:.2f}"],
                                },
                                "source": "passive",
                                "offset": elapsed
                            })

                    self.is_channeling = False
                    self.current_channel_spell = None
                    self.channel_mastery_snapshot = False
            elapsed += step
        return total_damage, log_entries
