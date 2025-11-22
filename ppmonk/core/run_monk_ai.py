import gymnasium as gym
from gymnasium import spaces
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.utils import get_device


# ==========================================
# 1. Core Logic (保持逻辑完全不变，只改训练参数)
# ==========================================
# ... (此处粘贴 PlayerState, Spell, SpellBook, Timeline, MonkEnv 类的代码) ...
# ... (为了节省篇幅，请直接使用上一版 run_monk_pro.py 中的这几个类，逻辑完全一致) ...
# ... (务必确保 MonkEnv 的 _get_obs 和 step 逻辑是最新的纯净版) ...

# 为了方便运行，我把关键类再次精简列出，实际运行时请确保完整
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
        if apply_mastery: dmg *= (1.0 + player.mastery)
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


class Timeline:
    def __init__(self, scenario_id):
        self.scenario_id = scenario_id
        self.duration = 20.0
        self.is_random_dt = False
        self.burst_start = -1.0
        if scenario_id == 3: self.burst_start = 16.0

    def reset(self):
        self.is_random_dt = (np.random.rand() < 0.2) if self.scenario_id == 2 else False

    def get_status(self, t):
        uptime, mod, done = True, 1.0, False
        if t >= self.duration: return uptime, mod, True
        if self.scenario_id == 1 and 8.0 <= t < 12.0: uptime = False
        if self.scenario_id == 2 and 8.0 <= t < 12.0 and self.is_random_dt: uptime = False
        if self.scenario_id == 3 and t >= self.burst_start: mod = 3.0
        return uptime, mod, done


class MonkEnv(gym.Env):
    def __init__(self, seed_offset=0):
        self.observation_space = spaces.Box(low=0, high=1, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(9)
        self.action_map = {0: 'Wait', 1: 'TP', 2: 'BOK', 3: 'RSK', 4: 'SCK', 5: 'FOF', 6: 'WDP', 7: 'SOTWL', 8: 'SW'}
        self.spell_keys = list(self.action_map.values())[1:]
        self.scenario = 0
        self.training_mode = True  # Enable RSI
        self.rng = np.random.default_rng(seed_offset)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.player = PlayerState()
        self.book = SpellBook(talents=['WDP', 'SW'])
        if options and 'timeline' in options:
            scen_id = options['timeline']
        else:
            scen_id = self.rng.integers(0, 4)
        self.scenario = scen_id
        self.timeline = Timeline(scen_id)
        self.timeline.reset()

        # RSI: 训练模式下随机出生
        if self.training_mode and (options is None):
            self.time = self.rng.uniform(0.0, 18.0)
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
        obs = [norm_energy, norm_chi, norm_gcd, *norm_cds, norm_time, 1.0 if uptime else 0.0, mod / 3.0, *scen_onehot,
               time_to_burst]
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
        reward = step_damage
        return self._get_obs(), reward, done, False, {'damage': step_damage}


def mask_fn(env): return env.action_masks()


# ==========================================
# 4. Hardware Optimization Wrapper
# ==========================================
def make_env(rank):
    def _init():
        env = MonkEnv(seed_offset=rank)
        env = ActionMasker(env, mask_fn)
        return env

    return _init


def run():
    # 检查 CUDA
    device = get_device("auto")
    print(f">>> 硬件检测: 正在使用 {device}")
    if device.type == 'cuda':
        print(f">>> GPU: {torch.cuda.get_device_name(0)}")

    # [极限压榨] 开 24 个进程 (9800X3D 是8核16线程，Python多进程开多点没事，能掩盖等待)
    num_cpu = 24
    print(f">>> 初始化大规模并行环境 ({num_cpu} Envs)...")
    env = SubprocVecEnv([make_env(i) for i in range(num_cpu)])

    # [网络升级] 暴力加宽网络，强迫GPU干活
    # [Batch Size] 拉满到 16384 (4096 steps * 4 mini-batches)
    # [Ent Coef] 0.05 保持高探索
    print(">>> 配置重型 PPO 模型 (Large Net, Huge Batch)...")
    model = MaskablePPO(
        "MlpPolicy",
        env,
        verbose=1,
        device="cuda",  # 强制 CUDA
        gamma=1.0,  # 纯粹的数学最优
        learning_rate=3e-4,
        ent_coef=0.05,  # 高探索
        n_steps=2048,  # 每个环境跑2048步才更新一次 (总buffer = 2048 * 24 = 49152)
        batch_size=4096,  # 每次喂给GPU 4096条数据
        n_epochs=10,  # 每次更新反复榨干数据 10 遍
        policy_kwargs=dict(
            net_arch=[512, 512, 512]  # 三层512的大网络，这下4080得动一动了
        )
    )

    # [海量训练] 500万步！
    # 由于并行度高，这其实跑得很快
    print(">>> 开始极限训练 (Steps: 5,000,000)...")
    model.learn(total_timesteps=5000000)

    # --- Evaluation ---
    print("\n>>> 训练完成，开始评估...")
    eval_env = MonkEnv()
    eval_env.training_mode = False  # 关闭 RSI，正常从0开始
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
    # Windows 必须加这行
    run()