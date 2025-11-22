import gymnasium as gym
from gymnasium import spaces
import numpy as np
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.utils import get_device

# ==========================================
# 1. Core Classes (数值保持原样)
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

    # [新功能] 精确快进
    def advance_time(self, duration):
        """
        快进指定的时间(duration)，期间处理能量回复和引导伤害。
        返回这段时间内的总伤害。
        """
        total_damage = 0
        dt = 0.01 # 内部模拟精度 10ms
        elapsed = 0.0
        
        regen_rate = 10.0 * (1.0 + self.haste)
        
        while elapsed < duration:
            step = min(dt, duration - elapsed)
            
            # 1. 能量回复
            self.energy = min(self.max_energy, self.energy + regen_rate * step)
            
            # 2. 冷却转动 (GCD在外面单独算，这里只算buff/channel)
            # (CDs are managed by SpellBook tick)
            
            # 3. 引导伤害
            if self.is_channeling:
                self.channel_time_remaining -= step
                self.time_until_next_tick -= step
                
                if self.time_until_next_tick <= 1e-6:
                    if self.channel_ticks_remaining > 0:
                        spell = self.current_channel_spell
                        # 伤害计算
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

    def is_usable(self, player):
        if not self.is_known: return False
        if self.current_cd > 1e-2: return False
        if player.energy < self.energy_cost: return False
        if player.chi < self.chi_cost: return False
        # 注意：现在允许打断引导，所以移除 is_channeling 检查，或者由策略决定
        # 为了简单，还是禁止在引导时施法
        if player.is_channeling: return False 
        return True

    def cast(self, player):
        # 消耗
        player.energy -= self.energy_cost
        player.chi = max(0, player.chi - self.chi_cost)
        player.chi = min(player.max_chi, player.chi + self.chi_gen)
        
        # CD
        self.current_cd = self.get_effective_cd(player)
        
        # 精通
        triggers_mastery = self.is_combo_strike and (player.last_spell_name is not None) and (player.last_spell_name != self.abbr)
        player.last_spell_name = self.abbr
        
        # 占用时间 (Lockout Time)
        # 对于瞬发：占用 = GCD
        # 对于引导：占用 = 0 (开始引导后立即进入引导状态，但后续时间由 step 函数快进)
        # 但为了模型简单，我们认为施放动作本身是瞬发的，"时间流逝"由 step 函数处理
        
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
        return rsk.current_cd > 0 and fof.current_cd > 0 # WDP Logic

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

class Timeline:
    def __init__(self, scenario_id):
        self.scenario_id = scenario_id
        self.duration = 20.0
        self.burst_start = -1.0
        if scenario_id == 3: self.burst_start = 16.0
        
        # 全局地图
        self.global_map = np.zeros(20, dtype=np.float32)
        for i in range(20):
            t = float(i)
            mod = 1.0
            if scenario_id == 3 and t >= self.burst_start: mod = 3.0
            self.global_map[i] = mod / 3.0

    def get_status(self, t):
        mod = 1.0
        if self.scenario_id == 3 and t >= self.burst_start: mod = 3.0
        return True, mod, (t >= self.duration)

class MonkEnv(gym.Env):
    def __init__(self, seed_offset=0):
        # Obs: 10 (Dynamic) + 20 (Map) = 30
        self.observation_space = spaces.Box(low=0, high=1, shape=(30,), dtype=np.float32)
        self.action_space = spaces.Discrete(9)
        self.action_map = {0: 'Wait', 1:'TP', 2:'BOK', 3:'RSK', 4:'SCK', 5:'FOF', 6:'WDP', 7:'SOTWL', 8:'SW'}
        self.spell_keys = list(self.action_map.values())[1:]
        self.scenario = 0
        self.rng = np.random.default_rng(seed_offset)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None: self.rng = np.random.default_rng(seed)
        self.player = PlayerState()
        self.book = SpellBook(talents=['WDP', 'SW']) 
        
        scen_id = options['timeline'] if options else self.rng.integers(0, 4)
        self.scenario = scen_id 
        self.timeline = Timeline(scen_id)
        self.time = 0.0
        return self._get_obs(), {}

    def _get_obs(self):
        uptime, mod, _ = self.timeline.get_status(self.time)
        norm_energy = self.player.energy / 120.0
        norm_chi = self.player.chi / 6.0
        norm_gcd = self.player.gcd_remaining / 1.5
        norm_time = self.time / 20.0
        norm_cds = [self.book.spells[k].current_cd / 30.0 for k in ['RSK', 'FOF', 'WDP', 'SOTWL', 'SW']]
        norm_mod = mod / 3.0
        
        dynamic = [norm_energy, norm_chi, norm_gcd, *norm_cds, norm_time, norm_mod]
        return np.concatenate((dynamic, self.timeline.global_map), axis=0).astype(np.float32)

    def action_masks(self):
        # 如果时间结束，封锁所有
        if self.time >= 20.0: return [False]*9 # 其实Gym会重置，但保险起见
        
        masks = [True] * 9
        # 如果 GCD 还没转好，或者正在引导，不允许施放新技能 (Wait除外)
        # [重要] 在 Event-Driven 模式下，我们希望 AI 只有在"空闲"时才决策
        # 但为了处理"能量不足等一等"的情况，Wait 始终是可用的
        
        is_locked = (self.player.gcd_remaining > 0.01) or self.player.is_channeling
        if is_locked:
            # 理论上 Event-Driven 不应该出现在锁定状态被 call step
            # 除非我们显式设计了 "Wait until ready"
            pass

        for i, key in enumerate(self.spell_keys):
            spell = self.book.spells[key]
            # 特殊：对于 WDP，需要传入 spellbook 检查其他 CD
            if key == 'WDP':
                masks[i+1] = spell.is_usable(self.player, self.book.spells)
            else:
                masks[i+1] = spell.is_usable(self.player)
        return masks

    # ==========================================
    # [核心] 事件驱动的 Step 函数
    # ==========================================
    def step(self, action_idx):
        total_damage = 0
        current_mod = 1.0
        if self.scenario == 3 and self.time >= 16.0: current_mod = 3.0
        
        # 1. 执行动作 (Decision)
        executed = False
        time_advanced = 0.0
        
        if action_idx > 0: # Cast Spell
            key = self.action_map[action_idx]
            spell = self.book.spells[key]
            
            # 施放 (扣资源, 进CD, 给直接伤害)
            # 注意：引导技能返回0伤害，伤害在 tick 里出
            dmg = spell.cast(self.player)
            total_damage += dmg * current_mod
            
            # 确定这个动作占用的时间 (Lockout)
            # 瞬发 = GCD (通常1.0s, SW 0.4s)
            # 引导 = 引导时间 (FOF 4s)
            if spell.is_channeled:
                lockout = spell.get_effective_cast_time(self.player)
            else:
                lockout = self.player.gcd_remaining # 施放后自动设置了 gcd_remaining
                
            # [快进] 直接跳过这段时间！
            # 在这段时间里，PlayerState.tick 会处理引导伤害和能量回复
            dmg_tick = self.player.advance_time(lockout)
            
            # 处理 Mod (稍微复杂点，因为快进期间 Mod 可能变化)
            # 为了简单，这里假设快进期间 Mod 不变，或者取当前的。
            # 严格来说应该切片计算，但对于 20s 战斗误差可接受。
            total_damage += dmg_tick * current_mod
            
            # 也要让 SpellBook 转 CD
            self.book.tick(lockout)
            
            self.time += lockout
            executed = True
            
        else: # Wait (0)
            # 没技能打，或者没能量，或者纯粹想等
            # 我们强制它"等一小会儿"，比如 0.1s，或者等到最近的一个 CD 转好
            # 简单起见，Wait = 空过 0.1s 回能
            wait_time = 0.1
            dmg_tick = self.player.advance_time(wait_time)
            self.book.tick(wait_time)
            self.time += wait_time
            total_damage += dmg_tick * current_mod # 只有引导伤害可能在这里跳

        done = self.time >= 20.0
        
        # 纯伤害奖励，无作弊
        # 因为步数变少了（200步 -> 20步），每一步的权重变大了
        # 这极大地帮助了信用分配 (Credit Assignment)
        reward = total_damage 

        return self._get_obs(), reward, done, False, {'damage': total_damage}

def mask_fn(env): return env.action_masks()

# ==========================================
# 5. Execution
# ==========================================
def make_env(rank):
    def _init():
        env = MonkEnv(seed_offset=rank)
        env = ActionMasker(env, mask_fn)
        return env
    return _init

def run():
    print(f">>> 初始化事件驱动环境 (Event-Driven: ~20 Steps/Episode)...")
    # 步数极少，所以不需要太多并行
    num_cpu = 16 
    env = SubprocVecEnv([make_env(i) for i in range(num_cpu)])
    
    model = MaskablePPO(
        "MlpPolicy", 
        env, 
        verbose=1, 
        gamma=1.0,          
        learning_rate=3e-4,
        ent_coef=0.02, # 适当探索
        n_steps=256,   # 因为每局只有20步，256步=12局，足够了
        batch_size=512,    
    )
    
    # 步数少，总步数也可以减少
    # 50万步相当于玩了 2.5万局游戏！足够学会了
    print(">>> 开始训练 (Steps: 500k)...")
    model.learn(total_timesteps=500000) 
    
    print("\n>>> 评估结果...")
    eval_env = MonkEnv()
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

if __name__ == '__main__':
    run()