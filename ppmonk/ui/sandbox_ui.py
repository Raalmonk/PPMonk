import customtkinter as ctk
import datetime
from ppmonk.core.player import PlayerState
from ppmonk.core.spell_book import SpellBook

class SandboxWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Manual Sandbox")
        self.geometry("1100x700")

        self.player = None
        self.spell_book = None
        self.combat_log = []
        self.time_elapsed = 0.0

        self._build_ui()
        self._reset_sandbox()

    def _build_ui(self):
        # Top Panel: Agility and Reset
        top_panel = ctk.CTkFrame(self)
        top_panel.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(top_panel, text="Agility:").pack(side="left", padx=5)
        self.agility_entry = ctk.CTkEntry(top_panel, width=80)
        self.agility_entry.insert(0, "2000")
        self.agility_entry.pack(side="left", padx=5)

        ctk.CTkButton(top_panel, text="Reset Sandbox", command=self._reset_sandbox, fg_color="#C0392B").pack(side="left", padx=20)

        # Main Content
        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=10, pady=5)

        # Left: Spell Icons
        left_panel = ctk.CTkFrame(content, width=400)
        left_panel.pack(side="left", fill="y", padx=5, pady=5)

        ctk.CTkLabel(left_panel, text="Spells", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        self.spells_frame = ctk.CTkScrollableFrame(left_panel)
        self.spells_frame.pack(fill="both", expand=True)

        # Right: Log
        right_panel = ctk.CTkFrame(content)
        right_panel.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(right_panel, text="Combat Log", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        self.log_textbox = ctk.CTkTextbox(right_panel, font=("Consolas", 12))
        self.log_textbox.pack(fill="both", expand=True)

    def _reset_sandbox(self):
        try:
            agility = float(self.agility_entry.get())
        except ValueError:
            agility = 2000.0
            self.agility_entry.delete(0, "end")
            self.agility_entry.insert(0, "2000")

        self.player = PlayerState(agility=agility)
        # Enable all talents for sandbox to allow testing all spells
        all_talents = ["1-1", "1-2", "1-3", "2-1", "2-2", "2-3", "WDP", "SW", "Ascension", "Teachings of the Monastery", "Glory of the Dawn"]
        # Note: Actual talent IDs might differ, passing list of strings as common convention in this codebase
        self.spell_book = SpellBook(talents=all_talents)
        self.spell_book.apply_talents(self.player)

        self.time_elapsed = 0.0
        self.combat_log = []
        self.log_textbox.delete("1.0", "end")
        self._log_message(f"Sandbox Reset. Agility: {agility}")

        self._refresh_spell_buttons()

    def _refresh_spell_buttons(self):
        # Clear existing buttons
        for widget in self.spells_frame.winfo_children():
            widget.destroy()

        # Define spells and variants
        # (Label, SpellKey, ForceGlory, ForceReset)
        spell_defs = [
            ("Tiger Palm", "TP", False, False),
            ("Blackout Kick", "BOK", False, False),
            ("BOK (Force Reset)", "BOK", False, True),
            ("Rising Sun Kick", "RSK", False, False),
            ("RSK (Force Glory)", "RSK", True, False),
            ("Fists of Fury", "FOF", False, False),
            ("Whirling Dragon Punch", "WDP", False, False),
            ("Spinning Crane Kick", "SCK", False, False),
            ("Strike of the Windlord", "SOTWL", False, False),
            ("Shattering Star", "SW", False, False), # Abbr check
            ("Invoke Xuen", "Xuen", False, False),
            ("Zenith", "Zenith", False, False)
        ]

        for label, key, force_glory, force_reset in spell_defs:
            if key not in self.spell_book.spells:
                continue

            btn = ctk.CTkButton(
                self.spells_frame,
                text=label,
                command=lambda k=key, g=force_glory, r=force_reset: self._cast_spell(k, g, r)
            )
            btn.pack(pady=5, padx=10, fill="x")

        # Advance Time Button
        ctk.CTkButton(self.spells_frame, text="Wait (GCD)", command=lambda: self._advance_time(1.5), fg_color="gray").pack(pady=20, padx=10, fill="x")

    def _cast_spell(self, key, force_glory, force_reset):
        spell = self.spell_book.spells[key]

        # Advance time by GCD or cast time
        cast_time = spell.get_effective_cast_time(self.player)
        gcd = 1.5 / (1.0 + self.player.haste)
        if spell.gcd_override is not None:
            gcd = spell.gcd_override

        step_duration = max(cast_time, gcd) if cast_time > 0 else gcd
        if step_duration < 0.1: step_duration = 0.1 # Minimum step

        dmg, breakdown = spell.cast(self.player, other_spells=self.spell_book.spells,
                                    force_proc_glory=force_glory, force_proc_reset=force_reset)

        self._log_action(f"{key}{' (+Glory)' if force_glory else ''}{' (+Reset)' if force_reset else ''}",
                         dmg, breakdown)

        # Advance time
        self._advance_time(step_duration)

    def _advance_time(self, duration):
        dmg, entries = self.player.advance_time(duration)
        self.spell_book.tick(duration)
        self.time_elapsed += duration

        # Entries is now a list of dicts with 'Action', 'Expected DMG', and 'Breakdown'
        for entry in entries:
            name = entry.get("Action", "Unknown")
            d = entry.get("Expected DMG", 0.0)
            b = entry.get("Breakdown", "")
            self._log_action(name, d, b)

    def _log_action(self, action_name, damage, breakdown):
        # Format: [0.0s] RSK (+Glory) | Dmg: 15000 (Base:xx, Vers:xx...) | Chi: 3 | Eng: 100
        timestamp = f"[{self.time_elapsed:.1f}s]"
        state = f"Chi: {self.player.chi} | Eng: {int(self.player.energy)}"

        # breakdown is expected to be a string like "(Base: 8000, ...)"
        log_line = f"{timestamp} {action_name} | Dmg: {int(damage)} {breakdown} | {state}"
        self._log_message(log_line)

    def _log_message(self, msg):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", msg + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")
