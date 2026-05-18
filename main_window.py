# -*- coding: utf-8 -*-
"""
小说提示词 AI —— 纯界面骨架（main_window.py）
--------------------------------------------
课设**完整可交互程序**请以 ``main.py`` 为入口（已整合管线与历史）。

本文件保留最小 Tk 窗口，便于对照「仅 UI」与「UI+业务」差异；直接运行本文件
仅打开占位窗口，不调用 HashMap / 链表 / 队列。

运行：``python main_window.py``  正式课设演示：``python main.py``
"""

import tkinter as tk
from tkinter import scrolledtext, ttk


class MainWindow(object):
    WIN_WIDTH = 820
    WIN_HEIGHT = 640

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("小说提示词AI — UI 骨架（请运行 main.py）")
        self.root.resizable(False, False)
        self.root.minsize(self.WIN_WIDTH, self.WIN_HEIGHT)
        self.root.maxsize(self.WIN_WIDTH, self.WIN_HEIGHT)
        self._status_var = tk.StringVar(value="此为占位界面；完整功能请运行 main.py")
        self._build()
        self._center()

    def _center(self):
        self.root.update_idletasks()
        w, h = self.WIN_WIDTH, self.WIN_HEIGHT
        x = max((self.root.winfo_screenwidth() - w) // 2, 0)
        y = max((self.root.winfo_screenheight() - h) // 2, 0)
        self.root.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def _build(self):
        ttk.Label(self.root, text="UI 骨架 · 无业务逻辑", font=("Microsoft YaHei UI", 14, "bold")).pack(
            pady=12
        )
        ttk.Entry(self.root, width=60).pack(pady=4, padx=12, fill=tk.X)
        ttk.Button(self.root, text="生成提示词（占位）").pack(pady=4)
        st = scrolledtext.ScrolledText(self.root, height=12, state=tk.DISABLED)
        st.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        ttk.Label(self.root, textvariable=self._status_var, relief=tk.SUNKEN, anchor=tk.W).pack(
            fill=tk.X, padx=12, pady=6
        )

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    MainWindow().run()
