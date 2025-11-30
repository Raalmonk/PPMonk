import customtkinter as ctk
import tkinter as tk
import json
import random
import os
from PIL import Image, ImageTk

from ppmonk.core.player import PlayerState
from ppmonk.core.spell_book import SpellBook

# --- Localization & Config ---

SPELL_LOCALIZATION = {
    'TP': '猛虎掌 (Tiger Palm)',
    'BOK': '幻灭踢 (Blackout Kick)',
    'RSK': '旭日东升踢 (Rising Sun Kick)',
    'FOF': '怒雷破 (Fists of Fury)',
    'SCK': '神鹤引项踢 (Spinning Crane Kick)',
    'WDP': '升龙霸 (Whirling Dragon Punch)',
    'SOTWL': '风击 (Strike of the Windlord)',
    'SW': '切削之风 (Slicing Winds)',
    'Xuen': '召唤白虎 (Invoke Xuen)',
    'Zenith': '顶峰 (Zenith)',
    'ToD': '轮回之触 (Touch of Death)',
    'Conduit': '天神御身 (Celestial Conduit)',
    'WAIT_0_5': '等待 0.5s',
    'CMD_RESET_RSK': '指令: 重置 RSK',
    'CMD_COMBO_BREAKER': '指令: 免费幻灭踢'
}

SPELL_GROUPS = [
    ("爆发技能 (Major Cooldowns)", ["Zenith", "Xuen", "Conduit", "ToD"]),
    ("小爆发 (Minor Cooldowns)", ["SOTWL", "WDP", "SW"]),
    ("主要填充 (Major Fillers)", ["FOF", "RSK"]),
    ("基础技能 (Basic Fillers)", ["SCK", "TP", "BOK"]),
    ("控制 & 指令 (Control)", ["WAIT_0_5", "CMD_RESET_RSK", "CMD_COMBO_BREAKER"]),
    ("近战攻击 (Melee)", ["Auto Attack", "AA"]),
    ("特殊事件 (Special Events)", ["Expel Harm", "Flurry Strikes", "Shado Over Battlefield", "High Impact", "Niuzao Stomp", "Jade Ignition", "Glory of Dawn", "Zenith Blast", "Courage of White Tiger", "TotM Hits"])
]

GCD_FREE_SPELLS = ["Zenith", "CMD_RESET_RSK", "CMD_COMBO_BREAKER"]

# Friendly Names for Internal Events
EVENT_NAME_MAP = {
    'passive': '自动攻击 (Auto Attack)',
    'active': '技能直伤',
    'tick': '周期性伤害 (DoT)',
    'cast_extra': '额外效果',
    'Auto Attack': '自动攻击 (Auto Attack)'
}

ICON_SIZE_PALETTE = 32
ICON_SIZE_TIMELINE = 48
ROW_HEIGHT = 80
HEADER_WIDTH = 200
PIXELS_PER_SECOND = 60 # Time scale

class DraggableBlock:
    def __init__(self, canvas, item_id, data, on_click, on_drag_end, on_right_click):
        self.canvas = canvas
        self.item_id = item_id # Canvas ID (tag)
        self.data = data # Dictionary with spell info
        self.on_click = on_click
        self.on_drag_end = on_drag_end
        self.on_right_click = on_right_click

        self.start_x = 0
        self.dragging = False

        self.canvas.tag_bind(item_id, "<Button-1>", self._on_press)
        self.canvas.tag_bind(item_id, "<B1-Motion>", self._on_drag)
        self.canvas.tag_bind(item_id, "<ButtonRelease-1>", self._on_release)
        self.canvas.tag_bind(item_id, "<Button-3>", self._on_right_click)

    def _on_press(self, event):
        self.start_x = event.x
        self.dragging = False
        self.on_click(self.data) # Show info

    def _on_drag(self, event):
        if not self.dragging:
            self.dragging = True
            self.canvas.lift(self.item_id) # Bring to front

        dx = event.x - self.start_x
        self.canvas.move(self.item_id, dx, 0)
        self.start_x = event.x

    def _on_release(self, event):
        if self.dragging:
            self.on_drag_end(self.item_id, event.x) # Pass final X to calculate new index
        self.dragging = False

    def _on_right_click(self, event):
        self.on_right_click(self.data)

class SandboxWindow(ctk.CTkToplevel):
    def __init__(self, parent, active_talents=None, player_stats=None):
        super().__init__(parent)
        self.title("手动沙盒 (Sequence Editor)")
        self.geometry("1400x900")

        self.active_talents = active_talents if active_talents else []
        self.player_stats = player_stats if player_stats else {}

        # Initialize target_count
        self.target_count = ctk.IntVar(value=1)
        self.weapon_type = ctk.StringVar(value="dw") # Default Dual Wield

        # Core Data Structure
        self.action_sequence = [] # List of dicts: {'name': 'RSK', 'settings': {}, 'uuid': ...}

        # Temporary State for Simulation
        self.sim_player = None
        self.sim_spell_book = None
        self.icon_cache = {}
        self.simulation_events = [] # Stores derived events: (name, time, damage)
        self.sequence_time_map = [] # [(item, start_time, end_time), ...]

        # State Snapshots for Cursor
        self.state_snapshots = [] # [(timestamp, state_dict), ...]
        self.palette_buttons = {} # Stores references to palette buttons

        # UI Constants
        self.block_height = 60
        self.block_map = {}

        # Cursor
        self.cursor_id = None
        self.is_dragging_cursor = False

        self._load_icons()
        self._init_spellbook()
        self._build_ui()
        self._recalculate_timeline()

    def _load_icons(self):
        # Mapping from spell abbr to filename (copied/adapted from timeline_view.py)
        icon_map = {
            'RSK': 'ability_monk_risingsunkick.jpg',
            'FOF': 'monk_ability_fistoffury.jpg',
            'SCK': 'ability_monk_cranekick_new.jpg',
            'TP': 'ability_monk_tigerpalm.jpg',
            'WDP': 'ability_monk_hurricanestrike.jpg',
            'SOTWL': 'inv_hand_1h_artifactskywall_d_01.jpg',
            'Zenith': 'spell_nature_giftofthewild.jpg',
            'Xuen': 'ability_monk_summontigerstatue.jpg',
            'BOK': 'ability_monk_roundhousekick.jpg',
            'SW': 'ability_skyreach_wind_wall.jpg',
            'ToD': 'ability_monk_touchofdeath.jpg',
            'Conduit': 'inv_ability_conduitofthecelestialsmonk_celestialconduit.jpg'
        }

        # Use relative path from this file location for safety
        assets_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'abilityIcons')
        assets_path = os.path.normpath(assets_path)

        for key, filename in icon_map.items():
            full_path = os.path.join(assets_path, filename)
            if os.path.exists(full_path):
                try:
                    # Load and resize for Palette
                    img = Image.open(full_path)
                    self.icon_cache[f"{key}_palette"] = ctk.CTkImage(light_image=img, dark_image=img, size=(ICON_SIZE_PALETTE, ICON_SIZE_PALETTE))

                    # Load and resize for Timeline (Canvas uses ImageTk)
                    img_tm = img.resize((ICON_SIZE_TIMELINE, ICON_SIZE_TIMELINE), Image.Resampling.LANCZOS)
                    self.icon_cache[f"{key}_timeline"] = ImageTk.PhotoImage(img_tm)
                except Exception as e:
                    print(f"Error loading icon {key}: {e}")

    def _init_spellbook(self):
        self.ref_player = PlayerState() # Dummy
        # Apply weapon type to ref player for CD calcs if needed (mostly haste affects CD)
        self.ref_player.weapon_type = self.weapon_type.get()
        self.ref_spell_book = SpellBook(active_talents=self.active_talents)
        self.ref_spell_book.apply_talents(self.ref_player)

    def _build_ui(self):
        # --- Top Controls ---
        top_panel = ctk.CTkFrame(self)
        top_panel.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(top_panel, text="清空序列 (Clear)", fg_color="#C0392B", command=self._clear_sequence).pack(side="left", padx=5)
        ctk.CTkButton(top_panel, text="导出 JSON", command=self._export_json).pack(side="left", padx=5)
        ctk.CTkButton(top_panel, text="导入 JSON", command=self._import_json).pack(side="left", padx=5)

        # Resource Display (Task: Energy / Chi)
        self.resource_label = ctk.CTkLabel(top_panel, text="预计结束资源: Energy 0 | Chi 0", font=("Arial", 12, "bold"), text_color="#F1C40F")
        self.resource_label.pack(side="left", padx=20)

        self.stats_label = ctk.CTkLabel(top_panel, text="总伤害: 0 | DPS: 0", font=("Arial", 14, "bold"))
        self.stats_label.pack(side="right", padx=20)

        # --- Stat Editors ---
        stats_frame = ctk.CTkFrame(self)
        stats_frame.pack(fill="x", padx=10, pady=5)

        self.stat_inputs = {}
        stat_defs = [
            ("agility", "敏捷", 2000),
            ("crit_rating", "暴击", 2000),
            ("haste_rating", "急速", 1500),
            ("mastery_rating", "精通", 1000),
            ("vers_rating", "全能", 500)
        ]

        for key, label, default in stat_defs:
            val = self.player_stats.get(key, default)

            f = ctk.CTkFrame(stats_frame, fg_color="transparent")
            f.pack(side="left", padx=10)

            ctk.CTkLabel(f, text=label).pack(side="left", padx=2)

            var = ctk.StringVar(value=str(int(val)))
            entry = ctk.CTkEntry(f, width=60, textvariable=var)
            entry.pack(side="left", padx=2)
            entry.bind("<Return>", lambda e: self._recalculate_timeline())
            entry.bind("<FocusOut>", lambda e: self._recalculate_timeline())

            self.stat_inputs[key] = var

        # Target Count
        f_target = ctk.CTkFrame(stats_frame, fg_color="transparent")
        f_target.pack(side="left", padx=10)
        ctk.CTkLabel(f_target, text="目标数").pack(side="left", padx=2)
        target_entry = ctk.CTkEntry(f_target, width=40, textvariable=self.target_count)
        target_entry.pack(side="left", padx=2)
        target_entry.bind("<Return>", lambda e: self._recalculate_timeline())
        target_entry.bind("<FocusOut>", lambda e: self._recalculate_timeline())

        # Weapon Toggle
        f_wep = ctk.CTkFrame(stats_frame, fg_color="transparent")
        f_wep.pack(side="left", padx=10)
        ctk.CTkLabel(f_wep, text="武器类型:").pack(side="left", padx=2)

        self.wep_switch = ctk.CTkSwitch(f_wep, text="双持 (DW)", variable=self.weapon_type, onvalue="dw", offvalue="2h", command=self._on_weapon_change)
        # Note: switch usually toggles. If text is static, better use separate label or dynamic text.
        # But for now "DW" is ON, "2H" is OFF.
        # Let's adjust text to reflect state or just say "双持" (Dual Wield)
        self.wep_switch.pack(side="left", padx=2)

        # --- Main Content ---
        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=10, pady=5)

        # Left: Spell Palette (Categorized)
        palette_frame = ctk.CTkFrame(content, width=280)
        palette_frame.pack(side="left", fill="y", padx=5, pady=5)

        ctk.CTkLabel(palette_frame, text="技能面板 (Palette)", font=("Arial", 16, "bold")).pack(pady=10)
        self.palette_scroll = ctk.CTkScrollableFrame(palette_frame, width=260)
        self.palette_scroll.pack(fill="both", expand=True)

        self._populate_palette()

        # Right: Sequence View
        seq_frame = ctk.CTkFrame(content)
        seq_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(seq_frame, text="动作序列 (拖拽排序, 右键删除)", font=("Arial", 14)).pack(pady=5)

        self.canvas_container = ctk.CTkFrame(seq_frame)
        self.canvas_container.pack(fill="both", expand=True)

        h_scroll = tk.Scrollbar(self.canvas_container, orient="horizontal")
        v_scroll = tk.Scrollbar(self.canvas_container, orient="vertical") # Added Vertical Scroll

        self.canvas = tk.Canvas(self.canvas_container, bg="#2B2B2B", height=400,
                                xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        h_scroll.config(command=self.canvas.xview)
        v_scroll.config(command=self.canvas.yview)

        h_scroll.pack(side="bottom", fill="x")
        v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="top", fill="both", expand=True)

        # Bind events for cursor dragging
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # Info Box / Inspector
        self.info_box = ctk.CTkTextbox(seq_frame, height=200) # Increased height for Inspector
        self.info_box.pack(fill="x", pady=5)
        self.info_box.insert("1.0", "点击方块查看详情，或拖动竖线查看状态...")
        self.info_box.configure(state="disabled")

    def _on_weapon_change(self):
        # Update switch text for clarity
        if self.weapon_type.get() == "dw":
            self.wep_switch.configure(text="双持 (DW)")
        else:
            self.wep_switch.configure(text="双手 (2H)")
        self._recalculate_timeline()

    def _populate_palette(self):
        # Clear existing
        for widget in self.palette_scroll.winfo_children():
            widget.destroy()

        self.palette_buttons = {} # Clear references

        # Re-calc reference player stats for CD display
        try:
            haste = float(self.stat_inputs['haste_rating'].get())
        except:
            haste = 1500.0

        # Update ref player stats from sim player (if available) or defaults
        if self.sim_player:
             self.ref_player.haste = self.sim_player.haste
        else:
             self.ref_player.haste = 1.0 + (haste / 17000.0)

        for group_name, spell_keys in SPELL_GROUPS:
            # Header
            ctk.CTkLabel(self.palette_scroll, text=group_name, font=("Arial", 12, "bold"), text_color="#bdc3c7").pack(pady=(10, 2), anchor="w")

            for key in spell_keys:
                if key.startswith("CMD_") or key == "WAIT_0_5":
                    # Commands
                    display_name = SPELL_LOCALIZATION.get(key, key)
                    btn = ctk.CTkButton(self.palette_scroll, text=display_name, fg_color="#555555",
                                        command=lambda k=key: self._add_to_sequence(k))
                    btn.pack(pady=2, padx=5, fill="x")
                elif key in self.ref_spell_book.spells:
                     spell = self.ref_spell_book.spells[key]
                     if spell.is_known:
                         display_name = SPELL_LOCALIZATION.get(key, spell.name)

                         # Initial CD Display (Base) - Dynamic updates will handle cursor time
                         # cd_text = f" ({spell.get_effective_cd(self.ref_player):.1f}s)" if spell.base_cd > 0 else ""
                         # User feedback: fixed numbers confusing. Let's just show Name initially.

                         icon = self.icon_cache.get(f"{key}_palette", None)

                         btn = ctk.CTkButton(self.palette_scroll,
                                             text=f" {display_name}",
                                             image=icon,
                                             compound="left",
                                             anchor="w",
                                             command=lambda k=key: self._add_to_sequence(k))
                         btn.pack(pady=2, padx=5, fill="x")
                         self.palette_buttons[key] = btn

    def _add_to_sequence(self, spell_key):
        item = {
            'name': spell_key,
            'settings': {},
            'uuid': random.randint(0, 1000000)
        }
        self.action_sequence.append(item)
        self._recalculate_timeline()

    def _clear_sequence(self):
        self.action_sequence = []
        self._recalculate_timeline()

    def _remove_item(self, data):
        if data in self.action_sequence:
            self.action_sequence.remove(data)
            self._recalculate_timeline()

    def _on_canvas_click(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        self._update_cursor(canvas_x)
        self.is_dragging_cursor = True

    def _on_canvas_drag(self, event):
        if self.is_dragging_cursor:
            canvas_x = self.canvas.canvasx(event.x)
            self._update_cursor(canvas_x)

    def _on_canvas_release(self, event):
        self.is_dragging_cursor = False

    def _update_cursor(self, x):
        # Constrain
        x = max(HEADER_WIDTH + 10, x)

        # Move visual line
        if not self.cursor_id:
            total_height = len(SPELL_GROUPS) * ROW_HEIGHT
            self.cursor_id = self.canvas.create_line(x, 0, x, total_height, fill="white", width=2, dash=(4, 2))
        else:
            self.canvas.coords(self.cursor_id, x, 0, x, len(SPELL_GROUPS) * ROW_HEIGHT)
            self.canvas.lift(self.cursor_id)

        # Calculate Time
        relative_x = x - (HEADER_WIDTH + 10)
        time = relative_x / PIXELS_PER_SECOND

        self._show_state_at_time(time)

    def _show_state_at_time(self, time):
        if not self.state_snapshots:
            return

        closest = self.state_snapshots[0]
        for snap in self.state_snapshots:
            if snap['time'] > time:
                break
            closest = snap

        # Update Info Box
        state = closest['state']
        text = f"--- 状态监视器 (Time: {time:.2f}s) ---\n"
        text += f"能量: {int(state['energy'])} / {int(state['max_energy'])}\n"
        text += f"真气: {state['chi']}\n"
        text += f"连击层数: {state.get('hit_combo', 0)}\n"

        if state.get('buffs'):
            text += "\nBuffs:\n"
            for b, d in state['buffs'].items():
                text += f"  {b}: {d:.1f}s\n"

        self.info_box.configure(state="normal")
        self.info_box.delete("1.0", "end")
        self.info_box.insert("1.0", text)
        self.info_box.configure(state="disabled")

        # Update Palette Buttons with CD info
        spell_states = closest.get('spells', {})
        for key, btn in self.palette_buttons.items():
            if key in spell_states:
                cd_rem = spell_states[key]['cd']
                charges = spell_states[key]['charges']
                max_charges = spell_states[key]['max_charges']

                display_name = SPELL_LOCALIZATION.get(key, key)
                status_text = ""

                if cd_rem > 0 and charges < max_charges:
                    status_text = f" ({cd_rem:.1f}s)"
                    btn.configure(fg_color="#555555") # Dim
                else:
                    if max_charges > 1:
                        status_text = f" ({charges}/{max_charges})"
                    btn.configure(fg_color="#2E86C1") # Active color (or default)

                # Check resource availability (rough check)
                # Need costs from Spell object, but we only have snapshots here.
                # Just CD display is a big improvement.

                btn.configure(text=f" {display_name}{status_text}")

    def _capture_state_snapshot(self, time):
        p = self.sim_player
        buffs = {}
        if p.xuen_active: buffs['Xuen'] = p.xuen_duration
        if p.zenith_active: buffs['Zenith'] = p.zenith_duration
        if p.dance_of_chiji_stacks > 0: buffs[f'DanceOfChiJi ({p.dance_of_chiji_stacks})'] = p.dance_of_chiji_duration
        if p.combo_breaker_stacks > 0: buffs[f'ComboBreaker ({p.combo_breaker_stacks})'] = 15.0 # Dummy
        if p.rwk_ready: buffs['RWK Ready'] = 0.0

        # Capture Spell CDs
        spell_states = {}
        if self.sim_spell_book:
            for s_key, s in self.sim_spell_book.spells.items():
                spell_states[s_key] = {
                    'cd': s.current_cd,
                    'charges': s.charges,
                    'max_charges': s.max_charges
                }

        return {
            'time': time,
            'state': {
                'energy': p.energy,
                'max_energy': p.max_energy,
                'chi': p.chi,
                'hit_combo': p.hit_combo_stacks,
                'buffs': buffs
            },
            'spells': spell_states
        }

    def _on_block_click(self, data):
        # Show details in info box
        if 'event_info' in data:
             evt = data['event_info']
             # Map Source Name
             src_name = evt['name']
             friendly_name = EVENT_NAME_MAP.get(src_name, src_name)
             if src_name == 'passive': friendly_name = EVENT_NAME_MAP['passive']

             text = f"Event: {friendly_name}\n"
             text += f"Time: {evt['time']:.2f}s\n"
             text += f"Damage: {int(evt['damage'])}\n"
        else:
            display_name = SPELL_LOCALIZATION.get(data['name'], data['name'])
            text = f"Action: {display_name}\n"
            if 'error' in data:
                text += f"ERROR: {data['error']}\n"

            if 'sim_result' in data:
                res = data['sim_result']
                text += f"Damage: {int(res['damage'])}\n"
                text += f"Time: {res['timestamp']:.2f}s\n"

                if data['name'] == 'FOF':
                    total_fof_dmg = res['damage']
                    text += f"\n总伤害 (整合): {int(total_fof_dmg)}\n"
                    text += "详细跳数 (分开):\n"
                    if 'breakdown' in res:
                        bd = res['breakdown']
                        if 'raw_base' in bd:
                            text += f"  Channel Dmg: {int(bd.get('total_dmg_after_aoe', 0))}\n"
                        if 'extra_events' in bd:
                            for evt in bd['extra_events']:
                                text += f"  {evt['name']}: {int(evt['damage'])}\n"

                if 'breakdown' in res:
                    bd = res['breakdown']
                    text += f"\nBreakdown:\n"
                    for k, v in bd.items():
                        if k == 'modifiers':
                             text += f"  Modifiers: {', '.join(v)}\n"
                        elif k == 'crit_sources':
                             text += f"  Crit Sources: {', '.join(v)}\n"
                        else:
                             text += f"  {k}: {v}\n"

        self.info_box.configure(state="normal")
        self.info_box.delete("1.0", "end")
        self.info_box.insert("1.0", text)
        self.info_box.configure(state="disabled")

    def _on_drag_end(self, item_id, final_x):
        # Time-based insertion
        scroll_x = self.canvas.canvasx(final_x)
        effective_x = scroll_x - HEADER_WIDTH
        if effective_x < 0: effective_x = 0

        target_time = effective_x / PIXELS_PER_SECOND

        target_data = self.block_map.get(item_id)
        if not target_data or target_data not in self.action_sequence:
            return

        # Find closest insertion index based on time
        # We look at sequence_time_map: [(item, start, end), ...]
        new_index = len(self.action_sequence)

        min_dist = 999999
        best_idx = 0

        # Check insertion before first item
        if not self.sequence_time_map:
            best_idx = 0
        else:
            # Check positions: Before item 0, After item 0, After item 1...
            # Positions are roughly: item[i].start_time
            # Actually we want to insert where the gap is or where closest item starts

            # Simple heuristic: insert before the item whose start_time is closest to target_time?
            # Or item whose center is closest?
            # Let's iterate through start times

            # Add a dummy end time for the last slot
            last_end = self.sequence_time_map[-1][2]
            check_points = [x[1] for x in self.sequence_time_map] + [last_end]

            for i, time_point in enumerate(check_points):
                dist = abs(target_time - time_point)
                if dist < min_dist:
                    min_dist = dist
                    best_idx = i

        new_index = best_idx

        current_index = self.action_sequence.index(target_data)
        if new_index != current_index:
             # Adjust index because popping changes subsequent indices
             if new_index > current_index:
                 new_index -= 1

             self.action_sequence.insert(new_index, self.action_sequence.pop(current_index))
             self._recalculate_timeline()
        else:
             self._draw_sequence() # Snap back

    def _export_json(self):
        out = json.dumps(self.action_sequence, indent=2)
        print("EXPORT JSON:")
        print(out)
        self.info_box.configure(state="normal")
        self.info_box.delete("1.0", "end")
        self.info_box.insert("1.0", "Check Console for JSON Output (or copy here):\n" + out)
        self.info_box.configure(state="disabled")

    def _import_json(self):
        dialog = ctk.CTkInputDialog(text="Paste JSON here:", title="Import Sequence")
        txt = dialog.get_input()
        if txt:
            try:
                data = json.loads(txt)
                if isinstance(data, list):
                    self.action_sequence = data
                    self._recalculate_timeline()
            except Exception as e:
                print(f"Import failed: {e}")

    def _recalculate_timeline(self):
        # 1. Reset Simulation with Stats from Inputs
        try:
            agi = float(self.stat_inputs['agility'].get())
            crit = float(self.stat_inputs['crit_rating'].get())
            haste = float(self.stat_inputs['haste_rating'].get())
            mastery = float(self.stat_inputs['mastery_rating'].get())
            vers = float(self.stat_inputs['vers_rating'].get())
        except ValueError:
            agi, crit, haste, mastery, vers = 2000, 2000, 1500, 1000, 500

        self.sim_player = PlayerState(
            agility=agi,
            rating_crit=crit,
            rating_haste=haste,
            rating_mastery=mastery,
            rating_vers=vers,
            weapon_type=self.weapon_type.get()
        )
        self.sim_player.target_count = self.target_count.get()

        self.sim_spell_book = SpellBook(active_talents=self.active_talents)
        self.sim_spell_book.apply_talents(self.sim_player)

        time_elapsed = 0.0
        total_damage = 0.0
        self.simulation_events = [] # Clear events
        self.sequence_time_map = [] # Clear time map
        self.state_snapshots = [] # Clear snapshots

        # Initial snapshot
        self.state_snapshots.append(self._capture_state_snapshot(0.0))

        next_cast_force_reset = False
        next_cast_force_cb = False

        # 2. Iterate Sequence
        for item in self.action_sequence:
            name = item['name']
            start_time = time_elapsed

            item.pop('error', None)
            item.pop('sim_result', None)

            if name == "WAIT_0_5":
                self.sim_player.advance_time(0.5)
                self.sim_spell_book.tick(0.5)
                time_elapsed += 0.5
                item['sim_result'] = {'damage': 0, 'timestamp': time_elapsed, 'breakdown': 'Wait 0.5s', 'duration': 0.5}
                self.sequence_time_map.append((item, start_time, time_elapsed))
                self.state_snapshots.append(self._capture_state_snapshot(time_elapsed))
                continue

            if name == "CMD_RESET_RSK":
                next_cast_force_reset = True
                item['sim_result'] = {'damage': 0, 'timestamp': time_elapsed, 'breakdown': 'Instruction: Force RSK Reset', 'duration': 0.2} # Visual duration
                self.sequence_time_map.append((item, start_time, time_elapsed)) # Zero duration or small visual?
                self.state_snapshots.append(self._capture_state_snapshot(time_elapsed))
                continue

            if name == "CMD_COMBO_BREAKER":
                next_cast_force_cb = True
                item['sim_result'] = {'damage': 0, 'timestamp': time_elapsed, 'breakdown': 'Instruction: Force Combo Breaker', 'duration': 0.2}
                self.sequence_time_map.append((item, start_time, time_elapsed))
                self.state_snapshots.append(self._capture_state_snapshot(time_elapsed))
                continue

            if name not in self.sim_spell_book.spells:
                item['error'] = "Unknown Spell"
                continue

            spell = self.sim_spell_book.spells[name]

            # Check usability
            if not spell.is_usable(self.sim_player, self.sim_spell_book.spells):
                item['error'] = "Not Ready / No Resources"

            # Cast with flags
            dmg, breakdown = spell.cast(
                self.sim_player,
                other_spells=self.sim_spell_book.spells,
                use_expected_value=True,
                force_proc_reset=next_cast_force_reset,
                force_proc_combo_breaker=next_cast_force_cb
            )

            next_cast_force_reset = False
            next_cast_force_cb = False

            total_damage += dmg

            if 'extra_events' not in breakdown:
                breakdown['extra_events'] = []

            for evt in breakdown.get('extra_events', []):
                 self.simulation_events.append({
                     'name': evt['name'],
                     'damage': evt['damage'],
                     'time': time_elapsed,
                     'source': 'cast_extra'
                 })

            # Advance Time
            cast_time = max(self.sim_player.gcd_remaining, spell.get_effective_cast_time(self.sim_player))

            if name in GCD_FREE_SPELLS:
                 cast_time = 0.0

            # Special case: Zenith is technically 0.0 in simulation but for visualization we might want minimum width?
            # We will handle visual width in draw, but logical time remains 0.

            pdmg, events = self.sim_player.advance_time(cast_time, use_expected_value=True)
            self.sim_spell_book.tick(cast_time)

            for evt in events:
                dmg_val = evt.get('Expected DMG', 0)
                total_damage += dmg_val

                # Filter out passive events for visualization if needed, OR map names
                src = evt.get('source', 'Tick')
                if src == 'passive': src = 'Auto Attack' # Map early

                self.simulation_events.append({
                    'name': src,
                    'damage': dmg_val,
                    'time': time_elapsed + evt.get('timestamp', 0),
                    'source': 'tick'
                })

                breakdown['extra_events'].append({
                     'name': src,
                     'damage': dmg_val
                })

            block_total_damage = dmg + pdmg

            time_elapsed += cast_time

            item['sim_result'] = {
                'damage': block_total_damage,
                'timestamp': time_elapsed,
                'breakdown': breakdown,
                'duration': cast_time
            }
            self.sequence_time_map.append((item, start_time, time_elapsed))
            self.state_snapshots.append(self._capture_state_snapshot(time_elapsed))

        # 3. Update Stats
        dps = total_damage / time_elapsed if time_elapsed > 0 else 0
        self.stats_label.configure(text=f"总伤害: {int(total_damage):,} | DPS: {int(dps):,}")
        self.resource_label.configure(text=f"预计结束资源: Energy {int(self.sim_player.energy)} | Chi {self.sim_player.chi}")

        # 4. Refresh Palette with new stats (CD updates)
        # Note: This refreshes base palette state. Dynamic updates happen on cursor move.
        self._populate_palette()

        # 5. Redraw
        self._draw_sequence()

    def _draw_sequence(self):
        self.canvas.delete("all")
        self.block_map = {} # item_id (tag) -> data
        self.cursor_id = None # Reset cursor handle

        # 1. Draw Group Headers/Backgrounds
        for idx, (group_name, _) in enumerate(SPELL_GROUPS):
            y_start = idx * ROW_HEIGHT
            # Header Box
            self.canvas.create_rectangle(0, y_start, HEADER_WIDTH, y_start + ROW_HEIGHT, fill="#2c3e50", outline="#34495e")
            self.canvas.create_text(10, y_start + ROW_HEIGHT/2, text=group_name, fill="#ecf0f1", anchor="w", width=HEADER_WIDTH-20, font=("Arial", 10, "bold"))

            # Lane Background
            self.canvas.create_rectangle(HEADER_WIDTH, y_start, 5000, y_start + ROW_HEIGHT, fill="#1a1a1a", outline="#333333")

        # 2. Draw Main Sequence Blocks (Time Scale)

        for i, item in enumerate(self.action_sequence):
            name_key = item['name']
            sim_res = item.get('sim_result', {})
            duration = sim_res.get('duration', 1.0) # Default if not calc

            # Retrieve start time from our map to ensure consistency
            # Finding it by identity/uuid in map is safer
            start_t = 0
            for mapping in self.sequence_time_map:
                if mapping[0] is item:
                    start_t = mapping[1]
                    break

            # Visual Width
            # If duration is 0 (instant/GCD free), give it a small visual width
            visual_duration = max(duration, 0.5)
            block_w = visual_duration * PIXELS_PER_SECOND

            x = HEADER_WIDTH + 10 + (start_t * PIXELS_PER_SECOND)

            # Determine Row
            row_idx = 4
            found = False
            for r_idx, (g_name, g_keys) in enumerate(SPELL_GROUPS):
                if name_key in g_keys:
                    row_idx = r_idx
                    found = True
                    break
            if not found and (name_key.startswith("CMD_") or name_key == "WAIT_0_5"):
                row_idx = 4

            y = row_idx * ROW_HEIGHT + (ROW_HEIGHT - self.block_height) / 2

            color = "#2E86C1"
            outline = "black"
            text = SPELL_LOCALIZATION.get(name_key, name_key)
            if name_key.startswith("CMD_"): text = text.replace("指令: ", "")

            if 'error' in item:
                color = "#922B21" # Red
                text += "\n(!)"
            elif name_key == "WAIT_0_5":
                color = "#555555"
            elif name_key.startswith("CMD_"):
                color = "#D35400"

            rect_h = self.block_height
            if name_key == 'FOF':
                rect_h = self.block_height * 0.75

            # Draw Block
            rect_id = self.canvas.create_rectangle(x, y, x + block_w, y + rect_h, fill=color, outline=outline, width=2)

            icon_img = self.icon_cache.get(f"{name_key}_timeline")
            if icon_img and not 'error' in item:
                 # Check if icon fits width
                 if block_w > 20:
                     self.canvas.create_image(x + block_w/2, y + rect_h/2, image=icon_img, tags=f"item_{item['uuid']}")
            else:
                 # Check if text fits
                 if block_w > 40:
                    text_id = self.canvas.create_text(x + block_w/2, y + rect_h/2, text=text, fill="white", font=("Arial", 10, "bold"), width=block_w-4)
                    self.canvas.itemconfig(text_id, tags=f"item_{item['uuid']}")

            # FOF Ticks
            if name_key == 'FOF':
                 tick_y_start = y + rect_h
                 tick_h = self.block_height * 0.25
                 tick_w = block_w / 5

                 # Retrieve Tick Events from breakdown
                 tick_events = []
                 if 'sim_result' in item and 'breakdown' in item['sim_result']:
                     extra = item['sim_result']['breakdown'].get('extra_events', [])
                     # Filter for 'Tick' or known FOF tick events (actually source='FOF' or name='Tick')
                     # In _recalculate_timeline we appended ticks as source='tick' and name=source from advance_time ('FOF')
                     # Wait, in breakdown['extra_events'], we stored: {'name': evt.get('source', 'Tick/Event'), 'damage': dmg_val}
                     # FOF ticks usually have name='FOF' in the extra_events list from advance_time.
                     # Let's collect them.
                     tick_events = [e for e in extra if e['name'] == 'FOF']
                     # Fallback if name varies
                     if not tick_events:
                         tick_events = [e for e in extra if 'Tick' in e.get('name', '') or e['name'] == 'FOF']

                 for t in range(5):
                     tx1 = x + t * tick_w
                     tx2 = x + (t + 1) * tick_w
                     ty1 = tick_y_start
                     ty2 = tick_y_start + tick_h

                     self.canvas.create_rectangle(tx1, ty1, tx2, ty2, fill="#E74C3C", outline="black")

                     # Interactive Tick
                     if t < len(tick_events):
                         tevt = tick_events[t]
                         # Create invisible hit box
                         tick_tag = f"tick_{item['uuid']}_{t}"
                         self.canvas.create_rectangle(tx1, ty1, tx2, ty2, fill="", outline="", tags=tick_tag)

                         tick_data = {'event_info': {'name': f"FOF Tick {t+1}", 'damage': tevt['damage'], 'time': 0}} # Time is approximate here relative to block
                         self.block_map[tick_tag] = tick_data
                         self.canvas.tag_bind(tick_tag, "<Button-1>", lambda e, d=tick_data: self._on_block_click(d))
                         self.canvas.lift(tick_tag)

            tag = f"item_{item['uuid']}"
            self.canvas.itemconfig(rect_id, tags=tag)

            DraggableBlock(self.canvas, tag, item, self._on_block_click, self._on_drag_end, self._remove_item)

            self.block_map[tag] = item

            if 'sim_result' in item and 'error' not in item and not item['name'].startswith("CMD_"):
                res = item['sim_result']
                # Compact damage text if narrow
                if block_w > 30:
                    self.canvas.create_text(x + block_w/2, y + self.block_height + 5, text=f"{int(res['damage']/1000)}k", fill="#A9DFBF", font=("Arial", 9), anchor="n")
                self.canvas.create_text(x + 2, y + 2, text=f"{i+1}", fill="#BDC3C7", font=("Arial", 8), anchor="nw")

        # 3. Draw Derived Events (Time Scale)
        for evt in self.simulation_events:
             name = evt['name']
             damage = evt['damage']
             time_pt = evt['time']

             x = HEADER_WIDTH + 10 + (time_pt * PIXELS_PER_SECOND)

             target_row = -1
             for r_idx, (g_name, g_keys) in enumerate(SPELL_GROUPS):
                 for k in g_keys:
                     if k in name:
                         target_row = r_idx
                         break
                 if target_row != -1: break

             if target_row == -1:
                  # Force to Special Events row (last row index)
                  target_row = len(SPELL_GROUPS) - 1

             if target_row != -1:
                 y = target_row * ROW_HEIGHT + (ROW_HEIGHT - 20) / 2

                 color = "#E67E22" if damage > 0 else "#95A5A6"
                 tag = f"evt_{int(time_pt*100)}_{int(random.random()*10000)}"

                 # Draw Dot
                 self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=color, outline="black")
                 # Draw hit box on top
                 rect_id = self.canvas.create_rectangle(x - 6, y - 6, x + 6, y + 6, fill="", outline="", tags=tag)

                 # Bind click
                 self.block_map[tag] = {'event_info': evt}
                 self.canvas.tag_bind(tag, "<Button-1>", lambda e, d={'event_info': evt}: self._on_block_click(d))
                 self.canvas.lift(tag) # Ensure top

        # Set Scroll Region
        # Determine max time
        max_time = 0
        if self.sequence_time_map:
            max_time = self.sequence_time_map[-1][2]

        total_width = HEADER_WIDTH + 10 + (max_time + 2.0) * PIXELS_PER_SECOND
        total_height = len(SPELL_GROUPS) * ROW_HEIGHT
        self.canvas.configure(scrollregion=(0, 0, total_width, total_height))

        # Time Ruler
        for t in range(int(max_time) + 2):
            rx = HEADER_WIDTH + 10 + t * PIXELS_PER_SECOND
            self.canvas.create_line(rx, 0, rx, total_height, fill="#333333", dash=(2, 4))
            self.canvas.create_text(rx + 2, total_height - 10, text=f"{t}s", fill="#777", anchor="nw")
