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

        # History for redrawing
        self.event_history = []

        # UI State
        self.force_proc_glory = tk.BooleanVar(value=False)
        self.force_proc_reset = tk.BooleanVar(value=False)
        self.target_hp_pct = tk.DoubleVar(value=1.0) # [Task 2]

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

        # [Task 2: Target HP]
        ctk.CTkLabel(top_panel, text="Target HP%:").pack(side="left", padx=5)
        self.hp_slider = ctk.CTkSlider(top_panel, from_=0.0, to=1.0, number_of_steps=100, variable=self.target_hp_pct, command=self._on_hp_change, width=150)
        self.hp_slider.pack(side="left", padx=5)
        self.hp_label = ctk.CTkLabel(top_panel, text="100%")
        self.hp_label.pack(side="left", padx=2)

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

        # Timeline Header (Zoom controls)
        tl_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        tl_header.pack(fill="x", pady=5)

        ctk.CTkLabel(tl_header, text="Tactical Timeline", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        # [Task 1: Zoom Controls for Sandbox]
        ctk.CTkButton(tl_header, text="+", width=30, command=self._zoom_in).pack(side="right", padx=2)
        ctk.CTkButton(tl_header, text="-", width=30, command=self._zoom_out).pack(side="right", padx=2)
        self.zoom_lbl = ctk.CTkLabel(tl_header, text="Zoom: 50")
        self.zoom_lbl.pack(side="right", padx=5)

        # Timeline Container (Canvas + Scrollbar)
        timeline_container = ctk.CTkFrame(right_panel)
        timeline_container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(timeline_container, bg="#2B2B2B", height=self.timeline_height, scrollregion=(0,0, self.canvas_width, self.timeline_height))

        hbar = tk.Scrollbar(timeline_container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.config(xscrollcommand=hbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._draw_timeline_grid()

    def _on_hp_change(self, value):
        self.hp_label.configure(text=f"{int(value*100)}%")
        if self.player:
            self.player.target_health_pct = value
            self._update_button_visuals_only()

    def _zoom_in(self):
        if self.pixels_per_second < 200:
            self.pixels_per_second += 10
            self._redraw_canvas()

    def _zoom_out(self):
        if self.pixels_per_second > 20:
            self.pixels_per_second -= 10
            self._redraw_canvas()

    def _redraw_canvas(self):
        self.zoom_lbl.configure(text=f"Zoom: {self.pixels_per_second}")
        self.canvas.delete("all")
        self._draw_timeline_grid()
        # Redraw history
        for evt in self.event_history:
            self._draw_block(evt['lane_y'], evt['start_time'], evt['duration'], evt['text'], evt['color'], evt['info'])

        # Move Red Line
        x = self.time_elapsed * self.pixels_per_second
        self.canvas.coords(self.time_indicator, x, 0, x, self.timeline_height)

    def _reset_sandbox(self):
        try:
            agility = float(self.agility_entry.get())
        except ValueError:
            agility = 2000.0
            self.agility_entry.delete(0, "end")
            self.agility_entry.insert(0, "2000")

        self.player = PlayerState(agility=agility)
        # Apply HP from slider
        self.player.target_health_pct = self.target_hp_pct.get()

        # Full Talent List from requirements
        all_talents = [
            "1-1",
            "2-1", "2-2", "2-3",
            "3-1", "3-2", "3-3", "Ascension",
            "4-1", "4-2", "4-3",
            "5-1", "5-2", "5-3", "5-4", "5-5", "5-6",
            "6-1", "6-2", "6-2_b",
            "WDP", "SW", "SOTWL"
        ]
        self.spell_book = SpellBook(talents=all_talents)
        self.spell_book.apply_talents(self.player)

        self.time_elapsed = 0.0
        self.event_history = []
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
        self._update_button_visuals_only()

        # Move Red Line
        x = self.time_elapsed * self.pixels_per_second
        self.canvas.coords(self.time_indicator, x, 0, x, self.timeline_height)

    def _update_button_visuals_only(self):
        for child in self.spells_frame.winfo_children():
            if hasattr(child, "spell_key"):
                self._update_button_visual(child)

    def _update_button_visual(self, btn):
        key = btn.spell_key
        spell = self.spell_book.spells[key]

        is_usable = spell.is_usable(self.player, self.spell_book.spells)

        if spell.current_cd > 0:
            btn.configure(text=f"{spell.name} ({spell.current_cd:.1f}s)", fg_color="#555555", state="disabled") # Gray out on CD
        elif not is_usable:
             btn.configure(text=f"{spell.name}", fg_color="#922B21", state="normal") # Red warning if unusable (resource)
        else:
            btn.configure(text=f"{spell.name}", fg_color="#2E86C1", state="normal")


    def _refresh_spell_buttons(self):
        for widget in self.spells_frame.winfo_children():
            widget.destroy()

        # Define spells
        spell_keys = [
            "TP", "BOK", "RSK", "FOF", "WDP", "SCK", "SOTWL", "SW", "Xuen", "Zenith", "ToD"
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
        elif key == "ToD": color = "#5B2C6F"

        self._record_and_draw(
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
                self._record_and_draw(
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
                self._record_and_draw(
                    lane_y=self.active_lane_y + 40, # Below main cast
                    start_time=evt_time,
                    duration=0.1,
                    text="Tick",
                    color="#D35400",
                    info={"Damage": event.get('Expected DMG'), "Breakdown": event.get('Breakdown')}
                )

        self._update_status()

    def _record_and_draw(self, lane_y, start_time, duration, text, color, info):
        # Record for redraw
        self.event_history.append({
            'lane_y': lane_y,
            'start_time': start_time,
            'duration': duration,
            'text': text,
            'color': color,
            'info': info
        })
        # Draw immediate
        self._draw_block(lane_y, start_time, duration, text, color, info)

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
