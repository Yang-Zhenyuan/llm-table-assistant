#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task 2 (ChatGPT version): LLM-based Table Selection
---------------------------------------------------
Given a natural-language query, ask a ChatGPT-style model to select the most
relevant tables by *reading your Task 1 summaries* (defaults to outputs/schema_summaries.json).

This follows the Mini-Project instruction that Task 2 should reference the
schema summaries produced in Task 1.

Usage
-----
python task2_search_chatgpt.py "films longer than 120 minutes in Italian" --k 5
python task2_search_chatgpt.py "employee salaries" --schemas outputs/schema_summaries.json --model gpt-4o-mini

Environment
-----------
- Requires OPENAI_API_KEY in env (or .env if you use python-dotenv)
- Optional OPENAI_MODEL (default: gpt-4o-mini)

Output
------
- Prints ranked tables with short justifications
- Saves a machine-readable dump to task2_llm_results.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
load_dotenv()  # 这样会自动读取同目录下的 .env 文件

# from src.retrieval_graph.utils import load_chat_model
from openai import OpenAI  # openai>=1.0


def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def compact_columns(columns: List[Dict[str, str]], max_cols: int = 12) -> str:
    names = [c.get("name", "") for c in columns if isinstance(c, dict)]
    if len(names) > max_cols:
        names = names[:max_cols] + ["..."]
    return ", ".join([n for n in names if n])


def build_table_snippet(tbl: Dict[str, Any], max_summary_len: int = 320) -> str:
    name = tbl.get("table") or tbl.get("name") or "unknown_table"
    path = tbl.get("path") or ""
    summ = (tbl.get("summary") or "").strip()
    if len(summ) > max_summary_len:
        summ = summ[:max_summary_len] + "..."
    cols = tbl.get("columns") or []
    col_line = compact_columns(cols, 16)
    parts = [f"- table: {name}"]
    if path:
        parts.append(f"  path: {path}")
    if summ:
        parts.append(f"  summary: {summ}")
    if col_line:
        parts.append(f"  columns: {col_line}")
    return "\n".join(parts)


# SYSTEM_PROMPT = """You are a meticulous data analyst.
# Given a user query and a list of candidate table summaries, select the K most relevant tables.

# Return ONLY a strict JSON object with this shape:
# {
#   "query": "<echo query>",
#   "choices": [
#     {"table": "<table_name>", "score": <1-5>, "reason": "<short phrase, <=15 words>"},
#     ...
#   ]
# }

# Rules:
# - Choose exactly K entries in "choices".
# - Higher score = more relevant.
# - Keep reasons short and specific (column names or key fields help).
# - Do NOT invent tables that were not provided.
# - Prefer tables whose summaries/columns directly support the query constraints.
# """
from src.retrieval_graph.prompts import TABLE_MATCH_PROMPT


def call_llm_rank(query: str, table_snippets: List[str], k: int, model: str) -> Dict[str, Any]:
    if OpenAI is None:
        raise RuntimeError("openai package not installed. Run: pip install openai")

    client = OpenAI()
    # We will send up to ~30 tables to keep prompt reasonable
    content = f"User query:\n{query}\n\nK = {k}\n\nCandidate tables:\n" + "\n".join(table_snippets)

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": TABLE_MATCH_PROMPT},
            {"role": "user", "content": content},
        ],
        temperature=0,
        response_format={"type": "json_object"},  # Ask the API to enforce JSON
    )
    txt = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(txt)
    except Exception:
        # Fallback: attempt to extract JSON via regex
        m = re.search(r"\{.*\}", txt, flags=re.S)
        if not m:
            raise ValueError(f"LLM did not return JSON. Raw:\n{txt}")
        data = json.loads(m.group(0))
    return data


def main():
    parser = argparse.ArgumentParser(description="Task 2 (ChatGPT): Rank tables using Task 1 summaries + LLM")
    parser.add_argument("query", type=str, help="Natural language query")
    parser.add_argument("--schemas", type=str, default="outputs/schema_summaries.json",
                        help="Path to Task 1 schema summaries JSON")
    parser.add_argument("--k", type=int, default=5, help="How many tables to select")
    parser.add_argument("--model", type=str, default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        help="OpenAI chat model (default from OPENAI_MODEL or 'gpt-4o-mini')")
    parser.add_argument("--limit", type=int, default=30, help="Max candidates to show the LLM")
    args = parser.parse_args()

    if not os.path.exists(args.schemas):
        raise FileNotFoundError(f"Schema summaries not found: {args.schemas}")

    summaries = read_json(args.schemas)
    if not isinstance(summaries, list) or not summaries:
        raise ValueError("Schema summaries JSON must be a non-empty list")

    # Build compact snippets for the LLM
    snippets = [build_table_snippet(s) for s in summaries[: args.limit]]

    result = call_llm_rank(args.query, snippets, args.k, args.model)

    # Normalize output
    choices = result.get("choices") or []
    ranked = []
    for c in choices:
        tbl = str(c.get("table", ""))
        score = int(c.get("score", 0)) if str(c.get("score", "")).isdigit() else c.get("score", 0)
        reason = str(c.get("reason", ""))
        # Find original record (path, full columns, summary) for convenience
        match = next((s for s in summaries if (s.get("table") or s.get("name")) == tbl), None)
        ranked.append({
            "table": tbl,
            "score": score,
            "reason": reason,
            "path": (match or {}).get("path"),
            "summary": (match or {}).get("summary"),
            "columns": (match or {}).get("columns"),
        })

    # Pretty print
    print("=" * 80)
    print(f"Query: {args.query}")
    print(f"Model: {args.model}")
    print(f"Schemas: {args.schemas}")
    print("-" * 80)
    for i, r in enumerate(ranked, 1):
        print(f"[{i}] table: {r['table']}  score: {r['score']}  reason: {r['reason']}")
        if r.get("path"):
            print(f"    path: {r['path']}")
    print("=" * 80)

  # 确保根目录下有 outputs/task2 文件夹
    os.makedirs(os.path.join("outputs", "task2"), exist_ok=True)
    
    # 保存结果到 outputs/task2/task2_llm_results.json
    write_json(os.path.join("outputs", "task2", "task2_llm_results.json"), {
        "query": args.query,
        "model": args.model,
        "schemas": args.schemas,
        "choices": ranked
    })
    print("Saved: outputs/task2/task2_llm_results.json")


if __name__ == "__main__":
    main()