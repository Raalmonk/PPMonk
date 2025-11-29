import customtkinter as ctk
import tkinter as tk
import json
import random
from ppmonk.core.player import PlayerState
from ppmonk.core.spell_book import SpellBook

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
        self.geometry("1400x850")

        self.active_talents = active_talents if active_talents else []
        self.player_stats = player_stats if player_stats else {}

        # Initialize target_count
        self.target_count = ctk.IntVar(value=1)

        # Core Data Structure
        self.action_sequence = [] # List of dicts: {'name': 'RSK', 'settings': {}, 'uuid': ...}

        # Temporary State for Simulation
        self.sim_player = None
        self.sim_spell_book = None

        # UI Constants
        self.block_width = 80
        self.block_height = 50
        self.block_gap = 5
        self.lane_y = 100
        self.block_map = {}

        self._init_spellbook()
        self._build_ui()
        self._recalculate_timeline()

    def _init_spellbook(self):
        self.ref_player = PlayerState() # Dummy
        self.ref_spell_book = SpellBook(active_talents=self.active_talents)
        self.ref_spell_book.apply_talents(self.ref_player)

    def _build_ui(self):
        # --- Top Controls ---
        top_panel = ctk.CTkFrame(self)
        top_panel.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(top_panel, text="清空序列", fg_color="#C0392B", command=self._clear_sequence).pack(side="left", padx=5)
        ctk.CTkButton(top_panel, text="导出 JSON", command=self._export_json).pack(side="left", padx=5)
        ctk.CTkButton(top_panel, text="导入 JSON", command=self._import_json).pack(side="left", padx=5)

        self.stats_label = ctk.CTkLabel(top_panel, text="总伤害: 0 | DPS: 0", font=("Arial", 14, "bold"))
        self.stats_label.pack(side="right", padx=20)

        # --- Task 3: Stat Editors ---
        stats_frame = ctk.CTkFrame(self)
        stats_frame.pack(fill="x", padx=10, pady=5)

        # We need Agile, Crit, Haste, Mastery, Vers
        # Input fields. We use player_stats as default.

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

        # Left: Spell Palette
        palette_frame = ctk.CTkFrame(content, width=200)
        palette_frame.pack(side="left", fill="y", padx=5, pady=5)

        ctk.CTkLabel(palette_frame, text="技能面板 (Palette)", font=("Arial", 16, "bold")).pack(pady=10)
        self.palette_scroll = ctk.CTkScrollableFrame(palette_frame)
        self.palette_scroll.pack(fill="both", expand=True)

        self._populate_palette()

        # Right: Sequence View
        seq_frame = ctk.CTkFrame(content)
        seq_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(seq_frame, text="动作序列 (拖拽排序, 右键删除)", font=("Arial", 14)).pack(pady=5)

        self.canvas_container = ctk.CTkFrame(seq_frame)
        self.canvas_container.pack(fill="both", expand=True)

        h_scroll = tk.Scrollbar(self.canvas_container, orient="horizontal")
        self.canvas = tk.Canvas(self.canvas_container, bg="#2B2B2B", height=400, xscrollcommand=h_scroll.set)
        h_scroll.config(command=self.canvas.xview)

        h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="top", fill="both", expand=True)

        # Info Box
        self.info_box = ctk.CTkTextbox(seq_frame, height=150)
        self.info_box.pack(fill="x", pady=5)
        self.info_box.insert("1.0", "点击方块查看详情...")
        self.info_box.configure(state="disabled")

    def _populate_palette(self):
        # Add buttons for spells
        spell_keys = ["TP", "BOK", "RSK", "FOF", "WDP", "SCK", "SOTWL", "SW", "Xuen", "Zenith", "ToD", "Conduit"]

        for key in spell_keys:
            if key in self.ref_spell_book.spells:
                 if self.ref_spell_book.spells[key].is_known:
                     btn = ctk.CTkButton(self.palette_scroll, text=self.ref_spell_book.spells[key].name,
                                         command=lambda k=key: self._add_to_sequence(k))
                     btn.pack(pady=2, padx=5, fill="x")

        ctk.CTkLabel(self.palette_scroll, text="控制 & 触发").pack(pady=10)
        ctk.CTkButton(self.palette_scroll, text="等待 0.5s", fg_color="gray", command=lambda: self._add_to_sequence("WAIT_0_5")).pack(pady=2, padx=5, fill="x")

        # Task 7: Trigger Buttons
        ctk.CTkButton(self.palette_scroll, text="触发 RSK 重置", fg_color="#D35400", command=lambda: self._add_to_sequence("CMD_RESET_RSK")).pack(pady=2, padx=5, fill="x")
        ctk.CTkButton(self.palette_scroll, text="触发 免费 BOK", fg_color="#D35400", command=lambda: self._add_to_sequence("CMD_COMBO_BREAKER")).pack(pady=2, padx=5, fill="x")

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
        text = f"Action: {data['name']}\n"
        if 'error' in data:
            text += f"ERROR: {data['error']}\n"

        if 'sim_result' in data:
            res = data['sim_result']
            text += f"Damage: {int(res['damage'])}\n"
            text += f"Time: {res['timestamp']:.2f}s\n"

            # Task 4: FOF Aggregation
            if data['name'] == 'FOF':
                total_fof_dmg = res['damage']

                # The user wants "Total Integrated" and "Details Separated".
                # res['damage'] is the integrated total.
                text += f"\n总伤害 (整合): {int(total_fof_dmg)}\n"
                text += "详细跳数 (分开):\n"

                # Display breakdown
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
        # Calculate new index based on x
        scroll_x = self.canvas.canvasx(final_x)
        new_index = int(scroll_x // (self.block_width + self.block_gap))

        # Find the data object corresponding to this visual block
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

    def _reset_sandbox(self):
        # Helper to force UI update if inputs changed externally (not really used now since we read inputs in _recalculate)
        self._recalculate_timeline()

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

        # Flags for triggers
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

            # Task 7: Trigger Logic
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
                continue

            # Cast with flags
            dmg, breakdown = spell.cast(
                self.sim_player,
                other_spells=self.sim_spell_book.spells,
                use_expected_value=True,
                force_proc_reset=next_cast_force_reset,
                force_proc_combo_breaker=next_cast_force_cb
            )

            # Reset flags
            next_cast_force_reset = False
            next_cast_force_cb = False

            total_damage += dmg

            # Advance Time
            cast_time = max(self.sim_player.gcd_remaining, spell.get_effective_cast_time(self.sim_player))
            pdmg, events = self.sim_player.advance_time(cast_time, use_expected_value=True)
            self.sim_spell_book.tick(cast_time)

            time_elapsed += cast_time

            # [Fix Task 4] Merge advance_time events (ticks) into breakdown['extra_events']
            if 'extra_events' not in breakdown:
                breakdown['extra_events'] = []

            for evt in events:
                dmg_val = evt.get('Expected DMG', 0)
                total_damage += dmg_val
                breakdown['extra_events'].append({
                     'name': evt.get('source', 'Tick/Event'),
                     'damage': dmg_val
                })

            item['sim_result'] = {
                'damage': dmg, # Spell.cast returns total_damage (base + extra)
                'timestamp': time_elapsed,
                'breakdown': breakdown
            }
            # Note: total_damage in loop includes dmg from cast (which includes extra_events inside cast)
            # AND evt['Expected DMG'] from advance_time.
            # So `total_damage` variable tracks sequence total correctly.

        # 3. Update Stats
        dps = total_damage / time_elapsed if time_elapsed > 0 else 0
        self.stats_label.configure(text=f"总伤害: {int(total_damage):,} | DPS: {int(dps):,}")

        # 4. Redraw
        self._draw_sequence()

    def _draw_sequence(self):
        self.canvas.delete("all")
        self.block_map = {} # item_id (tag) -> data

        x = 10
        for i, item in enumerate(self.action_sequence):
            color = "#2E86C1"
            outline = "black"
            text = item['name']

            if 'error' in item:
                color = "#922B21" # Red
                text += "\n(!)"
            elif item['name'] == "WAIT_0_5":
                color = "#555555"
            elif item['name'].startswith("CMD_"):
                color = "#D35400"
                text = text.replace("CMD_", "")

            # Create Block
            rect_id = self.canvas.create_rectangle(x, self.lane_y, x + self.block_width, self.lane_y + self.block_height, fill=color, outline=outline, width=2)
            text_id = self.canvas.create_text(x + self.block_width/2, self.lane_y + self.block_height/2, text=text, fill="white", font=("Arial", 10, "bold"))

            # Bind events via unique tag
            tag = f"item_{item['uuid']}"
            self.canvas.itemconfig(rect_id, tags=tag)
            self.canvas.itemconfig(text_id, tags=tag)

            DraggableBlock(self.canvas, tag, item, self._on_block_click, self._on_drag_end, self._remove_item)

            self.block_map[tag] = item

            # Info text below (Time, DMG)
            if 'sim_result' in item and 'error' not in item and not item['name'].startswith("CMD_"):
                res = item['sim_result']
                self.canvas.create_text(x + self.block_width/2, self.lane_y + self.block_height + 15, text=f"{int(res['damage']/1000)}k", fill="#A9DFBF", font=("Arial", 9))
                self.canvas.create_text(x + self.block_width/2, self.lane_y - 15, text=f"{res['timestamp']:.1f}s", fill="#BDC3C7", font=("Arial", 9))

            x += self.block_width + self.block_gap

        self.canvas.configure(scrollregion=(0, 0, x + 100, 400))
