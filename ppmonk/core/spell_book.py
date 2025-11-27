import random
import math
from .talents import TalentManager


class Spell:
    def __init__(self, abbr, ap_coeff, name=None, energy=0, chi_cost=0, chi_gen=0, cd=0, cd_haste=False,
                 cast_time=0, cast_haste=False, is_channeled=False, ticks=1, req_talent=False, gcd_override=None,
                 max_charges=1, category='', aoe_type='single'):
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

        # 伤害/暴击修正
        self.damage_multiplier = 1.0
        self.bonus_crit_chance = 0.0
        self.crit_damage_bonus = 0.0

    def update_tick_coeff(self):
        self.tick_coeff = self.ap_coeff / self.total_ticks if self.total_ticks > 0 else self.ap_coeff

    def get_effective_cd(self, player):
        if self.cd_haste: return self.base_cd / (1.0 + player.haste)
        return self.base_cd

    def get_effective_cast_time(self, player):
        if self.cast_haste: return self.base_cast_time / (1.0 + player.haste)
        return self.base_cast_time

    def get_tick_interval(self, player):
        if not self.is_channeled or self.total_ticks <= 0: return 0
        return self.get_effective_cast_time(player) / self.total_ticks

    def is_usable(self, player, other_spells=None):
        if not self.is_known: return False
        if self.charges < 1: return False

        # [Task 3: Inner Peace TP cost reduction]
        # Applied in Talent logic, but checking just in case
        e_cost = self.energy_cost

        if player.energy < e_cost: return False

        cost = self.chi_cost

        # [Task 2: Combo Breaker BOK free]
        if self.abbr == 'BOK' and player.combo_breaker_stacks > 0:
            cost = 0

        # [Task 3: Dance of Chi-Ji SCK free]
        if self.abbr == 'SCK' and player.dance_of_chiji_stacks > 0:
            cost = 0

        if player.zenith_active and self.chi_cost > 0:
            cost = max(0, cost - 1) # Reduce AFTER free checks? Or does Zenith not stack with free?
            # Usually Free > Reduction. If Free (0), Zenith does nothing.
            pass

        if player.chi < cost: return False
        return True

    def cast(self, player, other_spells=None, damage_meter=None, force_proc_glory=False, force_proc_reset=False):
        player.energy -= self.energy_cost

        actual_chi_cost = self.chi_cost

        # [Task 2: Combo Breaker Consumption]
        is_combo_breaker = False
        if self.abbr == 'BOK' and player.combo_breaker_stacks > 0:
            actual_chi_cost = 0
            player.combo_breaker_stacks -= 1
            is_combo_breaker = True

            # [Task 3: Energy Burst]
            if player.has_energy_burst:
                player.chi = min(player.max_chi, player.chi + 1)

        # [Task 3: Dance of Chi-Ji Consumption]
        is_dance_of_chiji = False
        if self.abbr == 'SCK' and player.dance_of_chiji_stacks > 0:
            actual_chi_cost = 0
            player.dance_of_chiji_stacks -= 1
            is_dance_of_chiji = True

        if not is_combo_breaker and not is_dance_of_chiji:
             if player.zenith_active and self.chi_cost > 0:
                actual_chi_cost = max(0, self.chi_cost - 1)

        # [Task 2: Obsidian Spiral (BOK generates 1 Chi during Zenith)]
        # Does BOK normally cost 1 Chi? Yes.
        # If Zenith is active, cost becomes 0.
        # Obsidian Spiral: "BOK generates 1 Chi when Zenith active".
        # So instead of costing 0, it costs 0 AND gains 1? Or just gains 1?
        # Usually standard behavior: Cost reduced to 0, and Effect adds "Generate 1 Chi".
        # If Zenith reduces cost to 0, then we don't spend.
        # Then if Obsidian Spiral, we add 1.
        obsidian_bonus = 0
        if self.abbr == 'BOK' and player.zenith_active and getattr(player, 'has_obsidian_spiral', False):
             obsidian_bonus = 1

        player.chi = max(0, player.chi - actual_chi_cost)
        player.chi = min(player.max_chi, player.chi + self.chi_gen + obsidian_bonus)

        if self.charges == self.max_charges:
            self.current_cd = self.get_effective_cd(player)
        self.charges -= 1
        if self.gcd_override is not None:
            player.gcd_remaining = self.gcd_override
        else:
            player.gcd_remaining = 1.0

        # [Mastery Check for Hit Combo]
        triggers_mastery = self.is_combo_strike and (
                    player.last_spell_name is None or player.last_spell_name != self.abbr)

        if triggers_mastery and getattr(player, 'has_hit_combo', False):
            player.hit_combo_stacks = min(5, player.hit_combo_stacks + 1)

        if self.is_combo_strike and not triggers_mastery and player.last_spell_name == self.abbr:
             if getattr(player, 'has_hit_combo', False):
                 player.hit_combo_stacks = 0

        player.last_spell_name = self.abbr

        # [Task 2: Combo Breaker Proc on TP]
        if self.abbr == 'TP' and getattr(player, 'has_combo_breaker', False):
            # 8% Chance
            if random.random() < 0.08:
                player.combo_breaker_stacks = min(2, player.combo_breaker_stacks + 1)

        # [Task 3: Dance of Chi-Ji Proc on Spenders]
        if self.chi_cost > 0 and getattr(player, 'has_dance_of_chiji', False):
            # Chance = 1.5% * Chi Cost (Simple approximation from user prompt)
            chance = 0.015 * self.chi_cost
            if random.random() < chance:
                player.dance_of_chiji_stacks = min(2, player.dance_of_chiji_stacks + 1)
                player.dance_of_chiji_duration = 15.0

        # 1. Sharp Reflexes
        if self.triggers_sharp_reflexes and other_spells:
            reduction = 1.0
            if player.zenith_active:
                reduction += 1.0
            if 'RSK' in other_spells:
                other_spells['RSK'].current_cd = max(0, other_spells['RSK'].current_cd - reduction)
            if 'FOF' in other_spells:
                other_spells['FOF'].current_cd = max(0, other_spells['FOF'].current_cd - reduction)

        # 2. Teachings of the Monastery
        if self.abbr == 'TP' and player.has_totm:
            player.totm_stacks = min(4, player.totm_stacks + 1)

        extra_damage = 0.0
        extra_damage_details = []

        # [Task 4: Jade Ignition]
        if self.abbr == 'SCK' and getattr(player, 'has_jade_ignition', False):
            ji_dmg = 1.80 * player.attack_power
            # Hit Combo Mod
            hit_combo_mod = 1.0
            if getattr(player, 'has_hit_combo', False):
                hit_combo_mod = 1.0 + (player.hit_combo_stacks * 0.01)

            ji_base = ji_dmg * (1.0 + player.versatility) * hit_combo_mod

            # Crit
            is_crit_ji = random.random() < player.crit
            if is_crit_ji:
                ji_base *= 2.0

            # [Task 8: Jade Ignition Soft Cap]
            ji_final = self._apply_aoe_scaling(ji_base, player, 'soft_cap')

            extra_damage += ji_final
            if damage_meter is not None:
                damage_meter['Jade Ignition'] = damage_meter.get('Jade Ignition', 0) + ji_final

            extra_damage_details.append({
                'name': 'Jade Ignition',
                'damage': ji_final,
                'crit': is_crit_ji
            })

        if self.abbr == 'BOK' and player.has_totm:
            if player.totm_stacks > 0:
                extra_hits = player.totm_stacks
                dmg_per_hit = 0.847 * player.attack_power

                # Hit Combo Mod
                hc_mod = 1.0
                if getattr(player, 'has_hit_combo', False):
                    hc_mod = 1.0 + (player.hit_combo_stacks * 0.01)

                is_crit = random.random() < (player.crit + self.bonus_crit_chance)
                crit_m = (2.0 + self.crit_damage_bonus) if is_crit else 1.0

                # TotM hits are single target usually?
                # Prompt doesn't specify TotM AOE. Assuming Single Target to main target.
                total_extra = extra_hits * dmg_per_hit * (1 + player.versatility) * crit_m * hc_mod
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

            # Force Reset Logic
            should_reset = False
            if force_proc_reset:
                should_reset = True
            elif random.random() < 0.12:
                should_reset = True

            if should_reset and other_spells and 'RSK' in other_spells:
                other_spells['RSK'].current_cd = 0.0

        # 3. Glory of the Dawn
        if self.abbr == 'RSK' and player.has_glory_of_the_dawn:
            should_proc_glory = False
            if force_proc_glory:
                should_proc_glory = True
            elif random.random() < player.haste:
                should_proc_glory = True

            if should_proc_glory:
                glory_dmg = 1.0 * player.attack_power

                hc_mod = 1.0
                if getattr(player, 'has_hit_combo', False):
                    hc_mod = 1.0 + (player.hit_combo_stacks * 0.01)

                is_crit = random.random() < (player.crit + self.bonus_crit_chance)
                crit_m = (2.0 + self.crit_damage_bonus) if is_crit else 1.0
                final_glory = glory_dmg * (1 + player.versatility) * crit_m * hc_mod
                extra_damage += final_glory
                player.chi = min(player.max_chi, player.chi + 1)
                if damage_meter is not None:
                    damage_meter['Glory of Dawn'] = damage_meter.get('Glory of Dawn', 0) + final_glory

                extra_damage_details.append({
                    'name': 'Glory of the Dawn',
                    'damage': final_glory,
                    'crit': is_crit
                })

        if self.abbr == 'Zenith':
            player.zenith_active = True
            # [Task 2: Drinking Horn Cover] 15s -> 20s if talented
            dur = 15.0
            if getattr(player, 'has_drinking_horn_cover', False):
                dur = 20.0
            player.zenith_duration = dur

            if other_spells and 'RSK' in other_spells:
                other_spells['RSK'].current_cd = 0
            player.chi = min(player.max_chi, player.chi + 2)

            # Zenith Explosion (Not explicitly detailed in prompt but usually it deals damage when cast or ending?)
            # Task 8 mentions "Zenith: ... apply Soft Cap rules".
            # Assuming Zenith has an immediate damage component (Spirits of Xuen?).
            # Prompt: "Zenith: 之前实装的 "1000% AP" 爆炸".
            # I will add this damage here.
            zenith_burst = 10.0 * player.attack_power
            hc_mod = 1.0
            if getattr(player, 'has_hit_combo', False):
                 hc_mod = 1.0 + (player.hit_combo_stacks * 0.01)

            zenith_burst = zenith_burst * (1.0 + player.versatility) * hc_mod
            # Soft Cap
            zenith_final = self._apply_aoe_scaling(zenith_burst, player, 'soft_cap')
            extra_damage += zenith_final

            extra_damage_details.append({
                'name': 'Zenith Blast',
                'damage': zenith_final,
                'crit': False # Can it crit? Assuming no for now or already averaged
            })


        # 4. Xuen
        if self.abbr == 'Xuen':
            player.xuen_active = True
            player.xuen_duration = 24.0
            player.update_stats()

        if self.triggers_combat_wisdom and getattr(player, 'combat_wisdom_ready', False):
            player.combat_wisdom_ready = False
            player.combat_wisdom_timer = 15.0
            eh_base = 1.2 * player.attack_power
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

            # [Task 3: Dance of Chi-Ji Bonus Dmg?]
            # If SCK consumed DoCJ, should ticks deal more damage?
            # I'll handle this in calculate_tick_damage by checking a flag on the spell instance if needed,
            # or player state. Player state 'dance_of_chiji_stacks' is consumed.
            # I need to snapshot this buff for the channel duration.
            # I'll add a temporary attribute to the spell instance or player channel state.
            player.channel_docj_snapshot = is_dance_of_chiji

            # Structured breakdown for channeling start
            breakdown = {
                'base': 0,
                'modifiers': {},
                'flags': ['Channeling'],
                'extra_events': extra_damage_details
            }
            return 0.0, breakdown
        else:
            base_dmg, breakdown = self.calculate_tick_damage(player, mastery_override=triggers_mastery)
            # base_dmg from calculate_tick_damage is now TOTAL AOE damage (see below)
            total_damage = base_dmg + extra_damage

            if extra_damage_details:
                breakdown['extra_events'] = extra_damage_details
                breakdown['extra_damage_total'] = extra_damage

            return total_damage, breakdown

    def calculate_tick_damage(self, player, mastery_override=None, tick_idx=0):
        # This calculates damage for ONE TICK (for channeled) or ONE CAST (instant)
        # It needs to return TOTAL damage across all targets.

        base_dmg_per_target = self.tick_coeff * player.attack_power

        modifiers = {}
        flags = []

        dmg_mod = 1.0

        # Spell Specific Mods
        spell_mod = self.damage_multiplier
        if spell_mod != 1.0:
             modifiers['Talent/Spell'] = spell_mod
        dmg_mod *= spell_mod

        # [Task 3: Dance of Chi-Ji Bonus Damage for SCK]
        # Check snapshot if channeling, or player state if instant (SCK is channeled).
        # SCK is channeled, so this function is called per tick.
        # We need to know if DoCJ was active.
        if self.abbr == 'SCK':
             is_docj = getattr(player, 'channel_docj_snapshot', False)
             if is_docj:
                 # "Damage increased" - user said optional, I chose 200%
                 dmg_mod *= 2.0
                 modifiers['DanceOfChiJi'] = 2.0

        hidden_mod = 1.0
        if self.abbr == 'RSK': hidden_mod *= 1.70
        if self.abbr == 'SCK': hidden_mod *= 1.10
        if hidden_mod != 1.0:
            modifiers['HiddenAura'] = hidden_mod
            dmg_mod *= hidden_mod

        # Aura Mod (Global)
        aura_mod = 1.04
        if self.abbr in ['TP', 'BOK', 'RSK', 'SCK', 'FOF', 'WDP', 'SOTWL']:
            aura_mod *= 1.04
        if aura_mod != 1.0:
            modifiers['Aura'] = aura_mod
        dmg_mod *= aura_mod

        # [Task 3: Shadowboxing Treads - BOK +5%]
        if self.abbr == 'BOK' and getattr(player, 'has_shadowboxing', False):
            dmg_mod *= 1.05
            modifiers['Shadowboxing'] = 1.05

        # [Task 4: Hit Combo]
        if getattr(player, 'has_hit_combo', False) and player.hit_combo_stacks > 0:
            hc_mod = 1.0 + (player.hit_combo_stacks * 0.01)
            modifiers['HitCombo'] = hc_mod
            dmg_mod *= hc_mod

        if self.haste_dmg_scaling:
            h_mod = (1.0 + player.haste)
            modifiers['HasteScale'] = h_mod
            dmg_mod *= h_mod

        if self.tick_dmg_ramp > 0:
            ramp_mod = (1.0 + (tick_idx + 1) * self.tick_dmg_ramp)
            modifiers['TickRamp'] = ramp_mod
            dmg_mod *= ramp_mod

        apply_mastery = mastery_override if mastery_override is not None else (
            self.is_channeled and player.channel_mastery_snapshot)
        if apply_mastery:
            m_mod = (1.0 + player.mastery)
            modifiers['Mastery'] = m_mod
            dmg_mod *= m_mod
            flags.append('Mastery')

        v_mod = (1.0 + player.versatility)
        modifiers['Versatility'] = v_mod
        dmg_mod *= v_mod

        crit_chance = min(1.0, player.crit + self.bonus_crit_chance)
        crit_mult = 2.0 + self.crit_damage_bonus

        # Expected value per target
        expected_dmg_single = (base_dmg_per_target * dmg_mod) * (1 + (crit_chance * (crit_mult - 1)))

        # [Task 6: AOE Scaling Calculation]
        # Now we apply target counting logic

        total_expected_dmg = 0.0

        # Determine AOE Type
        # BOK becomes 'cleave' if Shadowboxing Treads is active
        current_aoe_type = self.aoe_type
        if self.abbr == 'BOK' and getattr(player, 'has_shadowboxing', False):
            current_aoe_type = 'cleave'

        total_expected_dmg = self._apply_aoe_scaling(expected_dmg_single, player, current_aoe_type)

        breakdown = {
            'base': int(base_dmg_per_target),
            'modifiers': modifiers,
            'flags': flags,
            'crit_chance': crit_chance,
            'crit_mult': crit_mult,
            'final_mod': dmg_mod,
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
            # Main target full damage
            total = damage_per_target
            # Secondary targets (max 2) at 80%
            if target_count > 1:
                secondary_targets = min(target_count - 1, 2) # "Cleave 2 additional" -> Total 3 max
                total += damage_per_target * 0.80 * secondary_targets
            return total

        elif aoe_type == 'soft_cap':
            if target_count <= 5:
                return damage_per_target * target_count
            else:
                # > 5 targets: dmg = base * sqrt(5 / count)
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

# [Task 2: Touch of Death Class]
class TouchOfDeath(Spell):
    def is_usable(self, player, other_spells):
        if not super().is_usable(player): return False
        if player.target_health_pct >= 0.15: return False
        return True

    def calculate_tick_damage(self, player, mastery_override=None, tick_idx=0):
        base_dmg = player.max_health * 0.35

        modifiers = {}
        dmg_mod = 1.0

        if self.damage_multiplier != 1.0:
             modifiers['Talent'] = self.damage_multiplier
             dmg_mod *= self.damage_multiplier

        if getattr(player, 'has_hit_combo', False) and player.hit_combo_stacks > 0:
            hc_mod = 1.0 + (player.hit_combo_stacks * 0.01)
            modifiers['HitCombo'] = hc_mod
            dmg_mod *= hc_mod

        final_dmg = base_dmg * dmg_mod

        # AOE: ToD is Single Target ('single') usually.
        # But if Meridian Strikes or something makes it AOE? No.
        # Fatal Flying Guillotine? (Not in this prompt).
        # Assuming Single Target.

        breakdown = {
            'base': int(base_dmg),
            'modifiers': modifiers,
            'flags': ['True Damage'],
            'crit_chance': 0.0,
            'crit_mult': 1.0,
            'final_mod': dmg_mod
        }
        return final_dmg, breakdown

class SpellWDP(Spell):
    def is_usable(self, player, other_spells):
        if not super().is_usable(player): return False
        rsk = other_spells['RSK'];
        fof = other_spells['FOF']
        return rsk.current_cd > 0 and fof.current_cd > 0


class SpellBook:
    def __init__(self, active_talents=None, talents=None):
        if active_talents is not None and talents is not None:
            merged = list(dict.fromkeys([*active_talents, *talents]))
            active_talents = merged
        elif active_talents is None and talents is not None:
            active_talents = talents

        # [Task 1 & 6: Config AOE Types]
        fof_max_ticks = 5
        self.spells = {
            'TP': Spell('TP', 0.88, name="Tiger Palm", energy=50, chi_gen=2, category='Minor Filler', aoe_type='single'),
            'BOK': Spell('BOK', 3.56, name="Blackout Kick", chi_cost=1, category='Minor Filler', aoe_type='single'), # Becomes cleave via talent
            'RSK': Spell('RSK', 4.228, name="Rising Sun Kick", chi_cost=2, cd=10.0, cd_haste=True, category='Major Filler', aoe_type='single'),
            'SCK': Spell('SCK', 3.52, name="Spinning Crane Kick", chi_cost=2, is_channeled=True, ticks=4, cast_time=1.5, cast_haste=True, category='Minor Filler', aoe_type='soft_cap'),
            'FOF': Spell('FOF', 2.07 * fof_max_ticks, name="Fists of Fury", chi_cost=3, cd=24.0, cd_haste=True, is_channeled=True,
                         ticks=fof_max_ticks, cast_time=4.0, cast_haste=True, req_talent=True, category='Major Filler', aoe_type='soft_cap'),
            'WDP': SpellWDP('WDP', 5.40, name="Whirling Dragon Punch", cd=30.0, req_talent=True, category='Minor Cooldown', aoe_type='soft_cap'),
            'SOTWL': Spell('SOTWL', 15.12, name="Strike of the Windlord", chi_cost=2, cd=30.0, req_talent=True, category='Minor Cooldown', aoe_type='soft_cap'),
            'SW': Spell('SW', 8.96, name="Slicing Winds", cd=30.0, cast_time=0.4, req_talent=True, gcd_override=0.4, category='Minor Cooldown', aoe_type='single'), # Usually single? Or Cleave? Assuming Single.
            'Xuen': Spell('Xuen', 0.0, name="Invoke Xuen", cd=120.0, req_talent=True, gcd_override=0.0, category='Major Cooldown'),
            'Zenith': Spell('Zenith', 0.0, name="Zenith", cd=90.0, req_talent=False, max_charges=2, gcd_override=0.0, category='Major Cooldown', aoe_type='soft_cap'),
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
