import math
import os
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageTk

ROW_HEIGHT = 60
ROW_MARGIN = 10
# Removed global PIXELS_PER_SEC
ICON_SIZE = 40
LEFT_MARGIN = 150


class NativeTimelineWindow(ctk.CTkToplevel):
    def __init__(self, parent, timeline_data, assets_path="PPMonk/assets/abilityIcons"):
        super().__init__(parent)
        self.title("Combat Timeline Analysis")
        self.geometry("1400x500")

        self.data = timeline_data
        self.assets_path = assets_path
        self.icon_cache = {}

        # [Task 1: Zoom State]
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
        if self.pixels_per_sec < 200:
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
            'ToD': 'ability_monk_touchofdeath.jpg' # Assumption
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
                for f in files:
                    if spell_name.lower() in f.lower():
                        target_file = f
                        break

            if target_file:
                full_path = os.path.join(self.assets_path, target_file)
                try:
                    pil_img = Image.open(full_path)
                    pil_img = pil_img.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)
                    self.icon_cache[spell_name] = ImageTk.PhotoImage(pil_img)
                except Exception as exc:  # pragma: no cover - UI feedback only
                    print(f"Error loading {target_file}: {exc}")

    def _draw_scene(self):
        self.canvas.delete("all") # Clear previous

        groups = self.data.get('groups', [])
        items = self.data.get('items', [])

        max_time = max((i['start'] + i['duration']) for i in items) if items else 10
        canvas_width = LEFT_MARGIN + (max_time + 2) * self.pixels_per_sec
        canvas_height = len(groups) * (ROW_HEIGHT + ROW_MARGIN) + 50

        self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))

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
                10,
                y_start + ROW_HEIGHT / 2,
                text=group_name,
                fill="#cccccc",
                anchor="w",
                font=("Arial", 12, "bold"),
            )

        for t in range(math.ceil(max_time) + 2):
            x = LEFT_MARGIN + t * self.pixels_per_sec
            self.canvas.create_line(x, 0, x, canvas_height, fill="#444444", dash=(2, 4))
            self.canvas.create_text(x + 2, canvas_height - 20, text=f"{t}s", fill="#666", anchor="nw")

        for item in items:
            row = item.get('group_idx', 0)
            start_x = LEFT_MARGIN + item.get('start', 0) * self.pixels_per_sec
            width = item.get('duration', 0) * self.pixels_per_sec
            visual_width = max(width, ICON_SIZE + 10)
            y = row * (ROW_HEIGHT + ROW_MARGIN) + (ROW_HEIGHT - ICON_SIZE) / 2

            self.canvas.create_rectangle(
                start_x,
                y,
                start_x + visual_width,
                y + ICON_SIZE,
                fill=item.get('color', '#555555'),
                outline="#111",
                width=1,
            )

            spell_name = item.get('name')
            text_offset = 5
            if spell_name in self.icon_cache:
                self.canvas.create_image(
                    start_x + 2,
                    y,
                    image=self.icon_cache[spell_name],
                    anchor="nw",
                )
                text_offset = ICON_SIZE + 5

            label = f"{spell_name}\n{int(item.get('damage', 0))}"
            self.canvas.create_text(
                start_x + text_offset,
                y + ICON_SIZE / 2,
                text=label,
                fill="white",
                font=("Arial", 9),
                anchor="w",
            )
