import gymnasium as gym
from gymnasium import spaces
import numpy as np
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker


# ==========================================
# 1. Core: Player State
# ==========================================
class PlayerState:
    def __init__(self, attack_power=5000, rating_crit=2000, rating_haste=1500, rating_mastery=1000, rating_vers=500):
        self.attack_power = attack_power
        self.rating_crit = rating_crit
        self.rating_haste = rating_haste
        self.rating_mastery = rating_mastery
        self.rating_vers = rating_vers

        self.base_crit = 0.10
        self.base_mastery = 0.19

        self.max_energy = 120.0
        self.energy = 120.0
        self.max_chi = 6
        self.chi = 2  # 起手2豆

        self.last_spell_name = None
        self.gcd_remaining = 0.0
        self.is_channeling = False
        self.current_channel_spell = None
        self.channel_time_remaining = 0.0
        self.channel_ticks_remaining = 0
        self.time_until_next_tick = 0.0
        self.channel_tick_interval = 0.0

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
        regen = 10.0 * (1.0 + self.haste)
        self.energy = min(self.max_energy, self.energy + regen * delta_time)
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
        return tick_damage


# ==========================================
# 2. Core: Spell Book
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

        player.last_spell_name = self.abbr

        if self.is_channeled:
            cast_t = self.base_cast_time / (1.0 + player.haste) if self.cast_haste else self.base_cast_time
            player.is_channeling = True
            player.current_channel_spell = self
            player.channel_time_remaining = cast_t
            player.channel_ticks_remaining = self.total_ticks
            player.channel_tick_interval = cast_t / self.total_ticks
            player.time_until_next_tick = player.channel_tick_interval
            return 0
        else:
            return self.calculate_tick_damage(player)

    def calculate_tick_damage(self, player):
        dmg = player.attack_power * self.tick_coeff
        if player.last_spell_name != self.abbr: dmg *= (1.0 + player.mastery)
        dmg *= (1.0 + player.versatility)
        dmg *= (1.0 + player.crit)
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
            'FOF': Spell('FOF', 10.35, chi_cost=3, cd=24.0, cd_haste=True, is_channeled=True, ticks=5, cast_time=4.0,
                         cast_haste=True),
            'WDP': SpellWDP('WDP', 5.40, cd=30.0, req_talent=True),
            'SOTWL': Spell('SOTWL', 15.12, chi_cost=2, cd=30.0, req_talent=True),
            'SW': Spell('SW', 8.96, cd=30.0, cast_time=0.4, req_talent=True, gcd_override=0.4)
        }
        for s in self.spells.values():
            if s.req_talent and s.abbr not in talents:
                s.is_known = False
            else:
                if s.req_talent: s.is_known = True

    def tick(self, dt):
        for s in self.spells.values(): s.tick_cd(dt)


# ==========================================
# 3. Core: Timeline
# ==========================================
class Timeline:
    def __init__(self, scenario_id):
        self.scenario_id = scenario_id
        self.duration = 20.0
        self.is_random_dt = False

    def reset(self):
        self.is_random_dt = (np.random.rand() < 0.2) if self.scenario_id == 2 else False

    def get_status(self, t):
        uptime, mod, done = True, 1.0, False
        if t >= self.duration: return uptime, mod, True
        if self.scenario_id == 1 and 8.0 <= t < 12.0: uptime = False
        if self.scenario_id == 2 and 8.0 <= t < 12.0 and self.is_random_dt: uptime = False
        if self.scenario_id == 3 and t >= 16.0: mod = 3.0
        return uptime, mod, done


# ==========================================
# 4. Gym Environment (Improved)
# ==========================================
class MonkEnv(gym.Env):
    def __init__(self):
        self.observation_space = spaces.Box(low=0, high=1000, shape=(14,), dtype=np.float32)
        self.action_space = spaces.Discrete(9)
        self.action_map = {0: 'Wait', 1: 'TP', 2: 'BOK', 3: 'RSK', 4: 'SCK', 5: 'FOF', 6: 'WDP', 7: 'SOTWL', 8: 'SW'}
        self.spell_keys = list(self.action_map.values())[1:]
        self.scenario = 0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.player = PlayerState()

        # --- 配置核心点：只点 WDP 和 SW，不点 SOTWL ---
        self.book = SpellBook(talents=['WDP', 'SW'])

        scen_id = options['timeline'] if options else np.random.randint(0, 4)
        self.timeline = Timeline(scen_id)
        self.timeline.reset()
        self.time = 0.0
        return self._get_obs(), {}

    def _get_obs(self):
        uptime, mod, _ = self.timeline.get_status(self.time)
        obs = [
            self.player.energy, self.player.chi, self.player.gcd_remaining,
            self.book.spells['RSK'].current_cd,
            self.book.spells['FOF'].current_cd,
            self.book.spells['WDP'].current_cd,
            self.book.spells['SOTWL'].current_cd,
            self.book.spells['SW'].current_cd,
            self.time,
            1.0 if uptime else 0.0,
            mod
        ]
        return np.array(obs + [0] * (14 - len(obs)), dtype=np.float32)

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
        total_damage = 0
        uptime, mod, _ = self.timeline.get_status(self.time)

        # Action
        if action_idx > 0:
            key = self.action_map[action_idx]
            dmg = self.book.spells[key].cast(self.player)
            total_damage += dmg

        # Tick
        tick_dmg = self.player.tick(step_dt)
        total_damage += tick_dmg
        self.book.tick(step_dt)

        total_damage *= mod
        self.time += step_dt
        _, _, done = self.timeline.get_status(self.time)

        # --- Reward Shaping (关键修复) ---
        reward = total_damage

        # 1. 鼓励回豆：如果只有0-1个豆，且打了TP，给额外奖励
        if action_idx == 1 and self.player.chi <= 3:
            reward += 500  # 相当于打了一个小技能的奖励，诱导它去打TP

        # 2. 惩罚溢出：如果满豆还打TP，给惩罚
        if action_idx == 1 and self.player.chi >= 5:
            reward -= 500

        return self._get_obs(), reward, done, False, {'damage': total_damage}


def mask_fn(env): return env.action_masks()


def run():
    print(">>> 初始化训练环境 (Talents: WDP, SW)...")
    env = MonkEnv()
    env = ActionMasker(env, mask_fn)

    model = MaskablePPO("MlpPolicy", env, verbose=1, gamma=0.99, learning_rate=3e-4)
    # 增加步数到 80000，确保学会循环
    print(">>> 开始训练 (Steps: 80k)...")
    model.learn(total_timesteps=80000)

    scenarios = [(0, "Patchwerk"), (3, "Execute (End +200%)")]

    for scen_id, name in scenarios:
        print(f"\n{'=' * 30}\nTesting Scenario: {name}\n{'=' * 30}")
        obs, _ = env.reset(options={'timeline': scen_id})
        print(f"{'Time':<6} | {'Action':<8} | {'Chi':<3} | {'Eng':<4} | {'GCD':<4} | {'Dmg':<6}")

        done = False
        while not done:
            masks = env.action_masks()
            action, _ = model.predict(obs, action_masks=masks, deterministic=True)
            action_item = action.item()

            # State Capture
            t_now = env.unwrapped.time
            chi = env.unwrapped.player.chi
            en = env.unwrapped.player.energy
            gcd = env.unwrapped.player.gcd_remaining

            obs, reward, done, _, info = env.step(action_item)
            dmg = info['damage']

            act_name = env.unwrapped.action_map[action_item]

            # 智能Log: 如果是 Wait 且 GCD > 0，显示 Wait(GCD)
            # 如果是有伤害或者是非Wait动作，打印
            if action_item != 0:
                print(f"{t_now:<6.1f} | {act_name:<8} | {int(chi):<3} | {int(en):<4} | {0.0:<4} | {int(dmg):<6}")
            elif dmg > 0:  # 引导伤害
                print(f"{t_now:<6.1f} | {'(Tick)':<8} | {int(chi):<3} | {int(en):<4} | {gcd:<4.1f} | {int(dmg):<6}")
            # 如果是发呆，每 1.0 秒打印一次，避免刷屏
            elif int(t_now * 10) % 10 == 0:
                pass  # 可以选择打印 Wait 方便调试，这里暂时省略保持清爽


if __name__ == '__main__':
    run()