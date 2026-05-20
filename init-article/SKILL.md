---
name: init-article
description: 根据项目报告初始化演讲稿撰写规范，生成 topic/structure/voice/check 四份约束文档。用于课程汇报、答辩、3分钟演讲稿等场景；当用户提到 init-article、演讲稿规范、汇报稿撰写时使用。
disable-model-invocation: true
---

# Init Article — 演讲稿撰写规范初始化

## 何时使用

- 用户需要根据项目报告撰写**3 分钟汇报演讲稿**
- 用户指定语速（默认 **300 字/分钟**）与字数上限
- 需要先建立规范文档，再按规范产出 `speech.txt`

## 工作流

1. **阅读理解**项目报告（如 `report.md`），提取：背景痛点、方案、架构、测试数据、结论
2. **创建规范目录** `init-article/`，写入四份文件：
   - `topic.md` — 主题与核心信息
   - `structure.md` — 段落结构与时间分配
   - `voice.md` — 语气、人称与表达约束
   - `check.md` — 交付前自检清单
3. **按规范撰写**演讲稿，输出到项目根目录 `speech.txt`
4. **自检**：对照 `check.md` 逐项核对字数、数据、口语化程度

## 默认约束

| 项 | 默认值 |
|:---|:---|
| 时长 | 3 分钟 |
| 语速 | 300 字/分钟 |
| 字数上限 | **900 字**（含标点，不含 PPT 标记行） |
| 受众 | 课程答辩 / 项目汇报老师与同学 |
| 语言 | 简体中文，口语化但保留关键术语 |

## 规范文件说明

- [topic.md](topic.md) — 写什么
- [structure.md](structure.md) — 怎么排
- [voice.md](voice.md) — 怎么说
- [check.md](check.md) — 怎么验

## 输出

- 规范文档：`init-article/*.md`
- 演讲稿：`speech.txt`（根目录）
