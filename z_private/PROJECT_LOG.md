# 📘 PROJECT_LOG

## 1. 项目目标
实现一个 **表格助手（Table Assistant）**，支持以下任务：  

1. **Task 1 – Schema Summarization**  
   - 自动为每个数据表生成简洁摘要（表用途 + 列含义）。  
   - 输出保存到 `outputs/summaries.jsonl`。  

2. **Task 2 – Table Retrieval**  
   - 输入自然语言问题，检索最相关的表。  
   - 使用语义向量（SentenceTransformer）构建索引。  
   - 支持前 K 个相关表返回。  

3. **Task 3 – Table Evaluation**  
   - 对检索候选表进行 **相关性打分（1–5分）**。  
   - 可调用 LLM（OpenAI API）或本地启发式规则。  
   - 输出保存到 `outputs/eval_results.jsonl`。  

---

## 2. 已完成的配置

- **项目结构**
  ```
  llm-table-assistant/
  ├── data/          # 存放 CSV 表格数据
  ├── outputs/       # 存放摘要、索引、评估结果
  ├── src/           # 存放任务代码
  │   ├── task1_schema_summary.py
  │   ├── task2_search.py
  │   └── task3_eval.py
  ├── README.md
  ├── PROJECT_LOG.md
  ├── LICENSE
  └── .gitignore
  ```

- **环境依赖**  
  已在 `requirements.txt` 中列出：
  ```txt
  pandas
  numpy
  tqdm
  sentence-transformers
  scikit-learn
  openai        # 可选
  python-dotenv
  ```

- **数据库准备**  
  - 使用 **Sakila (SQLite 版本)** 数据集。  
  - 已下载 `sakila_master.db`，并通过 `prepare_data.py` 导出所有表为 CSV 到 `data/` 文件夹。  

- **GitHub 仓库**  
  - 已创建远程仓库并完成代码上传。  
  - `data/` 文件夹下保存了 CSV 表格数据。  

---

## 3. 已完成的工作

- ✅ 配置 Python 环境，安装依赖包。  
- ✅ 编写 `prepare_data.py`，导出表格为 CSV 文件。  
- ✅ 上传项目代码框架（`src/`、`data/`、`outputs/`）。  
- ✅ 编写 Task1、Task2、Task3 的基本代码（可在无 API Key 情况下运行）。  

---

## 4. 待完成工作

1. **完善数据集处理**  
   - 确认 `sakila_master.db` 的表格数是否满足实验要求（16 张表）。  
   - 确认 `data/` 下是否包含所有表的 CSV。  

2. **运行任务脚本**  
   - 运行 `task1_schema_summary.py` 生成表摘要。  
   - 运行 `task2_search.py` 构建索引并测试检索。  
   - 运行 `task3_eval.py` 对查询进行相关性打分。  

3. **可选：集成 LLM**  
   - 在 `.env` 文件中配置：  
     ```
     OPENAI_API_KEY=your_key_here
     ```  
   - 切换为 OpenAI LLM 打分模式，获得更高质量的摘要与评分。  

4. **文档撰写**  
   - 更新 `README.md`，提供运行说明和示例结果。  
   - 在 `outputs/` 保存样例输出（供老师复现）。  

---

## 5. 下一步计划

- [ ] 使用 `sakila_master.db` 完整导出表格到 `data/`。  
- [ ] 跑通 Task1（生成 summaries.jsonl）。  
- [ ] 跑通 Task2（检索并返回前 K 个表）。  
- [ ] 跑通 Task3（相关性打分，保存到 eval_results.jsonl）。  
- [ ] 整理结果 + 更新 README.md，形成最终提交版本。  
