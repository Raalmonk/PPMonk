import random
from .talents import TalentManager


class Spell:
    def __init__(self, abbr, ap_coeff, name=None, energy=0, chi_cost=0, chi_gen=0, cd=0, cd_haste=False,
                 cast_time=0, cast_haste=False, is_channeled=False, ticks=1, req_talent=False, gcd_override=None,
                 max_charges=1, category=''):
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
        if player.energy < self.energy_cost: return False
        cost = self.chi_cost
        if player.zenith_active and self.chi_cost > 0:
            cost = max(0, self.chi_cost - 1)
        if player.chi < cost: return False
        return True

    def cast(self, player, other_spells=None, damage_meter=None, force_proc_glory=False, force_proc_reset=False):
        player.energy -= self.energy_cost
        actual_chi_cost = self.chi_cost
        if player.zenith_active and self.chi_cost > 0:
            actual_chi_cost = max(0, self.chi_cost - 1)
        player.chi = max(0, player.chi - actual_chi_cost)
        player.chi = min(player.max_chi, player.chi + self.chi_gen)
        if self.charges == self.max_charges:
            self.current_cd = self.get_effective_cd(player)
        self.charges -= 1
        if self.gcd_override is not None:
            player.gcd_remaining = self.gcd_override
        else:
            player.gcd_remaining = 1.0

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

        if self.abbr == 'BOK' and player.has_totm:
            if player.totm_stacks > 0:
                extra_hits = player.totm_stacks
                dmg_per_hit = 0.847 * player.attack_power
                is_crit = random.random() < (player.crit + self.bonus_crit_chance)
                crit_m = (2.0 + self.crit_damage_bonus) if is_crit else 1.0
                total_extra = extra_hits * dmg_per_hit * (1 + player.versatility) * crit_m
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
                is_crit = random.random() < (player.crit + self.bonus_crit_chance)
                crit_m = (2.0 + self.crit_damage_bonus) if is_crit else 1.0
                final_glory = glory_dmg * (1 + player.versatility) * crit_m
                extra_damage += final_glory
                player.chi = min(player.max_chi, player.chi + 1)
                if damage_meter is not None:
                    damage_meter['Glory of Dawn'] = damage_meter.get('Glory of Dawn', 0) + final_glory

        if self.abbr == 'Zenith':
            player.zenith_active = True
            player.zenith_duration = 15.0
            if other_spells and 'RSK' in other_spells:
                other_spells['RSK'].current_cd = 0
            player.chi = min(player.max_chi, player.chi + 2)
        # 4. Xuen
        if self.abbr == 'Xuen':
            player.xuen_active = True
            player.xuen_duration = 24.0
            player.update_stats()

        if self.triggers_combat_wisdom and getattr(player, 'combat_wisdom_ready', False):
            player.combat_wisdom_ready = False
            player.combat_wisdom_timer = 15.0
            eh_base = 1.2 * player.attack_power
            # [实装] Strength of Spirit: EH 暴击 +15%
            eh_crit_chance = player.crit + 0.15
            is_crit_eh = random.random() < eh_crit_chance
            eh_dmg = eh_base * (1.0 + player.versatility) * (2.0 if is_crit_eh else 1.0)
            extra_damage += eh_dmg

            extra_damage_details.append({
                'name': 'Expel Harm (Passive)',
                'damage': eh_dmg,
                'crit': is_crit_eh
            })

        triggers_mastery = self.is_combo_strike and (player.last_spell_name is not None) and (
                    player.last_spell_name != self.abbr)
        player.last_spell_name = self.abbr

        if self.is_channeled:
            cast_t = self.get_effective_cast_time(player)
            player.is_channeling = True
            player.current_channel_spell = self
            player.channel_time_remaining = cast_t
            player.channel_ticks_remaining = self.total_ticks
            player.channel_tick_interval = self.get_tick_interval(player)
            player.time_until_next_tick = player.channel_tick_interval
            player.channel_mastery_snapshot = triggers_mastery
            # Return empty string or "Channeling..." for breakdown
            return 0.0, "(Channeling)"
        else:
            base_dmg, breakdown = self.calculate_tick_damage(player, mastery_override=triggers_mastery)
            total_damage = base_dmg + extra_damage

            # If extra damage happened, append to breakdown
            if extra_damage > 0:
                breakdown += f" + Extra: {int(extra_damage)}"

            return total_damage, breakdown

    def calculate_tick_damage(self, player, mastery_override=None, tick_idx=0):
        base_dmg = self.tick_coeff * player.attack_power

        modifiers = {}
        flags = []

        dmg_mod = 1.0

        # Spell Specific Mods
        spell_mod = 1.0
        if self.abbr == 'RSK':
            spell_mod *= 1.70
        if self.abbr == 'SCK':
            spell_mod *= 1.10
        if spell_mod != 1.0:
            modifiers['Spell'] = spell_mod
        dmg_mod *= spell_mod

        # Aura Mod
        aura_mod = 1.04
        if self.abbr in ['TP', 'BOK', 'RSK', 'SCK', 'FOF', 'WDP', 'SOTWL']:
            aura_mod *= 1.04
        if aura_mod != 1.0:
            modifiers['Aura'] = aura_mod
        dmg_mod *= aura_mod

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
            dmg_mod *= (1.0 + player.mastery)
        dmg_mod *= (1.0 + player.versatility)

        crit_chance = min(1.0, player.crit + self.bonus_crit_chance)
        crit_mult = 2.0 + self.crit_damage_bonus
        expected_dmg = (base_dmg * dmg_mod) * (1 + (crit_chance * (crit_mult - 1)))

        breakdown_string = f"(Base: {int(base_dmg)}, Mod: {dmg_mod:.2f}, Crit: {crit_chance*100:.1f}%)"

        return expected_dmg, breakdown_string

    def tick_cd(self, dt):
        if self.charges < self.max_charges:
            self.current_cd = max(0, self.current_cd - dt)
            if self.current_cd == 0:
                self.charges += 1
                if self.charges < self.max_charges:
                    self.current_cd = self.base_cd


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

        # 基础伤害系数需按实际修改，此处简化
        fof_max_ticks = 5
        self.spells = {
            'TP': Spell('TP', 0.88, name="Tiger Palm", energy=50, chi_gen=2, category='Minor Filler'),
            'BOK': Spell('BOK', 3.56, name="Blackout Kick", chi_cost=1, category='Minor Filler'),
            'RSK': Spell('RSK', 4.228, name="Rising Sun Kick", chi_cost=2, cd=10.0, cd_haste=True, category='Major Filler'),
            'SCK': Spell('SCK', 3.52, name="Spinning Crane Kick", chi_cost=2, is_channeled=True, ticks=4, cast_time=1.5, cast_haste=True, category='Minor Filler'),
            'FOF': Spell('FOF', 2.07 * fof_max_ticks, name="Fists of Fury", chi_cost=3, cd=24.0, cd_haste=True, is_channeled=True,
                         ticks=fof_max_ticks, cast_time=4.0, cast_haste=True, req_talent=True, category='Major Filler'),
            'WDP': SpellWDP('WDP', 5.40, name="Whirling Dragon Punch", cd=30.0, req_talent=True, category='Minor Cooldown'),
            'SOTWL': Spell('SOTWL', 15.12, name="Strike of the Windlord", chi_cost=2, cd=30.0, req_talent=True, category='Minor Cooldown'),
            'SW': Spell('SW', 8.96, name="Slicing Winds", cd=30.0, cast_time=0.4, req_talent=True, gcd_override=0.4, category='Minor Cooldown'),
            'Xuen': Spell('Xuen', 0.0, name="Invoke Xuen", cd=120.0, req_talent=True, gcd_override=0.0, category='Major Cooldown'),
            'Zenith': Spell('Zenith', 0.0, name="Zenith", cd=90.0, req_talent=False, max_charges=2, gcd_override=0.0, category='Major Cooldown')
        }
        self.spells['TP'].triggers_combat_wisdom = True
        self.spells['BOK'].triggers_sharp_reflexes = True
        self.active_talents = active_talents if active_talents else []
        self.talent_manager = TalentManager()

    def apply_talents(self, player):
        self.talent_manager.apply_talents(self.active_talents, player, self)

    def tick(self, dt):
        for s in self.spells.values(): s.tick_cd(dt)
