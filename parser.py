# -*- coding: utf-8 -*-
"""
脑洞解析模块（parser.py）—— 对接本地 LM Studio Qwen3.5 9B
--------------------------------------------------------
将任意一句话脑洞解析为**严格 JSON**（中文键），结果写入手写 ``HashMap``。

JSON 键（必须齐全）：
  「身份」「困境」「金手指」「世界观」「剧情走向」

映射到 ``novel_keys`` 中的 HashMap 键，供 ``setting_generator`` 与管线后续使用。

依赖：``hash_map.py``、``novel_keys.py``、``lm_studio.py``（内部用 ``requests``，``pip install -r requirements.txt``）。
"""

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from typing import Any, Dict, List, Optional

from hash_map import HashMap
from lm_studio import LMStudioJsonError, LMStudioNetworkError, chat_completion, extract_json_object
from novel_keys import (
    HM_CHEAT,
    HM_DILEMMA,
    HM_IDEA_RAW,
    HM_PLOT,
    HM_PROTAGONIST,
    HM_THEME,
    HM_WORLD,
)

# 兼容旧常量名（其它模块若仍引用 KEY_*）
KEY_PROTAGONIST = HM_PROTAGONIST
KEY_CHEAT = HM_CHEAT
KEY_PLOT = HM_PLOT
KEY_WORLD = HM_WORLD

_JSON_KEYS = ["身份", "困境", "金手指", "世界观", "剧情走向"]


def _build_parse_messages(idea_text, theme):
    # type: (str, str) -> List[Dict[str, str]]
    sys_prompt = """
        你现在是一个严格的JSON生成器，**只输出纯JSON结果，绝对不写任何思考过程、分析过程、解释说明、Markdown符号、代码块标记**。

格式必须严格为：
{
    "身份": "",
    "困境": "",
    "金手指": "",
    "世界观": "",
    "剧情走向": ""
}

规则：
1.  不要加任何额外文字，包括“好的”“我来分析”等
2.  不要用 ```json 包裹，也不要加任何注释
3.  不要写任何换行、空格以外的多余字符
4.  直接输出JSON文本即可
"""
    
    user_prompt = (
        "创作主题：%s（玄幻/都市/科幻/古风/末世/校园）。\n"
        "一句话脑洞：%s\n"
        "请填充五个字符串值：内容紧扣脑洞与主题，世界观简洁可扩展，剧情走向 1～2 句概括主线张力。"
        % (theme, idea_text.strip())
    )
    return [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _validate_and_store(obj, idea_text, theme, hm):
    # type: (Dict[str, Any], str, str, HashMap) -> None
    """校验 JSON 五键并写入 HashMap。"""
    for k in _JSON_KEYS:
        if k not in obj:
            raise LMStudioJsonError("缺少键：%s" % k, phase="parse")
        v = obj[k]
        if not isinstance(v, str) or not v.strip():
            raise LMStudioJsonError("键「%s」内容为空或格式非法" % k, phase="parse")

    hm.put(HM_IDEA_RAW, idea_text.strip())
    hm.put(HM_THEME, theme)
    hm.put(HM_PROTAGONIST, str(obj["身份"]).strip())
    hm.put(HM_DILEMMA, str(obj["困境"]).strip())
    hm.put(HM_CHEAT, str(obj["金手指"]).strip())
    hm.put(HM_WORLD, str(obj["世界观"]).strip())
    hm.put(HM_PLOT, str(obj["剧情走向"]).strip())


def parse_brainstorm(idea_text, target_map=None, theme="玄幻"):
    # type: (str, Optional[HashMap], str) -> HashMap
    """
    调用本地 Qwen3.5 9B，将脑洞解析为 JSON 并写入 ``HashMap``。

    :param idea_text: 用户输入（非空由调用方保证）
    :param target_map: 目标 HashMap；None 则新建
    :param theme: 创作主题（玄幻/都市/科幻/古风/末世/校园）
    :raises LMStudioNetworkError: 无法连接 LM Studio
    :raises LMStudioJsonError: 返回不是合法 JSON 或字段不合法（phase=parse）
    """
    hm = target_map if target_map is not None else HashMap()
    raw = (idea_text or "").strip()
    if not raw:
        hm.put(HM_PROTAGONIST, "（未识别）")
        hm.put(HM_DILEMMA, "（未识别）")
        hm.put(HM_CHEAT, "（未识别）")
        hm.put(HM_PLOT, "（未识别）")
        hm.put(HM_WORLD, "（未识别）")
        return hm

    messages = _build_parse_messages(raw, theme)
    try:
        content = chat_completion(messages, temperature=0.2)
    except LMStudioNetworkError:
        raise
    obj = extract_json_object(content, phase="parse")
    _validate_and_store(obj, raw, theme, hm)
    return hm


def _self_test():
    # type: () -> None
    """需 LM Studio 已启动并加载模型；否则打印跳过说明。"""
    from lm_studio import LMStudioNetworkError

    try:
        m = HashMap()
        parse_brainstorm("普通上班族获得读心术，逆袭职场大佬", m, theme="都市")
        assert m.contains_key(HM_PROTAGONIST)
        print("parser.py 自测通过（已连上 LM Studio）。")
        print(m.get(HM_PROTAGONIST)[:80])
    except LMStudioNetworkError:
        print("parser.py 自测跳过：未连接 LM Studio（正常）。")


if __name__ == "__main__":
    _self_test()
