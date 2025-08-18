#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, os, sys, datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT / "src"))

from retrieval_graph.io_utils import (
    read_json, write_text, append_jsonl, build_table_index, sample_rows, norm_name
)
from retrieval_graph.llm_utils import chat_json
from dotenv import load_dotenv
load_dotenv()

# 优先使用 prompts 中的评测提示词，缺失则回退
try:
    from retrieval_graph.prompts import EVAL_PROMPT as EVAL_SYSTEM_PROMPT
except Exception:
    EVAL_SYSTEM_PROMPT = """You are a rigorous data analyst.
Judge how relevant ONE candidate table is to the given user query.

Scoring scale:
5 = Fully aligned; 4 = Mostly; 3 = Partial; 2 = Weak; 1 = Irrelevant.

Instructions:
- Base on the provided table summary, column list, and the 3 sample rows.
- Output STRICT JSON ONLY with keys:
  { "query": str, "table": str, "relevance_rating": 1-5, "sufficient_to_answer": true/false,
    "why": [short bullets], "missing_info": [fields not found], "irrelevant_info": [off-topic fields] }
"""

def spearman(a: List[float], b: List[float]):
    if len(a) != len(b) or len(a) < 2:
        return None
    order_a = sorted(range(len(a)), key=lambda i: a[i])
    order_b = sorted(range(len(b)), key=lambda i: b[i])
    ra = [0]*len(a); rb = [0]*len(b)
    for r, i in enumerate(order_a, 1): ra[i] = r
    for r, i in enumerate(order_b, 1): rb[i] = r
    n = len(a)
    num = 6 * sum((ra[i]-rb[i])**2 for i in range(n))
    return 1 - num / (n*(n**2 - 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(ROOT / "outputs" / "task2_llm_results.json"))
    ap.add_argument("--schemas", default=str(ROOT / "outputs" / "schema_summaries.json"))
    ap.add_argument("--csv-dir", default=str(ROOT / "data"))
    ap.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    ap.add_argument("--sample-rows", type=int, default=3)
    args = ap.parse_args()

    t2 = read_json(args.results)
    summaries = read_json(args.schemas)

    query = t2.get("query", "")
    choices = t2.get("choices", [])
    if not query or not choices:
        raise ValueError("Task2 results missing 'query' or 'choices'")

    # schema 索引
    by_table: Dict[str, Dict[str, Any]] = {}
    for s in summaries:
        name = (s.get("table") or s.get("name") or "").strip()
        if name:
            by_table[norm_name(name)] = s

    csv_index = build_table_index(args.csv_dir)

    out_jsonl = str(ROOT / "outputs" / "task3_eval.jsonl")
    out_md = str(ROOT / "outputs" / "task3_examples.md")
    out_reflect = str(ROOT / "outputs" / "task3_reflection.md")

    # 清理旧 JSONL
    try:
        if os.path.exists(out_jsonl):
            os.remove(out_jsonl)
    except Exception:
        pass

    ratings_t3: List[float] = []
    scores_t2: List[float] = []
    lines_md: List[str] = [f"# Task 3 – LLM Evaluation for Query\n\n**Query:** {query}\n\n"]

    now = datetime.datetime.now().isoformat(timespec="seconds")

    for c in choices:
        tbl = c.get("table") or ""
        t2_score = c.get("score", None)
        key = norm_name(tbl)
        sch = by_table.get(key, {})
        summary = sch.get("summary") or ""
        columns = sch.get("columns") or []

        # 找样例行
        csv_path = csv_index.get(key)
        if not csv_path:
            for k, v in csv_index.items():
                if k == key or k.endswith("_" + key) or key.endswith("_" + k):
                    csv_path = v
                    break
        samples = sample_rows(csv_path, n=args.sample_rows) if csv_path else [{"_warning": "csv_not_found"}]

        payload = {
            "query": query,
            "table": tbl,
            "table_summary": summary[:800],
            "columns": [col.get("name", col) if isinstance(col, dict) else str(col) for col in columns][:40],
            "samples": samples[:3],
        }
        data = chat_json(EVAL_SYSTEM_PROMPT, payload, model=args.model)
        data.update({
            "model_name": args.model,
            "eval_time": now,
            "task2_score": t2_score,
            "csv_path": csv_path or "",
        })
        append_jsonl(out_jsonl, data)

        # 生成 MD
        lines_md.append(f"## Table: `{tbl}`")
        lines_md.append(f"- **Task3 rating:** {data.get('relevance_rating')}  "
                        f"{'✅ sufficient' if data.get('sufficient_to_answer') else '❌ not sufficient'}")
        if t2_score is not None:
            lines_md.append(f"- **Task2 score:** {t2_score}")
        why = data.get("why") or []
        if isinstance(why, list) and why:
            lines_md.append("- **Why:** " + "; ".join(str(x) for x in why))
        miss = data.get("missing_info") or []
        if miss:
            lines_md.append("- **Missing info:** " + "; ".join(str(x) for x in miss))
        irr = data.get("irrelevant_info") or []
        if irr:
            lines_md.append("- **Irrelevant info:** " + "; ".join(str(x) for x in irr))
        lines_md.append("")

        if isinstance(data.get("relevance_rating"), (int, float)) and isinstance(t2_score, (int, float)):
            ratings_t3.append(float(data["relevance_rating"]))
            scores_t2.append(float(t2_score))

    # 保存 MD
    write_text(out_md, "\n".join(lines_md))

    # 反思
    lines_ref: List[str] = ["# Task 3 – Reflection\n"]
    if ratings_t3 and scores_t2:
        r = spearman(scores_t2, ratings_t3)
        lines_ref.append(f"- Spearman(Task2_score, Task3_rating) = **{r:.3f}**" if r is not None else "- Not enough points for correlation.")
        lines_ref.append("\n- If correlation is low, check cases where Task2 high but Task3 ≤3, or vice versa.")
    else:
        lines_ref.append("- Not enough overlapping numeric scores to compute correlation.")
    write_text(out_reflect, "\n".join(lines_ref))

    print(f"Saved: {out_jsonl}")
    print(f"Saved: {out_md}")
    print(f"Saved: {out_reflect}")


if __name__ == "__main__":
    main()
