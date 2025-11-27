import customtkinter as ctk
import datetime
import tkinter as tk
from ppmonk.core.player import PlayerState
from ppmonk.core.spell_book import SpellBook

class SandboxWindow(ctk.CTkToplevel):
    def __init__(self, parent, active_talents=None):
        super().__init__(parent)
        self.title("Manual Sandbox")
        self.geometry("1400x800")

        self.active_talents = active_talents if active_talents else []

        self.player = None
        self.spell_book = None
        self.time_elapsed = 0.0

        # History for redrawing
        self.event_history = []

        # UI State
        self.force_proc_glory = tk.BooleanVar(value=False)
        self.force_proc_reset = tk.BooleanVar(value=False)
        self.target_hp_pct = tk.DoubleVar(value=1.0)
        self.target_count = tk.IntVar(value=1)

        # Timeline drawing config
        self.pixels_per_second = 50
        self.row_height = 40
        self.timeline_height = 300
        self.active_lane_y = 40
        self.passive_lane_y = 120
        self.canvas_width = 5000

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

        # Target HP
        ctk.CTkLabel(top_panel, text="Target HP%:").pack(side="left", padx=5)
        self.hp_slider = ctk.CTkSlider(top_panel, from_=0.0, to=1.0, number_of_steps=100, variable=self.target_hp_pct, command=self._on_hp_change, width=150)
        self.hp_slider.pack(side="left", padx=5)
        self.hp_label = ctk.CTkLabel(top_panel, text="100%")
        self.hp_label.pack(side="left", padx=2)

        # Target Count
        ctk.CTkLabel(top_panel, text="Targets:").pack(side="left", padx=10)
        self.target_slider = ctk.CTkSlider(top_panel, from_=1, to=20, number_of_steps=19, variable=self.target_count, command=self._on_target_change, width=150)
        self.target_slider.pack(side="left", padx=5)
        self.target_label = ctk.CTkLabel(top_panel, text="1")
        self.target_label.pack(side="left", padx=2)

        # Reset
        ctk.CTkButton(top_panel, text="Reset", command=self._reset_sandbox, fg_color="#C0392B", width=60).pack(side="left", padx=20)

        # Status Labels
        self.status_label_chi = ctk.CTkLabel(top_panel, text="Chi: 0", font=("Arial", 14, "bold"), text_color="#F1C40F")
        self.status_label_chi.pack(side="left", padx=15)

        self.status_label_energy = ctk.CTkLabel(top_panel, text="Energy: 0", font=("Arial", 14, "bold"), text_color="#F39C12")
        self.status_label_energy.pack(side="left", padx=15)

        self.status_label_xuen = ctk.CTkLabel(top_panel, text="Xuen: Inactive", font=("Arial", 12), text_color="gray")
        self.status_label_xuen.pack(side="left", padx=15)

        # Buff Status
        self.status_label_buffs = ctk.CTkLabel(top_panel, text="", font=("Arial", 10), text_color="#A9DFBF")
        self.status_label_buffs.pack(side="left", padx=15)

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

    def _on_target_change(self, value):
        val = int(value)
        self.target_label.configure(text=f"{val}")
        if self.player:
            self.player.target_count = val

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

        self.player = PlayerState(agility=agility, target_count=self.target_count.get())
        self.player.target_health_pct = self.target_hp_pct.get()

        # Update default talents to include interesting new ones
        talents_to_use = self.active_talents if self.active_talents else [
            "1-1",
            "2-1", "2-2", "2-3",
            "3-1", "3-2", "3-3", "Ascension",
            "4-1", "4-2", "4-3",
            "5-1", "5-2", "5-3", "5-4", "5-5", "5-6",
            "6-1", "6-2", "6-2_b",
            "WDP", "SW", "SOTWL",
            # Enable new stuff for testing
            "8-5", "8-5_b", "8-6", "8-7",
            "9-2", "9-3", "9-4", "9-5", "9-8"
        ]

        self.spell_book = SpellBook(talents=talents_to_use)
        self.spell_book.apply_talents(self.player)

        self.time_elapsed = 0.0
        self.event_history = []
        self.canvas.delete("all")
        self._draw_timeline_grid()
        self._update_status()
        self._refresh_spell_buttons()

    def _draw_timeline_grid(self):
        for i in range(0, 100):
            x = i * self.pixels_per_second
            color = "#404040" if i % 5 != 0 else "#606060"
            self.canvas.create_line(x, 0, x, self.timeline_height, fill=color)
            self.canvas.create_text(x + 2, self.timeline_height - 15, text=f"{i}s", anchor="w", fill="white", font=("Arial", 8))

        self.canvas.create_text(5, self.active_lane_y - 20, text="Active Spells", anchor="w", fill="#3498DB", font=("Arial", 10, "bold"))
        self.canvas.create_text(5, self.passive_lane_y - 20, text="Passive / Auto Attacks", anchor="w", fill="#95A5A6", font=("Arial", 10, "bold"))

        self.time_indicator = self.canvas.create_line(0, 0, 0, self.timeline_height, fill="red", width=2)

    def _update_status(self):
        self.status_label_chi.configure(text=f"Chi: {self.player.chi}")
        self.status_label_energy.configure(text=f"Energy: {int(self.player.energy)}")

        if self.player.xuen_active:
            self.status_label_xuen.configure(text=f"Xuen: {self.player.xuen_duration:.1f}s", text_color="#3498DB")
        else:
            self.status_label_xuen.configure(text="Xuen: Inactive", text_color="gray")

        # Buff display
        buffs = []
        if self.player.combo_breaker_stacks > 0:
            buffs.append(f"ComboBreaker({self.player.combo_breaker_stacks})")
        if self.player.dance_of_chiji_stacks > 0:
            buffs.append(f"DanceChiJi({self.player.dance_of_chiji_stacks})")
        if self.player.hit_combo_stacks > 0:
            buffs.append(f"HitCombo({self.player.hit_combo_stacks})")
        if self.player.thunderfist_stacks > 0:
            buffs.append(f"Thunderfist({self.player.thunderfist_stacks})")
        if self.player.totm_stacks > 0:
            buffs.append(f"TotM({self.player.totm_stacks})")
        if self.player.rwk_ready:
            buffs.append(f"RWK Ready")

        self.status_label_buffs.configure(text=" | ".join(buffs))
        self._update_button_visuals_only()

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
            btn.configure(text=f"{spell.name} ({spell.current_cd:.1f}s)", fg_color="#555555", state="disabled")
        elif not is_usable:
             btn.configure(text=f"{spell.name}", fg_color="#922B21", state="normal")
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
            btn.spell_key = key
            btn.pack(pady=4, padx=5, fill="x")

        # Wait Button
        ctk.CTkButton(self.spells_frame, text="Wait (0.5s)", fg_color="gray",
                      command=lambda: self._advance_simulation(0.5)).pack(pady=20, padx=5, fill="x")

    def _handle_cast_click(self, key):
        spell = self.spell_book.spells[key]

        if not spell.is_usable(self.player, self.spell_book.spells):
            self._show_rejection_popup(key)
            return

        force_glory = self.force_proc_glory.get()
        force_reset = self.force_proc_reset.get()

        cast_time = spell.get_effective_cast_time(self.player)
        gcd = 1.5 / (1.0 + self.player.haste)
        if spell.gcd_override is not None:
            gcd = spell.gcd_override

        action_start_time = self.time_elapsed

        dmg, breakdown = spell.cast(self.player, other_spells=self.spell_book.spells,
                                    force_proc_glory=force_glory, force_proc_reset=force_reset)

        step_duration = max(cast_time, gcd) if cast_time > 0 else gcd
        if step_duration < 0.1: step_duration = 0.1

        color = "#1ABC9C"
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

        self._advance_simulation(step_duration)

    def _advance_simulation(self, duration):
        base_time = self.time_elapsed
        dmg, events = self.player.advance_time(duration)
        self.spell_book.tick(duration)
        self.time_elapsed += duration

        for event in events:
            if event.get('source') == 'passive':
                evt_time = base_time + event.get('offset', 0.0)
                name = event.get('Action')

                self._record_and_draw(
                    lane_y=self.passive_lane_y + (0 if "Auto" in name else 25),
                    start_time=evt_time,
                    duration=0.1,
                    text=name[0:2],
                    color="#95A5A6",
                    info={"Damage": event.get('Expected DMG'), "Breakdown": event.get('Breakdown')}
                )
            elif event.get('source') == 'active':
                evt_time = base_time + event.get('offset', 0.0)
                self._record_and_draw(
                    lane_y=self.active_lane_y + 40,
                    start_time=evt_time,
                    duration=0.1,
                    text="Tick",
                    color="#D35400",
                    info={"Damage": event.get('Expected DMG'), "Breakdown": event.get('Breakdown')}
                )

        self._update_status()

    def _record_and_draw(self, lane_y, start_time, duration, text, color, info):
        self.event_history.append({
            'lane_y': lane_y,
            'start_time': start_time,
            'duration': duration,
            'text': text,
            'color': color,
            'info': info
        })
        self._draw_block(lane_y, start_time, duration, text, color, info)

    def _draw_block(self, lane_y, start_time, duration, text, color, info):
        x1 = start_time * self.pixels_per_second
        x2 = (start_time + duration) * self.pixels_per_second
        y1 = lane_y
        y2 = lane_y + 30

        tag = f"block_{int(start_time*100)}_{random_id()}"

        rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black", tags=tag)
        lbl = self.canvas.create_text((x1+x2)/2, (y1+y2)/2, text=text, fill="white", font=("Arial", 9, "bold"), tags=tag)
        self.canvas.tag_bind(tag, "<Button-1>", lambda e, i=info, n=text: self._show_tooltip(e, n, i))

    def _show_rejection_popup(self, spell_key):
        top = ctk.CTkToplevel(self)
        top.title("Rejection")
        top.geometry("300x150")

        ctk.CTkLabel(top, text=f"Cannot Cast {spell_key}", font=("Arial", 16, "bold"), text_color="#C0392B").pack(pady=20)
        ctk.CTkLabel(top, text="Cooldown not ready or insufficient resources.", font=("Arial", 12)).pack(pady=5)
        ctk.CTkButton(top, text="OK", command=top.destroy).pack(pady=10)

    def _show_tooltip(self, event, name, info):
        top = ctk.CTkToplevel(self)
        top.title(f"Details: {name}")
        top.geometry("400x350")

        dmg_val = int(info['Damage'])
        ctk.CTkLabel(top, text=f"Action: {name}", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkLabel(top, text=f"Damage: {dmg_val}", font=("Arial", 14, "bold"), text_color="#E67E22").pack(pady=5)

        breakdown = info['Breakdown']
        text_info = ""

        if isinstance(breakdown, dict):
            text_info += f"Base: {breakdown.get('base')}\n"

            # New Modifier List Display
            text_info += "Modifiers:\n"
            mods = breakdown.get('modifiers', [])
            if isinstance(mods, list):
                for m in mods:
                    text_info += f"  - {m}\n"
            elif isinstance(mods, dict): # Fallback
                for k, v in mods.items():
                    text_info += f"  - {k}: x{v:.2f}\n"

            # Crit Sources
            crit_src = breakdown.get('crit_sources', [])
            if crit_src:
                text_info += "\nCrit Sources:\n"
                for c in crit_src:
                    text_info += f"  - {c}\n"

            text_info += f"\nFinal Crit: {breakdown.get('final_crit', 0)*100:.1f}%\n"
            text_info += f"Crit Mult: {breakdown.get('crit_mult', 2.0):.2f}x\n"

            if 'aoe_type' in breakdown:
                 text_info += f"\nAOE Type: {breakdown['aoe_type']}\n"
                 text_info += f"Targets: {breakdown.get('targets')}\n"
                 if breakdown['aoe_type'] == 'cleave':
                     text_info += "  (Main + up to 2 Secondary @ 80%)\n"
                 elif breakdown['aoe_type'] == 'soft_cap':
                     text_info += "  (SQRT scaling > 5 targets)\n"
                 if 'total_dmg_after_aoe' in breakdown:
                     text_info += f"Total AOE Dmg: {int(breakdown['total_dmg_after_aoe'])}\n"

            if 'extra_events' in breakdown:
                text_info += "\nExtra Events:\n"
                for extra in breakdown['extra_events']:
                    text_info += f"  - {extra['name']}: {int(extra['damage'])} (Crit: {extra.get('crit')})\n"
        else:
            text_info = str(breakdown)

        textbox = ctk.CTkTextbox(top, width=380, height=220)
        textbox.pack(pady=10)
        textbox.insert("1.0", text_info)
        textbox.configure(state="disabled")

def random_id():
    import random
    return random.randint(0, 1000000)
