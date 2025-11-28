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
        self.title("Sequence Editor")
        self.geometry("1400x850")

        self.active_talents = active_talents if active_talents else []
        self.player_stats = player_stats if player_stats else {}

        # [Fix] Initialize target_count so ui.py doesn't crash when setting it
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
        # We need a reference spellbook just to get spell names/costs for the palette
        # The actual simulation uses a fresh one each time.
        self.ref_player = PlayerState() # Dummy
        self.ref_spell_book = SpellBook(active_talents=self.active_talents)
        self.ref_spell_book.apply_talents(self.ref_player)

    def _build_ui(self):
        # --- Top Controls ---
        top_panel = ctk.CTkFrame(self)
        top_panel.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(top_panel, text="Clear Sequence", fg_color="#C0392B", command=self._clear_sequence).pack(side="left", padx=5)
        ctk.CTkButton(top_panel, text="Export JSON", command=self._export_json).pack(side="left", padx=5)
        ctk.CTkButton(top_panel, text="Import JSON", command=self._import_json).pack(side="left", padx=5)

        self.stats_label = ctk.CTkLabel(top_panel, text="Total DMG: 0 | DPS: 0", font=("Arial", 14, "bold"))
        self.stats_label.pack(side="right", padx=20)

        # --- Main Content ---
        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=10, pady=5)

        # Left: Spell Palette
        palette_frame = ctk.CTkFrame(content, width=200)
        palette_frame.pack(side="left", fill="y", padx=5, pady=5)

        ctk.CTkLabel(palette_frame, text="Spell Palette", font=("Arial", 16, "bold")).pack(pady=10)
        self.palette_scroll = ctk.CTkScrollableFrame(palette_frame)
        self.palette_scroll.pack(fill="both", expand=True)

        self._populate_palette()

        # Right: Sequence View
        seq_frame = ctk.CTkFrame(content)
        seq_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(seq_frame, text="Action Sequence (Drag to Reorder, Right-Click to Delete)", font=("Arial", 14)).pack(pady=5)

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
        self.info_box.insert("1.0", "Click a block to see details...")
        self.info_box.configure(state="disabled")

    def _populate_palette(self):
        # Add buttons for spells
        spell_keys = ["TP", "BOK", "RSK", "FOF", "WDP", "SCK", "SOTWL", "SW", "Xuen", "Zenith", "ToD", "Conduit"]

        for key in spell_keys:
            # Check if known? For now, we show all, simulation will validation error them if unknown.
            if key in self.ref_spell_book.spells: # Only show spells in book (talents applied)
                 if self.ref_spell_book.spells[key].is_known:
                     btn = ctk.CTkButton(self.palette_scroll, text=self.ref_spell_book.spells[key].name,
                                         command=lambda k=key: self._add_to_sequence(k))
                     btn.pack(pady=2, padx=5, fill="x")

        ctk.CTkLabel(self.palette_scroll, text="Controls").pack(pady=10)
        ctk.CTkButton(self.palette_scroll, text="Wait 0.5s", fg_color="gray", command=lambda: self._add_to_sequence("WAIT_0_5")).pack(pady=2, padx=5, fill="x")

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

    def _recalculate_timeline(self):
        # 1. Reset Simulation
        self.sim_player = PlayerState(
            agility=self.player_stats.get('agility', 2000),
            rating_crit=self.player_stats.get('crit_rating', 2000),
            rating_haste=self.player_stats.get('haste_rating', 1500),
            rating_mastery=self.player_stats.get('mastery_rating', 1000),
            rating_vers=self.player_stats.get('vers_rating', 500)
        )
        self.sim_spell_book = SpellBook(active_talents=self.active_talents)
        self.sim_spell_book.apply_talents(self.sim_player)

        time_elapsed = 0.0
        total_damage = 0.0

        # 2. Iterate Sequence
        for item in self.action_sequence:
            name = item['name']
            item.pop('error', None) # Clear previous errors
            item.pop('sim_result', None)

            if name == "WAIT_0_5":
                self.sim_player.advance_time(0.5)
                self.sim_spell_book.tick(0.5)
                time_elapsed += 0.5
                item['sim_result'] = {'damage': 0, 'timestamp': time_elapsed, 'breakdown': 'Wait 0.5s'}
                continue

            if name not in self.sim_spell_book.spells:
                item['error'] = "Unknown Spell"
                continue

            spell = self.sim_spell_book.spells[name]

            # Check usability
            if not spell.is_usable(self.sim_player, self.sim_spell_book.spells):
                item['error'] = "Not Ready / No Resources"
                # Visualization: Red block, no cast
                continue

            # Cast
            dmg, breakdown = spell.cast(self.sim_player, other_spells=self.sim_spell_book.spells, use_expected_value=True)
            total_damage += dmg

            # Advance Time
            cast_time = max(self.sim_player.gcd_remaining, spell.get_effective_cast_time(self.sim_player))
            # Advance logic
            pdmg, events = self.sim_player.advance_time(cast_time, use_expected_value=True)
            self.sim_spell_book.tick(cast_time)

            time_elapsed += cast_time
            # Add passive damage
            for evt in events:
                total_damage += evt.get('Expected DMG', 0)

            item['sim_result'] = {
                'damage': dmg,
                'timestamp': time_elapsed,
                'breakdown': breakdown
            }

        # 3. Update Stats
        dps = total_damage / time_elapsed if time_elapsed > 0 else 0
        self.stats_label.configure(text=f"Total DMG: {int(total_damage):,} | DPS: {int(dps):,}")

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
            if 'sim_result' in item and 'error' not in item:
                res = item['sim_result']
                self.canvas.create_text(x + self.block_width/2, self.lane_y + self.block_height + 15, text=f"{int(res['damage']/1000)}k", fill="#A9DFBF", font=("Arial", 9))
                self.canvas.create_text(x + self.block_width/2, self.lane_y - 15, text=f"{res['timestamp']:.1f}s", fill="#BDC3C7", font=("Arial", 9))

            x += self.block_width + self.block_gap

        self.canvas.configure(scrollregion=(0, 0, x + 100, 400))
