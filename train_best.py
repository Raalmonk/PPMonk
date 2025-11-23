"""Robust training script for PPMonk using MaskablePPO and evaluation callbacks."""

from __future__ import annotations

import os

import torch
from stable_baselines3.common.callbacks import CallbackList, CheckpointCallback, EvalCallback
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecMonitor
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

from ppmonk.envs.monk_env import MonkEnv

LOG_DIR = "./logs/"
MODEL_DIR = "./models/"
TOTAL_TIMESTEPS = 2_000_000
NUM_CPU = 16
EVAL_FREQ = 10_000
CHECKPOINT_FREQ = 200_000

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)


def mask_fn(env: MonkEnv):
    """Expose action masks from the environment for MaskablePPO."""

    return env.action_masks()


def make_train_env(rank: int, seed: int = 0):
    """Factory to create a masked training environment with a unique seed."""

    def _init():
        env = MonkEnv(seed_offset=rank + seed)
        return ActionMasker(env, mask_fn)

    return _init


def make_eval_env():
    """Create a deterministic evaluation environment without RSI."""

    env = MonkEnv()
    env.training_mode = False
    return ActionMasker(env, mask_fn)


def get_best_hyperparameters():
    """Return the tuned hyperparameters for MaskablePPO."""

    return {
        "learning_rate": 3e-4,
        "n_steps": 512,
        "batch_size": 1024,
        "n_epochs": 10,
        "gamma": 1.0,
        "gae_lambda": 0.95,
        "clip_range": 0.2,
        "ent_coef": 0.02,
        "policy_kwargs": {"net_arch": [256, 256]},
    }


def run_training():
    """Launch parallelized training with evaluation and checkpointing."""

    print(f">>> [Init] 启动 {NUM_CPU} 核并行训练...")

    train_env = SubprocVecEnv([make_train_env(i) for i in range(NUM_CPU)])
    train_env = VecMonitor(train_env, filename=os.path.join(LOG_DIR, "train_monitor"))

    eval_env = DummyVecEnv([make_eval_env])
    eval_env = VecMonitor(eval_env, filename=os.path.join(LOG_DIR, "eval_monitor"))

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=MODEL_DIR,
        log_path=LOG_DIR,
        eval_freq=max(EVAL_FREQ // NUM_CPU, 1),
        n_eval_episodes=5,
        deterministic=True,
        render=False,
        verbose=1,
    )

    checkpoint_callback = CheckpointCallback(
        save_freq=max(CHECKPOINT_FREQ // NUM_CPU, 1),
        save_path=MODEL_DIR,
        name_prefix="monk_ckpt",
        save_vecnormalize=False,
    )

    callbacks = CallbackList([eval_callback, checkpoint_callback])

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f">>> [Device] 使用硬件: {device}")

    model = MaskablePPO(
        "MlpPolicy",
        train_env,
        verbose=1,
        tensorboard_log=LOG_DIR,
        device=device,
        **get_best_hyperparameters(),
    )

    print(f">>> [Start] 目标步数: {TOTAL_TIMESTEPS}")
    model.learn(total_timesteps=TOTAL_TIMESTEPS, callback=callbacks, progress_bar=True)

    print(">>> [Done] 训练结束！请检查 models/best_model.zip")

    print("\n>>> [Demo] 加载最强模型进行演示...")
    best_model = MaskablePPO.load(os.path.join(MODEL_DIR, "best_model"), env=eval_env)

    reset_output = eval_env.reset()
    obs = reset_output[0] if isinstance(reset_output, tuple) else reset_output
    print(f"{'Time':<6} | {'Action':<8} | {'Dmg':<6}")

    for _ in range(25):
        action_masks = eval_env.env_method("action_masks")[0]
        action, _ = best_model.predict(obs, action_masks=action_masks, deterministic=True)
        obs, rewards, dones, infos = eval_env.step(action)
        if dones[0]:
            break

        dmg = infos[0].get("damage", 0)
        if dmg > 0:
            print(f"{'Tick':<6} | {'HIT':<8} | {dmg:.2f}")


if __name__ == "__main__":
    run_training()
