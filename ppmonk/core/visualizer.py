class TimelineDataCollector:
    """Collects structured timeline data for downstream visualization."""

    def __init__(self):
        self.items = []
        # Task 6: 6 Groups (including AA and Shado-Pan)
        self.groups = [
            "主要技能 (Major)",
            "次要技能 (Minor)",
            "主要填充 (Filler)",
            "次要填充 (Filler)",
            "触发/被动/平A (Triggers/AA)",
            "影踪派 (Shado-Pan)"
        ]

        self.spell_config = {
            # Group 0: Major Cooldowns
            'Xuen': {'group': 0, 'color': '#27ae60'},
            'SEF': {'group': 0, 'color': '#2ecc71'},
            'Zenith': {'group': 0, 'color': '#8e44ad'},
            'Conduit': {'group': 0, 'color': '#f1c40f'},
            'ToD': {'group': 0, 'color': '#c0392b'},

            # Group 1: Minor Cooldowns
            'SOTWL': {'group': 1, 'color': '#c0392b'},
            'WDP': {'group': 1, 'color': '#d35400'},
            'SW': {'group': 1, 'color': '#16a085'},

            # Group 2: Major Filler
            'FOF': {'group': 2, 'color': '#e74c3c'},
            'RSK': {'group': 2, 'color': '#f39c12'},

            # Group 3: Minor Filler
            'SCK': {'group': 3, 'color': '#3498db'},
            'TP': {'group': 3, 'color': '#95a5a6'},
            'BOK': {'group': 3, 'color': '#7f8c8d'},
            'CJL': {'group': 3, 'color': '#2980b9'},

            # Group 4: Triggers/Passives/AA
            'EH': {'group': 4, 'color': '#bdc3c7'},
            'JadeIgnition': {'group': 4, 'color': '#2ecc71'},
            'NiuzaoStomp': {'group': 4, 'color': '#f39c12'},
            'ZenithBlast': {'group': 4, 'color': '#9b59b6'},
            'Expel Harm': {'group': 4, 'color': '#bdc3c7'},
            'AA': {'group': 4, 'color': '#95a5a6'},
            'Auto Attack': {'group': 4, 'color': '#95a5a6'},

            # Group 5: Shado-Pan
            'Flurry Strikes': {'group': 5, 'color': '#e74c3c'},
            'Shado Over Battlefield': {'group': 5, 'color': '#c0392b'},
            'High Impact': {'group': 5, 'color': '#d35400'},
            'Flurry Burst (FOF)': {'group': 5, 'color': '#e74c3c'},
            'Wisdom of Wall': {'group': 5, 'color': '#e67e22'},
        }

    def log_cast(self, time, spell_abbr, duration=0.0, damage=0, info=None):
        # Default to group 4 (Triggers) if unknown or not mapped
        cfg = self.spell_config.get(spell_abbr, {'group': 4, 'color': '#555555'})

        # Heuristic for unmapped Shado-Pan events
        if "Flurry" in spell_abbr or "Shado" in spell_abbr:
             cfg = {'group': 5, 'color': '#e74c3c'}

        self.items.append({
            "name": spell_abbr,
            "start": time,
            "duration": max(duration, 0.5), # 0.5s min duration for visibility of instant events
            "group_idx": cfg['group'],
            "color": cfg['color'],
            "damage": damage,
            "info": info
        })

    def get_data(self):
        return {
            "groups": self.groups,
            "items": self.items,
        }
