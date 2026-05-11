import tkinter as tk
from tkinter import ttk, messagebox
import ctypes
import json
import re
import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
DATA_FILE = os.path.join(APP_DIR, "teleport_data.json")

WORLDS = {
    "主世界": "minecraft:overworld",
    "下界": "minecraft:the_nether",
    "末地": "minecraft:the_end",
}

DEFAULT_WORLD = "主世界"

DIM_MAP = {
    "minecraft:overworld": "主世界", "overworld": "主世界",
    "minecraft:the_nether": "下界", "the_nether": "下界", "nether": "下界",
    "minecraft:the_end": "末地", "the_end": "末地", "end": "末地",
}


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"points": []}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_coords(text):
    text = text.strip()
    world = None

    m = re.match(
        r"/?execute\s+in\s+(\S+)\s+run\s+tp\s+@s\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)",
        text, flags=re.IGNORECASE,
    )
    if m:
        world = DIM_MAP.get(m.group(1))
        return float(m.group(2)), float(m.group(3)), float(m.group(4)), world

    text = text.lstrip("/")
    text = re.sub(r"^(tp|teleport)\s+", "", text, flags=re.IGNORECASE)
    parts = text.split()
    if len(parts) >= 3:
        try:
            return float(parts[0]), float(parts[1]), float(parts[2]), world
        except ValueError:
            pass
    return None


def fmt_coord(v):
    if v == int(v):
        return str(int(v))
    return f"{v:.2f}".rstrip("0").rstrip(".")


def build_command(x, y, z, world_name):
    dimension = WORLDS.get(world_name, "minecraft:overworld")
    return f"execute as @p in {dimension} run tp @s {fmt_coord(x)} {fmt_coord(y)} {fmt_coord(z)}"


class EditDialog:
    def __init__(self, parent, app, idx):
        self.app = app
        self.idx = idx
        point = app.data["points"][idx]

        self.dlg = tk.Toplevel(parent)
        self.dlg.title(f"编辑 - {point['name']}")
        self.dlg.geometry("340x300")
        self.dlg.resizable(False, False)
        self.dlg.transient(parent)
        self.dlg.grab_set()

        f = ttk.Frame(self.dlg, padding=15)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="名称").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.name_var = tk.StringVar(value=point["name"])
        ttk.Entry(f, textvariable=self.name_var, width=28).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(f, text="世界").grid(row=2, column=0, sticky="w", pady=(0, 2))
        wf = ttk.Frame(f)
        wf.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.world_var = tk.StringVar(value=point.get("world", DEFAULT_WORLD))
        for wn in WORLDS:
            ttk.Radiobutton(wf, text=wn, variable=self.world_var, value=wn).pack(
                side=tk.LEFT, padx=(0, 8))

        cs = f"{fmt_coord(point['x'])}  {fmt_coord(point['y'])}  {fmt_coord(point['z'])}"
        ttk.Label(f, text="坐标").grid(row=4, column=0, sticky="w", pady=(0, 2))
        ttk.Label(f, text=cs, font=("Consolas", 10)).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(f, text="排序").grid(row=6, column=0, sticky="w")
        sf = ttk.Frame(f)
        sf.grid(row=6, column=1, sticky="e")
        ttk.Button(sf, text="↑ 上移", command=self._move_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(sf, text="↓ 下移", command=self._move_down).pack(side=tk.LEFT)

        bf = ttk.Frame(f)
        bf.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        tk.Button(
            bf, text="删除", bg="#e74c3c", fg="white",
            activebackground="#c0392b", activeforeground="white",
            relief="flat", padx=14, pady=4, cursor="hand2",
            command=self._delete,
        ).pack(side=tk.LEFT)
        ttk.Button(bf, text="保存", command=self._save).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(bf, text="取消", command=self.dlg.destroy).pack(side=tk.RIGHT)

    def _move_up(self):
        if self.idx > 0:
            self.app.data["points"].insert(self.idx - 1, self.app.data["points"].pop(self.idx))
            save_data(self.app.data)
            self.idx -= 1
            self.app._refresh_list()
            self.dlg.lift()

    def _move_down(self):
        if self.idx < len(self.app.data["points"]) - 1:
            self.app.data["points"].insert(self.idx + 1, self.app.data["points"].pop(self.idx))
            save_data(self.app.data)
            self.idx += 1
            self.app._refresh_list()
            self.dlg.lift()

    def _delete(self):
        pn = self.app.data["points"][self.idx]["name"]
        if messagebox.askyesno("确认删除", f"确定要删除「{pn}」？", parent=self.dlg):
            del self.app.data["points"][self.idx]
            save_data(self.app.data)
            self.app._refresh_list()
            self.dlg.destroy()

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "名称不能为空", parent=self.dlg)
            return
        self.app.data["points"][self.idx]["name"] = name
        self.app.data["points"][self.idx]["world"] = self.world_var.get()
        save_data(self.app.data)
        self.app._refresh_list()
        self.dlg.destroy()


def set_app_icon(root):
    if getattr(sys, "frozen", False):
        root.iconbitmap(sys.argv[0])
    else:
        ico = os.path.join(APP_DIR, "icon.ico")
        if os.path.exists(ico):
            root.iconbitmap(ico)


class TeleportApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MC 传送点记录")
        self.root.geometry("740x520")
        self.root.minsize(520, 340)

        self.data = load_data()
        self.selected_world = tk.StringVar(value=DEFAULT_WORLD)

        self._build_input_area()
        self._build_world_selector()
        self._build_list()
        self._build_status_bar()
        self._build_context_menu()
        self._refresh_list()

    # ── input ───────────────────────────────────────────────
    def _build_input_area(self):
        f = ttk.Frame(self.root, padding="10 10 10 6")
        f.pack(fill=tk.X)

        ttk.Label(f, text="坐标:").pack(side=tk.LEFT)
        self.coord_entry = ttk.Entry(f, width=36)
        self.coord_entry.pack(side=tk.LEFT, padx=(6, 6))
        self.coord_entry.bind("<Return>", lambda e: self.add_point())
        self.coord_entry.focus_set()

        ttk.Label(f, text="名称:").pack(side=tk.LEFT)
        self.name_entry = ttk.Entry(f, width=16)
        self.name_entry.pack(side=tk.LEFT, padx=(6, 6))
        self.name_entry.bind("<Return>", lambda e: self.add_point())

        ttk.Button(f, text="＋ 添加", command=self.add_point).pack(side=tk.LEFT, padx=(4, 0))

    # ── world selector ──────────────────────────────────────
    def _build_world_selector(self):
        f = ttk.Frame(self.root, padding="10 2 10 6")
        f.pack(fill=tk.X)

        ttk.Label(f, text="传送点所在世界:").pack(side=tk.LEFT, padx=(0, 8))
        for wn in WORLDS:
            ttk.Radiobutton(f, text=wn, variable=self.selected_world, value=wn).pack(
                side=tk.LEFT, padx=(0, 6))

    # ── treeview list ───────────────────────────────────────
    def _build_list(self):
        # Style: increase row height
        style = ttk.Style()
        style.configure("Treeview", rowheight=32, font=("Microsoft YaHei UI", 10))

        outer = ttk.Frame(self.root, padding="10 0 10 10")
        outer.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            outer,
            columns=("name", "coords", "world", "hint"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("name", text="名称")
        self.tree.heading("coords", text="坐标")
        self.tree.heading("world", text="世界")
        self.tree.heading("hint", text="操作")

        self.tree.column("name", width=160, minwidth=80, stretch=True)
        self.tree.column("coords", width=180, minwidth=120, stretch=True)
        self.tree.column("world", width=70, minwidth=60, stretch=False)
        self.tree.column("hint", width=100, minwidth=90, stretch=False)

        sb = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        # Row tags for alternating colors
        self.tree.tag_configure("odd", background="#f4f4f4")
        self.tree.tag_configure("even", background="white")

        # Bindings
        self.tree.bind("<ButtonRelease-1>", self._on_click)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)

        # Keyboard: Delete to remove
        self.root.bind("<Delete>", lambda e: self._delete_selected())

    # ── status bar ──────────────────────────────────────────
    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg="#e8e8e8", height=26)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        tips = [
            ("🖱 单击行", "#0078d4"),
            ("复制传送指令", "#555"),
            ("  │  ", "#ccc"),
            ("🖱 双击行", "#0078d4"),
            ("编辑", "#555"),
            ("  │  ", "#ccc"),
            ("🖱 右键", "#0078d4"),
            ("更多操作", "#555"),
            ("  │  ", "#ccc"),
            ("⌨ Delete", "#0078d4"),
            ("删除", "#555"),
        ]
        for text, color in tips:
            tk.Label(
                bar, text=text, bg="#e8e8e8", fg=color,
                font=("Microsoft YaHei UI", 8),
            ).pack(side=tk.LEFT)
            if text == "  │  ":
                bar.pack_configure()

    # ── context menu ────────────────────────────────────────
    def _build_context_menu(self):
        self.ctx_menu = tk.Menu(self.root, tearoff=0)
        self.ctx_menu.add_command(label="📋 复制传送指令", command=self._ctx_copy)
        self.ctx_menu.add_command(label="✎ 编辑", command=self._ctx_edit)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="↑ 上移", command=self._ctx_move_up)
        self.ctx_menu.add_command(label="↓ 下移", command=self._ctx_move_down)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="🗑 删除", command=self._ctx_delete)

    def _ctx_idx(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _ctx_copy(self):
        i = self._ctx_idx()
        if i is not None:
            self._copy_point(i)

    def _ctx_edit(self):
        i = self._ctx_idx()
        if i is not None:
            self._open_edit(i)

    def _ctx_move_up(self):
        i = self._ctx_idx()
        if i is not None and i > 0:
            self.data["points"].insert(i - 1, self.data["points"].pop(i))
            save_data(self.data)
            self._refresh_list()
            self.tree.selection_set(str(i - 1))

    def _ctx_move_down(self):
        i = self._ctx_idx()
        if i is not None and i < len(self.data["points"]) - 1:
            self.data["points"].insert(i + 1, self.data["points"].pop(i))
            save_data(self.data)
            self._refresh_list()
            self.tree.selection_set(str(i + 1))

    def _ctx_delete(self):
        i = self._ctx_idx()
        if i is not None:
            self._delete_selected()

    # ── events ──────────────────────────────────────────────
    def _on_click(self, event):
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item:
            return
        # Clicking the hint column copies
        if col == "#4":
            self._copy_point(int(item))

    def _on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self._open_edit(int(item))

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.ctx_menu.post(event.x_root, event.y_root)

    # ── data ────────────────────────────────────────────────
    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.data["points"]:
            return

        for i, p in enumerate(self.data["points"]):
            tag = "odd" if i % 2 == 0 else "even"
            cs = f"{fmt_coord(p['x'])}  {fmt_coord(p['y'])}  {fmt_coord(p['z'])}"
            ws = p.get("world", DEFAULT_WORLD)
            self.tree.insert(
                "", tk.END, iid=str(i), tags=(tag,),
                values=(p["name"], cs, ws, "「 复制 」"),
            )

    def add_point(self):
        raw = self.coord_entry.get().strip()
        name = self.name_entry.get().strip()

        if not raw:
            messagebox.showwarning("提示", "请输入坐标")
            return

        result = parse_coords(raw)
        if result is None:
            messagebox.showwarning(
                "提示",
                "无法解析坐标\n支持: /tp x y z  |  x y z  |  F3+C 复制",
            )
            return

        x, y, z, dw = result
        if not name:
            name = f"点 {len(self.data['points']) + 1}"
        world = dw if dw else self.selected_world.get()

        self.data["points"].append(
            {"name": name, "x": x, "y": y, "z": z, "world": world}
        )
        save_data(self.data)
        self._refresh_list()
        self.coord_entry.delete(0, tk.END)
        self.name_entry.delete(0, tk.END)
        self.coord_entry.focus_set()

    def _copy_point(self, idx):
        p = self.data["points"][idx]
        cmd = build_command(p["x"], p["y"], p["z"], p.get("world", DEFAULT_WORLD))
        self.root.clipboard_clear()
        self.root.clipboard_append(cmd)
        self.root.update()

    def _open_edit(self, idx):
        EditDialog(self.root, self, idx)

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        i = int(sel[0])
        pn = self.data["points"][i]["name"]
        if messagebox.askyesno("确认删除", f"确定要删除「{pn}」？"):
            del self.data["points"][i]
            save_data(self.data)
            self._refresh_list()


def main():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mc.teleport.tool")
    except Exception:
        pass

    root = tk.Tk()
    set_app_icon(root)
    TeleportApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
