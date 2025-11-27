import gymnasium as gym
from gymnasium import spaces
import numpy as np
from ppmonk.core.player import PlayerState
from ppmonk.core.spell_book import SpellBook
from ppmonk.core.timeline import Timeline


class MonkEnv(gym.Env):
    def __init__(self, seed_offset=0, current_talents=None, player_kwargs=None):
        # Obs: 18 (base) + 20 (map) = 38
        self.observation_space = spaces.Box(low=0, high=1, shape=(38,), dtype=np.float32)
        # [修复] Action Space 增加到 10 (0-9), 加入 Zenith
        self.action_space = spaces.Discrete(10)
        self.action_map = {
            0: 'Wait', 1: 'TP', 2: 'BOK', 3: 'RSK', 4: 'SCK',
            5: 'FOF', 6: 'WDP', 7: 'SOTWL', 8: 'SW', 9: 'Zenith'
        }
        self.spell_keys = list(self.action_map.values())[1:]  # TP ~ Zenith
        self.scenario = 0
        self.training_mode = True
        self.rng = np.random.default_rng(seed_offset)

        self.current_talents = current_talents if current_talents else []
        self.player_kwargs = player_kwargs if player_kwargs else {}

        # [新] 伤害统计
        self.damage_meter = {}

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None: self.rng = np.random.default_rng(seed)

        self.player = PlayerState(**self.player_kwargs)
        self.book = SpellBook(talents=self.current_talents)
        self.book.apply_talents(self.player)

        # 重置伤害统计
        self.damage_meter = {}

        if options and 'timeline' in options:
            scen_id = options['timeline']
        else:
            scen_id = self.rng.integers(0, 4)
        self.scenario = scen_id
        self.timeline = Timeline(scen_id)
        self.timeline.reset()

        if self.training_mode and (options is None):
            self.time = self.rng.uniform(0.0, 58.0)
            self.player.energy = self.rng.uniform(0.0, self.player.max_energy)
            self.player.chi = self.rng.integers(0, 7)
        else:
            self.time = 0.0
            self.player.energy = self.player.max_energy
            self.player.chi = self.player.max_chi

        return self._get_obs(), {}

    def _get_obs(self):
        uptime, mod, _ = self.timeline.get_status(self.time)
        time_to_burst = 0.0
        if self.timeline.burst_start > 0 and self.time < self.timeline.burst_start:
            time_to_burst = (self.timeline.burst_start - self.time) / 60.0

        norm_energy = self.player.energy / self.player.max_energy
        norm_chi = self.player.chi / 6.0
        norm_gcd = self.player.gcd_remaining / 1.5
        norm_time = self.time / 60.0

        # [修复] Zenith 现在在 SpellBook 里了，不会报错
        cds_to_track = ['RSK', 'FOF', 'WDP', 'SOTWL', 'SW', 'Zenith']
        norm_cds = []
        for k in cds_to_track:
            if k in self.book.spells:
                norm_cds.append(self.book.spells[k].current_cd / 30.0)
            else:
                norm_cds.append(0.0)  # 防止万一没了

        scen_onehot = [0.0, 0.0, 0.0, 0.0]
        scen_onehot[self.scenario] = 1.0
        last_action_val = 0.0
        if self.player.last_spell_name:
            for k, v in self.action_map.items():
                if v == self.player.last_spell_name:
                    last_action_val = k / 10.0  # 归一化
                    break

        obs = [norm_energy, norm_chi, norm_gcd, *norm_cds, norm_time, 1.0 if uptime else 0.0, mod / 3.0, *scen_onehot,
               time_to_burst, last_action_val]
        return np.concatenate((obs, self.timeline.global_map), axis=0).astype(np.float32)

    def action_masks(self):
        if self.time >= 60.0: return [False] * 10
        masks = [True] * 10

        for i, key in enumerate(self.spell_keys):
            spell = self.book.spells[key]
            is_usable = False
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
        log_details = ""
        auto_attack_logs = []
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
            dmg, logs = self._advance_time_with_mod(time_to_wait)
            total_damage += dmg
            auto_attack_logs.extend(logs)
        lockout = 0.0
        if action_idx > 0:
            key = self.action_map[action_idx]
            spell = self.book.spells[key]
            if spell.current_cd > 0.01:
                return self._get_obs(), -10.0, False, False, {'damage': 0, 'log_details': "", 'auto_attack_logs': []}
            dmg, log_details = spell.cast(self.player, other_spells=self.book.spells, damage_meter=self.damage_meter)
            _, current_mod, _ = self.timeline.get_status(self.time)
            scaled_dmg = dmg * current_mod
            total_damage += scaled_dmg
            self.damage_meter[key] = self.damage_meter.get(key, 0) + scaled_dmg
            if spell.is_channeled:
                lockout = spell.get_effective_cast_time(self.player)
            else:
                lockout = self.player.gcd_remaining
        else:
            lockout = 0.1
        remaining_time = max(0.0, self.timeline.duration - self.time)
        actual_duration = min(lockout, remaining_time)
        if actual_duration > 0:
            dmg, logs = self._advance_time_with_mod(actual_duration)
            total_damage += dmg
            auto_attack_logs.extend(logs)
        done = self.time >= 60.0
        reward = total_damage
        return self._get_obs(), reward, done, False, {'damage': total_damage, 'log_details': log_details, 'auto_attack_logs': auto_attack_logs}

    def _advance_time_with_mod(self, duration):
        total_damage = 0
        _, mod, _ = self.timeline.get_status(self.time)
        dmg, auto_attack_logs = self.player.advance_time(duration, damage_meter=self.damage_meter)
        self.book.tick(duration)
        total_damage += dmg * mod
        self.time += duration
        return total_damage, auto_attack_logs
