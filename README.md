# PPMonk

## Training the agent

Use `train_best.py` for a production-ready Stable-Baselines3 training loop with action masking, periodic evaluation, and automatic best-model checkpointing.

```
python train_best.py
```

The script will write TensorBoard logs to `./logs/` and persist checkpoints and the best-performing model to `./models/`.
