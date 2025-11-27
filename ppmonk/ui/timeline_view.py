import math
import os
import tkinter as tk
import textwrap

import customtkinter as ctk
from PIL import Image, ImageTk

ROW_HEIGHT = 100
ROW_MARGIN = 10
ICON_SIZE = 64
LEFT_MARGIN = 150
DEFAULT_PIXELS_PER_SEC = 80


class NativeTimelineWindow(ctk.CTkToplevel):
    def __init__(self, parent, timeline_data, assets_path="assets/abilityIcons"):
        super().__init__(parent)
        self.title("Combat Timeline Analysis")
        self.geometry("1400x500")

        self.data = timeline_data
        self.assets_path = assets_path
        self.icon_cache = {}

        # [Task 1: Zoom State]
        self.pixels_per_sec = DEFAULT_PIXELS_PER_SEC

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
            self.pixels_per_sec += 20
            self.zoom_label.configure(text=f"{self.pixels_per_sec} px/s")
            self._draw_scene()

    def _zoom_out(self):
        if self.pixels_per_sec > 40:
            self.pixels_per_sec -= 20
            self.zoom_label.configure(text=f"{self.pixels_per_sec} px/s")
            self._draw_scene()

    def _on_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def _load_icons(self):
        if not os.path.exists(self.assets_path):
            print(f"Assets path not found: {self.assets_path}")
            return

        # Map abbreviations to likely filenames
        # Priority: Exact match from map > Partial match in filename
        file_map = {
            'RSK': 'ability_monk_risingsunkick',
            'FOF': 'monk_ability_fistoffury',
            'TP': 'ability_monk_tigerpalm',
            'SCK': 'ability_monk_cranekick_new',
            'BOK': 'ability_monk_roundhousekick',
            'WDP': 'ability_monk_hurricanestrike',
            'SOTWL': 'inv_hand_1h_artifactskywall_d_01',
            'SEF': 'spell_nature_giftofthewild',  # Per task requirement: Zenith uses Gift of the Wild icon?
                                                  # Wait, SEF is Storm Earth Fire. Zenith is 'Zenith'.
                                                  # Task says: "For Zenith use spell_nature_giftofthewild.jpg"
            'Zenith': 'spell_nature_giftofthewild',
            'Xuen': 'ability_monk_summontigerstatue',
            'ToD': 'ability_monk_touchofdeath',
            'Expel Harm': 'ability_monk_expelharm',
            'CJL': 'ability_monk_cracklingjadelineing',
            'Vivify': 'ability_monk_vivify',
            'FLS': 'ability_monk_rushingjadewind', # Faeline Stomp / Jadefire Stomp?
            'JFS': 'ability_monk_rushingjadewind',
            'CB': 'ability_monk_chiburst',
            'CW': 'ability_monk_chiwave',
        }

        try:
            files = os.listdir(self.assets_path)
        except OSError as exc:
            print(f"Failed to list assets: {exc}")
            return

        # Normalize file list for case-insensitive matching
        lower_files = {f.lower(): f for f in files}

        def find_icon_file(key):
            # Check map first
            if key in file_map:
                target_base = file_map[key].lower()
                # Try adding .jpg
                if f"{target_base}.jpg" in lower_files:
                    return lower_files[f"{target_base}.jpg"]
                # Try exact match if user put extension in map
                if target_base in lower_files:
                    return lower_files[target_base]

            # Fallback: fuzzy search
            key_lower = key.lower()
            for f_lower, f_real in lower_files.items():
                if key_lower in f_lower and '.jpg' in f_lower:
                    return f_real
            return None

        # Pre-load icons for known keys and anything in data if needed
        # We'll just load everything we can map
        keys_to_load = list(file_map.keys())

        # Also, scan data to see what spells we actually have?
        # Ideally we load on demand or load all map keys.
        # Let's load map keys.

        for key in keys_to_load:
            filename = find_icon_file(key)
            if filename:
                full_path = os.path.join(self.assets_path, filename)
                try:
                    pil_img = Image.open(full_path)
                    pil_img = pil_img.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)
                    self.icon_cache[key] = ImageTk.PhotoImage(pil_img)
                except Exception as exc:
                    print(f"Error loading {filename}: {exc}")

    def _draw_scene(self):
        self.canvas.delete("all")  # Clear previous

        groups = self.data.get('groups', [])
        items = self.data.get('items', [])

        # Calculate canvas dimensions
        max_time = max((i['start'] + i['duration']) for i in items) if items else 10
        canvas_width = LEFT_MARGIN + (max_time + 2) * self.pixels_per_sec
        canvas_height = len(groups) * (ROW_HEIGHT + ROW_MARGIN) + 50

        self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))

        # Draw backgrounds and labels
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
            # Row Header
            self.canvas.create_rectangle(
                0,
                y_start,
                LEFT_MARGIN,
                y_start + ROW_HEIGHT,
                fill="#222222",
                outline="",
            )
            self.canvas.create_text(
                10,
                y_start + ROW_HEIGHT / 2,
                text=group_name,
                fill="#cccccc",
                anchor="w",
                font=("Arial", 14, "bold"), # Increased font size
            )

        # Draw Grid Lines and Time Labels
        for t in range(math.ceil(max_time) + 2):
            x = LEFT_MARGIN + t * self.pixels_per_sec
            self.canvas.create_line(x, 0, x, canvas_height, fill="#444444", dash=(2, 4))
            self.canvas.create_text(x + 2, canvas_height - 20, text=f"{t}s", fill="#666", anchor="nw", font=("Arial", 12))

        # Draw Items
        for item in items:
            row = item.get('group_idx', 0)
            start_x = LEFT_MARGIN + item.get('start', 0) * self.pixels_per_sec
            duration = item.get('duration', 0)
            width = duration * self.pixels_per_sec

            # Ensure minimum visual width for visibility
            visual_width = max(width, ICON_SIZE + 40)

            y = row * (ROW_HEIGHT + ROW_MARGIN) + (ROW_HEIGHT - ICON_SIZE) / 2

            # Spell Bar Background
            item_id = self.canvas.create_rectangle(
                start_x,
                y,
                start_x + visual_width,
                y + ICON_SIZE,
                fill=item.get('color', '#555555'),
                outline="#111",
                width=1,
            )

            spell_name = item.get('name', 'Unknown')
            text_offset = 10

            # Draw Icon if available
            if spell_name in self.icon_cache:
                self.canvas.create_image(
                    start_x + 2,
                    y,
                    image=self.icon_cache[spell_name],
                    anchor="nw",
                )
                text_offset = ICON_SIZE + 10

            # Draw Text
            dmg_val = int(item.get('damage', 0))
            label_text = f"{spell_name}"
            if dmg_val > 0:
                 label_text += f"\n{dmg_val}"

            self.canvas.create_text(
                start_x + text_offset,
                y + ICON_SIZE / 2,
                text=label_text,
                fill="white",
                font=("Arial", 14, "bold"), # Increased font size
                anchor="w",
            )

            # Tooltip binding
            self.canvas.tag_bind(item_id, "<Enter>", lambda e, i=item: self._show_tooltip(e, i))
            self.canvas.tag_bind(item_id, "<Leave>", self._hide_tooltip)

    def _show_tooltip(self, event, item):
        if hasattr(self, 'tooltip_window') and self.tooltip_window:
            self.tooltip_window.destroy()

        self.tooltip_window = ctk.CTkToplevel(self)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{event.x_root + 15}+{event.y_root + 15}")

        frame = ctk.CTkFrame(self.tooltip_window, corner_radius=5, fg_color="#222222", border_color="#555", border_width=1)
        frame.pack()

        # Build detailed text
        lines = [f"Spell: {item.get('name')}", f"Time: {item.get('start'):.2f}s"]
        if item.get('damage'):
            lines.append(f"Damage: {item.get('damage'):.0f}")

        breakdown = item.get('breakdown')
        if breakdown:
            lines.append("-" * 20)
            if isinstance(breakdown, dict):
                 for k, v in breakdown.items():
                    lines.append(f"{k}: {v}")
            else:
                 lines.append(str(breakdown))

        full_text = "\n".join(lines)

        label = ctk.CTkLabel(
            frame,
            text=full_text,
            text_color="#eee",
            justify="left",
            font=("Consolas", 16), # Increased font size for tooltip
            wraplength=600  # Increased wraplength
        )
        label.pack(padx=10, pady=5)

    def _hide_tooltip(self, event):
        if hasattr(self, 'tooltip_window') and self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
