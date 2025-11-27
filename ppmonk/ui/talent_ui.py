import customtkinter as ctk
import tkinter as tk

# Task 3: Hero Talent Tree Visualization
CANVAS_WIDTH = 1600
CANVAS_HEIGHT = 1800 # Increased height for Hero Talents
NODE_WIDTH = 100
NODE_HEIGHT = 55
X_GAP = 150
Y_GAP = 110

MONK_TALENT_DATA = [
    # --- Row 1 ---
    {"id": "1-1", "label": "Fists of Fury", "row": 0, "col": 4, "max_rank": 1, "req": []},

    # --- Row 2 ---
    {"id": "2-1", "label": "Momentum\nBoost", "row": 1, "col": 3, "max_rank": 1, "req": ["1-1"]},
    {"id": "2-2", "label": "Combat\nWisdom", "row": 1, "col": 4, "max_rank": 1, "req": ["1-1"]},
    {"id": "2-3", "label": "Sharp\nReflexes", "row": 1, "col": 5, "max_rank": 1, "req": ["1-1"]},

    # --- Row 3 ---
    {"id": "3-1", "label": "Touch of\nthe Tiger", "row": 2, "col": 2, "max_rank": 1, "req": ["2-1"]},
    {"id": "3-2", "label": "Ferociousness", "row": 2, "col": 3, "max_rank": 2, "req": ["2-1"]},
    {"id": "3-3", "label": "Hardened\nSoles", "row": 2, "col": 5, "max_rank": 2, "req": ["2-3"]},
    {"id": "3-4", "label": "Ascension", "row": 2, "col": 6, "max_rank": 1, "req": ["2-3"]},

    # --- Row 4 ---
    {"id": "4-1", "label": "Dual\nThreat", "row": 3, "col": 2, "max_rank": 1, "req": ["3-1", "3-2"]},
    {"id": "4-2", "label": "Teachings of\nMonastery", "row": 3, "col": 4, "max_rank": 1, "req": ["2-2"]},
    {"id": "4-3", "label": "Glory of\nthe Dawn", "row": 3, "col": 6, "max_rank": 1, "req": ["3-3", "3-4"]},

    # --- Row 5 ---
    {"id": "5-1", "label": "Crane\nVortex", "row": 4, "col": 1, "max_rank": 1, "req": ["4-1"]},
    {"id": "5-2", "label": "Meridian\nStrikes", "row": 4, "col": 2, "max_rank": 1, "req": ["4-1"]},
    {"id": "5-3", "label": "Rising\nStar", "row": 4, "col": 3, "max_rank": 1, "req": ["4-1", "4-2"]},
    {"id": "5-4", "label": "Zenith", "row": 4, "col": 4, "max_rank": 1, "req": ["4-2"]},
    {"id": "5-5", "label": "Hit\nCombo", "row": 4, "col": 5, "max_rank": 1, "req": ["4-2", "4-3"]},
    {"id": "5-6", "label": "Brawler's\nIntensity", "row": 4, "col": 7, "max_rank": 1, "req": ["4-3"]},

    # --- Row 6 ---
    {"id": "6-1", "label": "Jade\nIgnition", "row": 5, "col": 1, "max_rank": 1, "req": ["5-1"]},
    {"id": "6-2", "label": "Cyclone's\nDrift", "row": 5, "col": 2, "max_rank": 1, "req": ["5-1", "5-2", "5-3"],
     "is_choice": True, "choices": ["Cyclone's\nDrift", "Crashing\nFists"]},
    {"id": "6-3", "label": "Spiritual\nFocus", "row": 5, "col": 3, "max_rank": 1, "req": ["5-4"],
     "is_choice": True, "choices": ["Spiritual\nFocus", "Drinking\nHorn Cover"]},
    {"id": "6-4", "label": "Obsidian\nSpiral", "row": 5, "col": 5, "max_rank": 1, "req": ["5-4"]},
    {"id": "6-5", "label": "Combo\nBreaker", "row": 5, "col": 6, "max_rank": 1, "req": ["5-5", "5-6"]},

    # --- Row 7 ---
    {"id": "7-1", "label": "Dance of\nChi-Ji", "row": 6, "col": 2, "max_rank": 1, "req": ["6-1", "6-2"]},
    {"id": "7-2", "label": "Shadowboxing\nTreads", "row": 6, "col": 3, "max_rank": 1, "req": ["6-2", "6-3"]},
    {"id": "7-3", "label": "Whirling\nDragon Punch", "row": 6, "col": 4, "max_rank": 1, "req": ["5-4"],
     "is_choice": True, "choices": ["Whirling\nDragon Punch", "Strike of\nWindlord"]},
    {"id": "7-4", "label": "Energy\nBurst", "row": 6, "col": 5, "max_rank": 1, "req": ["6-5"]},
    {"id": "7-5", "label": "Inner\nPeace", "row": 6, "col": 7, "max_rank": 1, "req": ["6-5"]},

    # --- Row 8 ---
    {"id": "8-1", "label": "Tiger Eye\nBrew", "row": 7, "col": 0, "max_rank": 1, "req": []},
    {"id": "8-2", "label": "Sequenced\nStrikes", "row": 7, "col": 1, "max_rank": 1, "req": ["7-1"]},
    {"id": "8-3", "label": "Sunfire\nSpiral", "row": 7, "col": 2, "max_rank": 1, "req": ["7-2"]},
    {"id": "8-4", "label": "Communion\nw/ Wind", "row": 7, "col": 3, "max_rank": 1, "req": ["7-3"]},
    {"id": "8-5", "label": "Echo\nTechnique", "row": 7, "col": 4, "max_rank": 1, "req": ["7-3"],
     "is_choice": True, "choices": ["Echo\nTechnique", "Revolving\nWhirl"]},
    {"id": "8-6", "label": "Universal\nEnergy", "row": 7, "col": 5, "max_rank": 1, "req": ["7-3", "7-4"]},
    {"id": "8-7", "label": "Memory of\nMonastery", "row": 7, "col": 6, "max_rank": 1, "req": ["7-4", "7-5"]},

    # --- Row 9 ---
    {"id": "9-1", "label": "TEB\nBuff", "row": 8, "col": 0, "max_rank": 1, "req": ["8-1"]},
    {"id": "9-2", "label": "Rushing\nJade Wind", "row": 8, "col": 1, "max_rank": 1, "req": ["8-2"]},
    {"id": "9-3", "label": "Xuen's\nBattlegear", "row": 8, "col": 2, "max_rank": 1, "req": ["8-2", "8-3", "8-4"]},
    {"id": "9-4", "label": "Thunderfist", "row": 8, "col": 3, "max_rank": 1, "req": ["8-5"]},
    {"id": "9-5", "label": "Weapon of\nWind", "row": 8, "col": 4, "max_rank": 1, "req": ["8-5"]},
    {"id": "9-6", "label": "Knowledge\nTemple", "row": 8, "col": 5, "max_rank": 1, "req": ["8-5", "8-6"]},
    {"id": "9-7", "label": "Slicing\nWinds", "row": 8, "col": 6, "max_rank": 1, "req": ["8-6", "8-7"]},
    {"id": "9-8", "label": "Jadefire\nStomp", "row": 8, "col": 7, "max_rank": 1, "req": ["8-7"]},

    # --- Row 10 ---
    {"id": "10-1", "label": "TEB\nFinal", "row": 9, "col": 0, "max_rank": 1, "req": ["9-1"]},
    {"id": "10-2", "label": "Skyfire\nHeel", "row": 9, "col": 1, "max_rank": 1, "req": ["9-3"]},
    {"id": "10-3", "label": "Harmonic\nCombo", "row": 9, "col": 2, "max_rank": 1, "req": ["9-3"]},
    {"id": "10-4", "label": "Flurry of\nXuen", "row": 9, "col": 3, "max_rank": 1, "req": ["9-3", "9-4", "9-5"]},
    {"id": "10-5", "label": "Martial\nAgility", "row": 9, "col": 5, "max_rank": 1, "req": ["9-5", "9-6"]},
    {"id": "10-6", "label": "Airborne\nRhythm", "row": 9, "col": 6, "max_rank": 1, "req": ["9-7"],
     "is_choice": True, "choices": ["Airborne\nRhythm", "Hurricane's\nVault"]},
    {"id": "10-7", "label": "Path of\nJade", "row": 9, "col": 7, "max_rank": 1, "req": ["9-8"],
     "is_choice": True, "choices": ["Path of\nJade", "Singularly\nFocused"]},

    # --- Hero Talents ---
    # Row 12: Headers
    {"id": "hero-sp-base", "label": "SHADO-PAN", "row": 11, "col": 2, "max_rank": 1, "req": []},
    {"id": "hero-cotc-base", "label": "CONDUIT OF\nCELESTIALS", "row": 11, "col": 5, "max_rank": 1, "req": []},

    # Row 13 - Shado-Pan
    {"id": "hero-sp-1", "label": "Pride of\nPandaria", "row": 12, "col": 1, "max_rank": 1, "req": ["hero-sp-base"]},
    {"id": "hero-sp-2", "label": "High\nImpact", "row": 12, "col": 2, "max_rank": 1, "req": ["hero-sp-base"]},
    {"id": "hero-sp-3", "label": "Veteran's\nEye", "row": 12, "col": 3, "max_rank": 1, "req": ["hero-sp-base"]},

    # Row 14 - Shado-Pan
    {"id": "hero-sp-4", "label": "Martial\nPrecision", "row": 13, "col": 1, "max_rank": 1, "req": ["hero-sp-1"]},
    {"id": "hero-sp-5", "label": "Shado Over\nBattlefield", "row": 13, "col": 2, "max_rank": 1, "req": ["hero-sp-2"]},
    {"id": "hero-sp-6", "label": "One Vs\nMany", "row": 13, "col": 3, "max_rank": 1, "req": ["hero-sp-3"]},

    # Row 15 - Shado-Pan
    {"id": "hero-sp-7", "label": "Stand\nReady", "row": 14, "col": 1, "max_rank": 1, "req": ["hero-sp-4"]},
    {"id": "hero-sp-8", "label": "Against All\nOdds", "row": 14, "col": 2, "max_rank": 1, "req": ["hero-sp-5"]},
    {"id": "hero-sp-9", "label": "Efficient\nTraining", "row": 14, "col": 3, "max_rank": 1, "req": ["hero-sp-6"]},

    # Row 16 - Shado-Pan
    {"id": "hero-sp-10", "label": "Vigilant\nWatch", "row": 15, "col": 1, "max_rank": 1, "req": ["hero-sp-7"]},
    {"id": "hero-sp-11", "label": "Weapons of\nWall", "row": 15, "col": 2, "max_rank": 1, "req": ["hero-sp-8"]},
    {"id": "hero-sp-12", "label": "Wisdom of\nWall", "row": 15, "col": 3, "max_rank": 1, "req": ["hero-sp-9"]},

    # Row 13 - COTC
    {"id": "hero-cotc-1", "label": "Celestial\nConduit", "row": 12, "col": 5, "max_rank": 1, "req": ["hero-cotc-base"]},
    {"id": "hero-cotc-2", "label": "Xuen's\nBond", "row": 12, "col": 6, "max_rank": 1, "req": ["hero-cotc-base"]},

    # Row 14 - COTC
    {"id": "hero-cotc-3", "label": "Heart of\nJade", "row": 13, "col": 4, "max_rank": 1, "req": ["hero-cotc-1"]},
    {"id": "hero-cotc-4", "label": "Strength of\nOx", "row": 13, "col": 5, "max_rank": 1, "req": ["hero-cotc-1"]},
    {"id": "hero-cotc-5", "label": "Inner\nCompass", "row": 13, "col": 6, "max_rank": 1, "req": ["hero-cotc-2"]},

    # Row 15 - COTC
    {"id": "hero-cotc-6", "label": "Courage of\nTiger", "row": 14, "col": 4, "max_rank": 1, "req": ["hero-cotc-3"]},
    {"id": "hero-cotc-7", "label": "Xuen's\nGuidance", "row": 14, "col": 5, "max_rank": 1, "req": ["hero-cotc-4"]},
    {"id": "hero-cotc-8", "label": "Temple\nTraining", "row": 14, "col": 6, "max_rank": 1, "req": ["hero-cotc-5"]},

    # Row 16 - COTC
    {"id": "hero-cotc-9", "label": "Restore\nBalance", "row": 15, "col": 4, "max_rank": 1, "req": ["hero-cotc-6"]},
    {"id": "hero-cotc-10", "label": "Path of\nFalling Star", "row": 15, "col": 5, "max_rank": 1, "req": ["hero-cotc-7"]},
    {"id": "hero-cotc-11", "label": "Unity\nWithin", "row": 15, "col": 6, "max_rank": 1, "req": ["hero-cotc-8"]},
]

class TalentNode:
    def __init__(self, canvas, data, onClick):
        self.canvas = canvas
        self.data = data
        self.id = data["id"]
        self.max_rank = data.get("max_rank", 1)
        self.current_rank = 0
        self.reqs = data.get("req", [])
        self.is_choice = data.get("is_choice", False)
        self.choices = data.get("choices", [])
        self.current_choice_idx = 0
        self.onClick = onClick

        self.x = 60 + data["col"] * X_GAP
        self.y = 60 + data["row"] * Y_GAP

        self.bg_color = "#2b2b2b"
        self.active_color = "#3D9970"
        self.avail_color = "#FF851B"
        self.border_color = "#555555"

        if "hero-" in self.id and "base" in self.id:
            self.bg_color = "#4A235A" # Hero Header Color

        corner_radius = 15 if self.is_choice else 4

        self.btn = ctk.CTkButton(
            master=canvas,
            text=self._get_text(),
            width=NODE_WIDTH,
            height=NODE_HEIGHT,
            corner_radius=corner_radius,
            fg_color=self.bg_color,
            border_width=2,
            border_color=self.border_color,
            command=self.on_left_click,
            font=("Segoe UI", 10, "bold") if self.is_choice else ("Segoe UI", 10)
        )
        self.canvas_window = canvas.create_window(self.x, self.y, window=self.btn, anchor="nw")
        self.btn.bind("<Button-3>", self.on_right_click)

    def _get_text(self):
        if self.is_choice and self.choices:
            label = self.choices[self.current_choice_idx]
        else:
            label = self.data['label']

        if self.max_rank > 1:
            return f"{label}\n{self.current_rank}/{self.max_rank}"
        return label

    def update_visual(self, active, available):
        if active:
            border_c = "#2ECC40" if not self.is_choice else "#0074D9"
            self.btn.configure(fg_color=self.active_color, border_color=border_c, text_color="white")
            if self.max_rank > 1 and self.current_rank < self.max_rank:
                self.btn.configure(border_color="#FFDC00")
        elif available:
            self.btn.configure(fg_color="#444444", border_color=self.avail_color, text_color="#DDDDDD")
        else:
            self.btn.configure(fg_color="#222222", border_color="#333333", text_color="#555555")
        self.btn.configure(text=self._get_text())

    def on_left_click(self):
        if self.current_rank == 0:
            self.onClick(self.id, 1)
        else:
            if self.is_choice:
                self.current_choice_idx = 1 - self.current_choice_idx
                self.btn.configure(text=self._get_text())
            elif self.current_rank < self.max_rank:
                self.onClick(self.id, 1)

    def on_right_click(self, event):
        self.onClick(self.id, -1)

class TalentTreeWindow(ctk.CTkToplevel):
    def __init__(self, parent, on_close_callback):
        super().__init__(parent)
        self.title("Monk Talent Tree")
        self.geometry("1400x950")
        self.on_close_callback = on_close_callback

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True)

        v_scroll = ctk.CTkScrollbar(self.main_frame, orientation="vertical")
        h_scroll = ctk.CTkScrollbar(self.main_frame, orientation="horizontal")

        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")

        self.canvas = tk.Canvas(
            self.main_frame,
            bg="#151515",
            highlightthickness=0,
            scrollregion=(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT),
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        v_scroll.configure(command=self.canvas.yview)
        h_scroll.configure(command=self.canvas.xview)

        self._bind_mouse_wheel()

        self.nodes = {}
        self.selected_talents = set()

        self.control_panel = ctk.CTkFrame(self, height=60, fg_color="#222222")
        self.control_panel.place(relx=0, rely=1.0, anchor="sw", relwidth=1.0)

        self.info_label = ctk.CTkLabel(self.control_panel, text="Points Spent: 0", font=("Arial", 14, "bold"))
        self.info_label.pack(side="left", padx=20, pady=10)

        save_btn = ctk.CTkButton(self.control_panel, text="Apply & Close", command=self._on_save, fg_color="#1b8f61", width=150)
        save_btn.pack(side="right", padx=20, pady=10)

        reset_btn = ctk.CTkButton(self.control_panel, text="Reset All", command=self._on_reset, fg_color="#c0392b", width=100)
        reset_btn.pack(side="right", padx=10, pady=10)

        self._build_tree()
        self._refresh_state()

    def _bind_mouse_wheel(self):
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _build_tree(self):
        for data in MONK_TALENT_DATA:
            my_col = data["col"]
            my_row = data["row"]
            my_x = 60 + my_col * X_GAP + NODE_WIDTH / 2
            my_y = 60 + my_row * Y_GAP

            for req_id in data.get("req", []):
                parent_data = next((item for item in MONK_TALENT_DATA if item["id"] == req_id), None)
                if parent_data:
                    p_col = parent_data["col"]
                    p_row = parent_data["row"]
                    p_x = 60 + p_col * X_GAP + NODE_WIDTH / 2
                    p_y = 60 + p_row * Y_GAP + NODE_HEIGHT
                    self.canvas.create_line(p_x, p_y, my_x, my_y, fill="#444444", width=2, tags="conn_line")

        for data in MONK_TALENT_DATA:
            node = TalentNode(self.canvas, data, self._on_node_click)
            self.nodes[data["id"]] = node

    def _on_node_click(self, node_id, change):
        node = self.nodes[node_id]
        if change > 0:
            if node.current_rank < node.max_rank and self._is_node_available(node_id):
                node.current_rank += 1
                self.selected_talents.add(node_id)
                # Auto-select children if Header
                if "hero-" in node_id and "base" in node_id:
                     self._auto_select_hero_tree(node_id)
        else:
            if node.current_rank > 0 and self._can_unlearn(node_id):
                node.current_rank -= 1
                if node.current_rank == 0:
                    self.selected_talents.discard(node_id)
        self._refresh_state()

    def _auto_select_hero_tree(self, header_id):
        # Find all nodes that depend on this header (directly or indirectly)
        # Simple BFS
        queue = [header_id]
        while queue:
            current = queue.pop(0)
            for other_data in MONK_TALENT_DATA:
                oid = other_data["id"]
                if current in other_data.get("req", []):
                     if oid not in self.selected_talents:
                         node = self.nodes[oid]
                         node.current_rank = 1
                         self.selected_talents.add(oid)
                         queue.append(oid)

    def _is_node_available(self, node_id):
        reqs = self.nodes[node_id].reqs
        if not reqs: return True
        for req_id in reqs:
            parent = self.nodes.get(req_id)
            if parent and parent.current_rank >= parent.max_rank:
                return True
        return False

    def _can_unlearn(self, node_id):
        for other_id, other_node in self.nodes.items():
            if other_node.current_rank > 0 and node_id in other_node.reqs:
                active_parents = 0
                for p_id in other_node.reqs:
                    if self.nodes[p_id].current_rank >= self.nodes[p_id].max_rank:
                        active_parents += 1
                if active_parents <= 1:
                    return False
        return True

    def _refresh_state(self):
        total_points = 0
        for node_id, node in self.nodes.items():
            total_points += node.current_rank
            is_active = node.current_rank > 0
            is_avail = self._is_node_available(node_id)
            node.update_visual(is_active, is_avail)
        self.info_label.configure(text=f"Points Spent: {total_points}")

    def _on_reset(self):
        for node in self.nodes.values():
            node.current_rank = 0
            node.current_choice_idx = 0
        self.selected_talents.clear()
        self._refresh_state()

    def _on_save(self):
        final_list = []

        # ID Mapping for Hero Talents
        hero_map = {
            'hero-sp-base': 'ShadoPanBase',
            'hero-sp-1': 'PrideOfPandaria',
            'hero-sp-2': 'HighImpact',
            'hero-sp-3': 'VeteransEye',
            'hero-sp-4': 'MartialPrecision',
            'hero-sp-5': 'ShadoOverTheBattlefield',
            'hero-sp-6': 'OneVersusMany',
            'hero-sp-7': 'StandReady',
            'hero-sp-8': 'AgainstAllOdds',
            'hero-sp-9': 'EfficientTraining',
            'hero-sp-10': 'VigilantWatch',
            'hero-sp-11': 'WeaponsOfTheWall',
            'hero-sp-12': 'WisdomOfTheWall',

            'hero-cotc-base': 'COTCBase',
            'hero-cotc-1': 'CelestialConduit',
            'hero-cotc-2': 'XuensBond',
            'hero-cotc-3': 'HeartOfJadeSerpent',
            'hero-cotc-4': 'StrengthOfBlackOx',
            'hero-cotc-5': 'InnerCompass',
            'hero-cotc-6': 'CourageOfWhiteTiger',
            'hero-cotc-7': 'XuensGuidance',
            'hero-cotc-8': 'TempleTraining',
            'hero-cotc-9': 'RestoreBalance',
            'hero-cotc-10': 'PathOfFallingStar',
            'hero-cotc-11': 'UnityWithin'
        }

        for nid in self.selected_talents:
            # Check for mapping
            mapped_id = hero_map.get(nid, nid)

            node = self.nodes[nid]
            if node.is_choice and node.current_choice_idx == 1:
                final_list.append(mapped_id + "_b")
            else:
                final_list.append(mapped_id)

        self.on_close_callback(final_list)
        self.destroy()
