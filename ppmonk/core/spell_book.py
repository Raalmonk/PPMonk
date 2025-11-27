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

        # [Task 1: Modifiers Refactor]
        self.modifiers = [] # List[Tuple[str, float]] e.g. [("Base", 1.0)]
        self.crit_modifiers = [] # List[Tuple[str, float]]

        # Legacy attributes for compatibility with older code if any, but we should use new lists
        self.damage_multiplier = 1.0 # Deprecated but kept to avoid instant crashes if I missed one
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
        # [Task 3: Communion with Wind] (CD -5s for SOTWL/WDP)
        if self.abbr in ['SOTWL', 'WDP'] and getattr(player, 'has_communion_with_wind', False):
            base -= 5.0

        if self.cd_haste: return base / (1.0 + player.haste)
        return max(0.0, base)

    def get_effective_cast_time(self, player):
        if self.cast_haste: return self.base_cast_time / (1.0 + player.haste)
        return self.base_cast_time

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

    def cast(self, player, other_spells=None, damage_meter=None, force_proc_glory=False, force_proc_reset=False):
        player.energy -= self.energy_cost

        actual_chi_cost = self.chi_cost

        is_combo_breaker = False
        if self.abbr == 'BOK' and player.combo_breaker_stacks > 0:
            actual_chi_cost = 0
            player.combo_breaker_stacks -= 1
            is_combo_breaker = True

            if player.has_energy_burst:
                player.chi = min(player.max_chi, player.chi + 1)

            # [Task 3: RWK Trigger]
            # "When consuming BOK! Buff, 40% chance to trigger RWK"
            if getattr(player, 'has_rushing_wind_kick', False):
                if random.random() < 0.40:
                    player.rwk_ready = True
                    # print("RWK Ready!")

        is_dance_of_chiji = False
        if self.abbr == 'SCK' and player.dance_of_chiji_stacks > 0:
            actual_chi_cost = 0
            player.dance_of_chiji_stacks -= 1
            is_dance_of_chiji = True

            # [Task 3: Sequenced Strikes]
            # "Consume DoCJ -> Give 1 BOK!"
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

        # [Task 3: Memory of the Monastery - TP proc BOK 10% (up from 8%)]
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
            if random.random() < tp_proc_chance:
                player.combo_breaker_stacks = min(2, player.combo_breaker_stacks + 1)

        if self.chi_cost > 0 and getattr(player, 'has_dance_of_chiji', False):
            chance = 0.015 * self.chi_cost
            if random.random() < chance:
                player.dance_of_chiji_stacks = min(2, player.dance_of_chiji_stacks + 1)
                player.dance_of_chiji_duration = 15.0

        # [Task 3: Revolving Whirl & Echo Technique]
        if self.abbr in ['SOTWL', 'WDP']:
            if getattr(player, 'has_revolving_whirl', False):
                player.dance_of_chiji_stacks = min(2, player.dance_of_chiji_stacks + 1)
                player.dance_of_chiji_duration = 15.0
            if getattr(player, 'has_echo_technique', False):
                player.combo_breaker_stacks = min(2, player.combo_breaker_stacks + 1)

            # [Task 3: Knowledge of Broken Temple]
            if getattr(player, 'has_knowledge_of_broken_temple', False):
                player.totm_stacks = min(player.max_totm_stacks, player.totm_stacks + 4)

            # [Task 3: Thunderfist Stack Gen]
            # "stacks += 4 + target_count"
            if getattr(player, 'has_thunderfist', False):
                 player.thunderfist_stacks += (4 + player.target_count)

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

        extra_damage = 0.0
        extra_damage_details = []

        # Jade Ignition (Nature)
        if self.abbr == 'SCK' and getattr(player, 'has_jade_ignition', False):
            # 1.80 * AP * Agility
            ji_base = 1.80 * player.attack_power * player.agility

            ji_mods = 1.0 + player.versatility
            if getattr(player, 'has_hit_combo', False):
                ji_mods *= (1.0 + player.hit_combo_stacks * 0.01)
            # Universal Energy (Nature)
            if getattr(player, 'has_universal_energy', False):
                ji_mods *= 1.15
            if player.zenith_active and getattr(player, 'has_weapon_of_wind', False):
                ji_mods *= 1.10

            is_crit_ji = random.random() < player.crit
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

        # TotM Consumption (BOK)
        if self.abbr == 'BOK' and player.has_totm:
            if player.totm_stacks > 0:
                extra_hits = player.totm_stacks
                # 0.847 * AP * Agility
                dmg_per_hit = 0.847 * player.attack_power * player.agility

                hc_mod = 1.0
                if getattr(player, 'has_hit_combo', False):
                    hc_mod = 1.0 + (player.hit_combo_stacks * 0.01)

                is_crit = random.random() < (player.crit + self.bonus_crit_chance) # Approx
                crit_m = (2.0 + self.crit_damage_bonus) if is_crit else 1.0

                # Weapon Wind
                ww_mod = 1.10 if (player.zenith_active and getattr(player, 'has_weapon_of_wind', False)) else 1.0

                total_extra = extra_hits * dmg_per_hit * (1 + player.versatility) * crit_m * hc_mod * ww_mod
                extra_damage += total_extra

                if damage_meter is not None:
                    damage_meter['TotM'] = damage_meter.get('TotM', 0) + total_extra

                extra_damage_details.append({
                    'name': 'Teachings of the Monastery',
                    'damage': total_extra,
                    'hits': extra_hits,
                    'crit': is_crit
                })

                player.totm_stacks = 0

            should_reset = False
            if force_proc_reset:
                should_reset = True
            elif random.random() < 0.12:
                should_reset = True

            if should_reset and other_spells and 'RSK' in other_spells:
                other_spells['RSK'].current_cd = 0.0

        # Glory of the Dawn
        if self.abbr == 'RSK' and player.has_glory_of_the_dawn:
            should_proc_glory = False
            if force_proc_glory:
                should_proc_glory = True
            elif random.random() < player.haste:
                should_proc_glory = True

            if should_proc_glory:
                # 1.0 * AP * Agility
                glory_dmg = 1.0 * player.attack_power * player.agility

                hc_mod = 1.0
                if getattr(player, 'has_hit_combo', False):
                    hc_mod = 1.0 + (player.hit_combo_stacks * 0.01)

                is_crit = random.random() < (player.crit + self.bonus_crit_chance)
                crit_m = (2.0 + self.crit_damage_bonus) if is_crit else 1.0
                ww_mod = 1.10 if (player.zenith_active and getattr(player, 'has_weapon_of_wind', False)) else 1.0

                final_glory = glory_dmg * (1 + player.versatility) * crit_m * hc_mod * ww_mod
                extra_damage += final_glory
                player.chi = min(player.max_chi, player.chi + 1)
                if damage_meter is not None:
                    damage_meter['Glory of Dawn'] = damage_meter.get('Glory of Dawn', 0) + final_glory

                extra_damage_details.append({
                    'name': 'Glory of the Dawn',
                    'damage': final_glory,
                    'crit': is_crit
                })

        # Zenith
        if self.abbr == 'Zenith':
            player.zenith_active = True
            dur = 15.0
            if getattr(player, 'has_drinking_horn_cover', False):
                dur = 20.0
            player.zenith_duration = dur

            if other_spells and 'RSK' in other_spells:
                other_spells['RSK'].current_cd = 0
            player.chi = min(player.max_chi, player.chi + 2)

            # Zenith Blast
            zenith_burst = 10.0 * player.attack_power * player.agility
            hc_mod = 1.0
            if getattr(player, 'has_hit_combo', False):
                 hc_mod = 1.0 + (player.hit_combo_stacks * 0.01)

            ww_mod = 1.10 if (getattr(player, 'has_weapon_of_wind', False)) else 1.0

            zenith_burst = zenith_burst * (1.0 + player.versatility) * hc_mod * ww_mod
            zenith_final = self._apply_aoe_scaling(zenith_burst, player, 'soft_cap')
            extra_damage += zenith_final

            extra_damage_details.append({
                'name': 'Zenith Blast',
                'damage': zenith_final,
                'crit': False
            })

        if self.abbr == 'Xuen':
            player.xuen_active = True
            player.xuen_duration = 24.0
            player.update_stats()

        if self.triggers_combat_wisdom and getattr(player, 'combat_wisdom_ready', False):
            player.combat_wisdom_ready = False
            player.combat_wisdom_timer = 15.0
            eh_base = 1.2 * player.attack_power * player.agility
            eh_crit_chance = player.crit + 0.15
            is_crit_eh = random.random() < eh_crit_chance
            eh_dmg = eh_base * (1.0 + player.versatility) * (2.0 if is_crit_eh else 1.0)
            extra_damage += eh_dmg

            extra_damage_details.append({
                'name': 'Expel Harm (Passive)',
                'damage': eh_dmg,
                'crit': is_crit_eh
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
            base_dmg, breakdown = self.calculate_tick_damage(player, mastery_override=triggers_mastery)
            total_damage = base_dmg + extra_damage

            if extra_damage_details:
                breakdown['extra_events'] = extra_damage_details
                breakdown['extra_damage_total'] = extra_damage

            # [Task 3: RSK consuming RWK]
            if self.abbr == 'RSK' and getattr(player, 'rwk_ready', False):
                 player.rwk_ready = False # Consume

            # [Task 3: Xuen's Battlegear - RSK Crit -> FOF CD reduction]
            if self.abbr == 'RSK' and getattr(player, 'has_xuens_battlegear', False):
                crit_c = breakdown['final_crit']
                # Removed deterministic EV reduction to avoid double dipping with simulation roll.

                # Simulation Roll:
                if random.random() < crit_c:
                     if other_spells and 'FOF' in other_spells:
                         other_spells['FOF'].current_cd = max(0, other_spells['FOF'].current_cd - 4.0)

            return total_damage, breakdown

    def calculate_tick_damage(self, player, mastery_override=None, tick_idx=0):
        # [Task 4] Apply Agility
        # RWK Check: If this is RSK and rwk_ready is true, we simulate RWK properties
        is_rwk = (self.abbr == 'RSK' and getattr(player, 'rwk_ready', False))

        # RWK Coeff: 1.7975 * AP
        current_ap_coeff = self.tick_coeff
        if is_rwk:
            current_ap_coeff = 1.7975

        base_dmg_per_target = current_ap_coeff * player.attack_power * player.agility

        modifiers = [] # List of strings "Name: x1.0"
        crit_sources = [] # List of strings "Name: 10%"

        # 1. Multipliers
        current_mult = 1.0

        # Base Modifiers List
        for name, val in self.modifiers:
            current_mult *= val
            modifiers.append(f"{name}: x{val:.2f}")

        # RWK Dmg Bonus: 1 + 0.06 * target_count (Max 30% -> 5 targets)
        if is_rwk:
             rwk_bonus = min(0.30, 0.06 * player.target_count)
             if rwk_bonus > 0:
                 mod_val = 1.0 + rwk_bonus
                 current_mult *= mod_val
                 modifiers.append(f"RWK_Targets: x{mod_val:.2f}")

        # DoCJ SCK
        if self.abbr == 'SCK':
             is_docj = getattr(player, 'channel_docj_snapshot', False)
             if is_docj:
                 current_mult *= 2.0
                 modifiers.append("DanceOfChiJi: x2.00")

        # Hidden Auras
        hidden_mod = 1.0
        if self.abbr == 'RSK': hidden_mod *= 1.70
        if self.abbr == 'SCK': hidden_mod *= 1.10
        if hidden_mod != 1.0:
            current_mult *= hidden_mod
            modifiers.append(f"HiddenAura: x{hidden_mod:.2f}")

        # Global Aura
        aura_mod = 1.04
        if self.abbr in ['TP', 'BOK', 'RSK', 'SCK', 'FOF', 'WDP', 'SOTWL']:
            aura_mod *= 1.04
        if aura_mod != 1.0:
            current_mult *= aura_mod
            modifiers.append(f"Aura: x{aura_mod:.2f}")

        # Shadowboxing
        if self.abbr == 'BOK' and getattr(player, 'has_shadowboxing', False):
            current_mult *= 1.05
            modifiers.append("Shadowboxing: x1.05")

        # Hit Combo
        if getattr(player, 'has_hit_combo', False) and player.hit_combo_stacks > 0:
            hc_mod = 1.0 + (player.hit_combo_stacks * 0.01)
            current_mult *= hc_mod
            modifiers.append(f"HitCombo({player.hit_combo_stacks}): x{hc_mod:.2f}")

        # Communion with Wind (Dmg +10%)
        if self.abbr in ['SOTWL', 'WDP'] and getattr(player, 'has_communion_with_wind', False):
             current_mult *= 1.10
             modifiers.append("Communion: x1.10")

        # Weapon of the Wind (Zenith Active -> +10%)
        if player.zenith_active and getattr(player, 'has_weapon_of_wind', False):
            current_mult *= 1.10
            modifiers.append("WeaponOfWind: x1.10")

        # Universal Energy (Nature/Magic +15%)
        # RWK is Nature. SOTWL/WDP is Nature?
        # Prompt: "Jade Ignition, Chi Burst, Thunderfist, RWK 是自然伤害。"
        # Are SOTWL/WDP nature?
        # Default damage_type logic:
        # SOTWL usually Physical/Nature mix or just Physical?
        # Prompt doesn't explicitly say SOTWL is Nature.
        # But "Jade Ignition, Chi Burst, Thunderfist, RWK is Nature".
        # Assuming others Physical unless specified.
        # Wait, if SOTWL is not Nature, UnivEnergy doesn't apply.
        # I will check `damage_type` attribute.

        is_nature = (self.damage_type == 'Nature')
        if is_rwk: is_nature = True # RWK overrides RSK Physical

        if is_nature and getattr(player, 'has_universal_energy', False):
             current_mult *= 1.15
             modifiers.append("UniversalEnergy: x1.15")

        # Memory of Monastery (TP +15%)
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
            # [Task 3: Sunfire Spiral]
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

        bonus_crit = self.bonus_crit_chance # Legacy
        if bonus_crit > 0:
             crit_sources.append(f"LegacyBonus: {bonus_crit*100:.1f}%")

        for name, val in self.crit_modifiers:
            bonus_crit += val
            crit_sources.append(f"{name}: {val*100:.1f}%")

        # Xuen's Battlegear (RSK +20%)
        if self.abbr == 'RSK' and getattr(player, 'has_xuens_battlegear', False):
             bonus_crit += 0.20
             crit_sources.append("XuensBattlegear: 20.0%")

        final_crit_chance = min(1.0, base_crit + bonus_crit)
        crit_mult = 2.0 + self.crit_damage_bonus

        # Expected Value
        expected_dmg_single = (base_dmg_per_target * current_mult) * (1 + (final_crit_chance * (crit_mult - 1)))

        # 3. AOE Scaling
        # RWK becomes 'cone' or basically AOE.
        # Prompt: "AOE: 对前方所有敌人造成伤害（分摊机制可简化为全额或 Soft Cap）"
        # "AOE: Hit all enemies (simplify to full or soft cap)".
        # Usually RSK is single. RWK makes it AOE.
        # I'll use 'uncapped' or 'soft_cap' for RWK. "Simplification" -> let's use Soft Cap to be safe or Uncapped?
        # Prompt says "Soft Cap (5 targets)" for Jadefire.
        # For RWK, usually it's uncapped or soft capped. Let's stick to Soft Cap for consistency with other AOE.

        current_aoe_type = self.aoe_type
        if is_rwk:
             current_aoe_type = 'soft_cap'
        elif self.abbr == 'BOK' and getattr(player, 'has_shadowboxing', False):
            current_aoe_type = 'cleave'

        total_expected_dmg = self._apply_aoe_scaling(expected_dmg_single, player, current_aoe_type)

        breakdown = {
            'base': int(base_dmg_per_target),
            'modifiers': modifiers, # Now a list of strings
            'crit_sources': crit_sources,
            'final_crit': final_crit_chance,
            'crit_mult': crit_mult,
            'aoe_type': current_aoe_type,
            'targets': player.target_count,
            'total_dmg_after_aoe': total_expected_dmg
        }

        return total_expected_dmg, breakdown

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
            if target_count <= 5:
                return damage_per_target * target_count
            else:
                reduced_dmg = damage_per_target * math.sqrt(5.0 / target_count)
                return reduced_dmg * target_count

        elif aoe_type == 'uncapped':
             return damage_per_target * target_count

        return damage_per_target

    def tick_cd(self, dt):
        if self.charges < self.max_charges:
            self.current_cd = max(0, self.current_cd - dt)
            if self.current_cd == 0:
                self.charges += 1
                if self.charges < self.max_charges:
                    self.current_cd = self.base_cd

class TouchOfDeath(Spell):
    def is_usable(self, player, other_spells):
        if not super().is_usable(player): return False
        if player.target_health_pct >= 0.15: return False
        return True

    def calculate_tick_damage(self, player, mastery_override=None, tick_idx=0):
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
            'WDP': SpellWDP('WDP', 5.40, name="Whirling Dragon Punch", cd=30.0, req_talent=True, category='Minor Cooldown', aoe_type='soft_cap', damage_type='Physical'), # Assuming Physical
            'SOTWL': Spell('SOTWL', 15.12, name="Strike of the Windlord", chi_cost=2, cd=30.0, req_talent=True, category='Minor Cooldown', aoe_type='soft_cap', damage_type='Physical'), # Assuming Physical
            'SW': Spell('SW', 8.96, name="Slicing Winds", cd=30.0, cast_time=0.4, req_talent=True, gcd_override=0.4, category='Minor Cooldown', aoe_type='single', damage_type='Physical'),
            'Xuen': Spell('Xuen', 0.0, name="Invoke Xuen", cd=120.0, req_talent=True, gcd_override=0.0, category='Major Cooldown'),
            'Zenith': Spell('Zenith', 0.0, name="Zenith", cd=90.0, req_talent=False, max_charges=2, gcd_override=0.0, category='Major Cooldown', aoe_type='soft_cap', damage_type='Nature'),
            'ToD': TouchOfDeath('ToD', 0.0, name="Touch of Death", cd=90.0, energy=0, chi_gen=3, req_talent=False, category='Major Cooldown', aoe_type='single')
        }
        self.spells['TP'].triggers_combat_wisdom = True
        self.spells['BOK'].triggers_sharp_reflexes = True
        self.active_talents = active_talents if active_talents else []
        self.talent_manager = TalentManager()

    def apply_talents(self, player):
        self.talent_manager.apply_talents(self.active_talents, player, self)

    def tick(self, dt):
        for s in self.spells.values(): s.tick_cd(dt)
