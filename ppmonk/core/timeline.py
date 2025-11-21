# ppmonk/core/timeline.py
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
        
        # 用于 Scenario 2 的随机状态
        self.is_random_downtime_active = False

    def reset(self):
        # 在每次重置环境时，决定 Scenario 2 的随机结果
        if self.scenario_id == 2:
            # 20% 概率触发停手
            self.is_random_downtime_active = np.random.rand() < 0.2
        else:
            self.is_random_downtime_active = False

    def get_status(self, current_time):
        """
        返回: (is_uptime, damage_modifier, is_done)
        """
        is_uptime = True
        dmg_mod = 1.0
        is_done = False

        # --- 结束判定 ---
        if current_time >= self.duration:
            is_done = True
            return is_uptime, dmg_mod, is_done

        # --- 场景逻辑 ---
        
        # 场景 1: 固定停手 (8-12s)
        if self.scenario_id == 1:
            if 8.0 <= current_time < 12.0:
                is_uptime = False

        # 场景 2: 随机停手 (8-12s)
        elif self.scenario_id == 2:
            if 8.0 <= current_time < 12.0:
                if self.is_random_downtime_active:
                    is_uptime = False

        # 场景 3: 斩杀期/易伤 (最后4s, 16-20s)
        elif self.scenario_id == 3:
            if current_time >= 16.0:
                dmg_mod = 3.0 # +200% = 300% total

        return is_uptime, dmg_mod, is_done