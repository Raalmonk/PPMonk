import customtkinter as ctk
import tkinter as tk

# --- 天赋树数据结构 ---
# 网格设计: 7列 (0-6), 中心是 Col 3
# 逻辑: req 列表中的任意一个满足即可解锁 (OR逻辑)
MONK_TALENT_DATA = [
    # --- Row 1 (Index 0) ---
    {"id": "1-1", "label": "Fists of Fury", "row": 0, "col": 3, "max_rank": 1, "req": []},

    # --- Row 2 (Index 1) ---
    {"id": "2-1", "label": "Momentum\nBoost", "row": 1, "col": 2, "max_rank": 1, "req": ["1-1"]},
    {"id": "2-2", "label": "Combat\nWisdom", "row": 1, "col": 3, "max_rank": 1, "req": ["1-1"]},
    {"id": "2-3", "label": "Sharp\nReflexes", "row": 1, "col": 4, "max_rank": 1, "req": ["1-1"]},

    # --- Row 3 (Index 2) ---
    {"id": "3-1", "label": "Touch of\nthe Tiger", "row": 2, "col": 1, "max_rank": 1, "req": ["2-1"]},
    {"id": "3-2", "label": "Ferociousness", "row": 2, "col": 2, "max_rank": 2, "req": ["2-1"]},
    {"id": "3-3", "label": "Hardened\nSoles", "row": 2, "col": 4, "max_rank": 2, "req": ["2-3"]},
    {"id": "3-4", "label": "Ascension", "row": 2, "col": 5, "max_rank": 1, "req": ["2-3"]},

    # --- Row 4 (Index 3) ---
    {"id": "4-1", "label": "Dual\nThreat", "row": 3, "col": 1, "max_rank": 1, "req": ["3-1", "3-2"]}, # 3-1 OR 3-2
    {"id": "4-2", "label": "Teachings of\nMonastery", "row": 3, "col": 3, "max_rank": 1, "req": ["2-2"]},
    {"id": "4-3", "label": "Glory of\nthe Dawn", "row": 3, "col": 5, "max_rank": 1, "req": ["3-3", "3-4"]},

    # --- Row 5 (Index 4) ---
    # 4-1 leads to 5-1, 5-2, 5-3. Expanding left side.
    {"id": "5-1", "label": "Crane\nVortex", "row": 4, "col": 0, "max_rank": 1, "req": ["4-1"]},
    {"id": "5-2", "label": "Meridian\nStrikes", "row": 4, "col": 1, "max_rank": 1, "req": ["4-1"]},
    {"id": "5-3", "label": "Rising\nStar", "row": 4, "col": 2, "max_rank": 1, "req": ["4-1"]},
    {"id": "5-4", "label": "Zenith", "row": 4, "col": 3, "max_rank": 1, "req": ["4-2"]},
    {"id": "5-5", "label": "Hit\nCombo", "row": 4, "col": 4, "max_rank": 1, "req": ["4-3"]},
    {"id": "5-6", "label": "Brawler's\nIntensity", "row": 4, "col": 6, "max_rank": 1, "req": ["4-3"]},

    # --- Row 6 (Index 5) ---
    {"id": "6-1", "label": "Jade\nIgnition", "row": 5, "col": 0, "max_rank": 1, "req": ["5-1"]},
    {"id": "6-2", "label": "Cyclone's Drift\n/ Crashing Fists", "row": 5, "col": 1, "max_rank": 1, "req": ["5-1", "5-2", "5-3"]}, # Choice Node
    {"id": "6-3", "label": "Drinking Horn\n/ Spirit Focus", "row": 5, "col": 3, "max_rank": 1, "req": ["5-4"]}, # Choice Node
    {"id": "6-4", "label": "Obsidian\nSpiral", "row": 5, "col": 4, "max_rank": 1, "req": ["5-4"]}, # Careful with overlap, moved slightly right? visual only
    {"id": "6-5", "label": "Combo\nBreaker", "row": 5, "col": 6, "max_rank": 1, "req": ["5-5", "5-6"]},

    # --- Row 7 (Index 6) ---
    {"id": "7-1", "label": "Dance of\nChi-Ji", "row": 6, "col": 0, "max_rank": 1, "req": ["6-1", "6-2", "6-3"]},
    {"id": "7-2", "label": "Shadowboxing\nTreads", "row": 6, "col": 2, "max_rank": 1, "req": ["6-2", "6-3"]},
    {"id": "7-3", "label": "SOTWL\n/ WDP", "row": 6, "col": 3, "max_rank": 1, "req": ["5-4"]}, # Middle req 5-4 directly? Text says 5-4.
    {"id": "7-4", "label": "Energy\nBurst", "row": 6, "col": 5, "max_rank": 1, "req": ["6-5"]},
    {"id": "7-5", "label": "Inner\nPeace", "row": 6, "col": 6, "max_rank": 1, "req": ["6-5"]},

    # --- Row 8 (Index 7) ---
    {"id": "8-1", "label": "Tiger Eye\nBrew (Base)", "row": 7, "col": 0, "max_rank": 1, "req": []}, # No req? Text says "no Prerequisite" (odd for row 8, maybe separate tree?)
    {"id": "8-2", "label": "Sequenced\nStrikes", "row": 7, "col": 1, "max_rank": 1, "req": ["7-1"]},
    {"id": "8-3", "label": "Sunfire\nSpiral", "row": 7, "col": 2, "max_rank": 1, "req": ["7-2"]},
    {"id": "8-4", "label": "Communion\nw/ Wind", "row": 7, "col": 3, "max_rank": 1, "req": ["7-3"]},
    {"id": "8-5", "label": "Revolving Whirl\n/ Echo Tech", "row": 7, "col": 4, "max_rank": 1, "req": ["7-3"]},
    {"id": "8-6", "label": "Universal\nEnergy", "row": 7, "col": 5, "max_rank": 1, "req": ["7-3", "7-4"]},
    {"id": "8-7", "label": "Memory of\nMonastery", "row": 7, "col": 6, "max_rank": 1, "req": ["7-4", "7-5"]},

    # --- Row 9 (Index 8) ---
    {"id": "9-1", "label": "Tiger Eye\nBuff", "row": 8, "col": 0, "max_rank": 1, "req": ["8-1"]},
    {"id": "9-2", "label": "Rushing\nJade Wind", "row": 8, "col": 1, "max_rank": 1, "req": ["8-2"]},
    {"id": "9-3", "label": "Xuen's\nBattlegear", "row": 8, "col": 2, "max_rank": 1, "req": ["8-2", "8-3", "8-4"]},
    {"id": "9-4", "label": "Thunderfist", "row": 8, "col": 3, "max_rank": 1, "req": ["8-5"]},
    {"id": "9-5", "label": "Weapon of\nWind", "row": 8, "col": 4, "max_rank": 1, "req": ["8-5"]},
    {"id": "9-6", "label": "Knowl. Broken\nTemple", "row": 8, "col": 5, "max_rank": 1, "req": ["8-5", "8-6"]},
    {"id": "9-7", "label": "Slicing\nWinds", "row": 8, "col": 6, "max_rank": 1, "req": ["8-6", "8-7"]},
    {"id": "9-8", "label": "Jadefire\nStomp", "row": 8, "col": 7, "max_rank": 1, "req": ["8-7"]}, # Col 7 overflow, adjust grid or put far right

    # --- Row 10 (Index 9) ---
    {"id": "10-1", "label": "TEB\nFinal", "row": 9, "col": 0, "max_rank": 1, "req": ["9-1"]},
    {"id": "10-2", "label": "Skyfire\nHeel", "row": 9, "col": 1, "max_rank": 1, "req": ["9-3"]},
    {"id": "10-3", "label": "Harmonic\nCombo", "row": 9, "col": 2, "max_rank": 1, "req": ["9-3"]},
    {"id": "10-4", "label": "Flurry of\nXuen", "row": 9, "col": 3, "max_rank": 1, "req": ["9-3", "9-4", "9-5"]},
    {"id": "10-5", "label": "Martial\nAgility", "row": 9, "col": 4, "max_rank": 1, "req": ["9-5"]},
    {"id": "10-6", "label": "Airborne\nRhythm", "row": 9, "col": 6, "max_rank": 1, "req": ["9-7"]},
    {"id": "10-7", "label": "Path of\nJade", "row": 9, "col": 7, "max_rank": 1, "req": ["9-8"]},
]

class TalentNode:
    def __init__(self, canvas, data, config, onClick):
        self.canvas = canvas
        self.data = data
        self.id = data["id"]
        self.max_rank = data.get("max_rank", 1)
        self.current_rank = 0
        self.reqs = data.get("req", [])
        self.onClick = onClick

        # 动态计算坐标: 稍微缩小间距以适应大树
        # 基础 X=20, 间距=130; Y=20, 间距=90
        self.x = 20 + data["col"] * 130
        self.y = 20 + data["row"] * 90
        self.width = 110
        self.height = 60

        # 颜色定义
        self.color_inactive = "#333333"
        self.color_available = "#555555"
        self.color_active = "#1b8f61"
        self.border_available = "#f1c40f"
        self.border_active = "#2ecc71"

        self.btn = ctk.CTkButton(
            master=canvas,
            text=self._get_text(),
            width=self.width,
            height=self.height,
            corner_radius=8,
            fg_color=self.color_inactive,
            border_width=2,
            border_color="#444444",
            command=self.on_left_click,
            font=("Arial", 10)
        )
        self.canvas_window = canvas.create_window(self.x, self.y, window=self.btn, anchor="nw")
        self.btn.bind("<Button-3>", self.on_right_click)

    def _get_text(self):
        return f"{self.data['label']}\n({self.current_rank}/{self.max_rank})"

    def update_visual(self, active, available):
        if active:
            self.btn.configure(fg_color=self.color_active, border_color=self.border_active)
        elif available:
            self.btn.configure(fg_color=self.color_available, border_color=self.border_available)
        else:
            self.btn.configure(fg_color=self.color_inactive, border_color="#444444")
        self.btn.configure(text=self._get_text())

    def on_left_click(self):
        self.onClick(self.id, 1)

    def on_right_click(self, event):
        self.onClick(self.id, -1)


class TalentTreeWindow(ctk.CTkToplevel):
    def __init__(self, parent, on_close_callback):
        super().__init__(parent)
        self.title("Monk Class Talent Tree")
        # 增大窗口尺寸以适应 10 层天赋
        self.geometry("1100x950")
        self.on_close_callback = on_close_callback

        # 支持滚动的 Canvas (如果屏幕太小)
        self.canvas = tk.Canvas(self, bg="#151515", highlightthickness=0, scrollregion=(0,0,1200,1000))
        
        # 滚动条
        vbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        hbar = tk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.config(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)

        self.nodes = {}
        self.selected_talents = set()

        self._build_tree()
        self._refresh_state()

        # 悬浮保存按钮 (固定在底部，不随 Canvas 滚动)
        # 注意：这里简单起见放在 Window 底部，pack 会被 Canvas 挤压，建议用 place 绝对定位或 Frame
        self.save_btn = ctk.CTkButton(self, text="Apply Build", command=self._on_save, height=40, font=("Arial", 14, "bold"))
        self.save_btn.place(relx=0.5, rely=0.95, anchor="center")

    def _build_tree(self):
        # 1. 创建节点
        for data in MONK_TALENT_DATA:
            node = TalentNode(self.canvas, data, {}, self._on_node_click)
            self.nodes[data["id"]] = node

        # 2. 绘制连线
        for data in MONK_TALENT_DATA:
            node = self.nodes[data["id"]]
            for req_id in data.get("req", []):
                if req_id in self.nodes:
                    parent = self.nodes[req_id]
                    x1 = parent.x + parent.width / 2
                    y1 = parent.y + parent.height
                    x2 = node.x + node.width / 2
                    y2 = node.y
                    self.canvas.create_line(x1, y1, x2, y2, fill="#444444", width=2, tags="conn_line")

    def _on_node_click(self, node_id, change):
        node = self.nodes[node_id]
        if change > 0:
            if node.current_rank < node.max_rank and self._is_node_available(node_id):
                node.current_rank += 1
                self.selected_talents.add(node_id)
        else:
            if node.current_rank > 0 and self._can_unlearn(node_id):
                node.current_rank -= 1
                if node.current_rank == 0:
                    self.selected_talents.discard(node_id)
        self._refresh_state()

    def _is_node_available(self, node_id):
        reqs = self.nodes[node_id].reqs
        if not reqs:
            return True # 根节点
            
        # 核心逻辑修改：OR 关系。只要任意一个父节点点满了，就解锁当前节点。
        for req_id in reqs:
            parent = self.nodes.get(req_id)
            if parent and parent.current_rank >= parent.max_rank:
                return True
        return False

    def _can_unlearn(self, node_id):
        # 简单判定：如果当前节点是其他已激活节点的前置，则不可取消
        # (严谨的 WoW 逻辑需要 BFS 检查连通性，这里简化)
        for other_id, other_node in self.nodes.items():
            if other_node.current_rank > 0:
                # 检查 other_node 是否依赖 node_id
                # 依赖判定也需要考虑 OR 逻辑：如果 node_id 是唯一激活的父节点，则不能取消
                if node_id in other_node.reqs:
                    # 检查 other_node 是否还有其他已激活的父节点
                    active_parents = 0
                    for req in other_node.reqs:
                        if self.nodes[req].current_rank >= self.nodes[req].max_rank:
                            active_parents += 1
                    
                    if active_parents <= 1:
                        # 只有当前这个父节点是激活的，如果取消了，子节点就断连了
                        return False
        return True

    def _refresh_state(self):
        for node_id, node in self.nodes.items():
            is_active = node.current_rank > 0
            is_avail = self._is_node_available(node_id)
            node.update_visual(is_active, is_avail)

    def _on_save(self):
        final_list = []
        for nid in self.selected_talents:
            # 返回带 rank 的数据，例如 "id:rank" 或简单的 id 列表(如果是rank 1)
            # 这里为了兼容旧接口，如果是 max_rank > 1，可能需要特殊处理，
            # 但旧接口只接受 list of strings。
            # 我们暂且只返回 ID。如果是多级天赋，引擎端默认视为满级或需要在TalentManager里处理等级。
            final_list.append(nid)
        print(f"Build Saved: {final_list}")
        self.on_close_callback(final_list)
        self.destroy()
