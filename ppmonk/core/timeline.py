"""Timeline utilities extracted from the original run_monk_ai script."""

import numpy as np


class Timeline:
    def __init__(self, scenario_id):
        """
        0: 20s Patchwerk (纯木桩)
        1: Fixed Downtime (8s打 - 4s停 - 8s打)
        2: Probabilistic Downtime (中间4s有20%概率停手，否则继续打)
        3: Execute Phase (最后4s 伤害提高200% -> 3.0x)
        """
        self.scenario_id = scenario_id
        self.duration = 20.0
        self.burst_start = -1.0
        if scenario_id == 3:
            self.burst_start = 16.0

        self.global_map = np.zeros(20, dtype=np.float32)
        for i in range(20):
            t = float(i)
            mod = 1.0
            if scenario_id == 3 and t >= self.burst_start:
                mod = 3.0
            self.global_map[i] = mod / 3.0

        self.is_random_downtime_active = False

    def reset(self):
        if self.scenario_id == 2:
            self.is_random_downtime_active = np.random.rand() < 0.2
        else:
            self.is_random_downtime_active = False

    def get_status(self, current_time):
        """返回: (is_uptime, damage_modifier, is_done)"""
        is_uptime = True
        dmg_mod = 1.0
        is_done = current_time >= self.duration

        if is_done:
            return is_uptime, dmg_mod, is_done

        if self.scenario_id == 1 and 8.0 <= current_time < 12.0:
            is_uptime = False
        elif self.scenario_id == 2 and 8.0 <= current_time < 12.0:
            if self.is_random_downtime_active:
                is_uptime = False
        elif self.scenario_id == 3 and current_time >= 16.0:
            dmg_mod = 3.0

        return is_uptime, dmg_mod, is_done
