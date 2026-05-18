# -*- coding: utf-8 -*-
"""
手写队列模块 ``my_queue.py``（避免与标准库 ``queue`` 同名导致 ``import queue`` 冲突）。
------------------------------------------------------
用途：在窗口程序里按 FIFO 排队「解析 → 设定生成 → 剧情生成 → 组装」等阶段任务。

实现说明：
- **不**使用标准库 ``collections.deque`` 或 ``queue.Queue`` 作为底层容器。
- ``enqueue``：链表 ``add``，表尾入队，O(1)。
- ``dequeue``：链表 ``pop_front``，表头出队，O(1)。
- ``is_empty``：委托 ``LinkedList.is_empty``。

其它模块请使用：``from my_queue import Queue``。

运行自测：``python my_queue.py``
"""

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from typing import Any

from linked_list import LinkedList


class Queue(object):
    """
    FIFO 队列，底层为手写单链表。

    - ``enqueue(item)``：入队
    - ``dequeue()``：出队并返回队首；空队列抛出 ``IndexError``
    - ``is_empty()``：是否为空
    """

    def __init__(self):
        # type: () -> None
        self._data = LinkedList()

    def is_empty(self):
        # type: () -> bool
        return self._data.is_empty()

    def enqueue(self, item):
        # type: (Any) -> None
        """入队：元素置于队尾。"""
        self._data.add(item)

    def dequeue(self):
        # type: () -> Any
        """
        出队：移除并返回队首元素。

        :raises IndexError: 空队列
        """
        if self._data.is_empty():
            raise IndexError("dequeue from empty queue")
        front = self._data.pop_front()
        if front is None:
            raise RuntimeError("queue internal error: empty after is_empty check")
        return front

    def __len__(self):
        # type: () -> int
        return len(self._data)

    def __repr__(self):
        # type: () -> str
        return "Queue(%s)" % self._data.traverse()


def _demo():
    # type: () -> None
    q = Queue()
    assert q.is_empty() is True

    q.enqueue("步骤1：解析用户脑洞")
    q.enqueue("步骤2：加载人设与世界观")
    q.enqueue("步骤3：生成剧情骨架")
    q.enqueue("步骤4：组装最终提示词")

    assert len(q) == 4
    assert q.dequeue() == "步骤1：解析用户脑洞"
    assert q.dequeue() == "步骤2：加载人设与世界观"
    assert len(q) == 2

    q.enqueue("步骤5：写入历史记录")
    assert q.dequeue() == "步骤3：生成剧情骨架"
    assert q.dequeue() == "步骤4：组装最终提示词"
    assert q.dequeue() == "步骤5：写入历史记录"

    assert q.is_empty() is True
    try:
        q.dequeue()
    except IndexError as e:
        assert "empty" in str(e).lower()

    q2 = Queue()
    q2.enqueue("task")
    q2.enqueue("task")
    assert q2.dequeue() == "task"
    assert q2.dequeue() == "task"
    assert q2.is_empty()

    print("Queue 自测通过，repr:", repr(Queue()))


if __name__ == "__main__":
    _demo()
