"""Gym-compatible environment for PPMonk with talent support."""

from __future__ import annotations

import gymnasium as gym
from gymnasium import spaces
import numpy as np

from ppmonk.core.player import PlayerState
from ppmonk.core.spell_book import SpellBook
from ppmonk.core.timeline import Timeline


class MonkEnv(gym.Env):
    """Main training environment."""

    def __init__(self, seed_offset=0):
        self.observation_space = spaces.Box(low=0, high=1, shape=(37,), dtype=np.float32)
        self.action_space = spaces.Discrete(9)
        self.action_map = {0: 'Wait', 1: 'TP', 2: 'BOK', 3: 'RSK', 4: 'SCK', 5: 'FOF', 6: 'WDP', 7: 'SOTWL', 8: 'SW'}
        self.spell_keys = list(self.action_map.values())[1:]

        self.scenario = 0
        self.training_mode = True
        self.rng = np.random.default_rng(seed_offset)

        self.current_talents = ['WDP', 'SW', 'Ascension']

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self.rng = np.random.default_rng(seed)

        self.player = PlayerState()
        self.book = SpellBook(talents=self.current_talents)
        self.book.apply_talents(self.player)

        if options and 'timeline' in options:
            scen_id = options['timeline']
        else:
            scen_id = self.rng.integers(0, 4)
        self.scenario = scen_id
        self.timeline = Timeline(scen_id)
        self.timeline.reset()

        if self.training_mode and (options is None):
            self.time = self.rng.uniform(0.0, 18.0)
            self.player.energy = self.rng.uniform(0.0, self.player.max_energy)
            self.player.chi = self.rng.integers(0, 7)
        else:
            self.time = 0.0
            if not self.training_mode:
                self.player.energy = self.player.max_energy

        return self._get_obs(), {}

    def _get_obs(self):
        uptime, mod, _ = self.timeline.get_status(self.time)

        time_to_burst = 1.0
        if self.timeline.burst_start > 0:
            if self.time < self.timeline.burst_start:
                time_to_burst = (self.timeline.burst_start - self.time) / 20.0
            else:
                time_to_burst = 0.0

        norm_energy = self.player.energy / self.player.max_energy
        norm_chi = self.player.chi / 6.0
        norm_gcd = self.player.gcd_remaining / 1.5
        norm_time = self.time / 20.0
        norm_cds = [self.book.spells[k].current_cd / 30.0 for k in ['RSK', 'FOF', 'WDP', 'SOTWL', 'SW']]
        scen_onehot = [0.0, 0.0, 0.0, 0.0]
        scen_onehot[self.scenario] = 1.0

        last_action_val = 0.0
        if self.player.last_spell_name:
            for k, v in self.action_map.items():
                if v == self.player.last_spell_name:
                    last_action_val = k / 9.0
                    break

        obs = [norm_energy, norm_chi, norm_gcd, *norm_cds, norm_time, 1.0 if uptime else 0.0, mod / 3.0, *scen_onehot,
               time_to_burst, last_action_val]
        return np.concatenate((obs, self.timeline.global_map), axis=0).astype(np.float32)

    def action_masks(self):
        if self.time >= 20.0:
            return [False] * 9
        masks = [True] * 9
        for i, key in enumerate(self.spell_keys):
            spell = self.book.spells[key]
            if key == 'WDP':
                is_usable = spell.is_usable(self.player, self.book.spells)
            else:
                is_usable = spell.is_usable(self.player)

            if spell.abbr == self.player.last_spell_name:
                is_usable = False
            masks[i + 1] = is_usable
        return masks

    def step(self, action_idx):
        total_damage = 0

        time_to_wait = 0.0
        if self.player.gcd_remaining > 0:
            time_to_wait = max(time_to_wait, self.player.gcd_remaining)
        if action_idx > 0:
            key = self.action_map[action_idx]
            spell = self.book.spells[key]
            if spell.current_cd > 0:
                time_to_wait = max(time_to_wait, spell.current_cd)

        remaining_time = max(0.0, self.timeline.duration - self.time)
        time_to_wait = min(time_to_wait, remaining_time)

        if time_to_wait > 0:
            total_damage += self._advance_time_with_mod(time_to_wait)

        lockout = 0.0
        reward_shaping = 0.0

        if self.player.last_spell_name is None and action_idx != 1:
            reward_shaping -= 5.0
        if action_idx == 1 and self.player.chi < 4:
            reward_shaping += 1.0

        if action_idx > 0:
            key = self.action_map[action_idx]
            spell = self.book.spells[key]

            if spell.current_cd > 0.01:
                return self._get_obs(), -10.0, False, False, {'damage': 0}

            dmg = spell.cast(self.player)
            _, current_mod, _ = self.timeline.get_status(self.time)
            total_damage += dmg * current_mod

            if spell.is_channeled:
                lockout = spell.get_effective_cast_time(self.player)
            else:
                lockout = self.player.gcd_remaining
        else:
            lockout = 0.1

        remaining_time = max(0.0, self.timeline.duration - self.time)
        actual_duration = min(lockout, remaining_time)

        if actual_duration > 0:
            total_damage += self._advance_time_with_mod(actual_duration)

        done = self.time >= 20.0
        reward = total_damage + reward_shaping
        return self._get_obs(), reward, done, False, {'damage': total_damage}

    def _advance_time_with_mod(self, duration):
        total_damage = 0
        target_time = self.time + duration
        burst_time = 16.0

        if self.scenario == 3 and self.time < burst_time and target_time > burst_time:
            dt1 = burst_time - self.time
            if dt1 > 0:
                dmg1 = self.player.advance_time(dt1)
                self.book.tick(dt1)
                total_damage += dmg1 * 1.0

            dt2 = target_time - burst_time
            if dt2 > 0:
                dmg2 = self.player.advance_time(dt2)
                self.book.tick(dt2)
                total_damage += dmg2 * 3.0

            self.time = target_time
        else:
            _, mod, _ = self.timeline.get_status(self.time)
            dmg = self.player.advance_time(duration)
            self.book.tick(duration)
            total_damage += dmg * mod
            self.time += duration
        return total_damage
