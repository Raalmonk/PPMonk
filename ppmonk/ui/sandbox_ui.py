import customtkinter as ctk
import tkinter as tk
from datetime import datetime

from ppmonk.core.player import PlayerState
from ppmonk.core.spell_book import SpellBook, Spell
from ppmonk.core.talents import TalentManager, TALENT_DB
from ppmonk.ui.timeline_view import NativeTimelineWindow

class SandboxWindow(ctk.CTkToplevel):
    def __init__(self, parent, active_talents=None, player_stats=None):
        super().__init__(parent)
        self.title("Manual Sandbox Simulator")
        self.geometry("1600x900")

        # [Task 2: Attribute Inheritance]
        # Initialize Player State with inherited stats
        self.player_stats = player_stats or {}
        self.player = PlayerState(
            crit=self.player_stats.get('crit', 0.20),
            haste=self.player_stats.get('haste', 0.10),
            mastery=self.player_stats.get('mastery', 0.15),
            vers=self.player_stats.get('vers', 0.05),
            max_health=100000
        )

        # Manually set AP if passed, otherwise PlayerState calculates it
        if 'attack_power' in self.player_stats:
             self.player.attack_power = self.player_stats['attack_power']

        self.active_talents = active_talents or []
        self.spellbook = SpellBook(active_talents=self.active_talents)
        self.spellbook.apply_talents(self.player)

        # UI Components
        self._init_ui()

        self.simulation_log = []
        self.start_time = 0.0
        self.current_time = 0.0

    def _init_ui(self):
        # Layout: Left (Controls/Spells), Right (Log/Timeline)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left Panel
        left_panel = ctk.CTkFrame(self, width=300)
        left_panel.grid(row=0, column=0, sticky="nswe", padx=10, pady=10)

        # Stats Display
        stats_frame = ctk.CTkFrame(left_panel)
        stats_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(stats_frame, text="Player Stats", font=("Arial", 16, "bold")).pack()
        self.stats_label = ctk.CTkLabel(stats_frame, text=self._get_stats_text(), justify="left")
        self.stats_label.pack(padx=5, pady=5)

        # Spell Buttons
        spells_frame = ctk.CTkScrollableFrame(left_panel, label_text="Spells")
        spells_frame.pack(fill="both", expand=True, pady=5)

        # Use Standard Spells from SpellBook
        for spell_name in self.spellbook.spells.keys():
            btn = ctk.CTkButton(spells_frame, text=spell_name, command=lambda s=spell_name: self._cast_spell(s))
            btn.pack(fill="x", pady=2)

        # Control Buttons
        controls_frame = ctk.CTkFrame(left_panel)
        controls_frame.pack(fill="x", pady=5)
        ctk.CTkButton(controls_frame, text="Show Timeline", command=self._show_timeline).pack(pady=5)
        ctk.CTkButton(controls_frame, text="Clear Log", command=self._clear_log).pack(pady=5)

        # Right Panel (Log)
        right_panel = ctk.CTkFrame(self)
        right_panel.grid(row=0, column=1, sticky="nswe", padx=10, pady=10)

        self.log_text = ctk.CTkTextbox(right_panel, font=("Consolas", 12))
        self.log_text.pack(fill="both", expand=True)

    def _get_stats_text(self):
        return (f"Crit: {self.player.crit:.1%}\n"
                f"Haste: {self.player.haste:.1%}\n"
                f"Mastery: {self.player.mastery:.1%}\n"
                f"Vers: {self.player.versatility:.1%}\n"
                f"AP: {self.player.attack_power:.0f}")

    def _cast_spell(self, spell_name):
        # Use Expected Value for Sandbox usually, or stochastic?
        # Task 2 says "breakdown structure for logs".

        dmg, breakdown = self.spellbook.cast(spell_name, use_expected_value=False)

        if isinstance(breakdown, dict) and "error" in breakdown:
            self._log(f"Failed to cast {spell_name}: {breakdown['error']}")
            return

        # Advance Time (Mockup)
        # Real logic would handle GCD, etc.
        self.current_time += 1.5

        # Record Log
        entry = {
            "name": spell_name,
            "start": self.current_time - 1.5,
            "duration": 1.5, # GCD
            "damage": dmg,
            "breakdown": breakdown,
            "group_idx": 0 # For timeline
        }
        self.simulation_log.append(entry)

        # [Task 2: Log Format]
        self._log_breakdown(entry)

    def _log_breakdown(self, entry):
        # Format the new breakdown structure nicely
        bd = entry['breakdown']

        header = f"[{entry['start']:.2f}s] Cast {entry['name']} -> {entry['damage']:.0f} Dmg"
        details = []

        if "base" in bd:
             details.append(f"  Base: {bd['base']}")
        if "modifiers" in bd and bd['modifiers']:
             mods = ", ".join(bd['modifiers'])
             details.append(f"  Mods: {mods}")
        if "final_crit" in bd:
             details.append(f"  CritChance: {bd['final_crit']:.2%} (Mult: {bd.get('crit_mult', 2.0)})")
        if "total_dmg_after_aoe" in bd:
             details.append(f"  Total: {bd['total_dmg_after_aoe']:.1f}")

        full_msg = header + "\n" + "\n".join(details) + "\n" + "-"*40
        self._log(full_msg)

    def _log(self, message):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def _clear_log(self):
        self.log_text.delete("1.0", "end")
        self.simulation_log = []
        self.current_time = 0.0

    def _show_timeline(self):
        # Format data for timeline view
        timeline_data = {
            "groups": ["Actions"],
            "items": self.simulation_log
        }
        NativeTimelineWindow(self, timeline_data)
