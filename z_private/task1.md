# Mini-Project 文件结构说明

本文档总结了基于原有 **sql_agent** 项目改造后的 Mini-Project 文件组织与新增内容。

---

## 目录结构

```
llm_table_assistant/
├─ data/                          # 存放 16 张 Sakila CSV
├─ outputs/                       # 存放运行结果：summaries.jsonl / search_demo.json / eval_results.jsonl
├─ src/
│  ├─ retrieval_graph/             # 保留原 sql_agent 代码
│  │   ├─ __init__.py
│  │   ├─ configuration.py
│  │   ├─ prompts.py              # 在这里新增 Task1/2/3 的提示词常量
│  │   ├─ retrieval.py
│  │   ├─ sql_graph.py
│  │   ├─ state.py
│  │   └─ utils.py                # 复用 load_chat_model
│  │
│  └─ mini_project/               # 新增目录：专门放 Mini-Project 三个任务的脚本
│      ├─ __init__.py
│      ├─ task1_schema_summary.py # 任务1: 表摘要
│      ├─ task2_search.py         # 任务2: 表检索
│      └─ task3_eval.py           # 任务3: LLM 评分
├─ requirements.txt
└─ README.md                      # 总体运行说明（依赖/运行方法/示例/反思）
```

---

## 新增 / 修改文件

### 1. 修改 `src/retrieval_graph/prompts.py`
新增 3 个提示词常量：

```python
SCHEMA_SUMMARY_PROMPT = """..."""
TABLE_MATCH_PROMPT = """..."""
EVAL_PROMPT = """..."""
```

用于 Task1（摘要）、Task2（检索）、Task3（评分）。

---

### 2. 新建 `src/mini_project/task1_schema_summary.py`
- 输入：`data/*.csv`
- 输出：`outputs/summaries.jsonl`
- 功能：对每张表生成“表用途 + 列含义”的自然语言摘要。
- 调用 `retrieval_graph.utils.load_chat_model` 以支持 GPT-4o。

---

### 3. 新建 `src/mini_project/task2_search.py`
- 输入：`outputs/summaries.jsonl` + 用户 query
- 输出：`outputs/search_demo.json`
- 功能：基于摘要的表检索（TF-IDF 基线 + 嵌入模型）。

---

### 4. 新建 `src/mini_project/task3_eval.py`
- 输入：`outputs/summaries.jsonl` + Task2 检索结果
- 输出：`outputs/eval_results.jsonl`
- 功能：用规则或 LLM 对表-查询相关性打 1–5 分，并给解释。

---

### 5. 更新 `README.md`
需包含：
1. 如何运行三大任务（示例命令）
2. 依赖列表（pandas, scikit-learn, sentence-transformers, openai 等）
3. 示例输入输出（query → TopK → 打分）
4. 简短反思（Prompt 对比、LLM 与人类一致性等）

---

## 提交要求对齐

- **任务1**：summaries.jsonl + Prompt 设计说明  
- **任务2**：search_demo.json + 方法简述 + 示例  
- **任务3**：eval_results.jsonl + Prompt + 人类对齐反思  
- **README**：运行方法 / 依赖 / 示例 / 反思  

---

## 总结

需要 **新增 3 个文件**（`task1_schema_summary.py`, `task2_search.py`, `task3_eval.py`）+ **修改 1 个文件**（`prompts.py`）。  
这样既保留原 sql_agent 功能，又能完整覆盖 mini-project 的交付要求。
