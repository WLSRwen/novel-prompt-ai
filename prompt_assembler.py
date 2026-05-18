# -*- coding: utf-8 -*-
"""
提示词组装模块（prompt_assembler.py）
------------------------------------
供 Tkinter 调用：
1. 从 ``HashMap`` 读取解析与设定字段，从 ``LinkedList`` 读取剧情节拍；
2. 拼接为**结构清晰、可直接复制给 AI** 的长提示词（玄幻仙侠写作向）。
3. 使用项目内手写 ``my_queue.Queue``（``from my_queue import Queue``）做 FIFO 调度，
   **严格按顺序**调度：
   ``解析 → 设定生成 → 剧情生成 → 文本组装``；每步 ``try/except`` 单独捕获，
   失败时记录错误并尽量继续后续步骤（组装阶段仍可基于已有数据输出）。

运行自测：
    python prompt_assembler.py

依赖：``hash_map.py``、``linked_list.py``、``my_queue.py``（同目录）。
管线内还会 ``importlib`` 加载同目录 ``parser.py``、``setting_generator.py``、
``plot_generator.py``，避免与标准库 ``parser`` 同名冲突。
"""

import importlib.util
import os
import sys
import traceback

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from typing import Any, List, Optional, Tuple

from hash_map import HashMap
from linked_list import LinkedList
from lm_studio import LMStudioJsonError, LMStudioNetworkError
from my_queue import Queue
from novel_keys import (
    HM_CHEAT,
    HM_DILEMMA,
    HM_IDEA_RAW,
    HM_LLM_FINAL_PROMPT,
    HM_OUT_CHARACTER,
    HM_OUT_CHEAT_DETAIL,
    HM_OUT_CULTIVATION,
    HM_OUT_WORLD,
    HM_PLOT,
    HM_PROTAGONIST,
    HM_THEME,
    HM_WORLD,
)

# 管线阶段（入队顺序）
PHASE_PARSE = "parse"
PHASE_SETTING = "setting"
PHASE_PLOT = "plot"
PHASE_ASSEMBLE = "assemble"


def _load_module(filename, as_name):
    # type: (str, str) -> Any
    """从本目录按路径加载模块，避免与标准库同名包冲突。"""
    path = os.path.join(_THIS_DIR, filename)
    spec = importlib.util.spec_from_file_location(as_name, path)
    if spec is None or spec.loader is None:
        raise ImportError("无法加载模块文件: %s" % path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _safe_get(hm, key, default=""):
    # type: (HashMap, str, str) -> str
    if not hm.contains_key(key):
        return default
    v = hm.get(key)
    if v is None:
        return default
    return str(v).strip() if isinstance(v, str) else str(v)


def _hm_section_lines(hm, title, keys):
    # type: (HashMap, str, Tuple[str, ...]) -> List[str]
    """从 HashMap 取多键，格式化为 Markdown 小节。"""
    lines = ["## %s" % title, ""]
    for k in keys:
        lines.append("### %s" % k)
        lines.append(_safe_get(hm, k, "（暂无）"))
        lines.append("")
    return lines


def assemble_prompt_text(setting_map, plot_beats):
    # type: (HashMap, LinkedList) -> str
    """
    若已存在模型生成的「最终提示词」，则**直接返回**（主界面展示用）；
    否则回退为 Markdown 拼装（兼容无模型环境）。
    """
    final_llm = _safe_get(setting_map, HM_LLM_FINAL_PROMPT)
    if len(final_llm) > 40:
        return final_llm

    lines = []  # type: List[str]

    lines.append("# 小说 · AI 辅助写作提示词")
    lines.append("")
    lines.append("请将下文作为**单次对话中的用户指令**使用：先理解设定与剧情节拍，再输出小说正文或章纲。")
    lines.append("")
    lines.append("---")
    lines.append("")

    idea = _safe_get(setting_map, HM_IDEA_RAW)
    if not idea:
        idea = _safe_get(setting_map, HM_PLOT)[:120] if _safe_get(setting_map, HM_PLOT) else "（未提供脑洞原文，可从核心剧情推断）"

    lines.append("## 用户脑洞（原文）")
    lines.append("")
    lines.append("（创作主题：%s）" % _safe_get(setting_map, HM_THEME, "未选"))
    lines.append(idea)
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.extend(
        _hm_section_lines(
            setting_map,
            "解析摘要（关键词）",
            (HM_PROTAGONIST, HM_DILEMMA, HM_CHEAT, HM_WORLD, HM_PLOT),
        )
    )
    lines.append("---")
    lines.append("")

    lines.extend(
        _hm_section_lines(
            setting_map,
            "生成设定（结构化）",
            (
                HM_OUT_CHARACTER,
                HM_OUT_WORLD,
                HM_OUT_CULTIVATION,
                HM_OUT_CHEAT_DETAIL,
            ),
        )
    )
    lines.append("---")
    lines.append("")

    lines.append("## 剧情框架（按顺序执行）")
    lines.append("")
    beats = plot_beats.traverse() if plot_beats is not None else []
    if not beats:
        lines.append("（暂无剧情节点，请先运行剧情生成管线。）")
        lines.append("")
    else:
        for i, node in enumerate(beats, 1):
            lines.append("### 第 %d 段" % i)
            lines.append(str(node))
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 对 AI 的输出要求")
    lines.append("")
    lines.append("1. 文风：贴合创作主题「%s」，注意节奏与信息递进。" % _safe_get(setting_map, HM_THEME, "通用"))
    lines.append("2. 设定：严格沿用上文人设、世界观与修炼体系，不自相矛盾。")
    lines.append("3. 结构：按「剧情框架」顺序展开，可适当细化对白与场面，勿跳步。")
    lines.append("4. 篇幅：若未另行说明，先给出 **章纲（分场景 bullet）** 或 **约 1500 字开篇** 二选一，并在文首说明你选择了哪一种。")
    lines.append("5. 禁忌：不要引入与上文无关的现代梗；不要 OOC 毁人设。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*（本提示词由「小说提示词 AI」规则管线生成，可直接整段复制给大模型。）*")

    return "\n".join(lines)


def _execute_phase(phase, idea_text, hm, state):
    # type: (str, str, HashMap, dict) -> None
    """
    执行单个管线阶段，结果写入 state / hm。

    state 键：``plot_beats`` -> LinkedList, ``errors`` -> list
    """
    errors = state["errors"]  # type: List[str]

    if phase == PHASE_PARSE:
        parser_mod = _load_module("parser.py", "novel_brainstorm_parser")
        parser_mod.parse_brainstorm(idea_text, hm, theme=state.get("theme", "玄幻"))
        return

    if phase == PHASE_SETTING:
        sg = _load_module("setting_generator.py", "novel_setting_generator")
        sg.generate_settings(hm, theme=state.get("theme"))
        return

    if phase == PHASE_PLOT:
        pg = _load_module("plot_generator.py", "novel_plot_generator")
        state["plot_beats"] = pg.generate_plot_beats(hm)
        return

    if phase == PHASE_ASSEMBLE:
        # 组装在出队循环外统一调用，此处占位（防止误把 assemble 当数据处理）
        return

    errors.append("未知阶段: %s" % phase)


def run_prompt_pipeline(idea_text, setting_map=None, theme="玄幻", rethrow_llm_errors=False):
    # type: (str, Optional[HashMap], str, bool) -> Tuple[str, LinkedList, List[str]]
    """
    手写队列调度：解析 → 设定 → 剧情 → 组装。

    :param theme: 创作主题（与界面单选一致）
    :param rethrow_llm_errors: True 时 ``LMStudioNetworkError`` / ``LMStudioJsonError`` 向上抛出，便于 GUI 弹窗
    """
    hm = setting_map if setting_map is not None else HashMap()
    q = Queue()

    q.enqueue(PHASE_PARSE)
    q.enqueue(PHASE_SETTING)
    q.enqueue(PHASE_PLOT)
    q.enqueue(PHASE_ASSEMBLE)

    state = {"plot_beats": LinkedList(), "errors": [], "theme": theme}

    while not q.is_empty():
        try:
            phase = q.dequeue()
        except IndexError:
            state["errors"].append("queue: unexpected empty on dequeue")
            break

        if phase == PHASE_ASSEMBLE:
            continue

        try:
            _execute_phase(phase, idea_text, hm, state)
        except (LMStudioNetworkError, LMStudioJsonError):
            if rethrow_llm_errors:
                raise
            err = traceback.format_exc()
            state["errors"].append("[%s] LM 错误\n%s" % (phase, err))
        except Exception as e:
            tb = traceback.format_exc()
            state["errors"].append("[%s] %s\n%s" % (phase, e, tb))

    plot_beats = state["plot_beats"]
    if not isinstance(plot_beats, LinkedList):
        plot_beats = LinkedList()

    final_prompt = ""
    try:
        final_prompt = assemble_prompt_text(hm, plot_beats)
    except Exception as e:
        state["errors"].append("[assemble_prompt_text] %s\n%s" % (e, traceback.format_exc()))
        final_prompt = (
            "# 组装失败\n\n以下错误信息供调试：\n\n"
            + "\n\n---\n\n".join(state["errors"])
        )

    return final_prompt, plot_beats, state["errors"]


def _self_test():
    # type: () -> None
    """不默认请求 LM Studio（避免无服务时长时间阻塞）；请用 main.py 做联调。"""
    print("prompt_assembler.py：完整管线请运行 main.py（需 LM Studio）。")


if __name__ == "__main__":
    _self_test()
