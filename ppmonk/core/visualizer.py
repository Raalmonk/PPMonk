class TimelineDataCollector:
    """Collects structured timeline data for downstream visualization."""

    def __init__(self):
        self.items = []
        self.groups = [
            "Major Cooldowns",
            "Minor Cooldowns",
            "Major Filler",
            "Minor Filler",
        ]
        self.spell_config = {
            'FOF': {'group': 0, 'color': '#e74c3c'},
            'SOTWL': {'group': 0, 'color': '#c0392b'},
            'WDP': {'group': 0, 'color': '#d35400'},
            'SEF': {'group': 0, 'color': '#2ecc71'},
            'Xuen': {'group': 0, 'color': '#27ae60'},
            'RSK': {'group': 1, 'color': '#f39c12'},
            'SCK': {'group': 2, 'color': '#3498db'},
            'CJL': {'group': 2, 'color': '#2980b9'},
            'TP': {'group': 3, 'color': '#95a5a6'},
            'BOK': {'group': 3, 'color': '#7f8c8d'},
            'EH': {'group': 3, 'color': '#bdc3c7'},
        }

    def log_cast(self, time, spell_abbr, duration=0.0, damage=0):
        cfg = self.spell_config.get(spell_abbr, {'group': 3, 'color': '#555555'})
        self.items.append({
            "name": spell_abbr,
            "start": time,
            "duration": max(duration, 1.0),
            "group_idx": cfg['group'],
            "color": cfg['color'],
            "damage": damage,
        })

    def get_data(self):
        return {
            "groups": self.groups,
            "items": self.items,
        }
