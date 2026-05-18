# -*- coding: utf-8 -*-
"""
novel_keys —— HashMap 键名统一常量
---------------------------------
手写 ``HashMap`` 的 key 均为 str；value 均为 str（本项目中）。
"""

# 用户脑洞原文
HM_IDEA_RAW = "原始脑洞"

# 第一阶段：模型解析 JSON 写入（与 UI/第二段 prompt 对齐）
HM_PROTAGONIST = "主角身份"       # 对应 JSON「身份」
HM_DILEMMA = "困境"
HM_CHEAT = "金手指"
HM_WORLD = "世界观关键词"         # 对应 JSON「世界观」
HM_PLOT = "核心剧情"             # 对应 JSON「剧情走向」

# 创作主题（单选：玄幻/都市/…）
HM_THEME = "创作主题"

# 第二阶段：模型生成写入
HM_OUT_CHARACTER = "人设详情"
HM_OUT_WORLD = "世界观详情"
HM_OUT_CULTIVATION = "修炼体系"
HM_OUT_CHEAT_DETAIL = "金手指详情"
HM_LLM_PLOT_FRAMEWORK = "剧情框架_LLM"   # 多行文本 → 链表拆段
HM_LLM_FINAL_PROMPT = "最终提示词_LLM"  # 主展示：完整写作提示词
