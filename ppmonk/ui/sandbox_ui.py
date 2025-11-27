import customtkinter as ctk
import datetime
import tkinter as tk
from ppmonk.core.player import PlayerState
from ppmonk.core.spell_book import SpellBook
import math
import random

class SandboxWindow(ctk.CTkToplevel):
    def __init__(self, parent, active_talents=None, player_stats=None):
        super().__init__(parent)
        self.title("Manual Sandbox")
        self.geometry("1400x850")

        self.active_talents = active_talents if active_talents else []
        self.player_stats = player_stats if player_stats else {}

        self.player = None
        self.spell_book = None
        self.time_elapsed = 0.0

        self.event_history = []

        self.force_proc_glory = tk.BooleanVar(value=False)
        self.force_proc_reset = tk.BooleanVar(value=False)
        self.target_hp_pct = tk.DoubleVar(value=1.0)
        self.target_count = tk.IntVar(value=1)

        self.pixels_per_second = 50
        self.row_height = 40
        self.timeline_height = 400
        self.active_lane_y = 40
        self.derivative_lane_y = 90
        self.passive_lane_y = 140
        self.canvas_width = 5000

        self.selection_start_x = 0
        self.selection_rect = None

        self._build_ui()
        self._reset_sandbox()

    def _build_ui(self):
        top_panel = ctk.CTkFrame(self)
        top_panel.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(top_panel, text="Agility:").pack(side="left", padx=5)
        self.agility_entry = ctk.CTkEntry(top_panel, width=80)
        self.agility_entry.insert(0, str(self.player_stats.get('agility', 2000)))
        self.agility_entry.pack(side="left", padx=5)

        ctk.CTkLabel(top_panel, text="Target HP%:").pack(side="left", padx=5)
        self.hp_slider = ctk.CTkSlider(top_panel, from_=0.0, to=1.0, number_of_steps=100, variable=self.target_hp_pct, command=self._on_hp_change, width=150)
        self.hp_slider.pack(side="left", padx=5)
        self.hp_label = ctk.CTkLabel(top_panel, text="100%")
        self.hp_label.pack(side="left", padx=2)

        ctk.CTkLabel(top_panel, text="Targets:").pack(side="left", padx=10)
        self.target_slider = ctk.CTkSlider(top_panel, from_=1, to=20, number_of_steps=19, variable=self.target_count, command=self._on_target_change, width=150)
        self.target_slider.pack(side="left", padx=5)
        self.target_label = ctk.CTkLabel(top_panel, text="1")
        self.target_label.pack(side="left", padx=2)

        ctk.CTkButton(top_panel, text="Reset", command=self._reset_sandbox, fg_color="#C0392B", width=60).pack(side="left", padx=20)

        self.status_label_chi = ctk.CTkLabel(top_panel, text="Chi: 0", font=("Arial", 14, "bold"), text_color="#F1C40F")
        self.status_label_chi.pack(side="left", padx=15)
        self.status_label_energy = ctk.CTkLabel(top_panel, text="Energy: 0", font=("Arial", 14, "bold"), text_color="#F39C12")
        self.status_label_energy.pack(side="left", padx=15)
        self.status_label_xuen = ctk.CTkLabel(top_panel, text="Xuen: Inactive", font=("Arial", 12), text_color="gray")
        self.status_label_xuen.pack(side="left", padx=15)
        self.status_label_buffs = ctk.CTkLabel(top_panel, text="", font=("Arial", 10), text_color="#A9DFBF")
        self.status_label_buffs.pack(side="left", padx=15)

        ctk.CTkCheckBox(top_panel, text="Force Glory", variable=self.force_proc_glory).pack(side="right", padx=10)
        ctk.CTkCheckBox(top_panel, text="Force Reset", variable=self.force_proc_reset).pack(side="right", padx=10)

        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=10, pady=5)

        left_panel = ctk.CTkFrame(content, width=300)
        left_panel.pack(side="left", fill="y", padx=5, pady=5)
        ctk.CTkLabel(left_panel, text="Spells", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        self.spells_frame = ctk.CTkScrollableFrame(left_panel)
        self.spells_frame.pack(fill="both", expand=True)

        right_panel = ctk.CTkFrame(content)
        right_panel.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        tl_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        tl_header.pack(fill="x", pady=5)
        ctk.CTkLabel(tl_header, text="Tactical Timeline", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        ctk.CTkButton(tl_header, text="+", width=30, command=self._zoom_in).pack(side="right", padx=2)
        ctk.CTkButton(tl_header, text="-", width=30, command=self._zoom_out).pack(side="right", padx=2)
        self.zoom_lbl = ctk.CTkLabel(tl_header, text="Zoom: 50")
        self.zoom_lbl.pack(side="right", padx=5)

        timeline_container = ctk.CTkFrame(right_panel)
        timeline_container.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(timeline_container, bg="#2B2B2B", height=self.timeline_height, scrollregion=(0,0, self.canvas_width, self.timeline_height))
        hbar = tk.Scrollbar(timeline_container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.config(xscrollcommand=hbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._draw_timeline_grid()
        self.canvas.bind("<ButtonPress-3>", self._start_selection)
        self.canvas.bind("<B3-Motion>", self._update_selection)
        self.canvas.bind("<ButtonRelease-3>", self._end_selection)

    def _on_hp_change(self, value):
        self.hp_label.configure(text=f"{int(value*100)}%")
        if self.player:
            self.player.target_health_pct = value
            self._update_button_visuals_only()

    def _on_target_change(self, value):
        val = int(value)
        self.target_label.configure(text=f"{val}")
        if self.player: self.player.target_count = val

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
        for evt in self.event_history:
            self._draw_block(evt['lane_y'], evt['start_time'], evt['duration'], evt['text'], evt['color'], evt['info'])
        x = self.time_elapsed * self.pixels_per_second
        self.canvas.coords(self.time_indicator, x, 0, x, self.timeline_height)

    def _reset_sandbox(self):
        try:
            agility = float(self.agility_entry.get())
        except ValueError:
            agility = 2000.0
            self.agility_entry.delete(0, "end")
            self.agility_entry.insert(0, "2000")

        self.player = PlayerState(
            agility=agility,
            target_count=self.target_count.get(),
            rating_crit=self.player_stats.get('crit_rating', 2000),
            rating_haste=self.player_stats.get('haste_rating', 1500),
            rating_mastery=self.player_stats.get('mastery_rating', 1000),
            rating_vers=self.player_stats.get('vers_rating', 500)
        )
        self.player.target_health_pct = self.target_hp_pct.get()

        talents_to_use = self.active_talents if self.active_talents else [
            "1-1", "2-1", "2-2", "2-3", "3-1", "3-2", "3-3", "Ascension",
            "4-1", "4-2", "4-3", "5-1", "5-2", "5-3", "5-4", "5-5", "5-6",
            "6-1", "6-2", "6-2_b", "WDP", "SW", "SOTWL",
            "8-1", "8-2", "8-3", "8-4", "8-5", "8-5_b", "8-6", "8-7",
            "9-1", "9-2", "9-3", "9-4", "9-5", "9-8",
            "10-2", "10-3", "10-4", "10-5", "10-6", "10-7"
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
        self.canvas.create_text(5, self.derivative_lane_y - 20, text="Derivative / Procs", anchor="w", fill="#D4AC0D", font=("Arial", 10, "bold"))
        self.canvas.create_text(5, self.passive_lane_y - 20, text="Passive / Auto Attacks", anchor="w", fill="#95A5A6", font=("Arial", 10, "bold"))
        self.time_indicator = self.canvas.create_line(0, 0, 0, self.timeline_height, fill="red", width=2)

    def _update_status(self):
        self.status_label_chi.configure(text=f"Chi: {self.player.chi}")
        self.status_label_energy.configure(text=f"Energy: {int(self.player.energy)}")
        self.status_label_xuen.configure(text=f"Xuen: {self.player.xuen_duration:.1f}s" if self.player.xuen_active else "Xuen: Inactive", text_color="#3498DB" if self.player.xuen_active else "gray")
        buffs = []
        if self.player.combo_breaker_stacks > 0: buffs.append(f"ComboBreaker({self.player.combo_breaker_stacks})")
        if self.player.dance_of_chiji_stacks > 0: buffs.append(f"DanceChiJi({self.player.dance_of_chiji_stacks})")
        if self.player.hit_combo_stacks > 0: buffs.append(f"HitCombo({self.player.hit_combo_stacks})")
        if self.player.thunderfist_stacks > 0: buffs.append(f"Thunderfist({self.player.thunderfist_stacks})")
        if self.player.totm_stacks > 0: buffs.append(f"TotM({self.player.totm_stacks})")
        if self.player.rwk_ready: buffs.append(f"RWK Ready")
        if self.player.teb_stacks > 0: buffs.append(f"TEB({self.player.teb_stacks})")
        self.status_label_buffs.configure(text=" | ".join(buffs))
        self._update_button_visuals_only()
        x = self.time_elapsed * self.pixels_per_second
        self.canvas.coords(self.time_indicator, x, 0, x, self.timeline_height)

    def _update_button_visuals_only(self):
        for child in self.spells_frame.winfo_children():
            if hasattr(child, "spell_key"): self._update_button_visual(child)

    def _update_button_visual(self, btn):
        key = btn.spell_key
        if key not in self.spell_book.spells: return
        spell = self.spell_book.spells[key]
        if spell.current_cd > 0:
            btn.configure(text=f"{spell.name} ({spell.current_cd:.1f}s)", fg_color="#555555", state="disabled")
        elif not spell.is_usable(self.player, self.spell_book.spells):
             btn.configure(text=f"{spell.name}", fg_color="#922B21", state="normal")
        else:
            btn.configure(text=f"{spell.name}", fg_color="#2E86C1", state="normal")

    def _refresh_spell_buttons(self):
        for widget in self.spells_frame.winfo_children(): widget.destroy()
        spell_keys = ["TP", "BOK", "RSK", "FOF", "WDP", "SCK", "SOTWL", "SW", "Xuen", "Zenith", "ToD", "Conduit"]
        for key in spell_keys:
            if key in self.spell_book.spells:
                spell = self.spell_book.spells[key]
                btn = ctk.CTkButton(self.spells_frame, text=spell.name, command=lambda k=key: self._handle_cast_click(k))
                btn.spell_key = key
                btn.pack(pady=4, padx=5, fill="x")
        if "RSK" in self.spell_book.spells:
             ctk.CTkButton(self.spells_frame, text="RSK (Force Glory)", fg_color="#E74C3C", command=lambda: self._handle_cast_click("RSK", force_glory_override=True)).pack(pady=4, padx=5, fill="x")
        if "BOK" in self.spell_book.spells:
             ctk.CTkButton(self.spells_frame, text="BOK (Force Reset)", fg_color="#2E86C1", command=lambda: self._handle_cast_click("BOK", force_reset_override=True)).pack(pady=4, padx=5, fill="x")
        ctk.CTkButton(self.spells_frame, text="Wait (0.5s)", fg_color="gray", command=lambda: self._advance_simulation(0.5)).pack(pady=20, padx=5, fill="x")

    def _handle_cast_click(self, key, force_glory_override=False, force_reset_override=False):
        spell = self.spell_book.spells[key]
        if not spell.is_usable(self.player, self.spell_book.spells):
            self._show_rejection_popup(key)
            return

        # Task 4: Fix forced trigger logic
        force_glory = self.force_proc_glory.get() or force_glory_override
        force_reset = self.force_proc_reset.get() or force_reset_override
        cast_time = spell.get_effective_cast_time(self.player)

        # Cast with explicit params
        dmg, breakdown = spell.cast(self.player, other_spells=self.spell_book.spells,
                                    force_proc_glory=force_glory, force_proc_reset=force_reset,
                                    use_expected_value=True)

        step_duration = max(self.player.gcd_remaining, cast_time)
        visual_duration = max(step_duration, 0.15)
        action_start_time = self.time_elapsed

        color = "#1ABC9C"
        if key == "RSK": color = "#E74C3C"
        elif key == "FOF": color = "#8E44AD"
        elif key == "TP": color = "#27AE60"
        elif key == "ToD": color = "#5B2C6F"

        self._record_and_draw(self.active_lane_y, action_start_time, visual_duration, key, color, {"Damage": dmg, "Breakdown": breakdown})
        if 'extra_events' in breakdown:
            for extra in breakdown['extra_events']:
                 self._record_and_draw(self.derivative_lane_y, action_start_time, 0.15, extra['name'][:4], "#D4AC0D", {"Damage": extra.get('damage', 0), "Breakdown": extra})
        self._advance_simulation(step_duration)

    def _advance_simulation(self, duration):
        base_time = self.time_elapsed
        dmg, events = self.player.advance_time(duration, use_expected_value=True)
        self.spell_book.tick(duration)
        self.time_elapsed += duration
        for event in events:
            evt_time = base_time + event.get('offset', 0.0)
            name = event.get('Action')
            dmg_val = event.get('Expected DMG')
            if event.get('source') == 'passive':
                lane = self.passive_lane_y + (0 if "Auto" in name else 25)
                self._record_and_draw(lane, evt_time, 0.1, name[0:2], "#95A5A6", {"Damage": dmg_val, "Breakdown": event.get('Breakdown')})
            elif event.get('source') == 'active':
                self._record_and_draw(self.active_lane_y + 40, evt_time, 0.1, "Tick", "#D35400", {"Damage": dmg_val, "Breakdown": event.get('Breakdown')})
        self._update_status()

    def _record_and_draw(self, lane_y, start_time, duration, text, color, info):
        self.event_history.append({'lane_y': lane_y, 'start_time': start_time, 'duration': duration, 'text': text, 'color': color, 'info': info})
        self._draw_block(lane_y, start_time, duration, text, color, info)

    def _draw_block(self, lane_y, start_time, duration, text, color, info):
        x1 = start_time * self.pixels_per_second
        x2 = (start_time + duration) * self.pixels_per_second
        y1 = lane_y
        y2 = lane_y + 30
        tag = f"block_{int(start_time*100)}_{random.randint(0,1000000)}"
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black", tags=tag)
        self.canvas.create_text((x1+x2)/2, (y1+y2)/2, text=text, fill="white", font=("Arial", 9, "bold"), tags=tag)
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
        top.geometry("600x600") # Larger tooltip

        dmg_val = int(info['Damage'])
        ctk.CTkLabel(top, text=f"Action: {name}", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkLabel(top, text=f"Damage: {dmg_val}", font=("Arial", 14, "bold"), text_color="#E67E22").pack(pady=5)

        breakdown = info.get('Breakdown')
        text_info = ""

        if isinstance(breakdown, dict):
            # Formatted per Task 2
            if 'raw_base' in breakdown: text_info += f"Raw Base: {breakdown['raw_base']:.1f}\n"
            if 'components' in breakdown: text_info += f"Formula: {breakdown['components']}\n\n"

            text_info += "Modifiers:\n"
            mods = breakdown.get('modifiers', [])
            if isinstance(mods, list):
                for m in mods: text_info += f"  - {m}\n"

            crit_src = breakdown.get('crit_sources', [])
            if crit_src:
                text_info += "\nCrit Sources:\n"
                for c in crit_src: text_info += f"  - {c}\n"

            text_info += f"\nFinal Crit: {breakdown.get('final_crit', 0)*100:.1f}%\n"
            text_info += f"Crit Mult: {breakdown.get('crit_mult', 2.0):.2f}x\n"

            if 'expected_dmg' in breakdown:
                 text_info += f"\nExpected DMG: {breakdown['expected_dmg']:.1f}\n"
            if 'snapshot_dmg' in breakdown:
                 text_info += f"Snapshot DMG: {breakdown['snapshot_dmg']:.1f}\n"

            if 'extra_events' in breakdown:
                text_info += "\nExtra Events:\n"
                for extra in breakdown['extra_events']:
                    text_info += f"  - {extra['name']}: {int(extra.get('damage',0))}\n"
        else:
            text_info = str(breakdown)

        textbox = ctk.CTkTextbox(top, width=580, height=450)
        textbox.pack(pady=10)
        textbox.insert("1.0", text_info)
        textbox.configure(state="disabled")

    def _start_selection(self, event):
        self.selection_start_x = self.canvas.canvasx(event.x)
        if self.selection_rect: self.canvas.delete(self.selection_rect)
        self.selection_rect = self.canvas.create_rectangle(self.selection_start_x, 0, self.selection_start_x, self.timeline_height, fill="white", stipple="gray25", outline="")

    def _update_selection(self, event):
        cur_x = self.canvas.canvasx(event.x)
        self.canvas.coords(self.selection_rect, self.selection_start_x, 0, cur_x, self.timeline_height)

    def _end_selection(self, event):
        end_x = self.canvas.canvasx(event.x)
        start_time = min(self.selection_start_x, end_x) / self.pixels_per_second
        end_time = max(self.selection_start_x, end_x) / self.pixels_per_second
        if end_time - start_time < 0.1:
             self.canvas.delete(self.selection_rect)
             self.selection_rect = None
             return
        self._calculate_selection_stats(start_time, end_time)
        self.canvas.delete(self.selection_rect)
        self.selection_rect = None

    def _calculate_selection_stats(self, start, end):
        total_dmg = 0
        breakdown = {}
        for evt in self.event_history:
            t = evt['start_time']
            if start <= t <= end:
                 d = evt['info'].get('Damage', 0)
                 total_dmg += d
                 name = evt['text']
                 breakdown[name] = breakdown.get(name, 0) + d
        duration = end - start
        dps = total_dmg / duration if duration > 0 else 0
        self._show_selection_popup(total_dmg, dps, duration, breakdown)

    def _show_selection_popup(self, total_dmg, dps, duration, breakdown):
        top = ctk.CTkToplevel(self)
        top.title("Selection Analysis")
        top.geometry("400x500")
        ctk.CTkLabel(top, text="Selection Stats", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkLabel(top, text=f"Time: {duration:.2f}s", font=("Arial", 12)).pack()
        ctk.CTkLabel(top, text=f"Total EV Damage: {int(total_dmg)}", font=("Arial", 14, "bold"), text_color="#E67E22").pack(pady=5)
        ctk.CTkLabel(top, text=f"DPS: {int(dps)}", font=("Arial", 14, "bold"), text_color="#27AE60").pack(pady=5)
        ctk.CTkLabel(top, text="Breakdown:", font=("Arial", 12, "bold")).pack(pady=5)
        sorted_bd = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
        text_info = ""
        for name, dmg in sorted_bd:
            pct = (dmg / total_dmg * 100) if total_dmg > 0 else 0
            text_info += f"{name}: {int(dmg)} ({pct:.1f}%)\n"
        textbox = ctk.CTkTextbox(top, width=380, height=300)
        textbox.pack(pady=10)
        textbox.insert("1.0", text_info)
        textbox.configure(state="disabled")
