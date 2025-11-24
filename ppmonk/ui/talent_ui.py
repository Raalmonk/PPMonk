import customtkinter as ctk
import tkinter as tk

# --- 天赋树数据结构 (模拟影踪派) ---
# 坐标系统: (Row, Column) 0-based
SHADO_PAN_DATA = [
    # Row 0 (基石)
    {"id": "overwhelming_flurry", "label": "Overwhelming\nFlurry", "row": 0, "col": 1, "max_rank": 1, "req": []},

    # Row 1
    {"id": "pride", "label": "Pride of\nPandaria", "row": 1, "col": 0, "max_rank": 1, "req": ["overwhelming_flurry"]},
    {"id": "high_impact", "label": "High\nImpact", "row": 1, "col": 2, "max_rank": 1, "req": ["overwhelming_flurry"]},

    # Row 2 (选择节点示例)
    {"id": "protect", "label": "Protect &\nServe", "row": 2, "col": 0, "max_rank": 1, "req": ["pride"]},
    {"id": "martial", "label": "Martial\nPrecision", "row": 2, "col": 1, "max_rank": 1, "req": ["overwhelming_flurry"]},

    # Row 3 (核心大招)
    {"id": "wdp_hero", "label": "Whirling\nSteel", "row": 3, "col": 1, "max_rank": 1, "req": ["martial"]},
    {"id": "against_odds", "label": "Against\nAll Odds", "row": 3, "col": 2, "max_rank": 1, "req": ["high_impact"]},

    # Row 4 (终极天赋)
    {"id": "wisdom", "label": "Wisdom of\nthe Wall", "row": 4, "col": 1, "max_rank": 1, "req": ["wdp_hero", "against_odds"]},
]


class TalentNode:
    def __init__(self, canvas, data, config, onClick):
        self.canvas = canvas
        self.data = data
        self.id = data["id"]
        self.max_rank = data.get("max_rank", 1)
        self.current_rank = 0
        self.reqs = data.get("req", [])
        self.children = []  # 运行时填充
        self.onClick = onClick

        # 计算坐标
        # x_gap = 120, y_gap = 100, margin = 50
        self.x = 50 + data["col"] * 140
        self.y = 50 + data["row"] * 100
        self.width = 100
        self.height = 60

        # 绘制连接线 (Lines) - 需要父节点先存在，或者后处理
        # 这里我们采用简单策略：在 Window 里统一画线，Node 只管画自己

        # 绘制按钮 (Node)
        self.btn = ctk.CTkButton(
            master=canvas,
            text=f"{data['label']}\n({self.current_rank}/{self.max_rank})",
            width=self.width,
            height=self.height,
            corner_radius=10,
            fg_color="#333333",  # 未激活灰
            border_width=2,
            border_color="#555555",
            command=self.on_left_click,
        )
        # 将组件放置在 Canvas 上
        # tkinter canvas create_window 允许放置 widget
        self.canvas_window = canvas.create_window(self.x, self.y, window=self.btn, anchor="nw")

        # 绑定右键取消
        self.btn.bind("<Button-3>", self.on_right_click)

    def update_visual(self, active, available):
        if active:
            self.btn.configure(fg_color="#1b8f61", border_color="#2ecc71")  # 绿色激活
        elif available:
            self.btn.configure(fg_color="#555555", border_color="#f1c40f")  # 黄色可选
        else:
            self.btn.configure(fg_color="#333333", border_color="#555555")  # 灰色不可用

        self.btn.configure(text=f"{self.data['label']}\n({self.current_rank}/{self.max_rank})")

    def on_left_click(self):
        self.onClick(self.id, 1)

    def on_right_click(self, event):
        self.onClick(self.id, -1)


class TalentTreeWindow(ctk.CTkToplevel):
    def __init__(self, parent, on_close_callback):
        super().__init__(parent)
        self.title("Shado-Pan Talent Calculator")
        self.geometry("600x700")
        self.on_close_callback = on_close_callback

        # 画布
        self.canvas = tk.Canvas(self, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)

        self.nodes = {}
        self.selected_talents = set()

        self._build_tree()
        self._refresh_state()

        # 底部保存按钮
        save_btn = ctk.CTkButton(self, text="Confirm Build", command=self._on_save)
        save_btn.pack(pady=10)

    def _build_tree(self):
        # 1. 创建节点
        for data in SHADO_PAN_DATA:
            node = TalentNode(self.canvas, data, {}, self._on_node_click)
            self.nodes[data["id"]] = node

        # 2. 绘制连线 (底层)
        for data in SHADO_PAN_DATA:
            node = self.nodes[data["id"]]
            for req_id in data.get("req", []):
                if req_id in self.nodes:
                    parent = self.nodes[req_id]
                    # 画线：从父节点底部中心 -> 子节点顶部中心
                    x1 = parent.x + parent.width / 2
                    y1 = parent.y + parent.height
                    x2 = node.x + node.width / 2
                    y2 = node.y
                    self.canvas.create_line(x1, y1, x2, y2, fill="#555555", width=2, tags="conn_line")

    def _on_node_click(self, node_id, change):
        node = self.nodes[node_id]

        # 加点逻辑
        if change > 0:
            if node.current_rank < node.max_rank and self._is_node_available(node_id):
                node.current_rank += 1
                self.selected_talents.add(node_id)
        # 减点逻辑
        else:
            if node.current_rank > 0 and self._can_unlearn(node_id):
                node.current_rank -= 1
                if node.current_rank == 0:
                    self.selected_talents.discard(node_id)

        self._refresh_state()

    def _is_node_available(self, node_id):
        # 检查前置条件：所有 req 节点必须已满级 (简化逻辑)
        reqs = self.nodes[node_id].reqs
        if not reqs:
            return True  # 根节点
        for req_id in reqs:
            if self.nodes[req_id].current_rank < self.nodes[req_id].max_rank:
                return False
        return True

    def _can_unlearn(self, node_id):
        # 检查是否被其他已激活节点依赖
        for other_id, other_node in self.nodes.items():
            if other_node.current_rank > 0 and node_id in other_node.reqs:
                return False  # 不能取消，因为下面还有点
        return True

    def _refresh_state(self):
        for node_id, node in self.nodes.items():
            is_active = node.current_rank > 0
            is_avail = self._is_node_available(node_id)
            node.update_visual(is_active, is_avail)

    def _on_save(self):
        # 将选中的天赋 ID 列表传回主界面
        final_list = list(self.selected_talents)
        print(f"Selected Talents: {final_list}")
        self.on_close_callback(final_list)
        self.destroy()
