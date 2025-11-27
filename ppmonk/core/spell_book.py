import random
import math
from .talents import TalentManager

class Spell:
    def __init__(self, abbr, ap_coeff, name=None, energy=0, chi_cost=0, chi_gen=0, cd=0, cd_haste=False,
                 cast_time=0, cast_haste=False, is_channeled=False, ticks=1, req_talent=False, gcd_override=None,
                 max_charges=1, category='', aoe_type='single', damage_type='Physical'):
        self.abbr = abbr
        self.name = name if name else abbr
        self.ap_coeff = ap_coeff
        self.energy_cost = energy
        self.category = category
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
        self.max_charges = max_charges
        self.charges = self.max_charges
        self.current_cd = 0.0
        self.is_combo_strike = True
        self.haste_dmg_scaling = False
        self.tick_dmg_ramp = 0.0
        self.triggers_combat_wisdom = False
        self.triggers_sharp_reflexes = False
        self.aoe_type = aoe_type # 'single', 'cleave', 'soft_cap', 'uncapped'
        self.damage_type = damage_type # 'Physical' or 'Nature'

        self.modifiers = [] # List[Tuple[str, float]]
        self.crit_modifiers = [] # List[Tuple[str, float]]

        # Legacy attributes
        self.damage_multiplier = 1.0
        self.bonus_crit_chance = 0.0
        self.crit_damage_bonus = 0.0

    def add_modifier(self, name, value):
        self.modifiers.append((name, value))

    def add_crit_modifier(self, name, value):
        self.crit_modifiers.append((name, value))

    def update_tick_coeff(self):
        self.tick_coeff = self.ap_coeff / self.total_ticks if self.total_ticks > 0 else self.ap_coeff

    def get_effective_cd(self, player):
        base = self.base_cd
        if self.abbr in ['SOTWL', 'WDP'] and getattr(player, 'has_communion_with_wind', False):
            base -= 5.0
        # Efficient Training (Zenith CD -10s)
        if self.abbr == 'Zenith' and getattr(player, 'has_stand_ready', False):
             pass

        # [COTC] Xuen Bond CD reduction
        if self.abbr == 'Xuen' and getattr(player, 'has_xuens_bond', False):
            base -= 30.0

        if self.cd_haste: return base / (1.0 + player.haste)
        return max(0.0, base)

    def get_effective_cast_time(self, player):
        base = self.base_cast_time
        # [COTC] Jade Serpent CDR -> FOF 50% duration
        if self.abbr == 'FOF' and player.jade_serpent_cdr_active:
            base *= 0.5

        if self.cast_haste: return base / (1.0 + player.haste)
        return base

    def get_tick_interval(self, player):
        if not self.is_channeled or self.total_ticks <= 0: return 0
        return self.get_effective_cast_time(player) / self.total_ticks

    def is_usable(self, player, other_spells=None):
        if not self.is_known: return False
        if self.charges < 1: return False

        e_cost = self.energy_cost
        if player.energy < e_cost: return False

        cost = self.chi_cost

        if self.abbr == 'BOK' and player.combo_breaker_stacks > 0:
            cost = 0

        if self.abbr == 'SCK' and player.dance_of_chiji_stacks > 0:
            cost = 0

        if player.zenith_active and self.chi_cost > 0:
            cost = max(0, cost - 1)

        if player.chi < cost: return False
        return True

    def cast(self, player, other_spells=None, damage_meter=None, force_proc_glory=False, force_proc_reset=False, use_expected_value=False):
        player.energy -= self.energy_cost

        actual_chi_cost = self.chi_cost

        is_combo_breaker = False
        if self.abbr == 'BOK' and player.combo_breaker_stacks > 0:
            actual_chi_cost = 0
            player.combo_breaker_stacks -= 1
            is_combo_breaker = True

            if player.has_energy_burst:
                player.chi = min(player.max_chi, player.chi + 1)

            if getattr(player, 'has_rushing_wind_kick', False):
                # RWK Proc
                chance = 0.40
                if use_expected_value:
                    pass
                else:
                    if random.random() < chance:
                        player.rwk_ready = True

        is_dance_of_chiji = False
        if self.abbr == 'SCK' and player.dance_of_chiji_stacks > 0:
            actual_chi_cost = 0
            player.dance_of_chiji_stacks -= 1
            is_dance_of_chiji = True

            if getattr(player, 'has_sequenced_strikes', False):
                player.combo_breaker_stacks = min(2, player.combo_breaker_stacks + 1)

        if not is_combo_breaker and not is_dance_of_chiji:
             if player.zenith_active and self.chi_cost > 0:
                actual_chi_cost = max(0, self.chi_cost - 1)

        obsidian_bonus = 0
        if self.abbr == 'BOK' and player.zenith_active and getattr(player, 'has_obsidian_spiral', False):
             obsidian_bonus = 1

        player.chi = max(0, player.chi - actual_chi_cost)
        player.chi = min(player.max_chi, player.chi + self.chi_gen + obsidian_bonus)

        tp_proc_chance = 0.08
        if getattr(player, 'has_memory_of_monastery', False):
            tp_proc_chance = 0.10

        if self.charges == self.max_charges:
            self.current_cd = self.get_effective_cd(player)
        self.charges -= 1

        if self.gcd_override is not None:
            player.gcd_remaining = self.gcd_override
        else:
            player.gcd_remaining = 1.0

        # Hit Combo
        triggers_mastery = self.is_combo_strike and (
                    player.last_spell_name is None or player.last_spell_name != self.abbr)

        if triggers_mastery and getattr(player, 'has_hit_combo', False):
            player.hit_combo_stacks = min(5, player.hit_combo_stacks + 1)

        if self.is_combo_strike and not triggers_mastery and player.last_spell_name == self.abbr:
             if getattr(player, 'has_hit_combo', False):
                 player.hit_combo_stacks = 0

        player.last_spell_name = self.abbr

        if self.abbr == 'TP' and getattr(player, 'has_combo_breaker', False):
            if not use_expected_value:
                if random.random() < tp_proc_chance:
                    player.combo_breaker_stacks = min(2, player.combo_breaker_stacks + 1)

        if self.chi_cost > 0 and getattr(player, 'has_dance_of_chiji', False):
            chance = 0.015 * self.chi_cost
            if not use_expected_value:
                if random.random() < chance:
                    player.dance_of_chiji_stacks = min(2, player.dance_of_chiji_stacks + 1)
                    player.dance_of_chiji_duration = 15.0

        if self.abbr in ['SOTWL', 'WDP']:
            if getattr(player, 'has_revolving_whirl', False):
                 if not use_expected_value:
                    player.dance_of_chiji_stacks = min(2, player.dance_of_chiji_stacks + 1)
                    player.dance_of_chiji_duration = 15.0
            if getattr(player, 'has_echo_technique', False):
                 if not use_expected_value:
                    player.combo_breaker_stacks = min(2, player.combo_breaker_stacks + 1)

            if getattr(player, 'has_knowledge_of_broken_temple', False):
                player.totm_stacks = min(player.max_totm_stacks, player.totm_stacks + 4)

            if getattr(player, 'has_thunderfist', False):
                 player.thunderfist_stacks += (4 + player.target_count)

            # [COTC] Heart of the Jade Serpent
            if player.has_heart_of_jade_serpent:
                player.jade_serpent_cdr_active = True
                player.jade_serpent_cdr_duration = 8.0
                player.cooldown_recovery_rate = 1.75

        # 1. Sharp Reflexes
        if self.triggers_sharp_reflexes and other_spells:
            reduction = 1.0
            if player.zenith_active:
                reduction += 1.0
            if 'RSK' in other_spells:
                other_spells['RSK'].current_cd = max(0, other_spells['RSK'].current_cd - reduction)
            if 'FOF' in other_spells:
                other_spells['FOF'].current_cd = max(0, other_spells['FOF'].current_cd - reduction)

        # 2. TotM Stacking
        if self.abbr == 'TP' and player.has_totm:
            player.totm_stacks = min(player.max_totm_stacks, player.totm_stacks + 1)

            # [COTC] Courage of the White Tiger (Trigger Check)
            should_proc_courage = False
            ppm = 4.0
            chance = ppm * (player.base_swing_time / 60.0)

            if player.guaranteed_courage_proc:
                should_proc_courage = True
                player.guaranteed_courage_proc = False
            elif player.has_courage_of_white_tiger:
                 if use_expected_value:
                     # EV Logic: Don't proc, but add damage
                     should_proc_courage = False # No state change
                 else:
                     if random.random() < chance:
                         should_proc_courage = True

            courage_dmg = 3.375 * player.attack_power * player.agility
            c_mod = 1.0 + player.versatility
            c_mod *= player.get_physical_mitigation()
            if player.has_restore_balance and player.xuen_active:
                    c_mod *= 1.05
            c_crit = player.crit
            c_mult = 2.0

            if should_proc_courage:
                c_final = courage_dmg * c_mod * (1 + (c_crit * (c_mult - 1)))
                player.record_damage(c_final)
                if damage_meter is not None:
                     damage_meter['Courage of White Tiger'] = damage_meter.get('Courage of White Tiger', 0) + c_final
                player.advance_inner_compass()
                player.niuzao_ready = True

        extra_damage = 0.0
        extra_damage_details = []

        # EV for Courage of White Tiger
        if use_expected_value and player.has_courage_of_white_tiger and self.abbr == 'TP' and player.has_totm:
             # Calculate as above
             c_final_ev = (courage_dmg * c_mod * (1 + (c_crit * (c_mult - 1)))) * chance
             extra_damage += c_final_ev
             extra_damage_details.append({
                'name': 'Courage (EV)',
                'damage': c_final_ev,
                'chance': chance
             })

        # [Shado-Pan] FOF Consumption of Flurry Charges
        if self.abbr == 'FOF' and player.flurry_charges > 0:
            consumed = player.flurry_charges
            player.flurry_charges = 0
            flurry_total, sob_total, hi_total = self._calculate_flurry_strikes_damage(player, consumed, scale=1.0, use_expected_value=use_expected_value)
            extra_damage += flurry_total + sob_total + hi_total

            if damage_meter is not None:
                if flurry_total > 0: damage_meter['Flurry Strikes'] = damage_meter.get('Flurry Strikes', 0) + flurry_total
                if sob_total > 0: damage_meter['Shado Over Battlefield'] = damage_meter.get('Shado Over Battlefield', 0) + sob_total
                if hi_total > 0: damage_meter['High Impact'] = damage_meter.get('High Impact', 0) + hi_total

            extra_damage_details.append({
                'name': f'Flurry Burst (FOF) x{consumed}',
                'damage': flurry_total,
                'sob_damage': sob_total,
                'hi_damage': hi_total
            })

        # [Shado-Pan] Wisdom of the Wall
        if getattr(player, 'has_wisdom_of_the_wall', False) and player.zenith_active:
            if self.abbr in ['RSK', 'SCK']:
                 flurry_total, sob_total, hi_total = self._calculate_flurry_strikes_damage(player, 3, scale=1.0, use_expected_value=use_expected_value)
                 extra_damage += flurry_total + sob_total + hi_total
                 if damage_meter is not None:
                    if flurry_total > 0: damage_meter['Flurry Strikes'] = damage_meter.get('Flurry Strikes', 0) + flurry_total
                    if sob_total > 0: damage_meter['Shado Over Battlefield'] = damage_meter.get('Shado Over Battlefield', 0) + sob_total
                    if hi_total > 0: damage_meter['High Impact'] = damage_meter.get('High Impact', 0) + hi_total
                 extra_damage_details.append({
                    'name': f'Wisdom of Wall x3',
                    'damage': flurry_total
                 })

        # Jade Ignition
        if self.abbr == 'SCK' and getattr(player, 'has_jade_ignition', False):
            ji_base = 1.80 * player.attack_power * player.agility
            ji_mods = 1.0 + player.versatility
            if getattr(player, 'has_hit_combo', False):
                ji_mods *= (1.0 + player.hit_combo_stacks * 0.01)
            if getattr(player, 'has_universal_energy', False):
                ji_mods *= 1.15
            if player.zenith_active and getattr(player, 'has_weapon_of_wind', False):
                ji_mods *= 1.10
            if player.has_restore_balance and player.xuen_active:
                ji_mods *= 1.05

            ji_crit_chance = player.crit + (player.teb_active_bonus if player.zenith_active else 0.0)

            if use_expected_value:
                # EV: Base * Mod * (1 + Crit * (2.0 - 1))
                ji_final = ji_base * ji_mods * (1 + ji_crit_chance) # CritMult is 2.0
                ji_final = self._apply_aoe_scaling(ji_final, player, 'soft_cap')
                extra_damage += ji_final
                extra_damage_details.append({
                    'name': 'Jade Ignition (EV)',
                    'damage': ji_final,
                    'crit_chance': ji_crit_chance
                })
            else:
                is_crit_ji = random.random() < ji_crit_chance
                if is_crit_ji:
                    ji_base *= 2.0
                ji_final = self._apply_aoe_scaling(ji_base * ji_mods, player, 'soft_cap')
                extra_damage += ji_final
                if damage_meter is not None:
                    damage_meter['Jade Ignition'] = damage_meter.get('Jade Ignition', 0) + ji_final
                extra_damage_details.append({
                    'name': 'Jade Ignition',
                    'damage': ji_final,
                    'crit': is_crit_ji
                })

        # [COTC] Strength of the Black Ox
        if self.abbr == 'BOK' and player.niuzao_ready:
            player.niuzao_ready = False
            # Refund 2 TotM
            player.totm_stacks = min(player.max_totm_stacks, player.totm_stacks + 2)

            stomp_base = 2.0 * player.attack_power * player.agility
            stomp_mod = 1.0 + player.versatility
            stomp_mod *= player.get_physical_mitigation()
            if player.has_restore_balance and player.xuen_active:
                stomp_mod *= 1.05

            s_crit = player.crit
            s_mult = 2.0

            if use_expected_value:
                 stomp_ev = stomp_base * stomp_mod * (1 + (s_crit * (s_mult - 1)))
                 s_scale = self._get_aoe_modifier(player.target_count, 5)
                 stomp_total = stomp_ev * player.target_count * s_scale
            else:
                s_scale = self._get_aoe_modifier(player.target_count, 5)
                stomp_total = stomp_base * stomp_mod * player.target_count * s_scale * (1 + (s_crit * (s_mult - 1)))

            extra_damage += stomp_total
            if damage_meter is not None:
                damage_meter['Niuzao Stomp'] = damage_meter.get('Niuzao Stomp', 0) + stomp_total

            player.advance_inner_compass()
            extra_damage_details.append({
                'name': 'Niuzao Stomp',
                'damage': stomp_total
            })

        # TotM Consumption
        if self.abbr == 'BOK' and player.has_totm:
            if player.totm_stacks > 0:
                extra_hits = player.totm_stacks
                dmg_per_hit = 0.847 * player.attack_power * player.agility

                hc_mod = 1.0
                if getattr(player, 'has_hit_combo', False):
                    hc_mod = 1.0 + (player.hit_combo_stacks * 0.01)

                crit_chance = player.crit + self.bonus_crit_chance + (player.teb_active_bonus if player.zenith_active else 0.0)
                crit_m = 2.0 + self.crit_damage_bonus + player.teb_crit_dmg_bonus

                ww_mod = 1.10 if (player.zenith_active and getattr(player, 'has_weapon_of_wind', False)) else 1.0

                base_mult = (1 + player.versatility) * hc_mod * ww_mod
                if player.has_restore_balance and player.xuen_active:
                    base_mult *= 1.05

                if use_expected_value:
                    total_extra = extra_hits * dmg_per_hit * base_mult * (1 + crit_chance * (crit_m - 1))
                else:
                    is_crit = random.random() < crit_chance
                    final_crit_m = crit_m if is_crit else 1.0
                    total_extra = extra_hits * dmg_per_hit * base_mult * final_crit_m

                extra_damage += total_extra

                if damage_meter is not None:
                    damage_meter['TotM'] = damage_meter.get('TotM', 0) + total_extra

                extra_damage_details.append({
                    'name': 'Teachings of the Monastery',
                    'damage': total_extra,
                    'hits': extra_hits,
                    'ev_mode': use_expected_value
                })

                refunded = False
                if player.has_xuens_guidance:
                     if not use_expected_value:
                        if random.random() < 0.15:
                            player.totm_stacks = 1
                            refunded = True
                if not refunded:
                    player.totm_stacks = 0

            should_reset = False
            if force_proc_reset:
                should_reset = True
            elif not use_expected_value and random.random() < 0.12:
                should_reset = True

            if should_reset and other_spells and 'RSK' in other_spells:
                other_spells['RSK'].current_cd = 0.0

        # Glory of the Dawn
        if self.abbr == 'RSK' and player.has_glory_of_the_dawn:
            should_proc_glory = False
            chance = player.haste
            if force_proc_glory:
                should_proc_glory = True
            elif not use_expected_value and random.random() < chance:
                should_proc_glory = True

            glory_dmg = 1.0 * player.attack_power * player.agility
            hc_mod = 1.0
            if getattr(player, 'has_hit_combo', False):
                hc_mod = 1.0 + (player.hit_combo_stacks * 0.01)

            crit_chance = player.crit + self.bonus_crit_chance + (player.teb_active_bonus if player.zenith_active else 0.0)
            crit_m = 2.0 + self.crit_damage_bonus + player.teb_crit_dmg_bonus
            ww_mod = 1.10 if (player.zenith_active and getattr(player, 'has_weapon_of_wind', False)) else 1.0

            base_glory = glory_dmg * (1 + player.versatility) * hc_mod * ww_mod
            if player.has_restore_balance and player.xuen_active:
                base_glory *= 1.05

            if should_proc_glory:
                is_crit = random.random() < crit_chance
                final_m = crit_m if is_crit else 1.0
                final_glory = base_glory * final_m

                extra_damage += final_glory
                player.chi = min(player.max_chi, player.chi + 1)
                if damage_meter is not None:
                    damage_meter['Glory of Dawn'] = damage_meter.get('Glory of Dawn', 0) + final_glory

                extra_damage_details.append({
                    'name': 'Glory of the Dawn',
                    'damage': final_glory,
                    'crit': is_crit
                })
            elif use_expected_value:
                # Add Expected Damage
                ev_glory = base_glory * (1 + crit_chance * (crit_m - 1)) * chance
                extra_damage += ev_glory
                extra_damage_details.append({
                    'name': 'Glory of the Dawn (EV)',
                    'damage': ev_glory,
                    'chance': chance
                })

        # Zenith
        if self.abbr == 'Zenith':
            player.zenith_active = True
            dur = 15.0
            if getattr(player, 'has_drinking_horn_cover', False):
                dur = 20.0
            player.zenith_duration = dur

            if getattr(player, 'has_stand_ready', False):
                player.stand_ready_active = True
                player.flurry_charges += 10

            if other_spells and 'RSK' in other_spells:
                other_spells['RSK'].current_cd = 0
            player.chi = min(player.max_chi, player.chi + 2)

            consumed_stacks = player.teb_stacks
            player.teb_stacks = 0
            player.teb_active_bonus = consumed_stacks * 0.02

            zenith_burst = 10.0 * player.attack_power * player.agility
            hc_mod = 1.0
            if getattr(player, 'has_hit_combo', False):
                 hc_mod = 1.0 + (player.hit_combo_stacks * 0.01)

            ww_mod = 1.10 if (getattr(player, 'has_weapon_of_wind', False)) else 1.0
            if getattr(player, 'has_weapons_of_the_wall', False):
                 ww_mod *= 1.20

            zenith_burst = zenith_burst * (1.0 + player.versatility) * hc_mod * ww_mod
            if player.has_restore_balance and player.xuen_active:
                zenith_burst *= 1.05

            zenith_final = self._apply_aoe_scaling(zenith_burst, player, 'soft_cap')
            extra_damage += zenith_final

            extra_damage_details.append({
                'name': 'Zenith Blast',
                'damage': zenith_final,
                'crit': False,
                'teb_consumed': consumed_stacks
            })

        if self.abbr == 'Xuen':
            player.xuen_active = True
            player.xuen_duration = 24.0
            player.update_stats()
            if player.has_cotc_base:
                player.can_cast_conduit = True
                player.conduit_window_timer = 60.0
                player.advance_inner_compass()
                player.guaranteed_courage_proc = True

        if self.abbr == 'Conduit':
             player.advance_inner_compass()


        # Flurry of Xuen
        if getattr(player, 'has_flurry_of_xuen', False):
            should_proc_fox = False
            is_guaranteed = (self.abbr == 'Xuen')
            if is_guaranteed:
                should_proc_fox = True
            elif not use_expected_value and random.random() < 0.10:
                should_proc_fox = True

            fox_base = 3.92 * player.attack_power * player.agility
            fox_mod = 1.0 + player.versatility
            fox_crit_chance = player.crit
            if is_guaranteed: fox_crit_chance = 1.0

            fox_dmg_unit = self._apply_aoe_scaling(fox_base * fox_mod, player, 'soft_cap')
            crit_m = 2.0 + self.crit_damage_bonus + player.teb_crit_dmg_bonus

            if player.has_restore_balance and player.xuen_active:
                    fox_dmg_unit *= 1.05

            if should_proc_fox:
                fox_expected = fox_dmg_unit * (1 + (fox_crit_chance * (crit_m - 1)))
                extra_damage += fox_expected
                extra_damage_details.append({
                    'name': 'Flurry of Xuen',
                    'damage': fox_expected,
                    'guaranteed': is_guaranteed
                })
            elif use_expected_value:
                 chance = 0.10
                 fox_ev = fox_dmg_unit * (1 + (fox_crit_chance * (crit_m - 1))) * chance
                 extra_damage += fox_ev
                 extra_damage_details.append({
                    'name': 'Flurry of Xuen (EV)',
                    'damage': fox_ev,
                    'chance': chance
                })


        if self.triggers_combat_wisdom and getattr(player, 'combat_wisdom_ready', False):
            player.combat_wisdom_ready = False
            player.combat_wisdom_timer = 15.0
            eh_base = 1.2 * player.attack_power * player.agility
            eh_crit_chance = player.crit + 0.15
            if player.zenith_active:
                eh_crit_chance += player.teb_active_bonus

            mult = (1.0 + player.versatility)
            if player.has_restore_balance and player.xuen_active:
                mult *= 1.05

            crit_m = 2.0 + self.crit_damage_bonus + player.teb_crit_dmg_bonus

            if use_expected_value:
                eh_dmg = eh_base * mult * (1 + eh_crit_chance * (crit_m - 1))
            else:
                is_crit_eh = random.random() < eh_crit_chance
                eh_dmg = eh_base * mult * (crit_m if is_crit_eh else 1.0)

            extra_damage += eh_dmg

            extra_damage_details.append({
                'name': 'Expel Harm (Passive)',
                'damage': eh_dmg,
                'ev_mode': use_expected_value
            })

        if self.is_channeled:
            cast_t = self.get_effective_cast_time(player)
            player.is_channeling = True
            player.current_channel_spell = self
            player.channel_time_remaining = cast_t
            player.channel_ticks_remaining = self.total_ticks
            player.channel_tick_interval = self.get_tick_interval(player)
            player.time_until_next_tick = player.channel_tick_interval
            player.channel_mastery_snapshot = triggers_mastery
            player.channel_docj_snapshot = is_dance_of_chiji

            breakdown = {
                'base': 0,
                'modifiers': [],
                'crit_sources': [],
                'extra_events': extra_damage_details
            }
            return 0.0, breakdown
        else:
            base_dmg, breakdown = self.calculate_tick_damage(player, mastery_override=triggers_mastery, use_expected_value=use_expected_value)
            total_damage = base_dmg + extra_damage

            if extra_damage_details:
                breakdown['extra_events'] = extra_damage_details
                breakdown['extra_damage_total'] = extra_damage

            # [COTC] Record Total Spell Damage
            player.record_damage(total_damage)

            if self.abbr == 'RSK' and getattr(player, 'rwk_ready', False):
                 player.rwk_ready = False

            if self.abbr == 'RSK' and getattr(player, 'has_xuens_battlegear', False):
                crit_c = breakdown['final_crit']
                if not use_expected_value:
                    if random.random() < crit_c:
                         if other_spells and 'FOF' in other_spells:
                             other_spells['FOF'].current_cd = max(0, other_spells['FOF'].current_cd - 4.0)

            return total_damage, breakdown

    def _apply_aoe_scaling(self, damage_per_target, player, aoe_type):
        target_count = player.target_count
        if aoe_type == 'single':
            return damage_per_target

        elif aoe_type == 'cleave':
            total = damage_per_target
            if target_count > 1:
                secondary_targets = min(target_count - 1, 2)
                total += damage_per_target * 0.80 * secondary_targets
            return total

        elif aoe_type == 'soft_cap':
            return damage_per_target * target_count * self._get_aoe_modifier(target_count, 5)

        elif aoe_type == 'uncapped':
             return damage_per_target * target_count

        return damage_per_target

    def _calculate_flurry_strikes_damage(self, player, stacks, scale=1.0, use_expected_value=False):
        # Base: 0.6 AP per stack
        flurry_base = 0.6 * player.attack_power * player.agility * stacks * scale

        # Physical Mitigation
        mitigation = player.get_physical_mitigation()
        flurry_base *= mitigation

        # Mods
        f_mod = 1.0 + player.versatility

        # Pride of Pandaria
        crit_c = player.crit
        if getattr(player, 'has_pride_of_pandaria', False):
            crit_c += 0.15

        crit_mult = 2.0
        if player.has_restore_balance and player.xuen_active:
             f_mod *= 1.05

        if use_expected_value:
             flurry_total = flurry_base * f_mod * (1 + (crit_c * (crit_mult - 1)))
        else:
             flurry_total = flurry_base * f_mod * (1 + (crit_c * (crit_mult - 1)))

        # Shado Over Battlefield (Nature AOE)
        sob_total = 0.0
        if getattr(player, 'has_shado_over_battlefield', False):
            sob_base = 0.52 * player.attack_power * player.agility * stacks
            sob_mod = 1.0 + player.versatility
            if getattr(player, 'has_universal_energy', False):
                sob_mod *= 1.15
            if player.has_restore_balance and player.xuen_active:
                sob_mod *= 1.05

            sob_scale = self._get_aoe_modifier(player.target_count, 8)
            sob_total = sob_base * sob_mod * player.target_count * sob_scale * (1 + (crit_c * (crit_mult - 1)))

        # High Impact (Physical AOE)
        hi_total = 0.0
        if getattr(player, 'has_high_impact', False):
            hi_base = 1.0 * player.attack_power * player.agility * stacks
            hi_mod = 1.0 + player.versatility
            if player.has_restore_balance and player.xuen_active:
                hi_mod *= 1.05

            hi_scale = self._get_aoe_modifier(player.target_count, 8)
            hi_total = hi_base * hi_mod * player.target_count * hi_scale * (1 + (crit_c * (crit_mult - 1)))

        return flurry_total, sob_total, hi_total

    def _get_aoe_modifier(self, target_count, soft_cap):
        if target_count <= soft_cap:
            return 1.0
        else:
            return math.sqrt(soft_cap / float(target_count))

    def calculate_tick_damage(self, player, mastery_override=None, tick_idx=0, use_expected_value=False):
        is_rwk = (self.abbr == 'RSK' and getattr(player, 'rwk_ready', False))

        current_ap_coeff = self.tick_coeff
        if is_rwk:
            current_ap_coeff = 1.7975

        base_dmg_per_target = current_ap_coeff * player.attack_power * player.agility

        modifiers = []
        crit_sources = []

        # 1. Multipliers
        current_mult = 1.0

        if self.damage_type == 'Physical' and not is_rwk:
             mitigation = player.get_physical_mitigation()
             current_mult *= mitigation
             modifiers.append(f"PhysicalDR: x{mitigation:.3f}")

        for name, val in self.modifiers:
            current_mult *= val
            modifiers.append(f"{name}: x{val:.2f}")

        if is_rwk:
             rwk_bonus = min(0.30, 0.06 * player.target_count)
             if rwk_bonus > 0:
                 mod_val = 1.0 + rwk_bonus
                 current_mult *= mod_val
                 modifiers.append(f"RWK_Targets: x{mod_val:.2f}")

        if self.abbr == 'SCK':
             is_docj = getattr(player, 'channel_docj_snapshot', False)
             if is_docj:
                 current_mult *= 2.0
                 modifiers.append("DanceOfChiJi: x2.00")

        hidden_mod = 1.0
        if self.abbr == 'RSK': hidden_mod *= 1.70
        if self.abbr == 'SCK': hidden_mod *= 1.10
        if hidden_mod != 1.0:
            current_mult *= hidden_mod
            modifiers.append(f"HiddenAura: x{hidden_mod:.2f}")

        aura_mod = 1.04
        if self.abbr in ['TP', 'BOK', 'RSK', 'SCK', 'FOF', 'WDP', 'SOTWL']:
            aura_mod *= 1.04
        if aura_mod != 1.0:
            current_mult *= aura_mod
            modifiers.append(f"Aura: x{aura_mod:.2f}")

        if self.abbr == 'BOK' and getattr(player, 'has_shadowboxing', False):
            current_mult *= 1.05
            modifiers.append("Shadowboxing: x1.05")

        if self.abbr == 'TP' and getattr(player, 'has_xuens_guidance', False):
             current_mult *= 1.10
             modifiers.append("XuensGuidance: x1.10")

        if getattr(player, 'has_hit_combo', False) and player.hit_combo_stacks > 0:
            hc_mod = 1.0 + (player.hit_combo_stacks * 0.01)
            current_mult *= hc_mod
            modifiers.append(f"HitCombo({player.hit_combo_stacks}): x{hc_mod:.2f}")

        if self.abbr in ['SOTWL', 'WDP'] and getattr(player, 'has_communion_with_wind', False):
             current_mult *= 1.10
             modifiers.append("Communion: x1.10")

        if player.zenith_active and getattr(player, 'has_weapon_of_wind', False):
            current_mult *= 1.10
            modifiers.append("WeaponOfWind: x1.10")

        if getattr(player, 'has_restore_balance', False) and player.xuen_active:
             current_mult *= 1.05
             modifiers.append("RestoreBalance: x1.05")

        is_nature = (self.damage_type == 'Nature')
        if is_rwk: is_nature = True

        if is_nature and getattr(player, 'has_universal_energy', False):
             current_mult *= 1.15
             modifiers.append("UniversalEnergy: x1.15")

        if self.abbr == 'TP' and getattr(player, 'has_memory_of_monastery', False):
             current_mult *= 1.15
             modifiers.append("MemoryOfMonastery: x1.15")

        if self.haste_dmg_scaling:
            h_mod = (1.0 + player.haste)
            current_mult *= h_mod
            modifiers.append(f"HasteScaling: x{h_mod:.2f}")

        if self.tick_dmg_ramp > 0:
            ramp_mod = (1.0 + (tick_idx + 1) * self.tick_dmg_ramp)
            current_mult *= ramp_mod
            modifiers.append(f"TickRamp: x{ramp_mod:.2f}")

        apply_mastery = mastery_override if mastery_override is not None else (
            self.is_channeled and player.channel_mastery_snapshot)
        if apply_mastery:
            m_mod = (1.0 + player.mastery)
            if self.abbr == 'RSK' and getattr(player, 'has_sunfire_spiral', False):
                m_mod = 1.0 + (player.mastery * 1.2)
                modifiers.append(f"Mastery(Sunfire): x{m_mod:.2f}")
            else:
                modifiers.append(f"Mastery: x{m_mod:.2f}")
            current_mult *= m_mod

        v_mod = (1.0 + player.versatility)
        current_mult *= v_mod
        modifiers.append(f"Versatility: x{v_mod:.2f}")

        # 2. Crit Calculation
        base_crit = player.crit
        crit_sources.append(f"PlayerStat: {base_crit*100:.1f}%")

        bonus_crit = self.bonus_crit_chance
        if bonus_crit > 0:
             crit_sources.append(f"LegacyBonus: {bonus_crit*100:.1f}%")

        for name, val in self.crit_modifiers:
            bonus_crit += val
            crit_sources.append(f"{name}: {val*100:.1f}%")

        if self.abbr == 'RSK' and getattr(player, 'has_xuens_battlegear', False):
             bonus_crit += 0.20
             crit_sources.append("XuensBattlegear: 20.0%")

        if self.abbr == 'RSK' and getattr(player, 'has_skyfire_heel', False):
            sfh_bonus = min(0.20, 0.04 * player.target_count)
            bonus_crit += sfh_bonus
            crit_sources.append(f"SkyfireHeel: {sfh_bonus*100:.1f}%")

        if player.zenith_active:
             bonus_crit += player.teb_active_bonus
             crit_sources.append(f"TEB(Active): {player.teb_active_bonus*100:.1f}%")

        final_crit_chance = min(1.0, base_crit + bonus_crit)
        crit_mult = 2.0 + self.crit_damage_bonus + player.teb_crit_dmg_bonus

        # Expected Value
        expected_dmg_single = (base_dmg_per_target * current_mult) * (1 + (final_crit_chance * (crit_mult - 1)))

        # If NOT using Expected Value, roll for crit
        if not use_expected_value:
             is_crit = random.random() < final_crit_chance
             final_mult = crit_mult if is_crit else 1.0
             dmg_single = (base_dmg_per_target * current_mult) * final_mult
             # Use the rolled damage
             expected_dmg_single = dmg_single
             final_crit_chance = 1.0 if is_crit else 0.0 # For breakdown display if needed

        # 3. AOE Scaling
        current_aoe_type = self.aoe_type
        if is_rwk:
             current_aoe_type = 'soft_cap'
        elif self.abbr == 'BOK' and getattr(player, 'has_shadowboxing', False):
            current_aoe_type = 'cleave'

        skyfire_cleave = 0.0
        if self.abbr == 'RSK' and getattr(player, 'has_skyfire_heel', False):
             if player.target_count > 1:
                 extra_count = min(player.target_count - 1, 5)
                 skyfire_cleave = expected_dmg_single * 0.10 * extra_count
                 modifiers.append(f"SkyfireCleave: +{int(skyfire_cleave)} ({extra_count} add.)")

        total_expected_dmg = self._apply_aoe_scaling(expected_dmg_single, player, current_aoe_type)
        total_expected_dmg += skyfire_cleave

        breakdown = {
            'base': int(base_dmg_per_target),
            'modifiers': modifiers,
            'crit_sources': crit_sources,
            'final_crit': final_crit_chance,
            'crit_mult': crit_mult,
            'aoe_type': current_aoe_type,
            'targets': player.target_count,
            'total_dmg_after_aoe': total_expected_dmg
        }

        return total_expected_dmg, breakdown

    def tick_cd(self, dt, player=None):
        rate = 1.0
        if player:
            rate = player.cooldown_recovery_rate

        if self.charges < self.max_charges:
            self.current_cd = max(0, self.current_cd - dt * rate)
            if self.current_cd == 0:
                self.charges += 1
                if self.charges < self.max_charges:
                    self.current_cd = self.base_cd

class CelestialConduit(Spell):
    def is_usable(self, player, other_spells):
        if not super().is_usable(player): return False
        return player.can_cast_conduit

    def calculate_tick_damage(self, player, mastery_override=None, tick_idx=0, use_expected_value=False):
        # 5 * 2.75 * AP
        # Soft Cap 5
        base = 5.0 * 2.75 * player.attack_power * player.agility

        mult = 1.0 + player.versatility
        if player.has_universal_energy: mult *= 1.15
        if getattr(player, 'has_restore_balance', False) and player.xuen_active:
             mult *= 1.05

        targets = player.target_count
        if getattr(player, 'has_path_of_falling_star', False):
             bonus = max(0.0, 1.0 - 0.2 * (targets - 1))
             mult *= (1.0 + bonus)

        crit = player.crit
        crit_m = 2.0

        scale = self._get_aoe_modifier(targets, 5)

        if use_expected_value:
            total = base * mult * targets * scale * (1 + (crit * (crit_m - 1)))
        else:
            is_crit = random.random() < crit
            m_final = crit_m if is_crit else 1.0
            total = base * mult * targets * scale * m_final

        breakdown = {
            'base': int(base),
            'modifiers': [f"Scale: {scale:.2f}"],
            'targets': targets,
            'total_dmg_after_aoe': total
        }
        return total, breakdown

class TouchOfDeath(Spell):
    def is_usable(self, player, other_spells):
        if not super().is_usable(player): return False
        if player.target_health_pct >= 0.15: return False
        return True

    def calculate_tick_damage(self, player, mastery_override=None, tick_idx=0, use_expected_value=False):
        base_dmg = player.max_health * 0.35

        modifiers = []
        current_mult = 1.0

        if self.damage_multiplier != 1.0:
             current_mult *= self.damage_multiplier
             modifiers.append(f"Talent: x{self.damage_multiplier:.2f}")

        if getattr(player, 'has_hit_combo', False) and player.hit_combo_stacks > 0:
            hc_mod = 1.0 + (player.hit_combo_stacks * 0.01)
            current_mult *= hc_mod
            modifiers.append(f"HitCombo: x{hc_mod:.2f}")

        final_dmg = base_dmg * current_mult

        breakdown = {
            'base': int(base_dmg),
            'modifiers': modifiers,
            'crit_sources': ["True Damage: 0%"],
            'final_crit': 0.0,
            'crit_mult': 1.0,
            'aoe_type': 'single',
            'targets': 1,
            'total_dmg_after_aoe': final_dmg
        }
        return final_dmg, breakdown

class SpellWDP(Spell):
    def is_usable(self, player, other_spells):
        if not super().is_usable(player): return False
        rsk = other_spells['RSK']
        fof = other_spells['FOF']
        return rsk.current_cd > 0 and fof.current_cd > 0


class SpellBook:
    def __init__(self, active_talents=None, talents=None):
        if active_talents is not None and talents is not None:
            merged = list(dict.fromkeys([*active_talents, *talents]))
            active_talents = merged
        elif active_talents is None and talents is not None:
            active_talents = talents

        fof_max_ticks = 5
        self.spells = {
            'TP': Spell('TP', 0.88, name="Tiger Palm", energy=50, chi_gen=2, category='Minor Filler', aoe_type='single', damage_type='Physical'),
            'BOK': Spell('BOK', 3.56, name="Blackout Kick", chi_cost=1, category='Minor Filler', aoe_type='single', damage_type='Physical'),
            'RSK': Spell('RSK', 4.228, name="Rising Sun Kick", chi_cost=2, cd=10.0, cd_haste=True, category='Major Filler', aoe_type='single', damage_type='Physical'),
            'SCK': Spell('SCK', 3.52, name="Spinning Crane Kick", chi_cost=2, is_channeled=True, ticks=4, cast_time=1.5, cast_haste=True, category='Minor Filler', aoe_type='soft_cap', damage_type='Physical'),
            'FOF': Spell('FOF', 2.07 * fof_max_ticks, name="Fists of Fury", chi_cost=3, cd=24.0, cd_haste=True, is_channeled=True,
                         ticks=fof_max_ticks, cast_time=4.0, cast_haste=True, req_talent=True, category='Major Filler', aoe_type='soft_cap', damage_type='Physical'),
            'WDP': SpellWDP('WDP', 5.40, name="Whirling Dragon Punch", cd=30.0, req_talent=True, category='Minor Cooldown', aoe_type='soft_cap', damage_type='Physical'),
            'SOTWL': Spell('SOTWL', 15.12, name="Strike of the Windlord", chi_cost=2, cd=30.0, req_talent=True, category='Minor Cooldown', aoe_type='soft_cap', damage_type='Physical'),
            'SW': Spell('SW', 8.96, name="Slicing Winds", cd=30.0, cast_time=0.4, req_talent=True, gcd_override=0.4, category='Minor Cooldown', aoe_type='single', damage_type='Physical'),
            'Xuen': Spell('Xuen', 0.0, name="Invoke Xuen", cd=120.0, req_talent=True, gcd_override=0.0, category='Major Cooldown'),
            'Zenith': Spell('Zenith', 0.0, name="Zenith", cd=90.0, req_talent=False, max_charges=2, gcd_override=0.0, category='Major Cooldown', aoe_type='soft_cap', damage_type='Nature'),
            'ToD': TouchOfDeath('ToD', 0.0, name="Touch of Death", cd=90.0, energy=0, chi_gen=3, req_talent=False, category='Major Cooldown', aoe_type='single'),
            'Conduit': CelestialConduit('Conduit', 0.0, name="Celestial Conduit", cd=0.0, is_channeled=True, ticks=4, cast_time=4.0, category='Major Cooldown', damage_type='Nature', req_talent=True)
        }
        self.spells['TP'].triggers_combat_wisdom = True
        self.spells['BOK'].triggers_sharp_reflexes = True
        self.active_talents = active_talents if active_talents else []
        self.talent_manager = TalentManager()
        self.player = None

    def apply_talents(self, player):
        self.player = player
        self.talent_manager.apply_talents(self.active_talents, player, self)

    def tick(self, dt):
        for s in self.spells.values(): s.tick_cd(dt, player=self.player)
