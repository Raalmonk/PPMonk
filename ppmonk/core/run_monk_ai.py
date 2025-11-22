import gymnasium as gym
from gymnasium import spaces
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.utils import get_device

# ==========================================
# 1. Core Classes (Player) - 保持不变
# ==========================================
class PlayerState:
    def __init__(self, rating_crit=2000, rating_haste=1500, rating_mastery=1000, rating_vers=500):
        self.rating_crit = rating_crit
        self.rating_haste = rating_haste
        self.rating_mastery = rating_mastery
        self.rating_vers = rating_vers
        self.base_mastery = 0.19
        self.base_crit = 0.10
        self.max_energy = 120.0
        self.energy = 120.0
        self.max_chi = 6
        self.chi = 2 
        self.last_spell_name = None 
        self.gcd_remaining = 0.0
        self.is_channeling = False
        self.current_channel_spell = None
        self.channel_time_remaining = 0.0
        self.channel_ticks_remaining = 0
        self.time_until_next_tick = 0.0
        self.channel_tick_interval = 0.0
        self.channel_mastery_snapshot = False
        self.crit = 0.0
        self.versatility = 0.0
        self.haste = 0.0
        self.mastery = 0.0
        self.update_stats()

    def update_stats(self):
        self.crit = (self.rating_crit / 4600.0) + self.base_crit
        self.versatility = (self.rating_vers / 5400.0)
        self.haste = (self.rating_haste / 4400.0) 
        dr_threshold = 1380 
        eff_mast_rating = self.rating_mastery
        if self.rating_mastery > dr_threshold:
            excess = self.rating_mastery - dr_threshold
            eff_mast_rating = dr_threshold + (excess * 0.9)
        self.mastery = (eff_mast_rating / 2000.0) + self.base_mastery

    def advance_time(self, duration):
        total_damage = 0
        dt = 0.01 
        elapsed = 0.0
        regen_rate = 10.0 * (1.0 + self.haste)
        
        while elapsed < duration:
            step = min(dt, duration - elapsed)
            self.energy = min(self.max_energy, self.energy + regen_rate * step)
            if self.gcd_remaining > 0:
                self.gcd_remaining = max(0, self.gcd_remaining - step)
            
            if self.is_channeling:
                self.channel_time_remaining -= step
                self.time_until_next_tick -= step
                if self.time_until_next_tick <= 1e-6:
                    if self.channel_ticks_remaining > 0:
                        spell = self.current_channel_spell
                        tick_dmg = spell.calculate_tick_damage(self)
                        total_damage += tick_dmg
                        self.channel_ticks_remaining -= 1
                        self.time_until_next_tick += self.channel_tick_interval
                if self.channel_time_remaining <= 1e-6 or self.channel_ticks_remaining <= 0:
                    self.is_channeling = False
                    self.current_channel_spell = None
                    self.channel_mastery_snapshot = False
            elapsed += step
        return total_damage

# ==========================================
# 2. Core: Spell Book - 保持不变
# ==========================================
class Spell:
    def __init__(self, abbr, ap_coeff, energy=0, chi_cost=0, chi_gen=0, cd=0, cd_haste=False, 
                 cast_time=0, cast_haste=False, is_channeled=False, ticks=1, req_talent=False, gcd_override=None):
        self.abbr = abbr
        self.ap_coeff = ap_coeff
        self.energy_cost = energy
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
        self.is_known = True 
        self.current_cd = 0.0
        self.is_combo_strike = True 

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
        if self.current_cd > 0.01: return False 
        if player.energy < self.energy_cost: return False
        if player.chi < self.chi_cost: return False
        return True

    def cast(self, player):
        player.energy -= self.energy_cost
        player.chi = max(0, player.chi - self.chi_cost)
        player.chi = min(player.max_chi, player.chi + self.chi_gen)
        
        self.current_cd = self.get_effective_cd(player)
        
        if self.gcd_override is not None:
            player.gcd_remaining = self.gcd_override
        else:
            player.gcd_remaining = 1.0
            
        triggers_mastery = self.is_combo_strike and \
                           (player.last_spell_name is not None) and \
                           (player.last_spell_name != self.abbr)

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
            return 0.0 
        else:
            return self.calculate_tick_damage(player, mastery_override=triggers_mastery)

    def calculate_tick_damage(self, player, mastery_override=None):
        dmg = self.tick_coeff
        apply_mastery = False
        if mastery_override is not None:
            apply_mastery = mastery_override
        elif self.is_channeled:
            apply_mastery = player.channel_mastery_snapshot
        if apply_mastery: dmg *= (1.0 + player.mastery)
        dmg *= (1.0 + player.versatility)
        return dmg

    def tick_cd(self, dt):
        if self.current_cd > 0: self.current_cd = max(0, self.current_cd - dt)

class SpellWDP(Spell):
    def is_usable(self, player, other_spells):
        if not super().is_usable(player): return False
        rsk = other_spells['RSK']
        fof = other_spells['FOF']
        return rsk.current_cd > 0 and fof.current_cd > 0

class SpellBook:
    def __init__(self, talents):
        self.spells = {
            'TP': Spell('TP', 0.88, energy=50, chi_gen=2),
            'BOK': Spell('BOK', 3.56, chi_cost=1),
            'RSK': Spell('RSK', 4.228, chi_cost=2, cd=10.0, cd_haste=True),
            'SCK': Spell('SCK', 3.52, chi_cost=2, is_channeled=True, ticks=4, cast_time=1.5, cast_haste=True),
            'FOF': Spell('FOF', 2.07 * 5, chi_cost=3, cd=24.0, cd_haste=True, is_channeled=True, ticks=5, cast_time=4.0, cast_haste=True),
            'WDP': SpellWDP('WDP', 5.40, cd=30.0, req_talent=True),
            'SOTWL': Spell('SOTWL', 15.12, chi_cost=2, cd=30.0, req_talent=True),
            'SW': Spell('SW', 8.96, cd=30.0, cast_time=0.4, req_talent=True, gcd_override=0.4)
        }
        self.talents = talents
        for s in self.spells.values():
            if s.req_talent: s.is_known = (s.abbr in talents)
            else: s.is_known = True
    def tick(self, dt):
        for s in self.spells.values(): s.tick_cd(dt)

# ==========================================
# 3. Timeline (With Reset)
# ==========================================
class Timeline:
    def __init__(self, scenario_id):
        self.scenario_id = scenario_id
        self.duration = 20.0
        self.burst_start = -1.0
        if scenario_id == 3: self.burst_start = 16.0
        self.global_map = np.zeros(20, dtype=np.float32)
        for i in range(20):
            t = float(i)
            mod = 1.0
            if scenario_id == 3 and t >= self.burst_start: mod = 3.0
            self.global_map[i] = mod / 3.0

    def reset(self): pass

    def get_status(self, t):
        mod = 1.0
        if self.scenario_id == 3 and t >= self.burst_start: mod = 3.0
        return True, mod, (t >= self.duration)

# ==========================================
# 4. MonkEnv (Time Clamping Added)
# ==========================================
class MonkEnv(gym.Env):
    def __init__(self, seed_offset=0):
        self.observation_space = spaces.Box(low=0, high=1, shape=(37,), dtype=np.float32)
        self.action_space = spaces.Discrete(9)
        self.action_map = {0: 'Wait', 1:'TP', 2:'BOK', 3:'RSK', 4:'SCK', 5:'FOF', 6:'WDP', 7:'SOTWL', 8:'SW'}
        self.spell_keys = list(self.action_map.values())[1:]
        self.scenario = 0
        self.training_mode = True
        self.rng = np.random.default_rng(seed_offset)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None: self.rng = np.random.default_rng(seed)
        self.player = PlayerState()
        self.book = SpellBook(talents=['WDP', 'SW']) 
        if options and 'timeline' in options:
            scen_id = options['timeline']
        else:
            scen_id = self.rng.integers(0, 4)
        self.scenario = scen_id 
        self.timeline = Timeline(scen_id)
        self.timeline.reset()
        
        if self.training_mode and (options is None):
            self.time = self.rng.uniform(0.0, 18.0)
            self.player.energy = self.rng.uniform(0.0, 120.0)
            self.player.chi = self.rng.integers(0, 7)
        else:
            self.time = 0.0
        return self._get_obs(), {}

    def _get_obs(self):
        uptime, mod, _ = self.timeline.get_status(self.time)
        time_to_burst = 1.0
        if self.timeline.burst_start > 0:
            if self.time < self.timeline.burst_start:
                time_to_burst = (self.timeline.burst_start - self.time) / 20.0
            else:
                time_to_burst = 0.0 
        
        norm_energy = self.player.energy / 120.0
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
        # 如果时间到了，不允许任何操作 (Wait也不行，强制结束)
        if self.time >= 20.0: return [False]*9
        
        masks = [True] * 9
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
        return masks

    def step(self, action_idx):
        total_damage = 0
        
        # 1. 自动等待 (Auto Wait)
        time_to_wait = 0.0
        if self.player.gcd_remaining > 0:
            time_to_wait = max(time_to_wait, self.player.gcd_remaining)
        if action_idx > 0:
            key = self.action_map[action_idx]
            spell = self.book.spells[key]
            if spell.current_cd > 0:
                time_to_wait = max(time_to_wait, spell.current_cd)
        
        # [时间截断] 等待时间也不能超过战斗结束
        remaining_time = max(0.0, self.timeline.duration - self.time)
        time_to_wait = min(time_to_wait, remaining_time)

        if time_to_wait > 0:
            total_damage += self._advance_time_with_mod(time_to_wait)
            
        # 2. 执行动作
        lockout = 0.0
        reward_shaping = 0.0
        
        # 起手引导
        if self.player.last_spell_name is None and action_idx != 1: 
             reward_shaping -= 5.0
        if action_idx == 1 and self.player.chi < 4:
             reward_shaping += 1.0

        if action_idx > 0: 
            key = self.action_map[action_idx]
            spell = self.book.spells[key]
            
            if spell.current_cd > 0.01: 
                return self._get_obs(), -10.0, False, False, {'damage': 0}

            # 瞬发伤害（如 TP/RSK/SW）是在出手瞬间结算的，不受持续时间截断影响
            # 但如果是 FOF，cast() 返回 0，伤害靠 lockout 里的 tick
            dmg = spell.cast(self.player)
            _, current_mod, _ = self.timeline.get_status(self.time)
            total_damage += dmg * current_mod
            
            if spell.is_channeled:
                lockout = spell.get_effective_cast_time(self.player)
            else:
                lockout = self.player.gcd_remaining
        else: 
            lockout = 0.1
            
        # [核心修复] 截断动作持续时间
        # 如果此时是 19.4s，lockout 是 3.0s，我们只能跑 0.6s
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

def mask_fn(env): return env.action_masks()

def make_env(rank):
    def _init():
        env = MonkEnv(seed_offset=rank)
        env = ActionMasker(env, mask_fn)
        return env
    return _init

def run():
    print(f">>> 初始化终极修正版 (Time Clamping Fix)...")
    num_cpu = 16 
    env = SubprocVecEnv([make_env(i) for i in range(num_cpu)])
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    model = MaskablePPO(
        "MlpPolicy", 
        env, 
        verbose=1, 
        device=device,
        gamma=1.0,          
        learning_rate=3e-4,
        ent_coef=0.02,
        n_steps=512,       
        batch_size=1024,    
    )
    
    print(">>> 开始训练 (Steps: 1,000,000)...")
    model.learn(total_timesteps=1000000) 
    
    print("\n>>> 评估结果...")
    eval_env = MonkEnv()
    eval_env.training_mode = False 
    eval_env = ActionMasker(eval_env, mask_fn)
    
    scenarios = [(0, "Patchwerk"), (3, "Execute (End +200%)")]
    
    for scen_id, name in scenarios:
        print(f"\n{'='*30}\nTesting Scenario: {name}\n{'='*30}")
        obs, _ = eval_env.reset(options={'timeline': scen_id})
        print(f"{'Time':<6} | {'Action':<8} | {'Chi':<3} | {'Eng':<4} | {'AP%':<6}")
        
        total_ap = 0.0
        done = False
        while not done:
            masks = eval_env.action_masks()
            action, _ = model.predict(obs, action_masks=masks, deterministic=True)
            action_item = action.item()
            
            t_now = eval_env.unwrapped.time
            chi = eval_env.unwrapped.player.chi
            en = eval_env.unwrapped.player.energy
            
            obs, reward, done, _, info = eval_env.step(action_item)
            dmg = info['damage']
            total_ap += dmg
            act_name = eval_env.unwrapped.action_map[action_item]
            
            if action_item != 0:
                print(f"{t_now:<6.1f} | {act_name:<8} | {int(chi):<3} | {int(en):<4} | {dmg:<6.2f}")
            elif dmg > 0: 
                print(f"{t_now:<6.1f} | {'(Tick)':<8} | {int(chi):<3} | {int(en):<4} | {dmg:<6.2f}")
        
        print(f"{'-'*30}")
        print(f"Total AP Output: {total_ap:.2f}")
        
        p = eval_env.unwrapped.player
        print(f"--- Character Stats ---")
        print(f"Haste: {p.haste*100:.2f}%  Crit: {p.crit*100:.2f}%")
        print(f"Mast : {p.mastery*100:.2f}%  Vers: {p.versatility*100:.2f}%")

if __name__ == '__main__':
    run()