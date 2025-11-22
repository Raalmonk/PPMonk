"""Entrypoint for training or evaluation with the PPMonk environment."""

import torch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.vec_env import SubprocVecEnv

from ppmonk.envs.monk_env import MonkEnv


def mask_fn(env):
    return env.action_masks()


def make_env(rank):
    def _init():
        env = MonkEnv(seed_offset=rank)
        env = ActionMasker(env, mask_fn)
        return env

    return _init


def run():
    print(">>> 初始化 PPMonk (Refactored + Talent System)...")

    num_cpu = 16
    env = SubprocVecEnv([make_env(i) for i in range(num_cpu)])

    model = MaskablePPO(
        "MlpPolicy",
        env,
        verbose=1,
        device="cuda",
        gamma=1.0,
        learning_rate=3e-4,
        ent_coef=0.02,
        n_steps=512,
        batch_size=1024,
    )

    print(">>> 开始训练...")
    model.learn(total_timesteps=1000000)

    # ... (评估代码) ...


if __name__ == '__main__':
    run()
