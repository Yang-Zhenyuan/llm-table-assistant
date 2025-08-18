# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, os, sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT / "src"))

from retrieval_graph.io_utils import read_json, write_json
from retrieval_graph.llm_utils import chat_json
from dotenv import load_dotenv
load_dotenv()

# 优先用你的 prompts；没有就用内置严格 JSON 版
try:
    from retrieval_graph.prompts import TABLE_MATCH_PROMPT as SYSTEM_PROMPT
except Exception:
    SYSTEM_PROMPT = """You are a meticulous data analyst.
Given a user query and a list of candidate table summaries, select the K most relevant tables.

Return ONLY a strict JSON object with this shape:
{
  "query": "<echo query>",
  "choices": [
    {"table": "<table_name>", "score": 1-5, "reason": "<<=15 words>"}
  ]
}
Rules:
- Choose exactly K entries in "choices".
- Higher score = more relevant.
- Do NOT invent tables that were not provided.
- Prefer tables whose summaries/columns directly support the query constraints.
"""

def compact_columns(columns: List[Dict[str, str]], max_cols: int = 12) -> str:
    names = [c.get("name", "") for c in columns if isinstance(c, dict)]
    if len(names) > max_cols:
        names = names[:max_cols] + ["..."]
    return ", ".join([n for n in names if n])


def build_table_snippet(tbl: Dict[str, Any], max_summary_len: int = 320) -> str:
    name = tbl.get("table") or tbl.get("name") or "unknown_table"
    summ = (tbl.get("summary") or "").strip()
    if len(summ) > max_summary_len:
        summ = summ[:max_summary_len] + "..."
    cols = tbl.get("columns") or []
    col_line = compact_columns(cols, 16)
    parts = [f"- table: {name}"]
    if summ:
        parts.append(f"  summary: {summ}")
    if col_line:
        parts.append(f"  columns: {col_line}")
    return "\n".join(parts)


def call_rank_llm(query: str, table_snippets: List[str], k: int, model: str):
    content = f"User query:\n{query}\n\nK = {k}\n\nCandidate tables:\n" + "\n".join(table_snippets)
    return chat_json(SYSTEM_PROMPT, content, model=model)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", type=str)
    ap.add_argument("--schemas", default=str(ROOT / "outputs" / "schema_summaries.json"))
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--model", type=str, default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    ap.add_argument("--limit", type=int, default=30)
    args = ap.parse_args()

    summaries = read_json(args.schemas)
    snippets = [build_table_snippet(s) for s in summaries[: args.limit]]

    result = call_rank_llm(args.query, snippets, args.k, args.model)
    choices = result.get("choices") or []

    ranked = []
    for c in choices:
        tbl = str(c.get("table", ""))
        ranked.append({
            "table": tbl,
            "score": c.get("score", 0),
            "reason": str(c.get("reason", "")),
        })

    out = {"query": args.query, "model": args.model, "schemas": args.schemas, "choices": ranked}
    out_path = str(ROOT / "outputs" / "task2_llm_results.json")
    write_json(out_path, out)

    print("=" * 80)
    print(f"Query: {args.query}")
    print(f"Model: {args.model}")
    print(f"Schemas: {args.schemas}")
    print("-" * 80)
    for i, r in enumerate(ranked, 1):
        print(f"[{i}] table: {r['table']}  score: {r['score']}  reason: {r['reason']}")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
