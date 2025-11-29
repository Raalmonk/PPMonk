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

ICON_SIZE_PALETTE = 32
ICON_SIZE_TIMELINE = 48
ROW_HEIGHT = 80
HEADER_WIDTH = 200

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

        # Core Data Structure
        self.action_sequence = [] # List of dicts: {'name': 'RSK', 'settings': {}, 'uuid': ...}

        # Temporary State for Simulation
        self.sim_player = None
        self.sim_spell_book = None
        self.icon_cache = {}
        self.simulation_events = [] # Stores derived events: (name, time, damage)

        # UI Constants
        self.block_width = 80
        self.block_height = 60
        self.block_gap = 5
        self.block_map = {}

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

        # Target Count in Sandbox
        f_target = ctk.CTkFrame(stats_frame, fg_color="transparent")
        f_target.pack(side="left", padx=10)
        ctk.CTkLabel(f_target, text="目标数").pack(side="left", padx=2)
        target_entry = ctk.CTkEntry(f_target, width=40, textvariable=self.target_count)
        target_entry.pack(side="left", padx=2)
        target_entry.bind("<Return>", lambda e: self._recalculate_timeline())
        target_entry.bind("<FocusOut>", lambda e: self._recalculate_timeline())

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

        # Info Box
        self.info_box = ctk.CTkTextbox(seq_frame, height=150)
        self.info_box.pack(fill="x", pady=5)
        self.info_box.insert("1.0", "点击方块查看详情...")
        self.info_box.configure(state="disabled")

    def _populate_palette(self):
        for group_name, spell_keys in SPELL_GROUPS:
            # Header
            ctk.CTkLabel(self.palette_scroll, text=group_name, font=("Arial", 12, "bold"), text_color="#bdc3c7").pack(pady=(10, 2), anchor="w")

            # Grid container for buttons (optional, but packing is easier for now)
            # Using pack for simplicity
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
                         icon = self.icon_cache.get(f"{key}_palette", None)

                         btn = ctk.CTkButton(self.palette_scroll,
                                             text=f" {display_name}",
                                             image=icon,
                                             compound="left",
                                             anchor="w",
                                             command=lambda k=key: self._add_to_sequence(k))
                         btn.pack(pady=2, padx=5, fill="x")

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

    def _on_block_click(self, data):
        # Show details in info box
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

        # Also check if this is an event block (not in sequence, but in simulation_events)
        if isinstance(data, dict) and 'event_info' in data:
             evt = data['event_info']
             text = f"Event: {evt['name']}\n"
             text += f"Time: {evt['time']:.2f}s\n"
             text += f"Damage: {int(evt['damage'])}\n"

        self.info_box.configure(state="normal")
        self.info_box.delete("1.0", "end")
        self.info_box.insert("1.0", text)
        self.info_box.configure(state="disabled")

    def _on_drag_end(self, item_id, final_x):
        # Determine index based on block width, ignoring Y (since sequence is strictly linear in time, but displayed across rows)
        # Wait, if we split into rows, dragging horizontally is ambiguous if blocks are not on the same row.
        # But for 'Sandbox', it's a sequence editor. The 'Timeline' view shows rows.
        # The user request "Timeline and Skill bar must be separate" implies the VISUALIZATION should be separated by groups.
        # BUT this is an editor. If we separate rows, does it mean we have parallel execution? No, Monk is GCD locked.
        # It's still a single sequence.
        # So we display them in rows corresponding to their group, but the X axis is still 'Step Index'.

        # Calculate new index based on x
        # Since we spread blocks across rows but they share the same X grid (Step 1, Step 2...),
        # we can just use the X coordinate to determine the index in the linear sequence.

        scroll_x = self.canvas.canvasx(final_x)
        # Offset by header width
        effective_x = scroll_x - HEADER_WIDTH
        if effective_x < 0: effective_x = 0

        new_index = int(effective_x // (self.block_width + self.block_gap))

        target_data = self.block_map.get(item_id)

        if target_data and target_data in self.action_sequence:
            current_index = self.action_sequence.index(target_data)
            if new_index != current_index:
                new_index = max(0, min(new_index, len(self.action_sequence)-1))
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
            rating_vers=vers
        )
        self.sim_player.target_count = self.target_count.get()

        self.sim_spell_book = SpellBook(active_talents=self.active_talents)
        self.sim_spell_book.apply_talents(self.sim_player)

        time_elapsed = 0.0
        total_damage = 0.0
        self.simulation_events = [] # Clear events

        next_cast_force_reset = False
        next_cast_force_cb = False

        # 2. Iterate Sequence
        for item in self.action_sequence:
            name = item['name']
            item.pop('error', None)
            item.pop('sim_result', None)

            if name == "WAIT_0_5":
                self.sim_player.advance_time(0.5)
                self.sim_spell_book.tick(0.5)
                time_elapsed += 0.5
                item['sim_result'] = {'damage': 0, 'timestamp': time_elapsed, 'breakdown': 'Wait 0.5s'}
                continue

            if name == "CMD_RESET_RSK":
                next_cast_force_reset = True
                item['sim_result'] = {'damage': 0, 'timestamp': time_elapsed, 'breakdown': 'Instruction: Force RSK Reset'}
                continue

            if name == "CMD_COMBO_BREAKER":
                next_cast_force_cb = True
                item['sim_result'] = {'damage': 0, 'timestamp': time_elapsed, 'breakdown': 'Instruction: Force Combo Breaker'}
                continue

            if name not in self.sim_spell_book.spells:
                item['error'] = "Unknown Spell"
                continue

            spell = self.sim_spell_book.spells[name]

            # Check usability
            if not spell.is_usable(self.sim_player, self.sim_spell_book.spells):
                item['error'] = "Not Ready / No Resources"
                # Continue anyway in sandbox

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

            # Capture Cast Event (mostly for channel logic or instant extra damage)
            if 'extra_events' not in breakdown:
                breakdown['extra_events'] = []

            # For channeled spells (FOF), 'dmg' returned by cast() might be 0 or initial portion?
            # spell_book.py: FOF cast() returns (0.0, breakdown) if is_channeled.
            # The breakdown contains 'extra_events' (e.g. Flurry Burst).
            # The actual ticks happen in advance_time().

            # Wait, Spell.cast for channeled spells returns 0 damage initially?
            # Yes, `Spell.cast` returns `0.0, ...` if `is_channeled`.
            # But in the sandbox `total_damage` must include ticks!
            # The ticks are generated by `self.sim_player.advance_time(cast_time...)` below.

            # Store immediate extra events from cast
            for evt in breakdown.get('extra_events', []):
                 self.simulation_events.append({
                     'name': evt['name'],
                     'damage': evt['damage'],
                     'time': time_elapsed,
                     'source': 'cast_extra'
                 })

            # Advance Time
            cast_time = max(self.sim_player.gcd_remaining, spell.get_effective_cast_time(self.sim_player))

            # GCD override logic (Zenith, CMDs)
            if name in GCD_FREE_SPELLS:
                 cast_time = 0.0 # Instant, off-GCD (visually)
                 # But we still need to process ticks if any channel is active?
                 # If Zenith is off-GCD, we don't advance time?
                 # If we don't advance time, we don't tick dots/channels.
                 # Usually off-GCD spells don't consume time.
                 pass

            pdmg, events = self.sim_player.advance_time(cast_time, use_expected_value=True)
            self.sim_spell_book.tick(cast_time)

            # Store tick events
            for evt in events:
                dmg_val = evt.get('Expected DMG', 0)
                total_damage += dmg_val # Add tick damage to total!

                # If FOF ticks, we want to capture them for visualization
                # Events from advance_time are like: {'source': 'FOF', 'Expected DMG': 123, ...}
                self.simulation_events.append({
                    'name': evt.get('source', 'Tick'),
                    'damage': dmg_val,
                    'time': time_elapsed + evt.get('timestamp', 0), # timestamp relative to start of advance_time
                    'source': 'tick'
                })

                breakdown['extra_events'].append({
                     'name': evt.get('source', 'Tick/Event'),
                     'damage': dmg_val
                })

            # If it was a channeled spell, `dmg` was 0, but `pdmg` (passive/tick damage) holds the channel damage.
            # So `total_damage` is correct.
            # However, `item['sim_result']['damage']` currently sets `dmg` (the cast result).
            # For FOF, we need to sum up the tick damage associated with this cast block.
            # We can use `pdmg` for that.

            block_total_damage = dmg + pdmg

            time_elapsed += cast_time

            item['sim_result'] = {
                'damage': block_total_damage,
                'timestamp': time_elapsed,
                'breakdown': breakdown
            }

        # 3. Update Stats
        dps = total_damage / time_elapsed if time_elapsed > 0 else 0
        self.stats_label.configure(text=f"总伤害: {int(total_damage):,} | DPS: {int(dps):,}")

        # Update Resource Label
        self.resource_label.configure(text=f"预计结束资源: Energy {int(self.sim_player.energy)} | Chi {self.sim_player.chi}")

        # 4. Redraw
        self._draw_sequence()

    def _draw_sequence(self):
        self.canvas.delete("all")
        self.block_map = {} # item_id (tag) -> data

        # 1. Draw Group Headers/Backgrounds
        for idx, (group_name, _) in enumerate(SPELL_GROUPS):
            y_start = idx * ROW_HEIGHT
            # Header Box
            self.canvas.create_rectangle(0, y_start, HEADER_WIDTH, y_start + ROW_HEIGHT, fill="#2c3e50", outline="#34495e")
            self.canvas.create_text(10, y_start + ROW_HEIGHT/2, text=group_name, fill="#ecf0f1", anchor="w", width=HEADER_WIDTH-20, font=("Arial", 10, "bold"))

            # Lane Background
            self.canvas.create_rectangle(HEADER_WIDTH, y_start, 5000, y_start + ROW_HEIGHT, fill="#1a1a1a", outline="#333333")

        # 2. Draw Main Sequence Blocks
        start_x = HEADER_WIDTH + 10

        for i, item in enumerate(self.action_sequence):
            name_key = item['name']

            # Determine Row
            row_idx = 4 # Default to last group (Control)
            found = False
            for r_idx, (g_name, g_keys) in enumerate(SPELL_GROUPS):
                if name_key in g_keys:
                    row_idx = r_idx
                    found = True
                    break

            if not found and (name_key.startswith("CMD_") or name_key == "WAIT_0_5"):
                row_idx = 4

            y = row_idx * ROW_HEIGHT + (ROW_HEIGHT - self.block_height) / 2
            x = start_x + i * (self.block_width + self.block_gap)

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

            # FOF Special Logic: occupy 3/4 height
            rect_h = self.block_height
            if name_key == 'FOF':
                rect_h = self.block_height * 0.75

            # Draw Block
            rect_id = self.canvas.create_rectangle(x, y, x + self.block_width, y + rect_h, fill=color, outline=outline, width=2)

            icon_img = self.icon_cache.get(f"{name_key}_timeline")
            if icon_img and not 'error' in item:
                 self.canvas.create_image(x + self.block_width/2, y + rect_h/2, image=icon_img, tags=f"item_{item['uuid']}")
            else:
                 text_id = self.canvas.create_text(x + self.block_width/2, y + rect_h/2, text=text, fill="white", font=("Arial", 10, "bold"), width=self.block_width-4)
                 self.canvas.itemconfig(text_id, tags=f"item_{item['uuid']}")

            # FOF Ticks Visualization
            if name_key == 'FOF':
                 # Ticks area is the bottom 1/4 of the block height space (roughly)
                 tick_y_start = y + rect_h
                 tick_h = self.block_height * 0.25
                 # We want to represent 5 ticks? or just fill the space?
                 # Draw small rectangles for ticks
                 tick_w = self.block_width / 5
                 for t in range(5):
                     self.canvas.create_rectangle(x + t*tick_w, tick_y_start, x + (t+1)*tick_w, tick_y_start + tick_h, fill="#E74C3C", outline="black")

            # Bind events via unique tag
            tag = f"item_{item['uuid']}"
            self.canvas.itemconfig(rect_id, tags=tag)

            DraggableBlock(self.canvas, tag, item, self._on_block_click, self._on_drag_end, self._remove_item)

            self.block_map[tag] = item

            # Info text (Time, DMG)
            if 'sim_result' in item and 'error' not in item and not item['name'].startswith("CMD_"):
                res = item['sim_result']
                # Draw info BELOW the block as requested
                self.canvas.create_text(x + self.block_width/2, y + self.block_height + 5, text=f"{int(res['damage']/1000)}k", fill="#A9DFBF", font=("Arial", 9), anchor="n")
                # Draw index top left
                self.canvas.create_text(x + 2, y + 2, text=f"{i+1}", fill="#BDC3C7", font=("Arial", 8), anchor="nw")

        # 3. Draw Derived Events (Melee / Special)
        # These need to be mapped to the timeline based on X position of the "step" they occurred in.
        # However, they happen at specific times, while our timeline is discrete steps.
        # But we are drawing steps sequentially. The 'time' of an event determines where it falls relative to the sequence?
        # No, the timeline view here is "Step 1, Step 2...".
        # Melee/Special events happen *during* a step (during the cast time or GCD).
        # So we can just bucket them into the step index where they happened.
        # But `simulation_events` has exact timestamps, not step indices.
        # To map back to step index: We iterate `action_sequence` again, accumulate time, and check which events fall in that window.

        current_time = 0.0
        for i, item in enumerate(self.action_sequence):
            step_duration = 0
            if 'sim_result' in item and 'timestamp' in item['sim_result']:
                step_end = item['sim_result']['timestamp']
                step_start = step_end - step_duration # Wait, we don't have duration stored easily besides calc.
                # Actually, `timestamp` is end time. Previous item end time is start.
                pass

            # Re-calculate step duration or just trust the logic:
            # Events generated during step `i` are those that happened between step `i-1` end and step `i` end.
            prev_end = 0.0
            if i > 0 and 'sim_result' in self.action_sequence[i-1]:
                prev_end = self.action_sequence[i-1]['sim_result']['timestamp']

            curr_end = 0.0
            if 'sim_result' in item:
                curr_end = item['sim_result']['timestamp']

            # Find events in (prev_end, curr_end]
            # Floating point tolerance?
            step_events = [e for e in self.simulation_events if e['time'] > prev_end - 0.001 and e['time'] <= curr_end + 0.001]

            # Draw events in appropriate rows
            x_base = start_x + i * (self.block_width + self.block_gap)

            # Organize by row
            for evt in step_events:
                 name = evt['name']
                 damage = evt['damage']

                 # Map to row
                 target_row = -1
                 for r_idx, (g_name, g_keys) in enumerate(SPELL_GROUPS):
                     # Check partial match for special events (e.g. "Flurry Burst (FOF)")
                     for k in g_keys:
                         if k in name:
                             target_row = r_idx
                             break
                     if target_row != -1: break

                 # Default to Special Events row (last one) if not found?
                 # Or Melee if "Auto Attack"
                 if target_row == -1:
                      # Check last group manually?
                      # SPELL_GROUPS[-1] is Special Events.
                      # SPELL_GROUPS[-2] is Melee
                      pass

                 if target_row != -1:
                     y = target_row * ROW_HEIGHT + (ROW_HEIGHT - 30) / 2 # Smaller blocks
                     # Stack multiple events in same step?
                     # Just offset y slightly or overlap?
                     # For simplicity, draw small distinct markers.
                     # Let's use small colored circles or squares.

                     color = "#E67E22" if damage > 0 else "#95A5A6"
                     self.canvas.create_oval(x_base + 10, y, x_base + 30, y + 20, fill=color, outline="black")
                     self.canvas.create_text(x_base + 35, y + 10, text=f"{int(damage)}", anchor="w", fill="white", font=("Arial", 8))

                     # Tooltip simulation
                     # We can bind a click to show info
                     tag = f"evt_{i}_{int(random.random()*1000)}"
                     self.canvas.create_rectangle(x_base, y, x_base + self.block_width, y + 30, fill="", outline="", tags=tag) # Invisible hit box
                     self.block_map[tag] = {'event_info': evt} # Hack to re-use _on_block_click
                     self.canvas.tag_bind(tag, "<Button-1>", lambda e, d={'event_info': evt}: self._on_block_click(d))

        # Set Scroll Region
        total_width = start_x + len(self.action_sequence) * (self.block_width + self.block_gap) + 100
        total_height = len(SPELL_GROUPS) * ROW_HEIGHT
        self.canvas.configure(scrollregion=(0, 0, total_width, total_height))
