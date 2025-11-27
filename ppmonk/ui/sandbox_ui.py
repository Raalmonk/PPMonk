import customtkinter as ctk
import datetime
import tkinter as tk
from ppmonk.core.player import PlayerState
from ppmonk.core.spell_book import SpellBook

class SandboxWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Manual Sandbox")
        self.geometry("1400x800")

        self.player = None
        self.spell_book = None
        self.time_elapsed = 0.0

        # UI State
        self.force_proc_glory = tk.BooleanVar(value=False)
        self.force_proc_reset = tk.BooleanVar(value=False)

        # Timeline drawing config
        self.pixels_per_second = 50
        self.row_height = 40
        self.timeline_height = 300
        self.active_lane_y = 40
        self.passive_lane_y = 120
        self.canvas_width = 5000 # Expandable

        self._build_ui()
        self._reset_sandbox()

    def _build_ui(self):
        # --- Top Panel: Status & Settings ---
        top_panel = ctk.CTkFrame(self)
        top_panel.pack(fill="x", padx=10, pady=5)

        # Agility
        ctk.CTkLabel(top_panel, text="Agility:").pack(side="left", padx=5)
        self.agility_entry = ctk.CTkEntry(top_panel, width=80)
        self.agility_entry.insert(0, "2000")
        self.agility_entry.pack(side="left", padx=5)

        # Reset
        ctk.CTkButton(top_panel, text="Reset", command=self._reset_sandbox, fg_color="#C0392B", width=60).pack(side="left", padx=20)

        # Status Labels
        self.status_label_chi = ctk.CTkLabel(top_panel, text="Chi: 0", font=("Arial", 14, "bold"), text_color="#F1C40F")
        self.status_label_chi.pack(side="left", padx=15)

        self.status_label_energy = ctk.CTkLabel(top_panel, text="Energy: 0", font=("Arial", 14, "bold"), text_color="#F39C12")
        self.status_label_energy.pack(side="left", padx=15)

        self.status_label_xuen = ctk.CTkLabel(top_panel, text="Xuen: Inactive", font=("Arial", 12), text_color="gray")
        self.status_label_xuen.pack(side="left", padx=15)

        # Force Proc Toggles
        ctk.CTkCheckBox(top_panel, text="Force Glory", variable=self.force_proc_glory).pack(side="right", padx=10)
        ctk.CTkCheckBox(top_panel, text="Force Reset", variable=self.force_proc_reset).pack(side="right", padx=10)


        # --- Main Content ---
        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=10, pady=5)

        # --- Left Panel: Spells ---
        left_panel = ctk.CTkFrame(content, width=300)
        left_panel.pack(side="left", fill="y", padx=5, pady=5)

        ctk.CTkLabel(left_panel, text="Spells", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        self.spells_frame = ctk.CTkScrollableFrame(left_panel)
        self.spells_frame.pack(fill="both", expand=True)

        # --- Right Panel: Timeline ---
        right_panel = ctk.CTkFrame(content)
        right_panel.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(right_panel, text="Tactical Timeline", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)

        # Timeline Container (Canvas + Scrollbar)
        timeline_container = ctk.CTkFrame(right_panel)
        timeline_container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(timeline_container, bg="#2B2B2B", height=self.timeline_height, scrollregion=(0,0, self.canvas_width, self.timeline_height))

        hbar = tk.Scrollbar(timeline_container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.config(xscrollcommand=hbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._draw_timeline_grid()

    def _reset_sandbox(self):
        try:
            agility = float(self.agility_entry.get())
        except ValueError:
            agility = 2000.0
            self.agility_entry.delete(0, "end")
            self.agility_entry.insert(0, "2000")

        self.player = PlayerState(agility=agility)
        all_talents = ["1-1", "1-2", "1-3", "2-1", "2-2", "2-3", "WDP", "SW", "Ascension", "Teachings of the Monastery", "Glory of the Dawn"]
        self.spell_book = SpellBook(talents=all_talents)
        self.spell_book.apply_talents(self.player)

        self.time_elapsed = 0.0
        self.canvas.delete("all")
        self._draw_timeline_grid()
        self._update_status()
        self._refresh_spell_buttons()

    def _draw_timeline_grid(self):
        # Draw background lines for seconds
        for i in range(0, 100): # 100 seconds initially
            x = i * self.pixels_per_second
            color = "#404040" if i % 5 != 0 else "#606060"
            self.canvas.create_line(x, 0, x, self.timeline_height, fill=color)
            self.canvas.create_text(x + 2, self.timeline_height - 15, text=f"{i}s", anchor="w", fill="white", font=("Arial", 8))

        # Lane Labels
        self.canvas.create_text(5, self.active_lane_y - 20, text="Active Spells", anchor="w", fill="#3498DB", font=("Arial", 10, "bold"))
        self.canvas.create_text(5, self.passive_lane_y - 20, text="Passive / Auto Attacks", anchor="w", fill="#95A5A6", font=("Arial", 10, "bold"))

        # Current Time Indicator (Red Line)
        self.time_indicator = self.canvas.create_line(0, 0, 0, self.timeline_height, fill="red", width=2)

    def _update_status(self):
        self.status_label_chi.configure(text=f"Chi: {self.player.chi}")
        self.status_label_energy.configure(text=f"Energy: {int(self.player.energy)}")

        if self.player.xuen_active:
            self.status_label_xuen.configure(text=f"Xuen: {self.player.xuen_duration:.1f}s", text_color="#3498DB")
        else:
            self.status_label_xuen.configure(text="Xuen: Inactive", text_color="gray")

        # Update button states (CD / Resource)
        for child in self.spells_frame.winfo_children():
            if hasattr(child, "spell_key"):
                self._update_button_visual(child)

        # Move Red Line
        x = self.time_elapsed * self.pixels_per_second
        self.canvas.coords(self.time_indicator, x, 0, x, self.timeline_height)

        # Auto scroll if near edge
        # visible_width = self.canvas.winfo_width()
        # current_scroll = self.canvas.canvasx(0)
        # if x > current_scroll + visible_width * 0.8:
        #     self.canvas.xview_moveto(x / self.canvas_width)

    def _update_button_visual(self, btn):
        key = btn.spell_key
        spell = self.spell_book.spells[key]

        is_usable = spell.is_usable(self.player, self.spell_book.spells)

        if spell.current_cd > 0:
            btn.configure(text=f"{spell.name} ({spell.current_cd:.1f}s)", fg_color="#555555", state="disabled") # Gray out on CD
        elif not is_usable:
             btn.configure(text=f"{spell.name}", fg_color="#922B21", state="normal") # Red warning if unusable (resource)
             # Note: We keep it clickable to show "Rejection" message if we want, or just visual cue.
             # Prompt says: "If CD not ready or resource insufficient, button should be gray or show red border."
             # CTkButton border is tricky, changing fg_color is easier.
        else:
            btn.configure(text=f"{spell.name}", fg_color="#2E86C1", state="normal")


    def _refresh_spell_buttons(self):
        for widget in self.spells_frame.winfo_children():
            widget.destroy()

        # Define spells
        spell_keys = [
            "TP", "BOK", "RSK", "FOF", "WDP", "SCK", "SOTWL", "SW", "Xuen", "Zenith"
        ]

        for key in spell_keys:
            if key not in self.spell_book.spells: continue

            spell = self.spell_book.spells[key]
            btn = ctk.CTkButton(
                self.spells_frame,
                text=spell.name,
                command=lambda k=key: self._handle_cast_click(k)
            )
            btn.spell_key = key # Tag for updates
            btn.pack(pady=4, padx=5, fill="x")

        # Wait Button
        ctk.CTkButton(self.spells_frame, text="Wait (0.5s)", fg_color="gray",
                      command=lambda: self._advance_simulation(0.5)).pack(pady=20, padx=5, fill="x")

    def _handle_cast_click(self, key):
        spell = self.spell_book.spells[key]

        # 1. Rejection Logic
        if not spell.is_usable(self.player, self.spell_book.spells):
            self._show_rejection_popup(key)
            return

        # 2. Cast
        force_glory = self.force_proc_glory.get()
        force_reset = self.force_proc_reset.get()

        # Determine step duration (Cast Time or GCD)
        cast_time = spell.get_effective_cast_time(self.player)
        gcd = 1.5 / (1.0 + self.player.haste)
        if spell.gcd_override is not None:
            gcd = spell.gcd_override

        # Lock in timestamp for this action
        action_start_time = self.time_elapsed

        dmg, breakdown = spell.cast(self.player, other_spells=self.spell_book.spells,
                                    force_proc_glory=force_glory, force_proc_reset=force_reset)

        # 3. Draw Active Block
        step_duration = max(cast_time, gcd) if cast_time > 0 else gcd
        if step_duration < 0.1: step_duration = 0.1

        # Color coding
        color = "#1ABC9C" # Default Teal
        if key == "RSK": color = "#E74C3C"
        elif key == "FOF": color = "#8E44AD"
        elif key == "TP": color = "#27AE60"

        self._draw_block(
            lane_y=self.active_lane_y,
            start_time=action_start_time,
            duration=step_duration,
            text=key,
            color=color,
            info={"Damage": dmg, "Breakdown": breakdown}
        )

        # 4. Advance Time & Handle Passive Events
        self._advance_simulation(step_duration)

    def _advance_simulation(self, duration):
        # We need to process events in small chunks or get them with offsets from player.advance_time
        # In this refactor, player.advance_time returns events with 'offset'.

        # Current logic in player.advance_time loops with 0.01s steps.
        # It returns list of events with offset.

        base_time = self.time_elapsed
        dmg, events = self.player.advance_time(duration)
        self.spell_book.tick(duration)
        self.time_elapsed += duration # Exact increment

        # Process Passive Events
        for event in events:
            # event keys: Action, source, offset, Expected DMG, Breakdown
            if event.get('source') == 'passive':
                evt_time = base_time + event.get('offset', 0.0)
                name = event.get('Action')

                # Draw small marker for passive
                self._draw_block(
                    lane_y=self.passive_lane_y + (0 if "Auto" in name else 25), # Stagger slightly
                    start_time=evt_time,
                    duration=0.1, # Small blip
                    text=name[0:2], # AA or DT
                    color="#95A5A6",
                    info={"Damage": event.get('Expected DMG'), "Breakdown": event.get('Breakdown')}
                )
            elif event.get('source') == 'active':
                # Channel ticks
                evt_time = base_time + event.get('offset', 0.0)
                self._draw_block(
                    lane_y=self.active_lane_y + 40, # Below main cast
                    start_time=evt_time,
                    duration=0.1,
                    text="Tick",
                    color="#D35400",
                    info={"Damage": event.get('Expected DMG'), "Breakdown": event.get('Breakdown')}
                )

        self._update_status()

    def _draw_block(self, lane_y, start_time, duration, text, color, info):
        x1 = start_time * self.pixels_per_second
        x2 = (start_time + duration) * self.pixels_per_second
        y1 = lane_y
        y2 = lane_y + 30

        tag = f"block_{int(start_time*100)}_{random_id()}"

        rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black", tags=tag)
        lbl = self.canvas.create_text((x1+x2)/2, (y1+y2)/2, text=text, fill="white", font=("Arial", 9, "bold"), tags=tag)

        # Bind Click
        self.canvas.tag_bind(tag, "<Button-1>", lambda e, i=info, n=text: self._show_tooltip(e, n, i))

    def _show_rejection_popup(self, spell_key):
        top = ctk.CTkToplevel(self)
        top.title("Rejection")
        top.geometry("300x150")

        ctk.CTkLabel(top, text=f"Cannot Cast {spell_key}", font=("Arial", 16, "bold"), text_color="#C0392B").pack(pady=20)
        ctk.CTkLabel(top, text="Cooldown not ready or insufficient resources.", font=("Arial", 12)).pack(pady=5)
        ctk.CTkButton(top, text="OK", command=top.destroy).pack(pady=10)

    def _show_tooltip(self, event, name, info):
        # Simple popup using a Toplevel
        top = ctk.CTkToplevel(self)
        top.title(f"Details: {name}")
        top.geometry("400x300")

        ctk.CTkLabel(top, text=f"Action: {name}", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkLabel(top, text=f"Damage: {int(info['Damage'])}", font=("Arial", 14, "bold"), text_color="#E67E22").pack(pady=5)

        breakdown = info['Breakdown']
        text_info = ""

        if isinstance(breakdown, dict):
            # Render structured dict
            text_info += f"Base: {breakdown.get('base')}\n"
            text_info += "Modifiers:\n"
            for k, v in breakdown.get('modifiers', {}).items():
                text_info += f"  - {k}: x{v:.2f}\n"

            if breakdown.get('flags'):
                text_info += f"Flags: {', '.join(breakdown['flags'])}\n"

            text_info += f"Crit Chance: {breakdown.get('crit_chance', 0)*100:.1f}%\n"
            text_info += f"Crit Mult: {breakdown.get('crit_mult', 2.0):.2f}x\n"

            if 'extra_events' in breakdown:
                text_info += "\nExtra Events:\n"
                for extra in breakdown['extra_events']:
                    text_info += f"  - {extra['name']}: {int(extra['damage'])} (Crit: {extra.get('crit')})\n"
        else:
            text_info = str(breakdown)

        textbox = ctk.CTkTextbox(top, width=350, height=200)
        textbox.pack(pady=10)
        textbox.insert("1.0", text_info)
        textbox.configure(state="disabled")

def random_id():
    import random
    return random.randint(0, 1000000)
