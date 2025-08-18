# LLM-Table-Assistant

A hands-on mini-project for schema summarisation, table search, and LLM-based evaluation.

------------------------------------------------------------------------


## 📁 Project Directory Structure

```python
llm_table_assistant/
├── .gitignore
├── .env #Due to security concerns, you need to create the .env file yourself.
├── README.md
├── data/
│   └── sakila_xxx.csv #16 tables
├── outputs #results
├── prepare_data.py #Convert the db file to a csv file
├── test_api.py  #Test to see if you are connected to LLM
├── task1_schema_summary.py
├── task2_search.py
├── task3_eval.py
└── src/
    └── retrieval_graph/
        ├── prompts.py #contain prompts
        └── utils.py #load llm

```

## Environment & Dependencies

-   Python: \<3.12.7\>

-   Required packages:

    ``` bash
    pip install langgraph langchain_community "langchain[openai]"
    pip install langchain-openai python-dotenv
    pip install pandas
    pip install sqlite3-to-csv
    ```

- Environment variables in `.env`:

  Due to security concerns, you need to create the .env file yourself.

      OPENAI_API_KEY=<your_api_key>
      OPENAI_MODEL=gpt-4o-mini   # or another model

-   Development Environment Note

    ```
    > Note: This project was developed and tested in an **Anaconda environment** using **Spyder IDE**,  
    > but any standard Python 3.10+ environment with the listed dependencies can work.
    ```

------------------------------------------------------------------------

## 📝 Task Overview

### Task 1

-   **Goal**: Summarise each table (purpose + column descriptions).

-   **Run**:

    ``` bash
    python task1_schema_summary.py
    ```

-   **Deliverables**:

    -   Prompts used
    -   Schema summaries (JSON/Markdown)
    -   Explanation of prompt design

### Task 2

-   **Goal**: Match a user query to the most relevant tables using Task
    1 summaries.

-   **Run**:

    ``` bash
    python task2_search.py "find an actor whose last name is GUINESS" --k 5
    ```

-   **Deliverables**:

    -   Implementation (Python)
    -   Example outputs (query → matched tables)
    -   Method explanation

### Task 3

-   **Goal**: Evaluate whether Task 2's results are relevant to the
    query.

-   **Run**:

    ``` bash
    python task3_eval.py
    ```

-   **Deliverables**:

    -   Evaluation prompts
    -   LLM ratings & explanations
    -   Reflection (agreement with your own judgment)

------------------------------------------------------------------------

## 📌 Method Explanation (to be filled by you)

-   Task 1: \<描述你的方法，例如：是否加入样例行，如何约束格式\>\
-   Task 2: \<描述检索方法，例如：embedding + cosine，相似度+LLM重排\>\
-   Task 3: `<描述评估提示与打分准则>`{=html}

------------------------------------------------------------------------

## 📊 Example Runs (fill with your actual outputs)

-   Example 1
    -   Query: `"find Italian films longer than 120 minutes"`\
    -   Matched Tables: `<填写输出>`\
    -   Evaluation: `<1–5 + 解释>`
-   Example 2
    -   Query:
        `"Which table contains information about employee salaries?"`\
    -   Matched Tables: `<填写输出>`\
    -   Evaluation: `<1–5 + 解释>`

------------------------------------------------------------------------

## 🚀 Key Insights & Challenges (to be filled by you)

- **Insights:** 

  

-   Challenges: \<填写，如 schema 含义歧义、模型幻觉等\>

------------------------------------------------------------------------

## ▶️ Quick Reproduce

``` bash
# 1. Install dependencies
pip install langgraph langchain_community "langchain[openai]"
pip install langchain-openai python-dotenv pandas

# 2. Set environment variables in .env
echo OPENAI_MODEL=gpt-4o-mini >> .env
echo OPENAI_API_KEY=<your_api_key> >> .env

# 3. Prepare data (optional)
python prepare_data.py --out_dir ./data

# 4. Run Task 1
python task1_schema_summary.py

# 5. Run Task 2
python task2_search.py "find an actor whose last name is GUINESS" --k 5

# 6. Run Task 3
python task3_eval.py
```

