import gymnasium as gym
from gymnasium import spaces
import numpy as np
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.utils import get_device


# ==========================================
# 1. Core Logic (Player & Spell) - 保持不变
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

    def tick(self, delta_time):
        regen_rate = 10.0 * (1.0 + self.haste)
        self.energy = min(self.max_energy, self.energy + regen_rate * delta_time)
        self.gcd_remaining = max(0, self.gcd_remaining - delta_time)
        tick_damage = 0
        if self.is_channeling:
            self.channel_time_remaining -= delta_time
            self.time_until_next_tick -= delta_time
            if self.time_until_next_tick <= 0:
                if self.channel_ticks_remaining > 0:
                    spell = self.current_channel_spell
                    tick_damage = spell.calculate_tick_damage(self)
                    self.channel_ticks_remaining -= 1
                    self.time_until_next_tick += self.channel_tick_interval
            if self.channel_time_remaining <= 0 or self.channel_ticks_remaining <= 0:
                self.is_channeling = False
                self.current_channel_spell = None
                self.channel_mastery_snapshot = False
        return tick_damage


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

    def is_usable(self, player, other_spells):
        if not self.is_known: return False
        if self.current_cd > 1e-2: return False
        if player.energy < self.energy_cost: return False
        if player.chi < self.chi_cost: return False
        if player.is_channeling: return False
        return True

    def cast(self, player):
        player.energy -= self.energy_cost
        player.chi = max(0, player.chi - self.chi_cost)
        player.chi = min(player.max_chi, player.chi + self.chi_gen)
        cd_val = self.base_cd / (1.0 + player.haste) if self.cd_haste else self.base_cd
        self.current_cd = cd_val
        if self.gcd_override is not None:
            player.gcd_remaining = self.gcd_override
        else:
            player.gcd_remaining = 1.0
        triggers_mastery = self.is_combo_strike and (player.last_spell_name is not None) and (
                    player.last_spell_name != self.abbr)
        player.last_spell_name = self.abbr
        if self.is_channeled:
            cast_t = self.base_cast_time / (1.0 + player.haste) if self.cast_haste else self.base_cast_time
            player.is_channeling = True
            player.current_channel_spell = self
            player.channel_time_remaining = cast_t
            player.channel_ticks_remaining = self.total_ticks
            player.channel_tick_interval = cast_t / self.total_ticks
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
        if apply_mastery:
            dmg *= (1.0 + player.mastery)
        dmg *= (1.0 + player.versatility)
        return dmg

    def tick_cd(self, dt):
        if self.current_cd > 0: self.current_cd = max(0, self.current_cd - dt)


class SpellWDP(Spell):
    def is_usable(self, player, other_spells):
        if not super().is_usable(player, other_spells): return False
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
            # FOF
            'FOF': Spell('FOF', 2.07 * 5, chi_cost=3, cd=24.0, cd_haste=True, is_channeled=True, ticks=5, cast_time=4.0,
                         cast_haste=True),
            'WDP': SpellWDP('WDP', 5.40, cd=30.0, req_talent=True),
            'SOTWL': Spell('SOTWL', 15.12, chi_cost=2, cd=30.0, req_talent=True),
            'SW': Spell('SW', 8.96, cd=30.0, cast_time=0.4, req_talent=True, gcd_override=0.4)
        }
        self.talents = talents
        for s in self.spells.values():
            if s.req_talent:
                s.is_known = (s.abbr in talents)
            else:
                s.is_known = True

    def tick(self, dt):
        for s in self.spells.values(): s.tick_cd(dt)


# ==========================================
# 3. Timeline (The Brain)
# ==========================================
class Timeline:
    def __init__(self, scenario_id):
        self.scenario_id = scenario_id
        self.duration = 20.0
        self.burst_start = -1.0
        if scenario_id == 3: self.burst_start = 16.0

        # [核心功能] 生成全图视野
        self.global_map = self._generate_global_map()

    def _generate_global_map(self):
        # 创建一个 20 维的向量，每一位代表第 N 秒的伤害倍率
        # Resolution: 1 second per bin
        map_vec = np.zeros(20, dtype=np.float32)
        for i in range(20):
            t = float(i)
            _, mod, _ = self.get_status_at(t)
            map_vec[i] = mod / 3.0  # 归一化 (最大倍率3.0)
        return map_vec

    def get_status_at(self, t):
        uptime, mod, done = True, 1.0, False
        if t >= self.duration: return uptime, mod, True
        if self.scenario_id == 1 and 8.0 <= t < 12.0: uptime = False
        if self.scenario_id == 2 and 8.0 <= t < 12.0:
            # 这里简化处理，静态地图不包含概率性停手，只包含确定性易伤
            # AI 需要在运行时应对概率，但易伤通常是确定的
            pass
        if self.scenario_id == 3 and t >= self.burst_start: mod = 3.0
        return uptime, mod, done

    def get_status(self, t):
        return self.get_status_at(t)


# ==========================================
# 4. Gym Environment (Global View)
# ==========================================
class MonkEnv(gym.Env):
    def __init__(self, seed_offset=0):
        # Obs 结构:
        # [0-9]: 动态状态 (能量, 真气, GCD, 5个CD, 时间, Mod) -> 10 维
        # [10-29]: 全局地图 (Global Map) -> 20 维
        # Total = 30
        self.observation_space = spaces.Box(low=0, high=1, shape=(30,), dtype=np.float32)
        self.action_space = spaces.Discrete(9)
        self.action_map = {0: 'Wait', 1: 'TP', 2: 'BOK', 3: 'RSK', 4: 'SCK', 5: 'FOF', 6: 'WDP', 7: 'SOTWL', 8: 'SW'}
        self.spell_keys = list(self.action_map.values())[1:]
        self.scenario = 0
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
        self.timeline = Timeline(scen_id)  # 初始化时生成地图

        self.time = 0.0
        return self._get_obs(), {}

    def _get_obs(self):
        uptime, mod, _ = self.timeline.get_status(self.time)

        # 1. Dynamic State
        norm_energy = self.player.energy / 120.0
        norm_chi = self.player.chi / 6.0
        norm_gcd = self.player.gcd_remaining / 1.5
        norm_time = self.time / 20.0
        norm_cds = [self.book.spells[k].current_cd / 30.0 for k in ['RSK', 'FOF', 'WDP', 'SOTWL', 'SW']]
        norm_mod = mod / 3.0

        dynamic_state = [norm_energy, norm_chi, norm_gcd, *norm_cds, norm_time, norm_mod]

        # 2. Static Global Map (God View)
        # 直接把整场战斗的剧本贴在它脸上
        global_map = self.timeline.global_map

        obs = np.concatenate((dynamic_state, global_map), axis=0)
        return np.array(obs, dtype=np.float32)

    def action_masks(self):
        uptime, _, _ = self.timeline.get_status(self.time)
        if not uptime: return [True] + [False] * 8
        if self.player.gcd_remaining > 0: return [True] + [False] * 8
        if self.player.is_channeling: return [True] + [False] * 8
        masks = [True] * 9
        for i, key in enumerate(self.spell_keys):
            masks[i + 1] = self.book.spells[key].is_usable(self.player, self.book.spells)
        return masks

    def step(self, action_idx):
        step_dt = 0.1
        step_damage = 0
        uptime, mod, _ = self.timeline.get_status(self.time)

        if action_idx > 0:
            key = self.action_map[action_idx]
            dmg = self.book.spells[key].cast(self.player)
            step_damage += dmg

        tick_dmg = self.player.tick(step_dt)
        step_damage += tick_dmg
        self.book.tick(step_dt)

        step_damage *= mod
        self.time += step_dt
        _, _, done = self.timeline.get_status(self.time)

        # Pure Reward
        reward = step_damage
        return self._get_obs(), reward, done, False, {'damage': step_damage}


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
    print(f">>> 初始化全知全能环境 (Global Timeline View)...")
    num_cpu = 16
    env = SubprocVecEnv([make_env(i) for i in range(num_cpu)])

    model = MaskablePPO(
        "MlpPolicy",
        env,
        verbose=1,
        gamma=1.0,
        learning_rate=3e-4,
        ent_coef=0.01,
        n_steps=1024,
        batch_size=2048,
        policy_kwargs=dict(net_arch=[256, 256])  # 标准网络即可
    )

    # 30万步足以收敛，因为不需要"猜"了
    print(">>> 开始训练 (Steps: 300,000)...")
    model.learn(total_timesteps=300000)

    print("\n>>> 评估结果...")
    eval_env = MonkEnv()
    eval_env = ActionMasker(eval_env, mask_fn)

    scenarios = [(0, "Patchwerk"), (3, "Execute (End +200%)")]

    for scen_id, name in scenarios:
        print(f"\n{'=' * 30}\nTesting Scenario: {name}\n{'=' * 30}")
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

        print(f"{'-' * 30}")
        print(f"Total AP Output: {total_ap:.2f}")


if __name__ == '__main__':
    run()