import torch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.vec_env import SubprocVecEnv

from ppmonk.core.callbacks import TrainingControlCallback
from ppmonk.core.visualizer import TimelineDataCollector
from ppmonk.envs.monk_env import MonkEnv

SCENARIO_MAP = {
    "Patchwerk": 0,
    "Execute (End +200%)": 3
}


def mask_fn(env):
    return env.action_masks()


def make_env(rank, current_talents, player_kwargs):
    def _init():
        env = MonkEnv(seed_offset=rank, current_talents=current_talents, player_kwargs=player_kwargs)
        env = ActionMasker(env, mask_fn)
        return env

    return _init


def run_simulation(
        haste_rating=1500,
        crit_rating=2000,
        mastery_rating=1000,
        vers_rating=500,
        talents=None,
        scenario_name="Patchwerk",
        log_callback=print,
        status_callback=None,
        stop_event=None,
):
    if talents is None: talents = ['WDP', 'SW', 'Ascension', 'Zenith']

    def log(msg):
        if log_callback: log_callback(str(msg))

    player_kwargs = {
        'rating_haste': float(haste_rating),
        'rating_crit': float(crit_rating),
        'rating_mastery': float(mastery_rating),
        'rating_vers': float(vers_rating)
    }

    log(f">>> 初始化 PPMonk (UI 模式)...")
    log(f"  天赋: {talents}")
    log(f"  属性: {player_kwargs}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"Device Name: {torch.cuda.get_device_name(0)}")
    else:
        print("WARNING: Running on CPU! This will be slow.")

    num_cpu = 8
    env = SubprocVecEnv([make_env(i, talents, player_kwargs) for i in range(num_cpu)])

    device = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"  设备: {device}")

    if status_callback: status_callback("Training AI Model...", 0.1)

    model = MaskablePPO(
        "MlpPolicy",
        env,
        verbose=0,
        device=device,
        gamma=1.0,
        learning_rate=3e-4,
        ent_coef=0.02,
        n_steps=512,
        batch_size=1024,
    )

    total_steps = 50000
    log(f">>> 开始训练 ({total_steps} steps)...")

    callback = TrainingControlCallback(
        total_timesteps=total_steps,
        status_callback=status_callback,
        stop_event=stop_event,
    )

    model.learn(total_timesteps=total_steps, callback=callback)

    if stop_event and stop_event.is_set():
        log(">>> 训练已终止 (用户操作)")
        if status_callback:
            status_callback("Training Stopped", 0)
        return {"total_ap": 0, "scenario": scenario_name, "status": "stopped"}

    if status_callback: status_callback("Evaluating Strategy...", 0.8)

    log("\n>>> 训练完成，开始评估...")
    if status_callback: status_callback("Generating Timeline...", 0.95)

    eval_env = MonkEnv(current_talents=talents, player_kwargs=player_kwargs)
    eval_env.training_mode = False
    eval_env = ActionMasker(eval_env, mask_fn)

    target_scenario = SCENARIO_MAP.get(scenario_name, 0)

    log(f"\n{'=' * 30}")
    log(f"Testing Scenario: {scenario_name}")
    log(f"{'=' * 30}")

    obs, _ = eval_env.reset(options={'timeline': target_scenario})
    log(f"{'Time':<6} | {'Action':<8} | {'Chi':<3} | {'Eng':<4} | {'AP%':<6}")

    total_ap = 0.0
    done = False
    collector = TimelineDataCollector()

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

        duration = max(eval_env.unwrapped.time - t_now, 0.0)

        if action_item != 0:
            log(f"{t_now:<6.1f} | {act_name:<8} | {int(chi):<3} | {int(en):<4} | {dmg:<6.2f}")
            collector.log_cast(t_now, act_name, duration=duration, damage=dmg)
        elif dmg > 0:
            log(f"{t_now:<6.1f} | {'(Tick)':<8} | {int(chi):<3} | {int(en):<4} | {dmg:<6.2f}")

    log(f"{'-' * 30}")
    log(f"Total AP Output: {total_ap:.2f}")

    # Damage Breakdown
    damage_meter = eval_env.unwrapped.damage_meter
    sorted_damage = sorted(damage_meter.items(), key=lambda item: item[1], reverse=True)
    total_damage_from_meter = sum(damage_meter.values())

    log("\n=== Damage Breakdown ===")
    for i, (spell, damage) in enumerate(sorted_damage):
        percentage = (damage / total_damage_from_meter) * 100 if total_damage_from_meter > 0 else 0
        log(f"{i+1}. {spell:<18}: {damage:>8.0f} ({percentage:.1f}%)")
    log(f"Total                 : {total_damage_from_meter:>8.0f}")
    log("========================")

    p = eval_env.unwrapped.player
    log(f"\n{'=' * 40}")
    log("FINAL CHARACTER STATS:")
    log(f"  Talents: {eval_env.unwrapped.book.active_talents}")
    log(f"  Energy : {p.max_energy} (Regen: {10.0 * (1.0 + p.haste) * p.energy_regen_mult:.2f}/s)")
    log(f"  Haste  : {p.haste * 100:.2f}%")
    log(f"  Crit   : {p.crit * 100:.2f}%")
    log(f"  Mast   : {p.mastery * 100:.2f}%")
    log(f"  Vers   : {p.versatility * 100:.2f}%")
    log(f"{'=' * 40}\n")

    if status_callback: status_callback("Complete", 1.0)

    return {
        "total_ap": total_ap,
        "scenario": scenario_name,
        "timeline_data": collector.get_data(),
    }

if __name__ == '__main__':
    run_simulation()