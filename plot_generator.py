# -*- coding: utf-8 -*-
"""
剧情框架生成模块（plot_generator.py）
--------------------------------------
供 Tkinter 调用：从 ``HashMap`` 读取解析与设定类字段，按玄幻爽文常见节拍
「开局困境 → 机缘 → （打脸）→ （成长）→ 逆袭」**规则生成 3～5 段剧情节点**，
依次 ``LinkedList.add`` 尾插写入单链表，保证**链表顺序即剧情顺序**。

遍历：对链表调用 ``traverse()`` 即可得到从左到右的节点列表（供 UI 列表或拼接展示）。

运行自测：
    python plot_generator.py

依赖：同目录 ``hash_map.py``、``linked_list.py``。
"""

import os
import re
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from typing import List

from hash_map import HashMap
from linked_list import LinkedList

from novel_keys import (
    HM_CHEAT,
    HM_DILEMMA,
    HM_LLM_PLOT_FRAMEWORK,
    HM_OUT_CHARACTER,
    HM_OUT_CHEAT_DETAIL,
    HM_OUT_CULTIVATION,
    HM_OUT_WORLD,
    HM_PLOT,
    HM_PROTAGONIST,
    HM_WORLD,
)

KEY_PROTAGONIST = HM_PROTAGONIST
KEY_CHEAT = HM_CHEAT
KEY_PLOT = HM_PLOT
KEY_WORLD = HM_WORLD
KEY_OUT_CHARACTER = HM_OUT_CHARACTER
KEY_OUT_WORLD = HM_OUT_WORLD
KEY_OUT_CULTIVATION = HM_OUT_CULTIVATION
KEY_OUT_CHEAT_DETAIL = HM_OUT_CHEAT_DETAIL


def _safe_get(hm, key, default=""):
    # type: (HashMap, str, str) -> str
    if not hm.contains_key(key):
        return default
    v = hm.get(key)
    if v is None:
        return default
    return str(v).strip() if isinstance(v, str) else str(v)


def _gather_context(hm):
    # type: (HashMap) -> str
    """拼一段上下文字符串，供关键词命中（纯子串规则）。"""
    keys = (
        KEY_PROTAGONIST,
        HM_DILEMMA,
        KEY_CHEAT,
        KEY_PLOT,
        KEY_WORLD,
        KEY_OUT_CHARACTER,
        KEY_OUT_WORLD,
        KEY_OUT_CULTIVATION,
        KEY_OUT_CHEAT_DETAIL,
    )
    chunks = []
    for k in keys:
        chunks.append(_safe_get(hm, k))
    return "\n".join(chunks)


def _has_any(haystack, *words):
    # type: (str, str) -> bool
    h = haystack or ""
    for w in words:
        if w and w in h:
            return True
    return False


def _beat_opening(hm, ctx):
    # type: (HashMap, str) -> str
    """开局困境。"""
    p = _safe_get(hm, KEY_PROTAGONIST)
    w = _safe_get(hm, KEY_WORLD)
    lines = []
    lines.append("【开局困境】")
    lines.append(
        "主角身处明显不利局面：资源被卡、身份被轻看或卷入更高层势力的夹缝；"
        "矛盾要在开篇用一场「可见的羞辱/失败/追杀」压实，读者才能期待翻盘。"
    )
    if _has_any(p, "废柴", "杂役", "外门", "赘婿", "退婚"):
        lines.append("强化点：当众受挫/资源克扣，把「屈辱感」写具体，但留一条不起眼的活路伏笔。")
    if _has_any(ctx, "宗门", "王朝"):
        short = w[:40] + "…" if len(w) > 40 else w
        lines.append("舞台锚点：%s —— 规则与秩序即枷锁，也是后续打脸时的对照尺。" % (short or "宗门/王朝秩序",))
    lines.append("（解析锚点：%s）" % (p[:80] + "…" if len(p) > 80 else p or "可补充身份",))
    return "\n".join(lines)


def _beat_luck(hm, ctx):
    # type: (HashMap, str) -> str
    """机缘降临。"""
    c = _safe_get(hm, KEY_CHEAT)
    cd = _safe_get(hm, KEY_OUT_CHEAT_DETAIL)
    lines = []
    lines.append("【机缘降临】")
    lines.append(
        "危机顶点触发机缘：秘境裂缝、古物认主、系统激活或传承共鸣——"
        "机缘必须「当场改变信息差或上限」，但立刻引来新的觊觎与限制条件。"
    )
    if _has_any(c + cd, "系统", "面板", "签到", "任务"):
        lines.append("系统流写法：先给「小收益+强约束」，让读者相信外挂有代价；第一条主线任务最好与当前羞辱者强相关。")
    elif _has_any(c + cd, "戒指", "传承", "血脉", "觉醒"):
        lines.append("传承流写法：觉醒伴随异象或追杀线，主角被迫在极短时间内做第一次高风险选择。")
    lines.append("（金手指摘要：%s）" % (c[:100] + "…" if len(c) > 100 else c or "可补充外挂形态",))
    return "\n".join(lines)


def _beat_face_slapping(hm, ctx):
    # type: (HashMap, str) -> str
    """打脸立威。"""
    pl = _safe_get(hm, KEY_PLOT)
    lines = []
    lines.append("【打脸立威】")
    lines.append(
        "用「同场景对照」完成第一次爽点：当初羞辱你的人仍在同一规则下评判你，"
        "但你已掌握他看不懂的底牌；打脸要落在具体赌注（名额/婚约/资源）上。"
    )
    if _has_any(pl + ctx, "退婚", "擂台", "大比"):
        lines.append("可选舞台：宗门大比/擂台赌斗，把胜负与「公开名誉」绑定，爽感更集中。")
    lines.append("（剧情关键词参考：%s）" % (pl[:100] + "…" if len(pl) > 100 else pl or "可补充矛盾",))
    return "\n".join(lines)


def _beat_growth(hm, ctx):
    # type: (HashMap, str) -> str
    """修行成长。"""
    cu = _safe_get(hm, KEY_OUT_CULTIVATION)
    lines = []
    lines.append("【修行成长】")
    lines.append(
        "机缘之后进入「资源—功法—境界」的爬坡段：每次突破都要付代价（伤、债、因果），"
        "并引出更大地图的线索，避免纯数值膨胀。"
    )
    if _has_any(cu, "炼气", "筑基", "金丹", "元婴"):
        lines.append("可把下一小目标钉在某一境界门槛或某一秘境钥匙上，让读者有明确期待。")
    lines.append("（修炼体系摘录：%s）" % (cu[:120] + "…" if len(cu) > 120 else cu or "可补充境界目标",))
    return "\n".join(lines)


def _beat_finale(hm, ctx):
    # type: (HashMap, str) -> str
    """逆袭翻盘（收束段，可接续篇钩子）。"""
    pl = _safe_get(hm, KEY_PLOT)
    lines = []
    lines.append("【逆袭翻盘】")
    lines.append(
        "阶段性胜利：当众扭转关键利益格局，让「旧秩序解释不了你的成长」；"
        "同时埋下更大反派或更大世界观的钩子，避免一卷写完无路可走。"
    )
    if _has_any(pl + ctx, "复仇", "争霸", "灭门"):
        lines.append("若走复仇/争霸线：本段先赢「一局棋」而非终局，留主线仇人仍在更高层。")
    lines.append("（核心剧情锚点：%s）" % (pl[:100] + "…" if len(pl) > 100 else pl or "可补充终局方向",))
    return "\n".join(lines)


def generate_plot_beats(setting_map):
    # type: (HashMap) -> LinkedList
    """
    优先使用模型写入的 ``HM_LLM_PLOT_FRAMEWORK``（多行）拆成链表结点；
    否则回退到规则模板生成 3～5 段。
    """
    if setting_map.contains_key(HM_LLM_PLOT_FRAMEWORK):
        raw = setting_map.get(HM_LLM_PLOT_FRAMEWORK)
        if isinstance(raw, str) and raw.strip():
            out = LinkedList()
            for part in re.split(r"[\n\r]+", raw.strip()):
                p = part.strip()
                if len(p) >= 2:
                    out.add(p)
            if len(out) >= 1:
                return out

    ctx = _gather_context(setting_map)

    has_face = _has_any(ctx, "打脸", "羞辱", "退婚", "擂台", "大比", "当众")
    has_growth = _has_any(
        ctx,
        "炼气",
        "筑基",
        "金丹",
        "元婴",
        "秘境",
        "突破",
        "功法",
        "闭关",
    )

    pieces = []  # type: List[str]
    pieces.append(_beat_opening(setting_map, ctx))
    pieces.append(_beat_luck(setting_map, ctx))
    if has_face:
        pieces.append(_beat_face_slapping(setting_map, ctx))
    if has_growth:
        pieces.append(_beat_growth(setting_map, ctx))
    pieces.append(_beat_finale(setting_map, ctx))

    # 保证 3～5 段
    n = len(pieces)
    if n < 3:
        while len(pieces) < 3:
            pieces.append("【补位节点】请补充设定后重新生成。")
    if n > 5:
        pieces = pieces[:5]

    out = LinkedList()
    for p in pieces:
        out.add(p)
    return out


def format_plot_lines(beat_list):
    # type: (LinkedList) -> str
    """
    将剧情链表遍历为多行字符串，便于 ``Text`` / ``Message`` 展示。

    :param beat_list: ``generate_plot_beats`` 的返回值
    """
    rows = beat_list.traverse()
    sep = "\n\n" + ("-" * 40) + "\n\n"
    return sep.join(str(r) for r in rows)


def _self_test():
    # type: () -> None
    """自测：构造 HashMap → 生成链表 → 校验段数与顺序遍历。"""
    hm = HashMap()
    # 最小字段，触发 5 段（含打脸+成长）
    hm.put(KEY_PROTAGONIST, "外门废柴弟子，遭当众羞辱退婚")
    hm.put(KEY_CHEAT, "签到系统，宗门大比前激活面板")
    hm.put(KEY_PLOT, "打脸前任、夺取大比名额、秘境夺宝突破筑基")
    hm.put(KEY_WORLD, "东荒宗门林立，秘境周期性现世")
    hm.put(KEY_OUT_CULTIVATION, "炼气九层卡关，筑基需秘境灵物")

    beats = generate_plot_beats(hm)
    seq = beats.traverse()
    assert 3 <= len(seq) <= 5
    assert "【开局困境】" in seq[0]
    assert "【机缘降临】" in seq[1]
    assert "【逆袭翻盘】" in seq[-1]

    text = format_plot_lines(beats)
    assert "开局困境" in text and "逆袭翻盘" in text

    # 稀疏设定：应仍能产出至少 3 段
    hm2 = HashMap()
    hm2.put(KEY_PROTAGONIST, "某人")
    hm2.put(KEY_CHEAT, "某物")
    hm2.put(KEY_PLOT, "某事")
    hm2.put(KEY_WORLD, "某地")
    beats2 = generate_plot_beats(hm2)
    assert 3 <= len(beats2.traverse()) <= 5

    print("plot_generator.py 自测通过，段数:", len(seq), "/ 稀疏段数:", len(beats2.traverse()))
    print(format_plot_lines(beats)[:500] + "…")


if __name__ == "__main__":
    _self_test()
