from stable_baselines3.common.callbacks import BaseCallback


class TrainingControlCallback(BaseCallback):
    """Callback to relay training progress and honor stop requests."""

    def __init__(self, total_timesteps, status_callback, stop_event, verbose=0):
        super().__init__(verbose)
        self.total_timesteps = total_timesteps
        self.status_callback = status_callback
        self.stop_event = stop_event

    def _on_step(self) -> bool:
        # 1. 检查是否收到停止信号
        if self.stop_event and self.stop_event.is_set():
            if self.status_callback:
                self.status_callback("Stopping training...", 0)
            return False  # 返回 False 会立即终止训练

        # 2. 汇报进度 (每 1000 步汇报一次，避免 UI 卡死)
        if self.n_calls % 1000 == 0:
            progress = self.num_timesteps / self.total_timesteps
            if self.status_callback:
                # 发送百分比 (0.0 - 1.0)
                self.status_callback(f"Training: {int(progress * 100)}%", progress)

        return True
