import customtkinter as ctk
import datetime
import math
from ppmonk.core.player import PlayerState
from ppmonk.core.spell_book import SpellBook

class SandboxWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Manual Sandbox - Tactical Analysis")
        self.geometry("1400x800")

        self.player = None
        self.spell_book = None
        self.current_time = 0.0

        # UI State
        self.force_glory = ctk.BooleanVar(value=False)
        self.force_reset = ctk.BooleanVar(value=False)

        self._build_ui()
        self._reset_sandbox()

        # Start update loop
        self.after(100, self._update_loop)

    def _build_ui(self):
        # 1. Top Panel: Stats & Controls
        top_panel = ctk.CTkFrame(self, height=60)
        top_panel.pack(fill="x", padx=10, pady=5)

        # Left: Reset & Agility
        ctk.CTkButton(top_panel, text="Reset", command=self._reset_sandbox, fg_color="#C0392B", width=80).pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(top_panel, text="Agility:").pack(side="left", padx=(10, 5))
        self.agility_entry = ctk.CTkEntry(top_panel, width=70)
        self.agility_entry.insert(0, "2000")
        self.agility_entry.pack(side="left", padx=5)

        # Right: Status Bar (Chi, Energy, Time)
        self.status_label = ctk.CTkLabel(top_panel, text="Time: 0.00s | Chi: 2 | Energy: 100", font=("Consolas", 16, "bold"))
        self.status_label.pack(side="right", padx=20)

        self.xuen_indicator = ctk.CTkLabel(top_panel, text="XUEN", fg_color="gray", corner_radius=5, padx=5, pady=2)
        self.xuen_indicator.pack(side="right", padx=10)

        # 2. Main Content
        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=10, pady=5)

        # 2a. Left: Skill Panel
        left_panel = ctk.CTkFrame(content, width=300)
        left_panel.pack(side="left", fill="y", padx=5, pady=5)

        # Proc Toggles
        proc_frame = ctk.CTkFrame(left_panel)
        proc_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkCheckBox(proc_frame, text="Force RSK Glory", variable=self.force_glory).pack(anchor="w", padx=5, pady=2)
        ctk.CTkCheckBox(proc_frame, text="Force BOK Reset", variable=self.force_reset).pack(anchor="w", padx=5, pady=2)

        # Skills Grid
        self.skills_frame = ctk.CTkScrollableFrame(left_panel)
        self.skills_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.skill_buttons = {} # key -> button widget
        self.cd_labels = {}     # key -> label widget

        # 2b. Right: Timeline Visualization
        right_panel = ctk.CTkFrame(content)
        right_panel.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(right_panel, text="Tactical Timeline", font=("Arial", 14, "bold")).pack(pady=5)

        # Canvas for timeline
        self.timeline_canvas = ctk.CTkCanvas(right_panel, bg="#2b2b2b", highlightthickness=0)
        self.timeline_canvas.pack(fill="both", expand=True)

        # Scrollbar for canvas
        # (For simplicity, we just keep scrolling right, or fit width. Let's make it drag scrollable later if needed, or simple scroll)
        # Actually, let's just make it auto-scroll or keep last N seconds visible?
        # The requirement says "ScrollableFrame" or "Canvas".
        # I'll implement a simple horizontal scroll via binding if needed, but for now simple draw.
        # We will keep drawing from left 0.

        self.timeline_canvas.bind("<Button-1>", self._on_canvas_click)

    def _reset_sandbox(self):
        try:
            agility = float(self.agility_entry.get())
        except ValueError:
            agility = 2000.0
            self.agility_entry.delete(0, "end")
            self.agility_entry.insert(0, "2000")

        self.player = PlayerState(agility=agility)
        # Enable all talents
        all_talents = ["1-1", "1-2", "1-3", "2-1", "2-2", "2-3", "WDP", "SW", "Ascension", "Teachings of the Monastery", "Glory of the Dawn"]
        self.spell_book = SpellBook(talents=all_talents)
        self.spell_book.apply_talents(self.player)

        self.current_time = 0.0
        self.timeline_events = [] # List of (type, start, duration, label, breakdown, source)
        self.timeline_canvas.delete("all")

        self._refresh_skill_grid()
        self._update_status()

    def _refresh_skill_grid(self):
        for w in self.skills_frame.winfo_children():
            w.destroy()
        self.skill_buttons = {}
        self.cd_labels = {}

        spells = [
            ("Tiger Palm", "TP"), ("Blackout Kick", "BOK"),
            ("Rising Sun Kick", "RSK"), ("Fists of Fury", "FOF"),
            ("Spinning Crane", "SCK"), ("Whirling Dragon", "WDP"),
            ("Slicing Winds", "SW"), ("Strike Windlord", "SOTWL"),
            ("Invoke Xuen", "Xuen"), ("Zenith", "Zenith")
        ]

        for label, key in spells:
            if key not in self.spell_book.spells: continue

            frame = ctk.CTkFrame(self.skills_frame)
            frame.pack(fill="x", pady=2)

            btn = ctk.CTkButton(
                frame, text=label,
                command=lambda k=key: self._try_cast(k),
                width=160, height=30
            )
            btn.pack(side="left", padx=2)
            self.skill_buttons[key] = btn

            cd_lbl = ctk.CTkLabel(frame, text="", width=40, font=("Consolas", 12))
            cd_lbl.pack(side="right", padx=5)
            self.cd_labels[key] = cd_lbl

        # Wait Button
        ctk.CTkButton(self.skills_frame, text="Wait (GCD)", command=self._wait_gcd, fg_color="gray").pack(fill="x", pady=10)

    def _update_loop(self):
        if self.player:
            # Update CD labels and Button states
            for key, btn in self.skill_buttons.items():
                spell = self.spell_book.spells[key]

                # Update CD text
                if spell.current_cd > 0:
                    self.cd_labels[key].configure(text=f"{spell.current_cd:.1f}")
                else:
                    self.cd_labels[key].configure(text="")

                # Visual Feedback
                # Check usability (ignoring GCD usually for button state, but strictly checking resource/cd)
                # spell.is_usable includes GCD check? No, spell.is_usable checks charges/resource.
                # But Step logic usually checks GCD. Here we want to see if it's available.

                is_usable = spell.is_usable(self.player, self.spell_book.spells)

                if is_usable:
                    if spell.current_cd > 0 and spell.charges < spell.max_charges:
                        # Usable but charging (if stacks)
                        btn.configure(state="normal", fg_color="#F39C12") # Orange for charging
                    else:
                        btn.configure(state="normal", fg_color="#1F618D") # Blue for ready
                else:
                    # Not usable (CD or Resource)
                    if spell.current_cd > 0 and spell.charges == 0:
                        btn.configure(state="disabled", fg_color="#922B21") # Red for CD
                    elif self.player.energy < spell.energy_cost or self.player.chi < spell.chi_cost:
                        btn.configure(state="normal", fg_color="#7F8C8D") # Grey for resource, keep enabled to show rejection?
                        # User requirement: "Button gray or red border".
                        # Let's disable for CD, Gray for Resource.
                    else:
                        btn.configure(state="disabled", fg_color="#555555")

        self.after(100, self._update_loop)

    def _update_status(self):
        if not self.player: return
        self.status_label.configure(text=f"Time: {self.current_time:.2f}s | Chi: {self.player.chi} | Energy: {int(self.player.energy)}")

        if self.player.xuen_active:
            self.xuen_indicator.configure(fg_color="#F1C40F", text_color="black")
        else:
            self.xuen_indicator.configure(fg_color="gray", text_color="white")

    def _try_cast(self, key):
        spell = self.spell_book.spells[key]

        # Rejection Mechanism
        if not spell.is_usable(self.player, self.spell_book.spells):
            self._show_warning(f"Cannot cast {key}: Resource or CD")
            return

        # Determine casting duration
        cast_time = spell.get_effective_cast_time(self.player)
        gcd = 1.5 / (1.0 + self.player.haste)
        if spell.gcd_override is not None:
            gcd = spell.gcd_override

        # Active Duration (occupies Main Lane)
        active_duration = max(cast_time, gcd) if cast_time > 0 else gcd
        if active_duration < 0.1: active_duration = 0.1

        # Log Timestamp
        start_time = self.current_time

        # Cast
        # Apply force proc flags
        f_glory = self.force_glory.get()
        f_reset = self.force_reset.get()

        dmg, breakdown = spell.cast(self.player, other_spells=self.spell_book.spells,
                                    force_proc_glory=f_glory, force_proc_reset=f_reset)

        # Add Active Event
        self._add_timeline_event("active", start_time, active_duration, key, breakdown)

        # Advance Time
        self._advance_time_logic(active_duration)

        self._update_status()
        self._draw_timeline()

    def _wait_gcd(self):
        gcd = 1.5 / (1.0 + self.player.haste)
        self._add_timeline_event("active", self.current_time, gcd, "Wait", {'base': 0})
        self._advance_time_logic(gcd)
        self._update_status()
        self._draw_timeline()

    def _advance_time_logic(self, duration):
        # player.advance_time returns events with relative timestamp
        total_dmg, events = self.player.advance_time(duration)
        self.spell_book.tick(duration)

        for e in events:
            # e has: timestamp (relative), Action, Breakdown, source
            rel_time = e.get('timestamp', 0.0)
            abs_time = self.current_time + rel_time
            self._add_timeline_event(
                e.get('source', 'passive'),
                abs_time,
                0.2, # Short blip for passive
                e.get('Action'),
                e.get('Breakdown')
            )

        self.current_time += duration

    def _add_timeline_event(self, lane, start, duration, label, breakdown):
        # lane: 'active' or 'passive'
        self.timeline_events.append({
            'lane': lane,
            'start': start,
            'duration': duration,
            'label': label,
            'breakdown': breakdown
        })

    def _draw_timeline(self):
        self.timeline_canvas.delete("all")

        scale = 50.0 # pixels per second
        lane_height = 40
        main_lane_y = 50
        passive_lane_y = 120

        # Draw tracks
        self.timeline_canvas.create_line(0, main_lane_y + lane_height, 2000, main_lane_y + lane_height, fill="#555")
        self.timeline_canvas.create_line(0, passive_lane_y + lane_height, 2000, passive_lane_y + lane_height, fill="#555")

        self.timeline_canvas.create_text(10, main_lane_y - 15, text="Active", fill="white", anchor="w")
        self.timeline_canvas.create_text(10, passive_lane_y - 15, text="Passive / Auto", fill="white", anchor="w")

        # Draw Events
        for i, ev in enumerate(self.timeline_events):
            x1 = ev['start'] * scale + 20 # Offset
            width = ev['duration'] * scale
            x2 = x1 + width

            y1 = main_lane_y if ev['lane'] == 'active' else passive_lane_y
            y2 = y1 + lane_height

            color = "#2E86C1" if ev['lane'] == 'active' else "#27AE60"
            if ev['label'] == "Wait": color = "#555"

            # Rect
            tag = f"event_{i}"
            self.timeline_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black", tags=tag)

            # Text
            text = ev['label']
            self.timeline_canvas.create_text((x1+x2)/2, (y1+y2)/2, text=text, fill="white", font=("Arial", 10), tags=tag)

            # Bind click
            # Need closures to capture event data? Or use tag
            # Using tag and finding event by index

        # Canvas Scroll Region
        max_width = (self.current_time + 5) * scale
        self.timeline_canvas.configure(scrollregion=(0, 0, max(1000, max_width), 300))

    def _on_canvas_click(self, event):
        # Find item
        x = self.timeline_canvas.canvasx(event.x)
        y = self.timeline_canvas.canvasy(event.y)
        items = self.timeline_canvas.find_overlapping(x, y, x+1, y+1)

        for item in items:
            tags = self.timeline_canvas.gettags(item)
            for t in tags:
                if t.startswith("event_"):
                    idx = int(t.split("_")[1])
                    ev = self.timeline_events[idx]
                    self._show_breakdown(ev)
                    return

    def _show_breakdown(self, ev):
        # Create a popup window
        popup = ctk.CTkToplevel(self)
        popup.title(f"Breakdown: {ev['label']}")
        popup.geometry("300x300")

        ctk.CTkLabel(popup, text=ev['label'], font=("Arial", 16, "bold")).pack(pady=10)

        bd = ev['breakdown']
        if isinstance(bd, dict):
            # Render Dict
            txt = f"Total Dmg: {int(bd.get('final_damage', 0))}\n\n"
            txt += f"Base: {int(bd.get('base', 0))}\n"

            mods = bd.get('modifiers', {})
            if mods:
                txt += "\nModifiers:\n"
                for k, v in mods.items():
                    txt += f"  {k}: x{v:.2f}\n"

            flags = bd.get('flags', [])
            if flags:
                txt += f"\nFlags: {', '.join(flags)}\n"

            if 'extra_damage' in bd:
                txt += "\nExtra Events:\n"
                for extra in bd['extra_damage']:
                    txt += f"  {extra.get('name')}: {int(extra.get('damage', 0))}\n"
        else:
            txt = str(bd)

        lbl = ctk.CTkLabel(popup, text=txt, justify="left")
        lbl.pack(padx=20, pady=10)

    def _show_warning(self, msg):
        # Simple overlay warning or just print to console/status?
        # Let's flash status label
        old_text = self.status_label.cget("text")
        self.status_label.configure(text=msg, text_color="red")
        self.after(2000, lambda: self.status_label.configure(text=old_text, text_color="white"))
