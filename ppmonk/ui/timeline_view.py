import math
import os
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageTk

# Task 1: UI Refactoring - Iconized Timeline
ROW_HEIGHT = 100
ROW_MARGIN = 10
ICON_SIZE = 64
LEFT_MARGIN = 200

class NativeTimelineWindow(ctk.CTkToplevel):
    def __init__(self, parent, timeline_data, assets_path="assets/abilityIcons"):
        super().__init__(parent)
        self.title("战斗时间轴分析")
        self.geometry("1600x800")

        self.data = timeline_data
        self.assets_path = assets_path
        self.icon_cache = {}

        self.pixels_per_sec = 80

        # Control Panel
        self.control_panel = ctk.CTkFrame(self, height=40)
        self.control_panel.pack(side="top", fill="x", padx=10, pady=5)

        ctk.CTkLabel(self.control_panel, text="缩放:").pack(side="left", padx=5)
        ctk.CTkButton(self.control_panel, text="-", width=30, command=self._zoom_out).pack(side="left", padx=2)
        ctk.CTkButton(self.control_panel, text="+", width=30, command=self._zoom_in).pack(side="left", padx=2)
        self.zoom_label = ctk.CTkLabel(self.control_panel, text=f"{self.pixels_per_sec} 像素/秒")
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
            self.zoom_label.configure(text=f"{self.pixels_per_sec} 像素/秒")
            self._draw_scene()

    def _zoom_out(self):
        if self.pixels_per_sec > 20:
            self.pixels_per_sec -= 10
            self.zoom_label.configure(text=f"{self.pixels_per_sec} 像素/秒")
            self._draw_scene()

    def _on_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def _load_icons(self):
        # Strict mapping as per Task 1
        icon_map = {
            'RSK': 'ability_monk_risingsunkick.jpg',
            'FOF': 'monk_ability_fistoffury.jpg',
            'SCK': 'ability_monk_cranekick_new.jpg',
            'TP': 'abilityIconsability_monk_tigerpalm.jpg.jpg', # Weird name matched
            'WDP': 'ability_monk_hurricanestrike.jpg',
            'SOTWL': 'inv_hand_1h_artifactskywall_d_01.jpg',
            'Zenith': 'Xuen_SEF.jpg', # SEF Icon
            'Xuen': 'ability_monk_summontigerstatue.jpg',
            'BOK': 'ability_monk_roundhousekick.jpg',
            'SW': 'ability_skyreach_wind_wall.jpg',
            'ToD': 'ability_monk_touchofdeath.jpg', # Extra for safety
            'Conduit': 'inv_ability_conduitofthecelestialsmonk_celestialconduit.jpg'
        }

        # Ensure assets path exists
        if not os.path.exists(self.assets_path):
             # Try absolute path from cwd
             self.assets_path = os.path.join(os.getcwd(), 'assets', 'abilityIcons')

        if not os.path.exists(self.assets_path):
            print(f"Assets path not found: {self.assets_path}")
            return

        for spell_name, filename in icon_map.items():
            full_path = os.path.join(self.assets_path, filename)
            if os.path.exists(full_path):
                try:
                    pil_img = Image.open(full_path)
                    pil_img = pil_img.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)
                    self.icon_cache[spell_name] = ImageTk.PhotoImage(pil_img)
                except Exception as e:
                    print(f"Error loading {spell_name}: {e}")
            else:
                print(f"Icon missing for {spell_name}: {full_path}")

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
            # Left Header
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
                font=("Arial", 16, "bold"), # Large font
            )

        # Draw Grid Lines
        for t in range(int(max_time) + 2):
            x = LEFT_MARGIN + t * self.pixels_per_sec
            self.canvas.create_line(x, 0, x, canvas_height, fill="#444444", dash=(2, 4))
            self.canvas.create_text(x + 2, canvas_height - 20, text=f"{t}s", fill="#666", anchor="nw")

        # Draw Items
        for item in items:
            row = item.get('group_idx', 0)
            start_x = LEFT_MARGIN + item.get('start', 0) * self.pixels_per_sec
            width = item.get('duration', 0) * self.pixels_per_sec
            # Ensure visible width
            visual_width = max(width, ICON_SIZE + 20)
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
            text_offset = 10

            # Draw Icon
            if spell_name in self.icon_cache:
                self.canvas.create_image(
                    start_x + 5,
                    y,
                    image=self.icon_cache[spell_name],
                    anchor="nw",
                    tags=tag
                )
                text_offset = ICON_SIZE + 15

            # Label - Large Bold Font
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
        top.title(f"详情: {name}")

        # Fixed large size to prevent truncation
        top.geometry("900x800")

        # Scrollable Frame for safety
        content_frame = ctk.CTkScrollableFrame(top)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(content_frame, text=f"动作: {name}", font=("Arial", 20, "bold")).pack(anchor="w", pady=5)

        dmg_val = int(info.get('Damage', 0))
        ctk.CTkLabel(content_frame, text=f"伤害: {dmg_val}", font=("Arial", 18, "bold"), text_color="#E67E22").pack(anchor="w", pady=5)

        breakdown = info.get('Breakdown')
        text_info = ""

        if isinstance(breakdown, dict):
            # Formatted text based on Task 2 structure
            if 'raw_base' in breakdown:
                 text_info += f"基础伤害: {breakdown['raw_base']:.1f}\n"
            if 'components' in breakdown:
                 text_info += f"公式: {breakdown['components']}\n\n"

            mods = breakdown.get('modifiers', [])
            if mods:
                text_info += "修正:\n"
                if isinstance(mods, list):
                    for m in mods: text_info += f" • {m}\n"
                text_info += "\n"

            crit_src = breakdown.get('crit_sources', [])
            if crit_src:
                text_info += "暴击来源:\n"
                for c in crit_src: text_info += f" • {c}\n"
                text_info += "\n"

            text_info += f"最终暴击率: {breakdown.get('final_crit', 0)*100:.1f}%\n"
            text_info += f"暴击倍率: {breakdown.get('crit_mult', 2.0):.2f}x\n"
            text_info += f"是否暴击: {breakdown.get('is_crit', False)}\n"

            if 'snapshot_dmg' in breakdown:
                 text_info += f"\n快照伤害: {breakdown['snapshot_dmg']:.1f}\n"
            if 'expected_dmg' in breakdown:
                 text_info += f"期望伤害: {breakdown['expected_dmg']:.1f}\n"

            if 'extra_events' in breakdown:
                text_info += "\n额外事件:\n"
                for extra in breakdown['extra_events']:
                     text_info += f" • {extra['name']}: {int(extra.get('damage',0))}\n"

        else:
            text_info = str(breakdown)

        lbl = ctk.CTkLabel(content_frame, text=text_info, font=("Consolas", 14), justify="left", anchor="w")
        lbl.pack(fill="both", expand=True)

