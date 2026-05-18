# -*- coding: utf-8 -*-
"""
小说提示词 AI —— 主程序（main.py）
---------------------------------
整合：手写 HashMap、单链表、队列（``prompt_assembler`` 管线）+ 本地 LM Studio
``qwen/qwen3.5-9b`` 两阶段 JSON 生成 + 历史链表。

运行：``python main.py``（需同目录依赖齐全，且 LM Studio 已监听 1234 端口）

异常提示（课设要求）：
- 网络：弹窗 + 状态栏「内容获取失败：请检查 LM Studio 是否启动并加载 qwen/qwen3.5-9b」
- 解析 JSON 失败：弹窗 + 状态栏「解析失败：脑洞格式不清晰，请重新输入」
- 空输入：状态栏「请输入脑洞内容」
"""

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from typing import Any, Optional

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from hash_map import HashMap
from history_manager import HistoryManager
from lm_studio import LMStudioJsonError, LMStudioNetworkError, MODEL_NAME
from prompt_assembler import run_prompt_pipeline

THEMES = ("玄幻", "都市", "科幻", "古风", "末世", "校园")

ERR_NET = (
    "内容获取失败：请检查 LM Studio 是否启动并加载 %s" % MODEL_NAME
)
ERR_JSON_PARSE = "解析失败：脑洞格式不清晰，请重新输入"
ERR_JSON_SETTING = "生成失败：模型返回格式异常，请重试或简化脑洞"


def _body_font(size, weight="normal"):
    # type: (int, str) -> tuple
    if weight == "bold":
        return ("Microsoft YaHei UI", size, "bold")
    return ("Microsoft YaHei UI", size)


class NovelPromptApp(object):
    WIN_WIDTH = 860
    WIN_HEIGHT = 720

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("小说提示词 AI · LM Studio %s" % MODEL_NAME)

        self.root.resizable(False, False)
        self.root.minsize(self.WIN_WIDTH, self.WIN_HEIGHT)
        self.root.maxsize(self.WIN_WIDTH, self.WIN_HEIGHT)

        self._current_map = None  # type: Optional[HashMap]
        self._history = HistoryManager()
        self._theme_var = tk.StringVar(value="玄幻")
        self._status_var = tk.StringVar(
            value="就绪：选择主题，输入脑洞；需 LM Studio 加载 %s。" % MODEL_NAME
        )

        self._apply_style()
        self._build_ui()
        self._center_window()
        self._bind_events()

    def _apply_style(self):
        style = ttk.Style(self.root)
        try:
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TLabel", padding=2)
        style.configure("TButton", padding=(10, 4))

    def _center_window(self):
        self.root.update_idletasks()
        w, h = self.WIN_WIDTH, self.WIN_HEIGHT
        x = max((self.root.winfo_screenwidth() - w) // 2, 0)
        y = max((self.root.winfo_screenheight() - h) // 2, 0)
        self.root.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}
        bf = _body_font(10)
        bf_small = _body_font(9)
        title_font = _body_font(16, "bold")

        ttk.Label(
            self.root,
            text="小说提示词 AI 生成器",
            font=title_font,
            anchor="center",
        ).grid(row=0, column=0, columnspan=6, sticky="ew", **pad)

        theme_lf = ttk.LabelFrame(self.root, text=" 创作主题（单选） ", padding=8)
        theme_lf.grid(row=1, column=0, columnspan=6, sticky="ew", padx=12, pady=(2, 6))
        for i, name in enumerate(THEMES):
            r, c = divmod(i, 3)
            ttk.Radiobutton(
                theme_lf,
                text=name,
                value=name,
                variable=self._theme_var,
            ).grid(row=r, column=c, padx=10, pady=4, sticky="w")

        input_lf = ttk.LabelFrame(self.root, text=" 脑洞输入 ", padding=8)
        input_lf.grid(row=2, column=0, columnspan=6, sticky="ew", padx=12, pady=4)
        input_lf.columnconfigure(0, weight=1)

        ttk.Label(
            input_lf,
            text="【示例：普通上班族获得读心术，逆袭职场大佬】",
            font=bf_small,
            foreground="#555555",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        self.idea_entry = ttk.Entry(input_lf, font=bf)
        self.idea_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))

        self.generate_btn = ttk.Button(
            input_lf,
            text="生成提示词",
            command=self._on_generate_clicked,
            width=14,
        )
        self.generate_btn.grid(row=1, column=1, sticky="e")

        result_lf = ttk.LabelFrame(self.root, text=" 生成结果（只读，可复制） ", padding=6)
        result_lf.grid(row=3, column=0, columnspan=6, sticky="nsew", padx=12, pady=4)
        result_lf.rowconfigure(0, weight=1)
        result_lf.columnconfigure(0, weight=1)

        self.result_text = scrolledtext.ScrolledText(
            result_lf,
            height=18,
            wrap=tk.WORD,
            font=bf,
            state=tk.DISABLED,
        )
        self.result_text.grid(row=0, column=0, sticky="nsew")

        hist_lf = ttk.LabelFrame(self.root, text=" 历史记录（新在上 · 双击加载全文） ", padding=6)
        hist_lf.grid(row=4, column=0, columnspan=6, sticky="nsew", padx=12, pady=4)
        hist_lf.rowconfigure(0, weight=1)
        hist_lf.columnconfigure(0, weight=1)

        self.history_list = tk.Listbox(
            hist_lf,
            height=6,
            font=bf_small,
            exportselection=False,
            selectmode=tk.BROWSE,
        )
        self.history_list.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(hist_lf, orient=tk.VERTICAL, command=self.history_list.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.history_list.configure(yscrollcommand=sb.set)

        btn_row = ttk.Frame(self.root)
        btn_row.grid(row=5, column=0, columnspan=6, sticky="e", padx=12, pady=(2, 4))
        ttk.Button(btn_row, text="删除选中", command=self._on_delete_history, width=12).pack(
            side=tk.RIGHT, padx=(6, 0)
        )
        ttk.Button(btn_row, text="清空历史", command=self._on_clear_history, width=12).pack(side=tk.RIGHT)

        ttk.Label(
            self.root,
            textvariable=self._status_var,
            relief=tk.SUNKEN,
            anchor="w",
            padding=(10, 6),
            font=bf_small,
        ).grid(row=6, column=0, columnspan=6, sticky="ew", padx=12, pady=(0, 8))

        self.root.rowconfigure(3, weight=2)
        self.root.rowconfigure(4, weight=1)
        self.root.columnconfigure(0, weight=1)

    def _bind_events(self):
        self.history_list.bind("<Double-Button-1>", self._on_history_double_click)
        self.idea_entry.bind("<Return>", lambda e: self._on_generate_clicked())

    def _set_result_text(self, content):
        # type: (str) -> None
        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, content or "")
        self.result_text.configure(state=tk.DISABLED)

    def _on_generate_clicked(self):
        idea = self.idea_entry.get().strip()
        if not idea:
            self._status_var.set("请输入脑洞内容")
            return
        self._status_var.set("正在请求本地模型：解析 JSON → 生成设定与提示词 …")
        self.generate_btn.configure(state=tk.DISABLED)
        self.idea_entry.configure(state=tk.DISABLED)
        self.root.configure(cursor="watch")
        self.root.update_idletasks()
        self.root.after(20, self._run_generation_job)

    def _run_generation_job(self):
        idea = self.idea_entry.get().strip()
        theme = self._theme_var.get()
        try:
            hm = HashMap()
            self._current_map = hm
            prompt, _beats, errs = run_prompt_pipeline(
                idea, hm, theme=theme, rethrow_llm_errors=True
            )
            self._set_result_text(prompt)
            if prompt and prompt.strip():
                self._history.add_record(prompt)
                self._history.sync_to_listbox(self.history_list)
            if errs:
                self._status_var.set("已完成（附带 %d 条内部告警）。" % len(errs))
            else:
                self._status_var.set("成功：已写入结果与历史（HashMap / 链表 / 队列已使用）。")
        except LMStudioNetworkError:
            self._status_var.set(ERR_NET)
            messagebox.showerror("网络 / 服务", ERR_NET)
            self._set_result_text("")
        except LMStudioJsonError as je:
            if getattr(je, "phase", "parse") == "parse":
                self._status_var.set(ERR_JSON_PARSE)
                messagebox.showwarning("解析", ERR_JSON_PARSE)
            else:
                self._status_var.set(ERR_JSON_SETTING)
                messagebox.showwarning("生成", ERR_JSON_SETTING)
            self._set_result_text("")
        except Exception as e:
            self._status_var.set("失败：%s" % e)
            messagebox.showerror("错误", str(e))
            self._set_result_text("")
        finally:
            self.generate_btn.configure(state=tk.NORMAL)
            self.idea_entry.configure(state=tk.NORMAL)
            self.root.configure(cursor="")

    def _on_clear_history(self):
        self._history.clear_and_refresh_listbox(self.history_list)
        self._status_var.set("历史已清空。")

    def _on_delete_history(self):
        if self._history.delete_selected_in_listbox(self.history_list):
            self._status_var.set("已删除选中条目。")
        else:
            self._status_var.set("请先选中一行历史。")

    def _on_history_double_click(self, event):
        # type: (Any) -> None
        try:
            idx = self.history_list.nearest(event.y)
            line = self.history_list.get(idx)
        except tk.TclError:
            return
        eid = HistoryManager.parse_id_from_line(line)
        if eid is None:
            return
        try:
            full = self._history.get_full_text(eid)
        except KeyError:
            return
        self._set_result_text(full)
        self._status_var.set("已加载历史 # %d" % eid)

    def run(self):
        self.root.mainloop()


def main():
    NovelPromptApp().run()


if __name__ == "__main__":
    main()
