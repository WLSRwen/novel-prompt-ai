# -*- coding: utf-8 -*-
"""
历史记录模块（history_manager.py）
----------------------------------
供 Tkinter 调用：用 ``linked_list.LinkedList`` **在内存中**保存每次生成的完整提示词；
支持查看全部、按选中项删除单条、清空全部，并提供 ``sync_to_listbox`` 与列表框同步。

不依赖数据库，进程结束即清空。

运行自测（含简易 Mock 列表框，无需弹出窗口）：
    python history_manager.py

依赖：同目录 ``linked_list.py``。
"""

import os
import re
import sys
from datetime import datetime

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from typing import Any, List, Optional

from linked_list import LinkedList

# 列表行前缀 ``[#id]``，供 ``delete_selected`` / ``parse_id_from_line`` 解析
_LINE_ID_RE = re.compile(r"^\[#(\d+)\]")


class HistoryEntry:
    """
    一条历史记录：唯一编号 + 时间戳 + 完整提示词 + 列表预览。

    ``LinkedList.remove`` 使用 ``==``：此处约定**仅比较 entry_id**，便于按 id 删除。
    """

    __slots__ = ("entry_id", "created_ts", "full_text", "preview")

    def __init__(self, entry_id, created_ts, full_text, preview):
        # type: (int, str, str, str) -> None
        self.entry_id = entry_id
        self.created_ts = created_ts
        self.full_text = full_text
        self.preview = preview

    def __eq__(self, other):
        # type: (object) -> bool
        if isinstance(other, HistoryEntry):
            return self.entry_id == other.entry_id
        return False

    def __repr__(self):
        # type: () -> str
        return "HistoryEntry(id=%r, preview=%r)" % (self.entry_id, self.preview[:30])


class HistoryManager:
    """
    历史管理器：底层单链表尾插保存 ``HistoryEntry``，时间正序（旧→新）。

    列表框展示默认**新在上**：``sync_to_listbox`` 按从新到旧插入行。
    """

    def __init__(self):
        # type: () -> None
        self._chain = LinkedList()
        self._next_id = 1

    def __len__(self):
        # type: () -> int
        return len(self._chain)

    def add_record(self, full_prompt):
        # type: (str) -> int
        """
        追加一条生成记录（内存）。

        :param full_prompt: 本次完整提示词文本
        :return: 新记录的 entry_id，便于界面绑定
        """
        text = (full_prompt or "").strip()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        one_line = text.replace("\r", "").replace("\n", " ")
        preview = one_line if len(one_line) <= 72 else one_line[:69] + "..."
        entry = HistoryEntry(self._next_id, ts, text, preview)
        self._chain.add(entry)
        self._next_id += 1
        return entry.entry_id

    def all_entries_chronological(self):
        # type: () -> List[HistoryEntry]
        """从旧到新遍历链表，返回所有条目（拷贝为 list，便于界面迭代）。"""
        raw = self._chain.traverse()
        return [e for e in raw if isinstance(e, HistoryEntry)]

    def all_entries_newest_first(self):
        # type: () -> List[HistoryEntry]
        """从新到旧，便于列表框自上而下展示。"""
        xs = self.all_entries_chronological()
        return list(reversed(xs))

    def format_list_line(self, entry):
        # type: (HistoryEntry) -> str
        """生成列表框一行展示文本（含可解析的 id 前缀）。"""
        return "[#%d] %s | %s" % (entry.entry_id, entry.created_ts, entry.preview)

    def get_full_text(self, entry_id):
        # type: (int) -> str
        """
        按 id 取完整提示词；不存在时抛 ``KeyError``。
        """
        for e in self.all_entries_chronological():
            if e.entry_id == entry_id:
                return e.full_text
        raise KeyError(entry_id)

    def delete_by_id(self, entry_id):
        # type: (int) -> bool
        """
        按唯一 id 删除一条记录（链表 ``remove``）。

        :return: 是否删除成功
        """
        stub = HistoryEntry(entry_id, "", "", "")
        return self._chain.remove(stub)

    def clear(self):
        # type: () -> None
        """清空全部历史（O(1) 换空链表，释放结点由 GC 回收）。"""
        self._chain = LinkedList()

    @staticmethod
    def parse_id_from_line(line):
        # type: (str) -> Optional[int]
        """从 ``format_list_line`` 格式的行首解析 entry_id；失败返回 None。"""
        m = _LINE_ID_RE.match((line or "").strip())
        if not m:
            return None
        return int(m.group(1))

    def sync_to_listbox(self, listbox):
        # type: (Any) -> None
        """
        用当前内存历史**重写**列表框内容（先清空再插入）。

        :param listbox: ``tkinter.Listbox`` 实例；需支持 ``delete`` / ``insert``。
        """
        import tkinter as tk

        listbox.delete(0, tk.END)
        for entry in self.all_entries_newest_first():
            listbox.insert(tk.END, self.format_list_line(entry))

    def delete_selected_in_listbox(self, listbox):
        # type: (Any) -> bool
        """
        读取列表框当前选中行，解析 id 并删除对应记录，**并调用** ``sync_to_listbox`` 刷新。

        :return: 是否成功删除一条；无选中或解析失败返回 False
        """
        import tkinter as tk

        sel = listbox.curselection()
        if not sel:
            return False
        line = listbox.get(sel[0])
        eid = self.parse_id_from_line(line)
        if eid is None:
            return False
        if not self.delete_by_id(eid):
            return False
        self.sync_to_listbox(listbox)
        return True

    def clear_and_refresh_listbox(self, listbox):
        # type: (Any) -> None
        """清空内存历史并刷新列表框。"""
        self.clear()
        self.sync_to_listbox(listbox)


def _self_test():
    # type: () -> None
    """无 GUI：用 Mock 列表框验证增删查与同步逻辑。"""

    class MockListbox(object):
        def __init__(self):
            self.items = []  # type: List[str]
            self._sel = ()  # type: tuple

        def delete(self, first, last=None):
            if last is None:
                last = first
            if first == 0 and str(last).lower() == "end":
                self.items = []

        def insert(self, index, text):
            self.items.append(text)

        def get(self, index):
            return self.items[index]

        def curselection(self):
            return self._sel

        def set_selection(self, index):
            self._sel = (index,)

    import tkinter as tk

    # 让 Mock 的 delete(0, tk.END) 清空：END 参与判断
    _orig_end = tk.END

    class MockListbox2(MockListbox):
        def delete(self, first, last=None):
            if first == 0 and last == _orig_end:
                self.items = []
            else:
                super(MockListbox2, self).delete(first, last)

    hm = HistoryManager()
    assert len(hm) == 0

    i1 = hm.add_record("第一版提示词\n段落A")
    i2 = hm.add_record("第二版提示词")
    assert len(hm) == 2 and i2 > i1

    chrono = hm.all_entries_chronological()
    assert chrono[0].entry_id == i1 and chrono[-1].entry_id == i2

    lb = MockListbox2()
    hm.sync_to_listbox(lb)
    assert len(lb.items) == 2
    assert "[#%d]" % i2 in lb.items[0]

    lb.set_selection(0)
    assert hm.delete_selected_in_listbox(lb) is True
    assert len(hm) == 1
    assert hm.get_full_text(i1) == "第一版提示词\n段落A"

    hm.clear_and_refresh_listbox(lb)
    assert len(hm) == 0 and len(lb.items) == 0

    print("history_manager.py 自测通过。")


if __name__ == "__main__":
    _self_test()
