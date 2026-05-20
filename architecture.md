# 小说提示词 AI 生成器 — 系统架构图

> 基于项目报告与源码整理。可在支持 Mermaid 的编辑器中预览。

## 图1 系统总体架构

```mermaid
flowchart TB
    subgraph UI["表示层"]
        A[用户输入创意梗概与主题<br/>Tkinter · main.py]
    end

    subgraph Pipeline["业务层 · prompt_assembler.py"]
        B[run_prompt_pipeline]
        Q[(手写 Queue<br/>FIFO 阶段调度)]
        B --> Q
        Q --> P1[parse · parser.py]
        Q --> P2[setting · setting_generator.py]
        Q --> P3[plot · plot_generator.py]
        Q --> P4[assemble · assemble_prompt_text]
    end

    subgraph DS["数据结构层"]
        H[(HashMap<br/>解析与设定键值)]
        L[(LinkedList<br/>剧情节拍 / 历史)]
    end

    subgraph LLM["模型层 · lm_studio.py"]
        M[GET /v1/models 预检]
        N[POST /v1/chat/completions<br/>qwen/qwen3.5-9b]
        J[JSON 抽取与字段校验]
        M --> N --> J
    end

    A --> B
    P1 --> H
    P1 --> N
    P2 --> H
    P2 --> N
    P3 --> L
    P4 --> H
    P4 --> L
    J --> H
    P4 --> O[Markdown 提示词<br/>GUI 展示与历史记录]
```

## 图2 四阶段流水线数据流

```mermaid
flowchart LR
    I[一句话创意 + 主题] --> S1[解析<br/>五字段 JSON]
    S1 --> S2[设定<br/>六字段 JSON]
    S2 --> S3[剧情<br/>3-5 节点]
    S3 --> S4[组装<br/>2000 字 Prompt]
    S1 -.-> HM[(HashMap)]
    S2 -.-> HM
    S3 -.-> LL[(LinkedList)]
    S4 --> OUT[结果区 / 历史]
```

## 图3 HashMap 链地址法示意

```mermaid
flowchart LR
    subgraph Buckets["桶数组 _buckets"]
        B1["下标 1 → 链表头"]
        Bi["下标 i → 链表头"]
    end
    B1 --> N1["(keyA, valA)"]
    N1 --> N2["(keyB, valB)"]
    Bi --> N3["(keyX, valX)"]
    N3 --> N4["(keyY, valY)"]
    Hfn["hash(key) % capacity"] -.-> B1
```

## 模块对照

| 层级 | 模块 | 职责 |
|:---|:---|:---|
| 表示层 | `main.py` | 主题选择、输入、结果展示、历史 |
| 业务层 | `parser.py` | 创意 → 五字段 JSON |
| 业务层 | `setting_generator.py` | 主题化六字段设定 |
| 业务层 | `plot_generator.py` | 剧情节拍生成 |
| 业务层 | `prompt_assembler.py` | 队列调度与文本组装 |
| 数据结构层 | `hash_map.py` / `linked_list.py` / `my_queue.py` | 键值存储、顺序存储、FIFO |
| 模型层 | `lm_studio.py` | HTTP 调用与 JSON 抽取 |
