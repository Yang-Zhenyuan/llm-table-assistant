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

## :gear:Environment & Dependencies

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

All the prompts are stored in `llm_table_assistant/src/retrieval_graph/prompts.py`.

### Task 1

-   **Goal**: Summarise each table (purpose + column descriptions).

-   **Run**:

    ``` bash
    python task1_schema_summary.py
    ```

-   **Deliverables**:

    1. Schema summaries for each table
    
       ```
       The output file `schema_summaries.json` contains the results of Task 1.  
       The field `summary` represents the model’s evaluation of the table as a whole, and it also provides evaluations for each column (attribute).
       ```
    
    2. why I designed like that?
    
       ```
       In Task 1, the LLM was instructed to take the role of a senior data analyst.  
       The output was required to be a strict JSON object, with the expected format explicitly provided in the prompt.  
       If a column name was ambiguous, the model was advised to refer to the five sample rows (provided by `task1_schema_summary.py`) in order to infer its semantics more accurately.
       ```
    
- 📝 Example Output

  1. prompt1

     ```python
     prompt:
         SCHEMA_SUMMARY_PROMPT = """
     You are a senior data analyst. Produce a STRICT JSON object ONLY in the EXACT shape below.
     Your goal is to help another analyst quickly understand a table's PURPOSE and how to use it.
     
     Required JSON shape:
     {
       "table": "<table_name>",
       "summary": "<2–3 sentences stating what the table represents (its PURPOSE) and typical use cases.>",
       "columns": [
         {"name": "<column_name>", "description": "<plain-English meaning of this column>"},
         ...
       ]
     }
     
     Rules:
     - Output ONLY JSON (no markdown fence, no extra commentary, no extra keys).
     - Base your descriptions on the column names and sample rows provided.
     - If a column name is ambiguous, infer cautiously from the samples.
     - Keep each column description short (≤1 sentence).
     ```

     ```python
     result:
          {
         "table": "actor",
         "summary": "This table contains information about actors, including their unique identifiers and names. It is typically used to manage actor data in a film or entertainment database.",
         "columns": [
           {
             "name": "actor_id",
             "description": "A unique identifier for each actor."
           },
           {
             "name": "first_name",
             "description": "The first name of the actor."
           },
           {
             "name": "last_name",
             "description": "The last name of the actor."
           },
           {
             "name": "last_update",
             "description": "The timestamp of the last update made to the actor's information."
           }
         ]
       }
     ```

  2. prompt 2

     ```python
     ```

     

### Task 2

-   **Goal**: Match a user query to the most relevant tables using Task
    1 summaries.

-   **Run**:

    ``` bash
    python task2_search.py "find an actor whose last name is GUINESS" --k 5
    ```

-   **Deliverables**:

    1. Output examples: natural language query -> matched tables
    
       The output examples are located in `llm_table_assistant/z_outputs-example/task2`.
    
    2. Method explanation
    
       1. load task1's result schema_summaries.json, as resources of tables.
    
       2. **Compact context: **for each table, build a short snippet (name, a truncated summary ≤320 chars, and up to 12–16 column names) to keep the prompt token‑efficient.
    
       3. **ranking prompt: **assigns a 1–5 relevance score
    
          ```python
          #llm_table_assistant\src\retrieval_graph
          
          TABLE_MATCH_PROMPT = """You are a meticulous data analyst.
          Given a user query and a list of candidate table summaries, select the K most relevant tables.
          
          Scoring scale:
          5 = Fully relevant. The table directly satisfies the query.
          4 = Mostly relevant. Covers the main intent but may miss minor fields or constraints.
          3 = Partially relevant. Provides some useful context but not sufficient alone.
          2 = Weakly relevant. Only tangentially connected to the query.
          1 = Irrelevant. No meaningful connection to the query.
          ```
    
       4. **Inference**: Send the user query + candidate snippets to the LLM 
    
       5. **Normalize results**
    
       6. **Outputs**

### Task 3

-   **Goal**: Evaluate whether Task 2's results are relevant to the query.
    
-   **Run**:

    ``` bash
    python task3_eval.py
    ```

-   **Deliverables**:

    - Evaluation prompts
    
      ```python
      #llm_table_assistant\src\retrieval_graph
      
      EVAL_PROMPT = """You are a rigorous data analyst.
      Judge how relevant ONE candidate table is to the given user query.
      
      Scoring scale:
      5 = Fully aligned. This table alone contains the key fields needed to answer the query.
      4 = Mostly aligned. It answers the main intent but might miss minor constraints/fields.
      3 = Partially related. Provides context/partial info; likely needs joins with other tables.
      2 = Weakly related. Only tangentially related to the topic.
      1 = Irrelevant.
      
      Instructions:
      - Base your decision on the provided table summary, column list, and the 3 sample rows.
      - Think about whether the table has the exact entities, filters, and measures needed.
      - Be concise and concrete in explanations.
      - Output STRICT JSON ONLY with keys:
        { "query": str, "table": str, "relevance_rating": 1-5, "sufficient_to_answer": true/false,
          "why": [short bullets], "missing_info": [fields/constraints not found],
          "irrelevant_info": [fields that are off-topic for this query] }
      - No markdown fences, no extra keys, no comments.
      """
      ```
    
    - LLM ratings & explanations
    
      ```python
      #code:llm_table_assistant\task3_eval.py
      #result:llm_table_assistant\outputs\task3\task3_eval&example		rating and explanations
      #		llm_table_assistant\outputs\task3\task3_reflection		Show whether the most relevant table selected by Task 2 and Task 3 is the same, and compare their relevance scores across the entire set of K candidate tables. 
      
      ```
    
    - Reflection
    
      ```html
      The LLM did identify the most relevant table, but its final judgment may be inaccurate, especially for vague queries. For example, when asked to find “films suitable for Chinese people,” it correctly pointed to the film table but did not assign the highest score (5). In my view, there are two reasons:
      
      1. The language_id field in the film table is stored as a numeric code, which must be joined with the separate language table. Relying on language_id alone cannot determine the actual language.
      
      2. Even knowing the language is not sufficient to decide whether a film is suitable for Chinese viewers.
      ```

------------------------------------------------------------------------

## 📌 Method Explanation (to be filled by you)

-   Task 1: \<描述你的方法，例如：是否加入样例行，如何约束格式\>\
-   Task 2: \<描述检索方法，例如：embedding + cosine，相似度+LLM重排\>\
-   Task 3: `<描述评估提示与打分准则>`{=html}

------------------------------------------------------------------------

## 🚀 Key Insights & Challenges (to be filled by you)

- **Insights:** 

  - **Structured prompts → stable outputs.** I explicitly set the model’s role, stated the task, enforced a **strict JSON schema**, and listed rules. This reduced drift and made results reproducible.
  - **Lean context, better accuracy.** For ranking/evaluation I pass only **salient columns** and a **few sample rows**. This provides enough signal for semantics while keeping tokens low.
  - **Consistent scoring.** A unified **1–5 relevance scale** with short reasons is used across Task 2/3, making results interpretable and easy to compare.

- **Challenges:** 

  - **File I/O details** (JSON/JSONL/CSV) required careful handling.

  Going forward: factor shared **I/O helpers**, **model loader**, and **path/logging utilities** into a small common module to remove duplication and make future tasks easier to extend.

------------------------------------------------------------------------

## ▶️ Quick Reproduce

``` bash
# 1. Install dependencies
pip install langgraph langchain_community "langchain[openai]"
pip install langchain-openai python-dotenv pandas

# 2. Prepare data (optional)
#python prepare_data.py --out_dir ./data

# 3. Run Task 1
python task1_schema_summary.py

# 4. Run Task 2
python task2_search.py "find an actor whose last name is GUINESS" --k 5

# 5. Run Task 3
python task3_eval.py
```

