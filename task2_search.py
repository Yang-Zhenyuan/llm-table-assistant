from __future__ import annotations
# -*- coding: utf-8 -*-
"""
Created on Sun Aug 18 09:19:12 2025

@author: LENOVO
"""
"""
Usage
-----
python task2_search_chatgpt.py "films longer than 120 minutes in Italian" --k 5
python task2_search_chatgpt.py "employee salaries" --schemas outputs/schema_summaries.json --model gpt-4o-mini


- Prints ranked tables with short justifications
- Saves a machine-readable dump to task2_llm_results.json
"""

import argparse
import json
import os
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
load_dotenv()  # load .envv

# from src.retrieval_graph.utils import load_chat_model
from openai import OpenAI  
try:
    from src.retrieval_graph.utils import load_chat_model
except ImportError:
    from utils import load_chat_model  # fallback for running directly from the project root

from src.retrieval_graph.embedding import embed_rank_tables
import math

def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def compact_columns(columns: List[Dict[str, str]], max_cols: int = 12) -> str:
    """
    Extract column names with a maximum of `max_cols` (default 12).
    If there are more, truncate and append "..." to keep the prompt concise.
    """
    names = [c.get("name", "") for c in columns if isinstance(c, dict)]
    if len(names) > max_cols:
        names = names[:max_cols] + ["..."]
    return ", ".join([n for n in names if n])


def build_table_snippet(tbl: Dict[str, Any], max_summary_len: int = 320) -> str:
    """
    Compress each table into a short description including:
        table name, path (if available), summary (≤320 chars), and the first 16 column names.
    These snippets are concatenated into the LLM prompt.
    """
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


from src.retrieval_graph.prompts import TABLE_MATCH_PROMPT

def call_llm_rank(query: str, table_snippets: List[str], k: int, model: str) -> Dict[str, Any]:
    """
    Use the LLM to rank candidate tables for a given query.
        - query: the user input question
        - table_snippets: compressed descriptions of tables (from build_table_snippet)
        - k: number of top tables to return
        - model: model name to load via load_chat_model
    Returns:
        Parsed JSON object with table scores and reasons.
    """
    
    if OpenAI is None:
        raise RuntimeError("openai package not installed. Run: pip install openai")

    llm = load_chat_model(model)
    content = f"User query:\n{query}\n\nK = {k}\n\nCandidate tables:\n" + "\n".join(table_snippets)

    resp = llm.invoke([
        {"role": "system", "content": TABLE_MATCH_PROMPT},
        {"role": "user", "content": content},
    ])

    txt = getattr(resp, "content", str(resp)).strip()
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
    """
    Define and configure command-line arguments for Task 2:
    This parser allows the user to provide:
      query              Natural language query (positional argument)
      --schemas          Path to Task 1 schema summaries JSON (default: outputs/task1/schema_summaries.json)
      --k                How many tables to select (default: 5)
      --model            OpenAI chat model name (default: from OPENAI_MODEL env var or "gpt-4o-mini")
      --limit            Max number of candidate tables to pass into the LLM (default: 30)
    """
    
    parser = argparse.ArgumentParser(description="Task 2 (ChatGPT): Rank tables using Task 1 summaries + LLM")
    parser.add_argument("query", type=str, help="Natural language query")
    parser.add_argument("--schemas", type=str, default="outputs/task1/schema_summaries.json",
                        help="Path to Task 1 schema summaries JSON")
    parser.add_argument("--k", type=int, default=5, help="How many tables to select")
    parser.add_argument("--model", type=str, default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        help="OpenAI chat model (default from OPENAI_MODEL or 'gpt-4o-mini')")
    parser.add_argument("--limit", type=int, default=30, help="Max candidates to show the LLM")
    #embedding
    parser.add_argument("--mode", type=str, default="llm",
                    choices=["llm", "embedding"],
                    help="Ranking mode: 'llm' (default) or 'embedding'")
    parser.add_argument("--embedding-model", type=str, default="text-embedding-3-small",
                    help="Embedding model name")
    args = parser.parse_args()
    
    
    
    # Validate schema summaries input
    if not os.path.exists(args.schemas):
        raise FileNotFoundError(f"Schema summaries not found: {args.schemas}")
        
    summaries = read_json(args.schemas)
    if not isinstance(summaries, list) or not summaries:
        raise ValueError("Schema summaries JSON must be a non-empty list")

    if args.mode == "embedding":
        ranked = embed_rank_tables(
            summaries=summaries,
            query=args.query,
            embedding_model=args.embedding_model,
            k=args.k,
        )

        print("=" * 80)
        print(f"Query: {args.query}")
        print(f"Mode: embedding")
        print(f"Embedding model: {args.embedding_model}")
        print(f"Schemas: {args.schemas}")
        print("-" * 80)
        for i, r in enumerate(ranked, 1):
            print(f"[{i}] table: {r['table']}  score: {r['score']:.4f}")
        print("=" * 80)
    
        os.makedirs(os.path.join("outputs", "task2"), exist_ok=True)
        out_path = os.path.join("outputs", "task2", "task2_llm_results.json")
        write_json(out_path, {
            "query": args.query,
            "mode": "embedding",   # mark that this result was produced by embedding
            "embedding_model": args.embedding_model,
            "schemas": args.schemas,
            "choices": ranked      # ranked list: [{"table": ..., "score": ...}]
        })
        print(f"Saved: {out_path}")

        return  # 结束 embedding 分支
    

    # Build compact snippets for the LLM
    snippets = [build_table_snippet(s) for s in summaries[: args.limit]]

    result = call_llm_rank(args.query, snippets, args.k, args.model)
    
    """
    Normalize the LLM output:
        - Extract table name / score / reason from the LLM response.
        - Look up the original summary record to recover path / full summary / full columns for downstream use.
    """
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

    # print results
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

    os.makedirs(os.path.join("outputs", "task2"), exist_ok=True)
    # insure contain outputs/task2 
    
    # save result to outputs/task2/task2_llm_results.json
    write_json(os.path.join("outputs", "task2", "task2_llm_results.json"), {
        "query": args.query,
        "model": args.model,
        "schemas": args.schemas,
        "choices": ranked
    })
    print("Saved: outputs/task2/task2_llm_results.json")


if __name__ == "__main__":
    main()