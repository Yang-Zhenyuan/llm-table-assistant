# -*- coding: utf-8 -*-
"""
Created on Sun Aug 18 09:13:22 2025

@author: LENOVO
"""
"""
Task 3: LLM-Based Evaluation of Retrieved Tables
------------------------------------------------
Reads Task 1's schema summaries and Task 2's retrieved-table results,
then asks an LLM to rate (1–5) the relevance of EACH candidate table to the query,
with short explanations + missing/irrelevant info. Includes 3 sample rows per table.

Outputs:
- outputs/task3_eval.jsonl        # one JSON per (query, table)
- outputs/task3_examples.md       # pretty examples for the current query
- outputs/task3_reflection.md     # quick numeric reflection vs Task2 scores

Usage:
  python task3_eval.py --results outputs/task2_llm_results.json \
                       --schemas outputs/schema_summaries.json \
                       --csv-dir data \
                       --model gpt-4o-mini
"""

import argparse, os, json, re, datetime, random
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()   #load .evn
try:
    from src.retrieval_graph.utils import load_chat_model
except Exception:
    from utils import load_chat_model


import pandas as pd


def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_text(path: str, s: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)


def append_jsonl(path: str, obj: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def norm_name(x: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", x.lower()).strip("_")


def build_table_index(csv_dir: str) -> Dict[str, str]:
    # Map normalized table_name -> csv path 'Sakila_actor.csv' -> 'sakila_actor'
    idx: Dict[str, str] = {}
    for p in Path(csv_dir).glob("*.csv"):
        stem = norm_name(p.stem)
        idx[stem] = str(p)
    return idx


def sample_rows(csv_path: str, n: int = 3) -> List[Dict[str, Any]]:
    try:
        df = pd.read_csv(csv_path)
        # head n (no random to keep determinism)
        df = df.head(n)
        rows = []
        for _, r in df.iterrows():
            row = {}
            for c, v in r.to_dict().items():
                s = "" if pd.isna(v) else str(v)
                if len(s) > 60:
                    s = s[:57] + "..."
                row[str(c)] = s
            rows.append(row)
        return rows
    except Exception as e:
        return [{"_warning": f"sample_rows_failed: {e}"}]


# EVAL_SYSTEM_PROMPT = """You are a rigorous data analyst.
# Judge how relevant ONE candidate table is to the given user query.

# Scoring scale:
# 5 = Fully aligned. This table alone contains the key fields needed to answer the query.
# 4 = Mostly aligned. It answers the main intent but might miss minor constraints/fields.
# 3 = Partially related. Provides context/partial info; likely needs joins with other tables.
# 2 = Weakly related. Only tangentially related to the topic.
# 1 = Irrelevant.

# Instructions:
# - Base your decision on the provided table summary, column list, and the 3 sample rows.
# - Think about whether the table has the exact entities, filters, and measures needed.
# - Be concise and concrete in explanations.
# - Output STRICT JSON ONLY with keys:
#   { "query": str, "table": str, "relevance_rating": 1-5, "sufficient_to_answer": true/false,
#     "why": [short bullets], "missing_info": [fields/constraints not found],
#     "irrelevant_info": [fields that are off-topic for this query] }
# - No markdown fences, no extra keys, no comments.
# """
# from src.retrieval_graph.prompts import EVAL_PROMPT

from src.retrieval_graph.prompts import EVAL_PROMPT

def call_llm_eval(model: str, query: str, table: str,
                  summary: str, columns: List[Dict[str, Any]],
                  samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Use utils.load_chat_model(model) to eval one candidate table against the query.
    Return STRICT-JSON as dictated by EVAL_PROMPT; robust to minor formatting drift.
    """
    llm = load_chat_model(model)
    if llm is None:
        raise RuntimeError("Failed to load chat model. Check utils.load_chat_model / OPENAI_* envs.")

    # 2) 压缩负载，控制 token
    col_names = [c["name"] if isinstance(c, dict) and "name" in c else str(c)
                 for c in (columns or [])][:64]

    payload: Dict[str, Any] = {
        "query": query,
        "table": table,
        "table_summary": (summary or "")[:800],  # 摘要截断
        "columns": col_names[:40],               # 只传前 40 列名
        "samples": samples[:3],                  # 只传 3 行样例
    }
    user_content = json.dumps(payload, ensure_ascii=False)

    # 3) 直接用 llm.invoke(messages)（与 Task1 一致）
    messages = [
        {"role": "system", "content": EVAL_PROMPT},
        {"role": "user", "content": user_content},
    ]
    resp = llm.invoke(messages)

    # 4) 解析输出
    txt = getattr(resp, "content", str(resp)).strip()
    try:
        data = json.loads(txt)
    except Exception:
        m = re.search(r"\{.*\}", txt, flags=re.S)
        if not m:
            raise ValueError(f"LLM did not return JSON. Raw:\n{txt}")
        data = json.loads(m.group(0))

    # 5) 补默认键，避免缺字段
    data.setdefault("query", query)
    data.setdefault("table", table)
    data.setdefault("relevance_rating", 0)
    data.setdefault("sufficient_to_answer", False)
    data.setdefault("why", [])
    data.setdefault("missing_info", [])
    data.setdefault("irrelevant_info", [])
    return data



def spearman(a: List[float], b: List[float]) -> Optional[float]:
    """Simple Spearman correlation (no SciPy)."""
    if len(a) != len(b) or len(a) < 2:
        return None
    def ranks(x):
        order = sorted(range(len(x)), key=lambda i: x[i])
        r = [0]*len(x)
        for rank, i in enumerate(order, start=1):
            r[i] = rank
        return r
    ra, rb = ranks(a), ranks(b)
    n = len(a)
    num = 6 * sum((ra[i]-rb[i])**2 for i in range(n))
    return 1 - num / (n*(n**2 - 1))

def write_reflection(out_reflect: str,
                     choices: List[Dict[str, Any]],
                     pairs: List[Tuple[str, float, float]],
                     scores_t2: List[float],
                     ratings_t3: List[float]) -> None:
    """
    生成 Task3 的 reflection 文件，包括 Top-1 一致性和 Spearman 秩相关。
    """
    lines_ref: List[str] = ["# Task 3 – Reflection\n"]

    # check top-1
    t2_top = None
    if choices:
        t2_top = max(
            choices,
            key=lambda c: (c.get("score", float("-inf")), -len(str(c.get("table", ""))))
        ).get("table")

    t3_top = None
    valid = [(tbl, r) for (tbl, _, r) in pairs if isinstance(r, (int, float))]
    if valid:
        t3_top = max(valid, key=lambda x: x[1])[0]

    lines_ref.append(f"- Top-1 (Task2): **{t2_top}**" if t2_top else "- Top-1 (Task2): N/A")
    lines_ref.append(f"- Top-1 (Task3): **{t3_top}**" if t3_top else "- Top-1 (Task3): N/A")
    if t2_top and t3_top:
        lines_ref.append(f"- Top-1 of task2 and task3 is same: **{'YES' if t2_top == t3_top else 'NO'}**")

    # ---- Spearman ----
    if ratings_t3 and scores_t2:
        r = spearman(scores_t2, ratings_t3)
        if r is not None:
            lines_ref.append(f"- Spearman(Task2_score, Task3_rating) = **{r:.3f}**")
    else:
        lines_ref.append("- Not enough overlapping numeric scores to compute correlation.")

    lines_ref.append("\nFor qualitative analysis, see `task3_examples.md`.")
    write_text(out_reflect, "\n".join(lines_ref))



def main():
    parser = argparse.ArgumentParser(description="Task 3: LLM-based evaluation of Task 2 tables")
    parser.add_argument("--results", type=str,
                        default=os.path.join("outputs", "task2", "task2_llm_results.json"),
                        help="Task 2 output JSON (contains query + candidate tables)")
    parser.add_argument("--schemas", type=str,
                        default=os.path.join("outputs", "task1", "schema_summaries.json"),
                        help="Task 1 summaries JSON")
    parser.add_argument("--csv-dir", type=str, default="data",
                        help="Folder with CSVs (for 3 sample rows)")
    parser.add_argument("--model", type=str, default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        help="OpenAI model (default from env or gpt-4o-mini)")
    parser.add_argument("--sample-rows", type=int, default=3, help="Rows per table to include")
    args = parser.parse_args()

    if not os.path.exists(args.results):
        raise FileNotFoundError(f"Task2 results not found: {args.results}")
    if not os.path.exists(args.schemas):
        raise FileNotFoundError(f"Task1 summaries not found: {args.schemas}")

    t2 = read_json(args.results)
    summaries = read_json(args.schemas)
    if not isinstance(summaries, list) or not summaries:
        raise ValueError("Schema summaries must be a non-empty list")

    query = t2.get("query", "")
    choices = t2.get("choices", [])
    if not query or not choices:
        raise ValueError("Task2 results missing 'query' or 'choices'")


    # Build table -> schema mapping
    by_table: Dict[str, Dict[str, Any]] = {}
    for s in summaries:
        name = (s.get("table") or s.get("name") or "").strip()
        if name:
            by_table[norm_name(name)] = s

    # Build table -> csv path index for samples
    csv_index = build_table_index(args.csv_dir)

    out_dir = os.path.join("outputs", "task3")
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    
    out_jsonl   = os.path.join(out_dir, "task3_eval.jsonl")
    out_md      = os.path.join(out_dir, "task3_examples.md")
    out_reflect = os.path.join(out_dir, "task3_reflection.md")
    
    # Clear old JSONL (optional)
    Path(out_jsonl).unlink(missing_ok=True)


    model = args.model
    model_env = os.getenv("OPENAI_MODEL")
    if model_env and model_env != model:
        # honor CLI flag if explicitly set
        pass

    print("="*80)
    print(f"Query: {query}")
    print(f"Model: {model}")
    print(f"Candidates from Task2: {len(choices)}")

    #make .md document
    ratings_t3: List[float] = []
    scores_t2: List[float] = []
    lines_md: List[str] = [f"# Task 3 – LLM Evaluation for Query\n\n**Query:** {query}\n\n"]
    pairs: List[Tuple[str, float, float]] = []   # (table, task2_score, task3_rating)

    
    now = datetime.datetime.now().isoformat(timespec="seconds")
    for c in choices:
        tbl = c.get("table") or ""
        t2_score = c.get("score", None)
        # lookup schema
        key = norm_name(tbl)
        sch = by_table.get(key, {})
        summary = sch.get("summary") or ""
        columns = sch.get("columns") or []

        # sample rows
        csv_path = csv_index.get(key)
        if not csv_path:
            # fallback: try raw table string against index
            for k, v in csv_index.items():
                if k == key or k.endswith("_" + key) or key.endswith("_" + k):
                    csv_path = v
                    break
        samples = sample_rows(csv_path, n=args.sample_rows) if csv_path else [{"_warning": "csv_not_found"}]

        # call llm
        data = call_llm_eval(model, query, tbl, summary, columns, samples)
        data.update({
            "model_name": model,
            "eval_time": now,
            "task2_score": t2_score,
            "csv_path": csv_path or "",
        })
        append_jsonl(out_jsonl, data)

        # For MD
        lines_md.append(f"## Table: `{tbl}`")
        lines_md.append(f"- **Task3 rating:** {data.get('relevance_rating')}  "
                        f"{'✅ sufficient' if data.get('sufficient_to_answer') else '❌ not sufficient'}")
        if t2_score is not None:
            lines_md.append(f"- **Task2 score:** {t2_score}")
        why = data.get("why") or []
        if isinstance(why, list) and why:
            lines_md.append(f"- **Why:** " + "; ".join(str(x) for x in why))
        miss = data.get("missing_info") or []
        if miss:
            lines_md.append(f"- **Missing info:** " + "; ".join(str(x) for x in miss))
        irr = data.get("irrelevant_info") or []
        if irr:
            lines_md.append(f"- **Irrelevant info:** " + "; ".join(str(x) for x in irr))
        lines_md.append("")

        # For reflection
        if isinstance(data.get("relevance_rating"), (int, float)) and isinstance(t2_score, (int, float)):
            ratings_t3.append(float(data["relevance_rating"]))
            scores_t2.append(float(t2_score))
            # 记录每个表的 (表名, Task2 分数, Task3 评分)
            pairs.append((tbl, float(t2_score) if isinstance(t2_score, (int, float)) else 0.0,
              float(data.get("relevance_rating", 0.0))))


    # Save MD
    write_text(out_md, "\n".join(lines_md))

    # # Quick numeric reflection
    # Reflection 输出
    write_reflection(out_reflect, choices, pairs, scores_t2, ratings_t3)


    print(f"Saved: {out_jsonl}")
    print(f"Saved: {out_md}")
    print(f"Saved: {out_reflect}")


if __name__ == "__main__":
    main()
