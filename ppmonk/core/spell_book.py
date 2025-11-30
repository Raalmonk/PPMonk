        # Glory of Dawn
        if self.abbr == 'RSK' and player.has_glory_of_the_dawn:
            should_proc_glory = force_proc_glory
            if not should_proc_glory and not use_expected_value and random.random() < player.haste:
                should_proc_glory = True

            if should_proc_glory or use_expected_value:
                glory_dmg = 1.0 * player.attack_power * player.agility
                # Apply same mods as RSK roughly
                hc_mod = 1.0 + (player.hit_combo_stacks * 0.01) if getattr(player, 'has_hit_combo', False) else 1.0
                ww_mod = 1.10 if (player.zenith_active and getattr(player, 'has_weapon_of_wind', False)) else 1.0
                base_glory = glory_dmg * (1 + player.versatility) * hc_mod * ww_mod * (1.0 + player.mastery) # Mastery Added

                crit_c = player.crit + self.bonus_crit_chance
                if player.zenith_active: crit_c += player.teb_active_bonus
                crit_m = 2.0 + self.crit_damage_bonus + player.teb_crit_dmg_bonus

                if use_expected_value:
                    final_glory = base_glory * (1 + crit_c * (crit_m - 1)) * player.haste # EV includes proc chance
                else:
                    is_crit = random.random() < crit_c
                    final_glory = base_glory * (crit_m if is_crit else 1.0)
                    player.chi = min(player.max_chi, player.chi + 1)

                extra_damage += final_glory
                if damage_meter is not None: damage_meter['Glory of Dawn'] = damage_meter.get('Glory of Dawn', 0) + final_glory
                extra_damage_details.append({'name': 'Glory of Dawn', 'damage': final_glory})

        # Zenith Cast
        if self.abbr == 'Zenith':
            player.zenith_active = True
            player.zenith_duration = 20.0 if getattr(player, 'has_drinking_horn_cover', False) else 15.0
            if getattr(player, 'has_stand_ready', False):
                player.stand_ready_active = True
                player.flurry_charges += 10
            if other_spells and 'RSK' in other_spells: other_spells['RSK'].current_cd = 0
            player.chi = min(player.max_chi, player.chi + 2)

            consumed = player.teb_stacks
            player.teb_stacks = 0
            player.teb_active_bonus = consumed * 0.02

            zenith_burst = 10.0 * player.attack_power * player.agility
            hc_mod = 1.0 + (player.hit_combo_stacks * 0.01) if getattr(player, 'has_hit_combo', False) else 1.0
            ww_mod = 1.10 if getattr(player, 'has_weapon_of_wind', False) else 1.0
            if getattr(player, 'has_weapons_of_the_wall', False): ww_mod *= 1.20

            zenith_final = zenith_burst * (1.0 + player.versatility) * hc_mod * ww_mod * (1.0 + player.mastery) # Mastery Added
            zenith_final = self._apply_aoe_scaling(zenith_final, player, 'soft_cap')

            extra_damage += zenith_final
            extra_damage_details.append({'name': 'Zenith Blast', 'damage': zenith_final})
