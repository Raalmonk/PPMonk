import math
import os
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageTk

ROW_HEIGHT = 100
ROW_MARGIN = 10
ICON_SIZE = 64
LEFT_MARGIN = 200 # Increased margin for larger icons/text


class NativeTimelineWindow(ctk.CTkToplevel):
    def __init__(self, parent, timeline_data, assets_path="PPMonk/assets/abilityIcons"):
        super().__init__(parent)
        self.title("Combat Timeline Analysis")
        self.geometry("1600x600")

        self.data = timeline_data
        self.assets_path = assets_path
        self.icon_cache = {}

        self.pixels_per_sec = 80

        # Control Panel
        self.control_panel = ctk.CTkFrame(self, height=40)
        self.control_panel.pack(side="top", fill="x", padx=10, pady=5)

        ctk.CTkLabel(self.control_panel, text="Zoom:").pack(side="left", padx=5)
        ctk.CTkButton(self.control_panel, text="-", width=30, command=self._zoom_out).pack(side="left", padx=2)
        ctk.CTkButton(self.control_panel, text="+", width=30, command=self._zoom_in).pack(side="left", padx=2)
        self.zoom_label = ctk.CTkLabel(self.control_panel, text=f"{self.pixels_per_sec} px/s")
        self.zoom_label.pack(side="left", padx=5)

        self.scroll_frame = ctk.CTkFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.h_scrollbar = ctk.CTkScrollbar(self.scroll_frame, orientation="horizontal")
        self.h_scrollbar.pack(side="bottom", fill="x")

        self.canvas = tk.Canvas(
            self.scroll_frame,
            bg="#2b2b2b",
            highlightthickness=0,
            xscrollcommand=self.h_scrollbar.set,
        )
        self.canvas.pack(side="top", fill="both", expand=True)

        self.h_scrollbar.configure(command=self.canvas.xview)

        self._load_icons()
        self._draw_scene()

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

    def _zoom_in(self):
        if self.pixels_per_sec < 400:
            self.pixels_per_sec += 10
            self.zoom_label.configure(text=f"{self.pixels_per_sec} px/s")
            self._draw_scene()

    def _zoom_out(self):
        if self.pixels_per_sec > 20:
            self.pixels_per_sec -= 10
            self.zoom_label.configure(text=f"{self.pixels_per_sec} px/s")
            self._draw_scene()

    def _on_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def _load_icons(self):
        if not os.path.exists(self.assets_path):
            print(f"Assets path not found: {self.assets_path}")
            return

        file_map = {
            'RSK': 'ability_monk_risingsunkick.jpg',
            'FOF': 'monk_ability_fistoffury.jpg',
            'TP': 'ability_monk_tigerpalm.jpg',
            'SCK': 'ability_monk_cranekick_new.jpg',
            'BOK': 'ability_monk_roundhousekick.jpg',
            'WDP': 'ability_monk_hurricanestrike.jpg',
            'SOTWL': 'inv_hand_1h_artifactskywall_d_01.jpg',
            'SEF': 'spell_nature_giftofthewild.jpg',
            'Xuen': 'ability_monk_summontigerstatue.jpg',
            'ToD': 'ability_monk_touchofdeath.jpg',
            'Zenith': 'Xuen_SEF.jpg',
            'Conduit': 'ability_monk_dragonkick.jpg' # Assumption/Placeholder if needed
        }

        try:
            files = os.listdir(self.assets_path)
        except OSError as exc:
            print(f"Failed to list assets: {exc}")
            return

        lower_files = {f.lower(): f for f in files}

        for spell_name, filename in file_map.items():
            target_file = None
            lower_name = filename.lower()
            if lower_name in lower_files:
                target_file = lower_files[lower_name]
            else:
                # Fuzzy match attempt
                for f in files:
                    if spell_name.lower() in f.lower():
                        target_file = f
                        break

            # Zenith specific handling if file mapping failed but we want to ensure Xuen_SEF.jpg is used if present
            if spell_name == 'Zenith' and not target_file:
                 if 'xuen_sef.jpg' in lower_files:
                     target_file = lower_files['xuen_sef.jpg']

            if target_file:
                full_path = os.path.join(self.assets_path, target_file)
                try:
                    pil_img = Image.open(full_path)
                    pil_img = pil_img.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)
                    self.icon_cache[spell_name] = ImageTk.PhotoImage(pil_img)
                except Exception as exc:  # pragma: no cover
                    print(f"Error loading {target_file}: {exc}")

    def _draw_scene(self):
        self.canvas.delete("all")

        groups = self.data.get('groups', [])
        items = self.data.get('items', [])

        max_time = max((i['start'] + i['duration']) for i in items) if items else 10
        canvas_width = LEFT_MARGIN + (max_time + 2) * self.pixels_per_sec
        canvas_height = len(groups) * (ROW_HEIGHT + ROW_MARGIN) + 50

        self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))

        # Draw Lanes
        for idx, group_name in enumerate(groups):
            y_start = idx * (ROW_HEIGHT + ROW_MARGIN)
            self.canvas.create_rectangle(
                0,
                y_start,
                canvas_width,
                y_start + ROW_HEIGHT,
                fill="#333333",
                outline="",
            )
            self.canvas.create_rectangle(
                0,
                y_start,
                LEFT_MARGIN,
                y_start + ROW_HEIGHT,
                fill="#222222",
                outline="",
            )
            self.canvas.create_text(
                20,
                y_start + ROW_HEIGHT / 2,
                text=group_name,
                fill="#cccccc",
                anchor="w",
                font=("Arial", 14, "bold"),
            )

        # Draw Grid Lines
        for t in range(math.ceil(max_time) + 2):
            x = LEFT_MARGIN + t * self.pixels_per_sec
            self.canvas.create_line(x, 0, x, canvas_height, fill="#444444", dash=(2, 4))
            self.canvas.create_text(x + 2, canvas_height - 20, text=f"{t}s", fill="#666", anchor="nw")

        # Draw Items
        for item in items:
            row = item.get('group_idx', 0)
            start_x = LEFT_MARGIN + item.get('start', 0) * self.pixels_per_sec
            width = item.get('duration', 0) * self.pixels_per_sec
            visual_width = max(width, ICON_SIZE + 10)
            y = row * (ROW_HEIGHT + ROW_MARGIN) + (ROW_HEIGHT - ICON_SIZE) / 2

            tag = f"item_{item.get('start')}_{row}"

            self.canvas.create_rectangle(
                start_x,
                y,
                start_x + visual_width,
                y + ICON_SIZE,
                fill=item.get('color', '#555555'),
                outline="#111",
                width=1,
                tags=tag
            )

            spell_name = item.get('name')
            text_offset = 5
            if spell_name in self.icon_cache:
                self.canvas.create_image(
                    start_x + 2,
                    y,
                    image=self.icon_cache[spell_name],
                    anchor="nw",
                    tags=tag
                )
                text_offset = ICON_SIZE + 10

            # Label
            label_text = f"{spell_name}\n{int(item.get('damage', 0))}"
            self.canvas.create_text(
                start_x + text_offset,
                y + ICON_SIZE / 2,
                text=label_text,
                fill="white",
                font=("Arial", 14, "bold"),
                anchor="w",
                tags=tag
            )

            # Bind Tooltip
            if 'info' in item:
                self.canvas.tag_bind(tag, "<Button-1>", lambda e, n=spell_name, i=item['info']: self._show_tooltip(e, n, i))

    def _show_tooltip(self, event, name, info):
        top = ctk.CTkToplevel(self)
        top.title(f"Details: {name}")

        # Adaptive Geometry based on content length
        # But we use pack, so we can just set minsize or let it expand.
        # Requirement: "No scrolling".

        content_frame = ctk.CTkFrame(top)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(content_frame, text=f"Action: {name}", font=("Arial", 18, "bold")).pack(anchor="w")

        dmg_val = int(info.get('Damage', 0))
        ctk.CTkLabel(content_frame, text=f"Damage: {dmg_val}", font=("Arial", 16, "bold"), text_color="#E67E22").pack(anchor="w", pady=5)

        breakdown = info.get('Breakdown')
        text_info = ""

        if isinstance(breakdown, dict):
            # Formatted text
            text_info += f"Base Damage: {breakdown.get('base', 0)}\n\n"

            mods = breakdown.get('modifiers', [])
            if mods:
                text_info += "Modifiers:\n"
                if isinstance(mods, list):
                    for m in mods: text_info += f" • {m}\n"
                else:
                    for k,v in mods.items(): text_info += f" • {k}: x{v:.2f}\n"
                text_info += "\n"

            crit_src = breakdown.get('crit_sources', [])
            if crit_src:
                text_info += "Crit Sources:\n"
                for c in crit_src: text_info += f" • {c}\n"
                text_info += "\n"

            text_info += f"Final Crit Chance: {breakdown.get('final_crit', 0)*100:.1f}%\n"
            text_info += f"Crit Multiplier: {breakdown.get('crit_mult', 2.0):.2f}x\n"

            if 'targets' in breakdown:
                text_info += f"\nAOE: {breakdown.get('aoe_type')} ({breakdown.get('targets')} targets)\n"
                if 'total_dmg_after_aoe' in breakdown:
                     text_info += f"Total AOE Dmg: {int(breakdown['total_dmg_after_aoe'])}\n"

            if 'extra_events' in breakdown:
                text_info += "\nExtra Events:\n"
                for extra in breakdown['extra_events']:
                     text_info += f" • {extra['name']}: {int(extra.get('damage',0))}\n"

        else:
            text_info = str(breakdown)

        # Use Label instead of Textbox for auto-sizing without scrollbar if possible,
        # or a very large Textbox. Requirement: "wraplength increased... no scroll needed".

        # We can use a label with justify left.
        lbl = ctk.CTkLabel(content_frame, text=text_info, font=("Consolas", 16), justify="left", anchor="w", wraplength=800)
        lbl.pack(fill="both", expand=True)

        # Update geometry after pending
        top.update_idletasks()
        w = min(top.winfo_reqwidth() + 20, 1000)
        h = min(top.winfo_reqheight() + 20, 900)
        top.geometry(f"{w}x{h}")
