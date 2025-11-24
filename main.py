import torch
import numpy as np
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.vec_env import SubprocVecEnv

from ppmonk.envs.monk_env import MonkEnv

def mask_fn(env):
    return env.action_masks()

def make_env(rank, current_talents):
    def _init():
        env = MonkEnv(seed_offset=rank, current_talents=current_talents)
        env = ActionMasker(env, mask_fn)
        return env
    return _init

def run():
    # 1. 配置天赋
    # 你可以在这里随意修改天赋组合
    current_talents = ['WDP', 'SW', 'Ascension']
    
    print(f">>> 初始化 PPMonk (Talents: {current_talents})...")

    # 2. 初始化并行训练环境
    num_cpu = 16
    env = SubprocVecEnv([make_env(i, current_talents) for i in range(num_cpu)])

    # 3. 配置模型
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f">>> Using device: {device}")
    
    model = MaskablePPO(
        "MlpPolicy",
        env,
        verbose=1,
        device=device,
        gamma=1.0,          # 纯数学逻辑，无时间折扣
        learning_rate=3e-4,
        ent_coef=0.02,      # 保持探索
        n_steps=512,
        batch_size=1024,
    )

    # 4. 开始训练
    print(">>> 开始训练 (Steps: 1,000,000)...")
    model.learn(total_timesteps=1000000)
    
    # ==========================================
    # 5. 评估阶段 (Evaluation Phase)
    # ==========================================
    print("\n>>> 训练完成，开始评估...")
    
    # 创建一个独立的单线程环境用于评估
    eval_env = MonkEnv(current_talents=current_talents)
    eval_env.training_mode = False # 关闭随机出生，固定从0秒开始
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

            # 获取执行前状态用于打印
            t_now = eval_env.unwrapped.time
            chi = eval_env.unwrapped.player.chi
            en = eval_env.unwrapped.player.energy

            # 执行动作
            obs, reward, done, _, info = eval_env.step(action_item)
            dmg = info['damage']
            total_ap += dmg
            
            act_name = eval_env.unwrapped.action_map[action_item]

            # 打印日志
            if action_item != 0:
                print(f"{t_now:<6.1f} | {act_name:<8} | {int(chi):<3} | {int(en):<4} | {dmg:<6.2f}")
            elif dmg > 0:
                print(f"{t_now:<6.1f} | {'(Tick)':<8} | {int(chi):<3} | {int(en):<4} | {dmg:<6.2f}")

        print(f"{'-' * 30}")
        print(f"Total AP Output: {total_ap:.2f}")

    # ==========================================
    # 6. 打印角色最终面板 (Character Stats)
    # ==========================================
    p = eval_env.unwrapped.player
    print(f"\n{'=' * 40}")
    print(f"FINAL CHARACTER STATS:")
    print(f"  Talents: {eval_env.unwrapped.book.active_talents}")
    print(f"  Energy : {p.max_energy} (Regen: {10.0*(1.0+p.haste)*p.energy_regen_mult:.2f}/s)")
    print(f"  Haste  : {p.haste * 100:.2f}%")
    print(f"  Crit   : {p.crit * 100:.2f}%")
    print(f"  Mast   : {p.mastery * 100:.2f}%")
    print(f"  Vers   : {p.versatility * 100:.2f}%")
    print(f"{'=' * 40}\n")

if __name__ == '__main__':
    run()