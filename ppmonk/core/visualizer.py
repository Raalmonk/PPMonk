class TimelineDataCollector:
    """Collects structured timeline data for downstream visualization."""

    def __init__(self):
        self.items = []
        # Task 1: 5 Groups with Chinese labels
        self.groups = [
            "爆发技能 (Major CD)",   # Index 0
            "短CD技能 (Minor CD)",   # Index 1
            "主要填充 (Major Filler)", # Index 2
            "次要填充 (Minor Filler)", # Index 3
            "被动/触发 (Triggers)"    # Index 4
        ]

        self.spell_config = {
            # Group 0: Major CD
            'Xuen': {'group': 0, 'color': '#27ae60'},
            'SEF': {'group': 0, 'color': '#2ecc71'},
            'ToD': {'group': 0, 'color': '#c0392b'},
            'Conduit': {'group': 0, 'color': '#f1c40f'},

            # Group 1: Minor CD
            'RSK': {'group': 1, 'color': '#f39c12'},
            'WDP': {'group': 1, 'color': '#d35400'},
            'SOTWL': {'group': 1, 'color': '#c0392b'},
            'SW': {'group': 1, 'color': '#16a085'},
            'Zenith': {'group': 1, 'color': '#8e44ad'},

            # Group 2: Major Filler
            'FOF': {'group': 2, 'color': '#e74c3c'},
            'SCK': {'group': 2, 'color': '#3498db'},

            # Group 3: Minor Filler
            'TP': {'group': 3, 'color': '#95a5a6'},
            'BOK': {'group': 3, 'color': '#7f8c8d'},
            'CJL': {'group': 3, 'color': '#2980b9'},

            # Group 4: Triggers
            'EH': {'group': 4, 'color': '#bdc3c7'},
            'Expel Harm': {'group': 4, 'color': '#bdc3c7'},
            'JadeIgnition': {'group': 4, 'color': '#2ecc71'},
            'NiuzaoStomp': {'group': 4, 'color': '#f39c12'},
            'ZenithBlast': {'group': 4, 'color': '#9b59b6'},
            'GloryOfDawn': {'group': 4, 'color': '#f1c40f'},
            'FlurryStrikes': {'group': 4, 'color': '#e74c3c'},
            'Flurry Burst (FOF)': {'group': 4, 'color': '#e74c3c'},
            'Shado Over Battlefield': {'group': 4, 'color': '#c0392b'},
            'High Impact': {'group': 4, 'color': '#d35400'},
            'Wisdom of Wall': {'group': 4, 'color': '#e67e22'},
            'AA': {'group': 4, 'color': '#95a5a6'},
            'Auto Attack': {'group': 4, 'color': '#95a5a6'},
        }

    def log_cast(self, time, spell_abbr, duration=0.0, damage=0, info=None):
        # Default to group 4 (Triggers) if unknown or not mapped
        cfg = self.spell_config.get(spell_abbr, {'group': 4, 'color': '#555555'})

        # Heuristic for unmapped Shado-Pan events
        if "Flurry" in spell_abbr or "Shado" in spell_abbr:
             cfg = {'group': 4, 'color': '#e74c3c'}

        # Special handling for Zenith visual duration
        vis_duration = duration
        if spell_abbr == 'Zenith':
             vis_duration = 0.5
        # Ensure minimum visibility for instant events (0.5s)
        elif vis_duration < 0.5:
             vis_duration = 0.5

        self.items.append({
            "name": spell_abbr,
            "start": time,
            "duration": vis_duration,
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
