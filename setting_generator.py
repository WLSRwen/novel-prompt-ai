# -*- coding: utf-8 -*-
"""
小说设定生成模块（setting_generator.py）—— 对接本地 LM Studio Qwen3.5 9B
------------------------------------------------------------------------
读取 ``parser`` 写入的 HashMap 字段，按用户所选**创作主题**，调用模型生成：

  JSON 键：「人设详情」「世界观详情」「修炼体系」「金手指详情」
          「剧情框架」「最终提示词」

其中「剧情框架」为多行文本（建议 4～6 条，每条一行，可带序号）；
「最终提示词」为可直接投喂写作模型的长提示词。

结果写回同一张 ``HashMap``（手写哈希表）。

依赖：``hash_map.py``、``novel_keys.py``、``lm_studio.py``
"""

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from typing import Any, Dict, List, Optional

from hash_map import HashMap
from lm_studio import LMStudioJsonError, LMStudioNetworkError, chat_completion, extract_json_object_setting
from novel_keys import (
    HM_CHEAT,
    HM_DILEMMA,
    HM_IDEA_RAW,
    HM_LLM_FINAL_PROMPT,
    HM_LLM_PLOT_FRAMEWORK,
    HM_OUT_CHARACTER,
    HM_OUT_CHEAT_DETAIL,
    HM_OUT_CULTIVATION,
    HM_OUT_WORLD,
    HM_PLOT,
    HM_PROTAGONIST,
    HM_THEME,
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

_SETTING_JSON_KEYS = [
    "人设详情",
    "世界观详情",
    "修炼体系",
    "金手指详情",
    "剧情框架",
    "最终提示词",
]


def _safe_get(hm, key, default=""):
    # type: (HashMap, str, str) -> str
    if not hm.contains_key(key):
        return default
    v = hm.get(key)
    if v is None:
        return default
    return str(v).strip() if isinstance(v, str) else str(v)


def _build_setting_messages(hm, theme):
    # type: (HashMap, str) -> List[Dict[str, str]]
    ctx = "\n".join(
        [
            "【创作主题】%s" % theme,
            "【身份】%s" % _safe_get(hm, HM_PROTAGONIST),
            "【困境】%s" % _safe_get(hm, HM_DILEMMA),
            "【金手指】%s" % _safe_get(hm, HM_CHEAT),
            "【世界观关键词】%s" % _safe_get(hm, HM_WORLD),
            "【剧情走向】%s" % _safe_get(hm, HM_PLOT),
            "【原始脑洞】%s" % _safe_get(hm, HM_IDEA_RAW, _safe_get(hm, HM_PLOT)),
        ]
    )
    sys_prompt = (
        "你是严格的 JSON 生成器（中文网络小说总策划）。\n"
        "【硬性输出】只输出一个合法 JSON 对象：从「{」开始到「}」结束；"
        "禁止思考过程、禁止 Markdown、禁止 ``` 代码块、禁止任何前后说明。\n"
        "JSON 必须且只能包含以下六个键（键名一字不差）：\n"
        "人设详情、世界观详情、修炼体系、金手指详情、剧情框架、最终提示词\n"
        "每个键的值必须是字符串（不要用数组或嵌套对象）。\n"
        "内容要求：\n"
        "1. 前四个键：多段中文说明；\n"
        "2. 修炼体系：都市/校园主题可写职场段位、资源体系，不必修仙；\n"
        "3. 剧情框架：4～6 行，每行一个剧情节点，用 \\n 连接在同一字符串内；\n"
        "4. 最终提示词：一段可直接给 AI 写小说用的完整长提示词。\n"
        "创作主题必须与用户给定的一致。"
    )
    user_prompt = "用户创作主题：%s\n\n%s" % (theme, ctx)
    return [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _validate_setting_obj(obj):
    # type: (Dict[str, Any]) -> None
    for k in _SETTING_JSON_KEYS:
        if k not in obj:
            raise LMStudioJsonError("缺少键：%s" % k, phase="setting")
        v = obj[k]
        if v is None:
            raise LMStudioJsonError("键「%s」内容为空或非法" % k, phase="setting")
        if isinstance(v, str):
            if not v.strip():
                raise LMStudioJsonError("键「%s」内容为空或非法" % k, phase="setting")
        elif isinstance(v, (list, tuple)):
            if not v:
                raise LMStudioJsonError("键「%s」内容为空或非法" % k, phase="setting")
        else:
            s = str(v).strip()
            if not s:
                raise LMStudioJsonError("键「%s」内容为空或非法" % k, phase="setting")


def generate_settings(setting_map, theme=None):
    # type: (HashMap, Optional[str]) -> HashMap
    """
    调用本地模型生成设定 JSON 并写回 ``setting_map``。

    :param theme: 若 None 则从 ``HM_THEME`` 读取，默认「玄幻」
    :raises LMStudioNetworkError / LMStudioJsonError(phase=setting)
    """
    th = theme if theme is not None else _safe_get(setting_map, HM_THEME, "玄幻")
    if not th:
        th = "玄幻"

    messages = _build_setting_messages(setting_map, th)
    try:
        content = chat_completion(messages, temperature=0.2)
    except LMStudioNetworkError:
        raise
    try:
        obj = extract_json_object_setting(content)
        _validate_setting_obj(obj)
    except LMStudioJsonError:
        print(
            "[setting_generator] 模型原始输出前 800 字：\n%s"
            % ((content or "")[:800])
        )
        raise

    def _as_str(v):
        # type: (Any) -> str
        if isinstance(v, str):
            return v.strip()
        if isinstance(v, (list, tuple)):
            return "\n".join(str(x).strip() for x in v)
        return str(v).strip()

    setting_map.put(HM_OUT_CHARACTER, _as_str(obj["人设详情"]))
    setting_map.put(HM_OUT_WORLD, _as_str(obj["世界观详情"]))
    setting_map.put(HM_OUT_CULTIVATION, _as_str(obj["修炼体系"]))
    setting_map.put(HM_OUT_CHEAT_DETAIL, _as_str(obj["金手指详情"]))
    setting_map.put(HM_LLM_PLOT_FRAMEWORK, _as_str(obj["剧情框架"]))
    setting_map.put(HM_LLM_FINAL_PROMPT, _as_str(obj["最终提示词"]))
    return setting_map


def format_structured_bundle(setting_map):
    # type: (HashMap) -> str
    keys = (
        (HM_OUT_CHARACTER, "一、人设详情"),
        (HM_OUT_WORLD, "二、世界观详情"),
        (HM_OUT_CULTIVATION, "三、修炼体系"),
        (HM_OUT_CHEAT_DETAIL, "四、金手指详情"),
    )
    blocks = []
    for k, title in keys:
        body = _safe_get(setting_map, k, "（尚未生成）")
        blocks.append("%s\n%s" % (title, body))
    blocks.append("五、剧情框架\n%s" % _safe_get(setting_map, HM_LLM_PLOT_FRAMEWORK, "（无）"))
    blocks.append("六、最终提示词\n%s" % _safe_get(setting_map, HM_LLM_FINAL_PROMPT, "（无）"))
    return "\n\n".join(blocks)


def _self_test():
    # type: () -> None
    from lm_studio import LMStudioNetworkError

    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "novel_parser", os.path.join(_THIS_DIR, "parser.py")
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("no parser")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        hm = HashMap()
        mod.parse_brainstorm("获得读心术的上班族逆袭", hm, theme="都市")
        generate_settings(hm)
        assert hm.contains_key(HM_LLM_FINAL_PROMPT)
        print("setting_generator.py 自测通过。")
    except LMStudioNetworkError:
        print("setting_generator.py 自测跳过：未连接 LM Studio。")


if __name__ == "__main__":
    _self_test()
