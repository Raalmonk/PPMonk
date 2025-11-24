import torch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.vec_env import SubprocVecEnv

from ppmonk.envs.monk_env import MonkEnv


SCENARIO_MAP = {
    "Patchwerk": 0,
    "Execute (End +200%)": 3,
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
    total_timesteps=1_000_000,
):
    if talents is None:
        talents = ['WDP', 'SW', 'Ascension']

    def log(msg):
        log_callback(str(msg))

    def notify(status_text, progress=None):
        if status_callback:
            status_callback(status_text, progress)

    scen_id = SCENARIO_MAP.get(scenario_name, 0)
    notify("Initializing...", 0.0)

    player_kwargs = {
        "rating_haste": haste_rating,
        "rating_crit": crit_rating,
        "rating_mastery": mastery_rating,
        "rating_vers": vers_rating,
    }

    log(">>> 初始化 PPMonk (UI Mode)...")
    log(f">>> 属性: Haste={haste_rating}, Crit={crit_rating}, Mast={mastery_rating}, Vers={vers_rating}")
    log(f">>> 天赋: {talents}")
    log(f">>> 场景: {scenario_name} (Timeline {scen_id})")

    num_cpu = 16
    env = SubprocVecEnv([make_env(i, talents, player_kwargs) for i in range(num_cpu)])

    device = "cuda" if torch.cuda.is_available() else "cpu"
    log(f">>> Using device: {device}")

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

    log(f">>> 开始训练 (Steps: {total_timesteps:,})...")
    notify("Training...", 0.1)
    model.learn(total_timesteps=total_timesteps)

    log("\n>>> 训练完成，开始评估...")
    notify("Evaluating...", 0.7)

    eval_env = MonkEnv(current_talents=talents, player_kwargs=player_kwargs)
    eval_env.training_mode = False
    eval_env = ActionMasker(eval_env, mask_fn)

    log(f"\n{'=' * 30}\nTesting Scenario: {scenario_name}\n{'=' * 30}")
    obs, _ = eval_env.reset(options={'timeline': scen_id})
    log(f"{'Time':<6} | {'Action':<8} | {'Chi':<3} | {'Eng':<4} | {'AP%':<6}")

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
            log(f"{t_now:<6.1f} | {act_name:<8} | {int(chi):<3} | {int(en):<4} | {dmg:<6.2f}")
        elif dmg > 0:
            log(f"{t_now:<6.1f} | {'(Tick)':<8} | {int(chi):<3} | {int(en):<4} | {dmg:<6.2f}")

    log(f"{'-' * 30}")
    log(f"Total AP Output: {total_ap:.2f}")

    p = eval_env.unwrapped.player
    log(f"\n{'=' * 40}")
    log("FINAL CHARACTER STATS:")
    log(f"  Talents: {eval_env.unwrapped.book.active_talents}")
    log(f"  Energy : {p.max_energy} (Regen: {10.0*(1.0+p.haste)*p.energy_regen_mult:.2f}/s)")
    log(f"  Haste  : {p.haste * 100:.2f}%")
    log(f"  Crit   : {p.crit * 100:.2f}%")
    log(f"  Mast   : {p.mastery * 100:.2f}%")
    log(f"  Vers   : {p.versatility * 100:.2f}%")
    log(f"{'=' * 40}\n")

    notify("Complete", 1.0)
    return {"scenario": scenario_name, "total_ap": total_ap}


def run():
    return run_simulation()


if __name__ == '__main__':
    run()