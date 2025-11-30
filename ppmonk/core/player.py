    def advance_time(self, duration, damage_meter=None, use_expected_value=False):
        total_damage = 0
        dt = 0.01
        elapsed = 0.0
        regen_rate = 10.0 * (1.0 + self.haste) * self.energy_regen_mult
        log_entries = []

        while elapsed < duration:
            # Advance simulation time in small steps (dt or remainder)
            step = min(dt, duration - elapsed)

            # --- Auto Attack Logic (Decoupled from step size where possible) ---
            # We want to process swings that happen within this 'step'
            # Instead of just decrementing, we calculate if swing_timer hits 0 within 'step'

            current_step_processed = 0.0

            # Use a while loop to handle very fast swings or large steps (though step is small)
            # Effectively, if swing_timer < step, we trigger event, reset timer, and continue

            temp_step = step
            step_damage = 0.0

            while self.swing_timer <= temp_step:
                # Consume time until swing
                time_to_swing = self.swing_timer
                temp_step -= time_to_swing

                # Update cooldowns/timers by the partial amount?
                # Doing that inside this inner loop is complex for other timers.
                # Simplification: We assume other timers tick linearly for 'step'.
                # But we record the swing event at 'elapsed + time_to_swing'

                swing_speed_mod = 1.0 + self.haste
                if self.momentum_buff_active:
                    swing_speed_mod *= 1.6

                if self.has_martial_agility:
                    ma_mod = 1.3
                    if self.zenith_active:
                        ma_mod = 1.6
                    swing_speed_mod *= ma_mod

                # Reset Timer
                self.swing_timer = self.base_swing_time / swing_speed_mod

                # --- Execute Swing ---
                # [Task 3 & 2] Thunderfist Consumption on Auto Attack
                thunderfist_dmg = 0.0
                thunderfist_proc = False

                if self.thunderfist_stacks > 0 and self.thunderfist_icd_timer <= 0:
                    self.thunderfist_stacks -= 1
                    self.thunderfist_icd_timer = 1.5
                    thunderfist_proc = True
                    tf_base = 1.61 * self.attack_power * self.agility

                is_dual_threat = False
                if self.has_dual_threat:
                    if use_expected_value:
                        pass
                    else:
                        is_dual_threat = random.random() < 0.30

                coeff = 1.0
                if self.weapon_type == '2h':
                    coeff = 2.40
                else:
                    coeff = 1.80 # DW

                dual_coeff = 3.726

                final_coeff = coeff
                if use_expected_value and self.has_dual_threat:
                     final_coeff = (0.7 * coeff) + (0.3 * dual_coeff)
                elif is_dual_threat:
                     final_coeff = dual_coeff

                base_dmg = final_coeff * self.attack_power * self.agility

                crit_chance = self.crit
                crit_mult = 2.0
                dmg_mod = 1.0 + self.versatility

                if self.has_restore_balance and self.xuen_active:
                    dmg_mod *= 1.05

                if self.zenith_active and getattr(self, 'has_weapon_of_wind', False):
                    dmg_mod *= 1.10

                if use_expected_value:
                    expected_dmg = (base_dmg * dmg_mod) * (1 + (crit_chance * (crit_mult - 1)))
                else:
                     is_crit = random.random() < crit_chance
                     expected_dmg = (base_dmg * dmg_mod) * (crit_mult if is_crit else 1.0)
                     if is_crit: crit_chance = 1.0 # For display

                step_damage += expected_dmg
                self.record_damage(expected_dmg)

                key = "Dual Threat" if is_dual_threat else "Auto Attack"
                if use_expected_value and self.has_dual_threat:
                     key = "Auto Attack (EV w/ DT)"

                if damage_meter is not None:
                    damage_meter[key] = damage_meter.get(key, 0) + expected_dmg

                breakdown = {
                    'base': int(base_dmg),
                    'modifiers': ['Versatility: x%.2f' % (1.0 + self.versatility)],
                    'crit_sources': ['Base: %.1f%%' % (self.crit*100)],
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
                    "timestamp": elapsed + time_to_swing, # Relative to start of advance_time call
                    "offset": elapsed + time_to_swing # Legacy key if needed
                })

                # [Shado-Pan] Flurry Strikes Stacking
                if self.has_shado_pan_base:
                    proc_chance = 1.0
                    if self.weapon_type == 'dw':
                        proc_chance = (17.14 * 2.6) / 60.0

                    if use_expected_value:
                        pass

                    if random.random() < proc_chance:
                        stacks_to_add = 1
                        if self.has_one_versus_many and random.random() < crit_chance:
                            stacks_to_add = 2
                        self.flurry_charges += stacks_to_add

                # [Shado-Pan] Stand Ready Trigger
                if self.stand_ready_active:
                    self.stand_ready_active = False

                    stacks = self.flurry_charges
                    self.flurry_charges = 0

                    if stacks > 0:
                        flurry_coeff = 0.6
                        flurry_base = flurry_coeff * self.attack_power * self.agility * stacks

                        mitigation = self.get_physical_mitigation()
                        flurry_base *= mitigation

                        f_mod = 1.0 + self.versatility

                        if self.has_restore_balance and self.xuen_active:
                            f_mod *= 1.05
                        f_mod *= 0.7

                        flurry_crit = self.crit
                        if self.has_pride_of_pandaria:
                            flurry_crit += 0.15

                        if use_expected_value:
                             flurry_dmg = flurry_base * f_mod * (1 + (flurry_crit * (crit_mult - 1)))
                        else:
                             flurry_dmg = flurry_base * f_mod * (1 + (flurry_crit * (crit_mult - 1)))

                        step_damage += flurry_dmg
                        self.record_damage(flurry_dmg)

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
                            "timestamp": elapsed + time_to_swing
                        })

                        if self.has_shado_over_battlefield:
                            sob_coeff = 0.52
                            sob_base = sob_coeff * self.attack_power * self.agility * stacks
                            sob_mod = 1.0 + self.versatility
                            if getattr(self, 'has_universal_energy', False):
                                sob_mod *= 1.15
                            if self.has_restore_balance and self.xuen_active:
                                sob_mod *= 1.05

                            eff_targets = self.target_count
                            scale = 1.0
                            if eff_targets > 8:
                                scale = (8.0 / eff_targets) ** 0.5

                            if use_expected_value:
                                sob_total = sob_base * sob_mod * eff_targets * scale * (1 + (flurry_crit * (crit_mult - 1)))
                            else:
                                sob_total = sob_base * sob_mod * eff_targets * scale * (1 + (flurry_crit * (crit_mult - 1)))

                            step_damage += sob_total
                            self.record_damage(sob_total)

                            if damage_meter is not None:
                                damage_meter['Shado Over Battlefield'] = damage_meter.get('Shado Over Battlefield', 0) + sob_total

                            log_entries.append({
                                "Action": "Shado Over Battlefield",
                                "Expected DMG": sob_total,
                                "source": "passive",
                                "timestamp": elapsed + time_to_swing
                            })

                        if self.has_high_impact:
                            hi_coeff = 1.0
                            hi_base = hi_coeff * self.attack_power * self.agility * stacks

                            hi_mod = 1.0 + self.versatility
                            if self.has_restore_balance and self.xuen_active:
                                hi_mod *= 1.05

                            eff_targets = self.target_count
                            scale = 1.0
                            if eff_targets > 8:
                                scale = (8.0 / eff_targets) ** 0.5

                            if use_expected_value:
                                hi_total = hi_base * hi_mod * eff_targets * scale * (1 + (flurry_crit * (crit_mult - 1)))
                            else:
                                hi_total = hi_base * hi_mod * eff_targets * scale * (1 + (flurry_crit * (crit_mult - 1)))

                            step_damage += hi_total
                            self.record_damage(hi_total)

                            if damage_meter is not None:
                                damage_meter['High Impact'] = damage_meter.get('High Impact', 0) + hi_total


                # Handle Thunderfist Event
                if thunderfist_proc:
                    tf_mod = 1.0 + self.versatility
                    if self.zenith_active and getattr(self, 'has_weapon_of_wind', False):
                        tf_mod *= 1.10

                    if self.has_restore_balance and self.xuen_active:
                        tf_mod *= 1.05

                    if getattr(self, 'has_universal_energy', False):
                        tf_mod *= 1.15

                    tf_crit = self.crit

                    if use_expected_value:
                        tf_expected = (tf_base * tf_mod) * (1 + (tf_crit * (crit_mult - 1)))
                    else:
                        is_crit = random.random() < tf_crit
                        tf_expected = (tf_base * tf_mod) * (crit_mult if is_crit else 1.0)
                        if is_crit: tf_crit = 1.0

                    step_damage += tf_expected
                    self.record_damage(tf_expected)

                    if damage_meter is not None:
                        damage_meter['Thunderfist'] = damage_meter.get('Thunderfist', 0) + tf_expected

                    tf_breakdown = {
                        'base': int(tf_base),
                        'modifiers': ['Versatility: x%.2f' % (1.0 + self.versatility)],
                        'crit_sources': ['Base: %.1f%%' % (self.crit*100)],
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
                        "timestamp": elapsed + time_to_swing
                    })

            # After Loop: Decrease Swing Timer by actual elapsed step
            self.swing_timer -= step
            total_damage += step_damage

            # --- End Auto Attack Logic ---

            self.simulation_time += step

            if self.jade_serpent_cdr_active:
                self.jade_serpent_cdr_duration -= step
                if self.jade_serpent_cdr_duration <= 0:
                    self.jade_serpent_cdr_active = False
                    self.cooldown_recovery_rate = 1.0

            if self.conduit_window_timer > 0:
                self.conduit_window_timer -= step
                if self.conduit_window_timer <= 0:
                    self.can_cast_conduit = False

            while self.recent_damage_window and self.recent_damage_window[0][0] <= self.simulation_time - 4.0:
                self.recent_damage_window.pop(0)

            self.energy = min(self.max_energy, self.energy + regen_rate * step)

            if self.has_teb_stacking:
                self.teb_timer -= step
                if self.teb_timer <= 0:
                    self.teb_stacks = min(20, self.teb_stacks + 1)
                    self.teb_timer += 8.0

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

                if self.has_cotc_base:
                    # Tiger Lightning
                    self.xuen_lightning_timer -= step
                    if self.xuen_lightning_timer <= 0:
                        self.xuen_lightning_timer += 1.0
                        tl_targets = min(self.target_count, 3)
                        # Corrected AP Logic: 0.257 * AP(1.0) * Agility
                        tl_base = 0.257 * self.attack_power * self.agility

                        tl_mod = 1.0 + self.versatility
                        if self.has_universal_energy:
                            tl_mod *= 1.15
                        if self.has_restore_balance:
                            tl_mod *= 1.05

                        crit_m = 2.0
                        if use_expected_value:
                             tl_mod *= (1 + (self.crit * (crit_m - 1)))
                        else:
                             if random.random() < self.crit:
                                 tl_mod *= crit_m

                        tl_total = tl_base * tl_mod * tl_targets
                        total_damage += tl_total
                        self.record_damage(tl_total)
                        if damage_meter is not None:
                             damage_meter['Xuen: Tiger Lightning'] = damage_meter.get('Xuen: Tiger Lightning', 0) + tl_total
                        log_entries.append({
                            "Action": "Xuen: Tiger Lightning",
                            "Expected DMG": tl_total,
                            "source": "passive",
                            "timestamp": elapsed
                        })

                    # Empowered Lightning
                    self.xuen_empowered_timer -= step
                    if self.xuen_empowered_timer <= 0:
                        self.xuen_empowered_timer += 4.0
                        recent = self.get_damage_last_4s()
                        el_base = recent * 0.08
                        el_total = el_base

                        total_damage += el_total
                        self.record_damage(el_total)
                        if damage_meter is not None:
                             damage_meter['Xuen: Empowered Lightning'] = damage_meter.get('Xuen: Empowered Lightning', 0) + el_total
                        log_entries.append({
                            "Action": "Xuen: Empowered Lightning",
                            "Expected DMG": el_total,
                            "source": "passive",
                            "timestamp": elapsed
                        })


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

            if self.is_channeling:
                self.channel_time_remaining -= step
                self.time_until_next_tick -= step
                if self.time_until_next_tick <= 1e-6:
                    if self.channel_ticks_remaining > 0:
                        spell = self.current_channel_spell
                        tick_idx = spell.total_ticks - self.channel_ticks_remaining
                        tick_dmg, breakdown = spell.calculate_tick_damage(self, tick_idx=tick_idx, use_expected_value=use_expected_value)
                        total_damage += tick_dmg
                        self.record_damage(tick_dmg)

                        if damage_meter is not None and spell:
                            damage_meter[spell.abbr] = damage_meter.get(spell.abbr, 0) + tick_dmg
                        self.channel_ticks_remaining -= 1
                        self.time_until_next_tick += self.channel_tick_interval

                        log_entries.append({
                            "Action": f"{spell.abbr} (Tick)",
                            "Expected DMG": tick_dmg,
                            "Breakdown": breakdown,
                            "source": "active",
                            "timestamp": elapsed
                        })

                if self.channel_time_remaining <= 1e-6 or self.channel_ticks_remaining <= 0:
                    # [COTC] Conduit Finish: Unity Within
                    if self.current_channel_spell.abbr == 'Conduit' and self.has_unity_within:
                         tick_dmg, breakdown = self.current_channel_spell.calculate_tick_damage(self, tick_idx=0, use_expected_value=use_expected_value)
                         burst_dmg = tick_dmg * 2.0
                         total_damage += burst_dmg
                         self.record_damage(burst_dmg)

                         if damage_meter is not None:
                             damage_meter['Conduit (Unity Within)'] = damage_meter.get('Conduit (Unity Within)', 0) + burst_dmg

                         log_entries.append({
                            "Action": "Conduit: Unity Within",
                            "Expected DMG": burst_dmg,
                            "Breakdown": breakdown,
                            "source": "passive",
                            "timestamp": elapsed
                        })


                    if self.current_channel_spell.abbr == 'FOF':
                        if self.has_momentum_boost:
                            self.momentum_buff_active = True
                            self.momentum_buff_duration = 8.0

                        if getattr(self, 'has_jadefire_stomp', False):
                            # Corrected: AP * Agility
                            jf_base = 0.4 * self.attack_power * self.agility

                            jf_mod = 1.0 + self.versatility
                            if self.zenith_active and getattr(self, 'has_weapon_of_wind', False):
                                jf_mod *= 1.10
                            if getattr(self, 'has_universal_energy', False):
                                jf_mod *= 1.15
                            if self.has_restore_balance and self.xuen_active:
                                jf_mod *= 1.05

                            eff_target_count = self.target_count
                            poj_bonus = 0.0
                            if getattr(self, 'has_path_of_jade', False):
                                poj_bonus = min(0.50, 0.10 * eff_target_count)
                                jf_mod *= (1.0 + poj_bonus)

                            if getattr(self, 'has_singularly_focused_jade', False):
                                jf_mod *= 4.0
                                eff_target_count = 1

                            scale = 1.0
                            if eff_target_count > 5:
                                scale = (5.0 / eff_target_count) ** 0.5

                            if use_expected_value:
                                jf_total = jf_base * jf_mod * eff_target_count * scale * (1 + (self.crit * (crit_mult - 1)))
                            else:
                                jf_total = jf_base * jf_mod * eff_target_count * scale * (1 + (self.crit * (crit_mult - 1)))

                            total_damage += jf_total
                            self.record_damage(jf_total)

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
                                "timestamp": elapsed
                            })

                    self.is_channeling = False
                    self.current_channel_spell = None
                    self.channel_mastery_snapshot = False
            elapsed += step
        return total_damage, log_entries
