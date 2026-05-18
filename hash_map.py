# -*- coding: utf-8 -*-
"""
简易哈希表（HashMap）实现
------------------------
用途示例：在窗口程序中存储「小说人设、世界观、修炼体系」等键值对。

设计要点：
1. 底层使用定长「桶数组」，每个桶是一条链表（链地址法 / separate chaining）处理冲突。
2. 当元素个数超过「负载因子 × 当前容量」时，扩容为约 2 倍并重新散列（rehash）。
3. 对外 API：put(key, value)、get(key)、contains_key(key)。

说明：Python 中「数组」用 list 表示桶的引用表；每个桶存链表头结点。
      链表结点为本文件内自定义类，不依赖 dict 实现映射逻辑。
"""

from typing import Any, List, Optional


class _ChainNode:
    """链表结点：保存一个 (key, value) 以及指向同桶下一个冲突项的指针。"""

    __slots__ = ("key", "value", "next")

    def __init__(self, key, value, next_node=None):
        # type: (Any, Any, Optional[_ChainNode]) -> None
        self.key = key
        self.value = value
        self.next = next_node  # type: Optional[_ChainNode]


class HashMap:
    """
    基于「数组 + 链地址法」的哈希映射表。

    - key 必须可哈希（实现 __hash__ 且与 __eq__ 一致），与内置 dict 要求相同。
    - value 可为任意对象。
    """

    # 初始桶数量：取质数有利于减少聚集（课程实现常用小质数起步）
    _INITIAL_CAPACITY = 11
    # 负载因子：超过后触发扩容；0.75 是经典折中
    _LOAD_FACTOR = 0.75

    def __init__(self, initial_capacity=None):
        # type: (Optional[int]) -> None
        """
        创建一个空的 HashMap。

        :param initial_capacity: 可选，指定初始桶数（会规范为至少 1）。
        """
        cap = initial_capacity if initial_capacity is not None else self._INITIAL_CAPACITY
        self._capacity = max(1, int(cap))
        # 桶数组：每个元素是同索引桶上链表的头结点，None 表示该桶为空
        self._buckets = [None] * self._capacity  # type: List[Optional[_ChainNode]]
        # 当前存储的键值对数量（去重后的 key 个数）
        self._size = 0

    def __len__(self):
        # type: () -> int
        """当前键值对数量。"""
        return self._size

    def _index_for(self, key):
        # type: (Any) -> int
        """
        计算 key 应落入的桶下标：hash(key) 对容量取模。

        注意：Python 的 hash() 可能为负，故与容量取模后需保证非负。
        """
        h = hash(key)
        return h % self._capacity

    def contains_key(self, key):
        # type: (Any) -> bool
        """
        判断是否包含指定 key。

        :param key: 查找键
        :return: 存在为 True，否则 False
        """
        idx = self._index_for(key)
        node = self._buckets[idx]
        while node is not None:
            if node.key == key:
                return True
            node = node.next
        return False

    def get(self, key):
        # type: (Any) -> Any
        """
        根据 key 获取 value。

        :param key: 查找键
        :return: 对应的 value
        :raises KeyError: key 不存在时抛出
        """
        idx = self._index_for(key)
        node = self._buckets[idx]
        while node is not None:
            if node.key == key:
                return node.value
            node = node.next
        raise KeyError(key)

    def put(self, key, value):
        # type: (Any, Any) -> None
        """
        插入或更新：若 key 已存在则覆盖 value；否则在对应桶的链表中插入新结点。

        插入后若超过负载因子，则扩容并 rehash。

        :param key: 键
        :param value: 值
        """
        idx = self._index_for(key)
        head = self._buckets[idx]

        # 先在当前桶链表中查找是否已有相同 key（用 == 比较，与 dict 一致）
        cur = head
        while cur is not None:
            if cur.key == key:
                cur.value = value
                return
            cur = cur.next

        # 未找到：头插法插入新结点（也可尾插；头插 O(1) 且实现简单）
        self._buckets[idx] = _ChainNode(key, value, head)
        self._size += 1

        # 超过负载因子则扩容
        if self._size > int(self._capacity * self._LOAD_FACTOR):
            self._resize()

    def _resize(self):
        # type: () -> None
        """
        将桶数组扩容为约 2 倍（取简单策略：原容量 * 2 + 1），
        把所有结点按新容量重新散列到新的桶数组中。
        """
        old_buckets = self._buckets
        old_cap = self._capacity
        self._capacity = old_cap * 2 + 1
        self._buckets = [None] * self._capacity
        self._size = 0

        for i in range(old_cap):
            node = old_buckets[i]
            while node is not None:
                # 拆出当前结点，先记下 next，避免丢失链表
                next_node = node.next
                node.next = None
                self._rehash_insert_node(node)
                node = next_node

    def _rehash_insert_node(self, node):
        # type: (_ChainNode) -> None
        """扩容时把一个已有结点挂到新桶数组上（不增加 _size 的中间态由调用方保证）。"""
        idx = self._index_for(node.key)
        node.next = self._buckets[idx]
        self._buckets[idx] = node
        self._size += 1

    def __repr__(self):
        # type: () -> str
        return "HashMap(size=%s, capacity=%s)" % (self._size, self._capacity)


def _demo():
    # type: () -> None
    """简单自测：模拟存储人设、世界观、修炼体系。"""
    m = HashMap()

    # 人设
    m.put("主角", "没落宗门弟子，外冷内热")
    m.put("反派", "夺舍重修的魔道巨擘")

    # 世界观
    m.put("时代", "末法将临，灵气衰退")
    m.put("地理", "东荒三十六国，中央有上古封印")

    # 修炼体系
    m.put("境界", "炼气、筑基、金丹、元婴、化神")
    m.put("功法类型", "剑修为主，兼符阵双修")

    assert m.contains_key("主角") is True
    assert m.contains_key("不存在") is False
    assert m.get("主角") == "没落宗门弟子，外冷内热"

    # 覆盖更新
    m.put("主角", "实为上古大能转世，记忆未觉醒")
    assert m.get("主角") == "实为上古大能转世，记忆未觉醒"

    print("HashMap 演示通过，当前条目数:", len(m))
    for k in ("主角", "反派", "时代", "地理", "境界", "功法类型"):
        print("  %s: %s" % (k, m.get(k)))

    try:
        m.get("无此键")
    except KeyError as e:
        print("预期 KeyError:", e)

    # 触发扩容与 rehash：小容量表连续插入多条，校验扩容后仍可正确读写
    stress = HashMap(initial_capacity=5)
    for i in range(30):
        stress.put("键_%d" % i, "值_%d" % i)
    assert len(stress) == 30
    for i in range(30):
        assert stress.get("键_%d" % i) == "值_%d" % i
    print("扩容/rehash 自测通过，stress 条目数:", len(stress))


if __name__ == "__main__":
    _demo()
