import gymnasium as gym
from gymnasium import spaces
import numpy as np
from ppmonk.core.player import PlayerState
from ppmonk.core.spell_book import SpellBook
from ppmonk.core.timeline import Timeline

class MonkEnv(gym.Env):
    def __init__(self, seed_offset=0, current_talents=None, player_kwargs=None):
        # Obs: 16 (Base) + 1 (Last Spell ID) + 20 (Global Map) = 37 dims
        self.observation_space = spaces.Box(low=0, high=1, shape=(37,), dtype=np.float32)
        self.action_space = spaces.Discrete(9)
        self.action_map = {0: 'Wait', 1:'TP', 2:'BOK', 3:'RSK', 4:'SCK', 5:'FOF', 6:'WDP', 7:'SOTWL', 8:'SW'}
        self.spell_keys = list(self.action_map.values())[1:]
        self.scenario = 0
        self.training_mode = True
        self.rng = np.random.default_rng(seed_offset)
        
        # [新] 保存配置参数
        self.current_talents = current_talents if current_talents else []
        self.player_kwargs = player_kwargs if player_kwargs else {}

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None: self.rng = np.random.default_rng(seed)
        
        # [核心修复] 使用传入的参数初始化 Player 和 SpellBook
        self.player = PlayerState(**self.player_kwargs)
        self.book = SpellBook(talents=self.current_talents)
        self.book.apply_talents(self.player)
        
        # 应用天赋被动 (如力贯千钧)
        # 注意：这里假设你已经有了 TalentManager 的逻辑，或者像之前那样手动处理
        # 这里简单处理 Ascension
        if 'Ascension' in self.current_talents:
            self.player.max_energy += 20
            self.player.energy_regen_mult *= 1.1

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
            # 评估模式下满能量起手
            if not self.training_mode:
                self.player.energy = self.player.max_energy

        return self._get_obs(), {}

    # ... (以下方法保持不变: _get_obs, action_masks, step, _advance_time_with_mod) ...
    # 请确保复制之前 run_monk_ai_v8.py 中的这些方法逻辑
    def _get_obs(self):
        uptime, mod, _ = self.timeline.get_status(self.time)
        time_to_burst = 1.0
        if self.timeline.burst_start > 0:
            if self.time < self.timeline.burst_start:
                time_to_burst = (self.timeline.burst_start - self.time) / 20.0
            else:
                time_to_burst = 0.0 
        norm_energy = self.player.energy / self.player.max_energy # Use dynamic max
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
        obs = [norm_energy, norm_chi, norm_gcd, *norm_cds, norm_time, 1.0 if uptime else 0.0, mod / 3.0, *scen_onehot, time_to_burst, last_action_val]
        return np.concatenate((obs, self.timeline.global_map), axis=0).astype(np.float32)

    def action_masks(self):
        if self.time >= 20.0: return [False]*9
        masks = [True] * 9
        fof_mask_idx = None
        fof_spell = self.book.spells.get('FOF') if hasattr(self, 'book') else None
        if hasattr(self.book, 'active_talents'):
            print(f"DEBUG: 当前 active_talents = {self.book.active_talents}")
        for i, key in enumerate(self.spell_keys):
            spell = self.book.spells[key]
            is_usable = False
            if key == 'WDP':
                is_usable = spell.is_usable(self.player, self.book.spells)
            else:
                is_usable = spell.is_usable(self.player)
            if spell.abbr == self.player.last_spell_name:
                is_usable = False
            masks[i+1] = is_usable
            if key == 'FOF':
                fof_mask_idx = i + 1

        # Debugging path specifically for Fists of Fury availability
        if fof_spell is not None and fof_mask_idx is not None:
            fof_available = masks[fof_mask_idx]
            if fof_available:
                print("DEBUG: FOF 可用！")
            else:
                reasons = []
                if not fof_spell.is_known:
                    reasons.append("未学会")
                if fof_spell.current_cd > 0:
                    reasons.append(f"冷却中: {fof_spell.current_cd:.2f}s")
                if self.player.chi < fof_spell.chi_cost:
                    reasons.append(f"真气不足 {self.player.chi}/{fof_spell.chi_cost}")
                if getattr(self.player, 'is_channeling', False) and getattr(self.player, 'current_channel_spell', None) not in (None, fof_spell):
                    reasons.append("正在引导其他技能")
                if self.player.energy < fof_spell.energy_cost:
                    reasons.append(f"能量不足 {self.player.energy}/{fof_spell.energy_cost}")
                if not reasons:
                    reasons.append("其他原因不可用")
                print("DEBUG: FOF 不可用 -> " + "; ".join(reasons))
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
        if action_idx > 0: 
            key = self.action_map[action_idx]
            spell = self.book.spells[key]
            if spell.current_cd > 0.01: 
                return self._get_obs(), -10.0, False, False, {'damage': 0}
            dmg = spell.cast(self.player, self.book)
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
        reward = total_damage 
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