# -*- coding: utf-8 -*-
"""
手写单链表（Singly Linked List）
------------------------------
用途示例：在窗口程序中按顺序保存「剧情框架节点」或「历史提示词」等条目；
          新条目追加到表尾，遍历时保持插入顺序。

结构说明：
- 每个元素封装为 Node，含数据域与 next 指针。
- LinkedList 维护 head（头结点）、_size（结点个数）；可选 tail 加速尾部追加。

本文件仅实现链表与自测演示，不包含 Tkinter 或其它业务逻辑。
"""

from typing import Any, Callable, List, Optional


class Node:
    """
    单链表结点：保存数据与指向下一结点的引用。

    :ivar data: 任意可存储对象（如一条剧情标题、一段提示词文本）
    :ivar next: 下一结点；表尾为 None
    """

    __slots__ = ("data", "next")

    def __init__(self, data, next_node=None):
        # type: (Any, Optional[Node]) -> None
        self.data = data
        self.next = next_node  # type: Optional[Node]

    def __repr__(self):
        # type: () -> str
        return "Node(%r)" % (self.data,)


class LinkedList:
    """
    单链表：头指针遍历全表；带尾指针时 add 为 O(1) 尾插。

    对外约定：
    - add(item)     ：在链表尾部追加一个结点（保持历史顺序）。
    - traverse()    ：从左到右访问每个结点，默认收集为 list 返回；也可传入回调。
    - remove(item) ：删除**第一个** data 与 item 相等（==）的结点；成功返回 True。
    """

    def __init__(self):
        # type: () -> None
        # 头指针：空表时为 None
        self._head = None  # type: Optional[Node]
        # 尾指针：空表时为 None；与 head 同步维护，便于 O(1) 尾插
        self._tail = None  # type: Optional[Node]
        self._size = 0  # type: int

    def __len__(self):
        # type: () -> int
        """结点个数。"""
        return self._size

    def is_empty(self):
        # type: () -> bool
        """是否为空表。"""
        return self._head is None

    def add(self, item):
        # type: (Any) -> None
        """
        在链表尾部追加一个新结点，数据为 item。

        时间复杂度：O(1)（因维护 _tail）。

        :param item: 要保存的数据（如一条提示词）
        """
        new_node = Node(item, None)
        if self._head is None:
            # 空表：头尾都指向新结点
            self._head = new_node
            self._tail = new_node
        else:
            # 非空：尾结点后接新结点，并更新尾指针
            assert self._tail is not None
            self._tail.next = new_node
            self._tail = new_node
        self._size += 1

    def peek_front(self):
        # type: () -> Optional[Any]
        """返回表头数据但不删除；空表返回 None。"""
        if self._head is None:
            return None
        return self._head.data

    def pop_front(self):
        # type: () -> Optional[Any]
        """
        删除并返回表头数据；空表返回 None。

        供手写 ``Queue`` 做 O(1) 出队；单链表头删。
        """
        if self._head is None:
            return None
        data = self._head.data
        self._head = self._head.next
        self._size -= 1
        if self._head is None:
            self._tail = None
        elif self._head.next is None:
            self._tail = self._head
        return data

    def traverse(self, callback=None):
        # type: (Optional[Callable[[Any], None]]) -> List[Any]
        """
        从左到右遍历链表。

        - 若 callback 为 None：将各结点 data 依次追加到列表并返回（便于打印或绑定 UI）。
        - 若 callback 不为 None：对每个 data 调用 callback(data)，返回空列表。

        注意：返回的 list 仅作遍历结果容器，链表的底层存储仍是结点链接，不是用 list 代替链表。

        :param callback: 可选，单参数函数，对每个元素调用一次
        :return: 无 callback 时为 data 的列表；有 callback 时为 []
        """
        result = []  # type: List[Any]
        cur = self._head
        while cur is not None:
            if callback is None:
                result.append(cur.data)
            else:
                callback(cur.data)
            cur = cur.next
        return result

    def remove(self, item):
        # type: (Any) -> bool
        """
        删除第一个 data == item 的结点（使用 == 比较）。

        - 若删除的是头结点：更新 head；若表变空，tail 置 None。
        - 若删除的是尾结点：需将 tail 指向前驱（通过扫描找到前驱）。
        - 若未找到：返回 False。

        时间复杂度：O(n)（最坏需遍历全表）。

        :param item: 要匹配删除的数据
        :return: 删除成功 True，未找到 False
        """
        if self._head is None:
            return False

        # 头结点即目标
        if self._head.data == item:
            self._head = self._head.next
            self._size -= 1
            if self._head is None:
                self._tail = None
            elif self._head.next is None:
                # 仅剩一个结点时，尾即头
                self._tail = self._head
            return True

        # 在后续链表中查找：prev -> cur
        prev = self._head
        cur = self._head.next
        while cur is not None:
            if cur.data == item:
                prev.next = cur.next
                self._size -= 1
                # 若删掉的是尾结点，tail 移到 prev
                if cur is self._tail:
                    self._tail = prev
                return True
            prev = cur
            cur = cur.next

        return False

    def __repr__(self):
        # type: () -> str
        return "LinkedList(%s)" % self.traverse()


def _demo():
    # type: () -> None
    """控制台自测：模拟剧情框架与历史提示词顺序存储。"""
    plot = LinkedList()
    plot.add("开端：凡人少年误入古修洞府")
    plot.add("发展：获得残缺功法，遭同门觊觎")
    plot.add("高潮：秘境中破境筑基")
    plot.add("收束：立誓查清师门旧案")

    assert len(plot) == 4
    assert plot.traverse() == [
        "开端：凡人少年误入古修洞府",
        "发展：获得残缺功法，遭同门觊觎",
        "高潮：秘境中破境筑基",
        "收束：立誓查清师门旧案",
    ]

    # traverse 带回调：拼接成一段展示文本
    chunks = []  # type: List[str]

    def collect(s):
        chunks.append("[%s]" % s)

    plot.traverse(collect)
    assert len(chunks) == 4

    # remove：删除中间一条
    ok = plot.remove("发展：获得残缺功法，遭同门觊觎")
    assert ok is True
    assert len(plot) == 3
    assert "发展" not in "".join(plot.traverse())

    # remove：删除不存在的项
    assert plot.remove("不存在的剧情") is False

    # remove：删掉头
    assert plot.remove("开端：凡人少年误入古修洞府") is True
    assert len(plot) == 2

    # 历史提示词：尾插保持时间顺序
    history = LinkedList()
    history.add("提示词 v1：...")
    history.add("提示词 v2：...")
    history.add("提示词 v3：...")
    assert history.traverse()[-1] == "提示词 v3：..."

    # pop_front：队首 O(1) 删除
    qsim = LinkedList()
    qsim.add("a")
    qsim.add("b")
    assert qsim.pop_front() == "a"
    assert qsim.pop_front() == "b"
    assert qsim.pop_front() is None
    assert qsim.is_empty()

    print("LinkedList 自测通过。")
    print("剧情 traverse:", plot.traverse())
    print("历史 traverse:", history.traverse())


if __name__ == "__main__":
    _demo()
