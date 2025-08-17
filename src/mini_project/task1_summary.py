from __future__ import annotations
# -*- coding: utf-8 -*-
"""
Created on Sun Aug 17 03:44:11 2025

@author: LENOVO
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task 1: Table Schema Summarisation

Reads a directory of CSV tables, infers light-weight schema signals (dtype, null%,
distinct count, example values), asks an LLM to summarise each table and describe
each column in natural language, then writes CSV/JSON/Markdown outputs.

Run:
  python -m retrieval_graph.task1_schema_summary \
    --csv_dir data/csv_tables \
    --out_csv data/schema_summaries.csv \
    --out_json data/schema_summaries.json \
    --out_md data/schema_summaries.md \
    --model azure-openai/GPT4-O \
    --sample_rows 5

The model is loaded using `load_chat_model`, which already supports Azure OpenAI etc.
"""


import argparse
import csv
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
from langchain_core.messages import SystemMessage, HumanMessage

from .prompts import SCHEMA_SUMMARY_SYSTEM_PROMPT
from .utils import load_chat_model  # uses your existing loader


def _infer_table_name(path: Path) -> str:
    return path.stem  # file name without extension


def _summarise_column_series(s: pd.Series) -> Dict[str, Any]:
    non_null = s.dropna()
    dtype = str(s.dtype)
    null_ratio = float(s.isna().mean()) if len(s) else 0.0
    distinct = int(non_null.nunique()) if len(non_null) else 0
    # Example values: up to 3 distinct non-null values (stringified)
    ex_values = list(map(lambda v: str(v), non_null.unique()[:3]))
    return {
        "dtype": dtype,
        "null_ratio": round(null_ratio, 4),
        "distinct": distinct,
        "examples": ex_values,
    }


def _build_schema_context(table_name: str, df: pd.DataFrame, sample_rows: int = 5) -> str:
    # Column stats block
    col_stats = []
    for col in df.columns:
        stats = _summarise_column_series(df[col])
        col_stats.append(
            f"- {col}: dtype={stats['dtype']}, null%={stats['null_ratio']*100:.1f}, "
            f"distinct={stats['distinct']}, examples={stats['examples']}"
        )
    col_block = "\n".join(col_stats)

    # Sample rows block (a few rows to help semantics)  【PDF建议包含一些示例行】
    # We truncate wide rows to avoid token blowups.
    sample = df.head(sample_rows).astype(str)
    sample_rows_txt = "\n".join(
        json.dumps(row, ensure_ascii=False)
        for row in sample.to_dict(orient="records")
    )

    context = f"""Table: {table_name}

Columns & stats:
{col_block}

Sample rows (first {sample_rows}):
{sample_rows_txt}
"""
    return context


def _robust_json_extract(text: str) -> Dict[str, Any]:
    """
    Try to parse JSON. If the model surrounded JSON with prose,
    grab the first {...} block heuristically.
    """
    text = text.strip()
    # Fast path
    try:
        return json.loads(text)
    except Exception:
        pass
    # Heuristic: find outermost JSON object
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    raise ValueError("LLM did not return valid JSON")


def llm_summarise_table(
    llm, table_name: str, schema_context: str
) -> Dict[str, Any]:
    messages = [
        SystemMessage(content=SCHEMA_SUMMARY_SYSTEM_PROMPT),
        HumanMessage(content=schema_context),
    ]
    resp = llm.invoke(messages)
    return _robust_json_extract(getattr(resp, "content", ""))


def summarise_csv_file(
    llm, csv_path: Path, sample_rows: int = 5, read_kwargs: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    read_kwargs = read_kwargs or {}
    df = pd.read_csv(csv_path, **read_kwargs)
    table_name = _infer_table_name(csv_path)
    schema_ctx = _build_schema_context(table_name, df, sample_rows=sample_rows)
    result = llm_summarise_table(llm, table_name, schema_ctx)
    # Ensure minimal shape
    result.setdefault("table", table_name)
    result.setdefault("summary", "")
    result.setdefault("columns", [])
    return result


def write_outputs(
    results: List[Dict[str, Any]],
    out_csv: Path | None,
    out_json: Path | None,
    out_md: Path | None,
):
    # 1) CSV: one row per table
    if out_csv:
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["table", "summary", "columns_json", "keys_json"])
            for r in results:
                writer.writerow(
                    [
                        r.get("table", ""),
                        r.get("summary", ""),
                        json.dumps(r.get("columns", []), ensure_ascii=False),
                        json.dumps(r.get("keys", {}), ensure_ascii=False),
                    ]
                )

    # 2) JSON: full structured output
    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3) Markdown: pretty doc for reading
    if out_md:
        out_md.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# Table Schema Summaries\n"]
        for r in results:
            lines.append(f"## {r.get('table','')}\n")
            lines.append(r.get("summary", "").strip() + "\n")
            cols = r.get("columns", [])
            if cols:
                lines.append("**Columns**\n")
                for c in cols:
                    lines.append(f"- **{c.get('name','')}**: {c.get('description','')}")
                lines.append("")
            keys = r.get("keys", {})
            if keys:
                lines.append("**Keys**\n")
                pk = keys.get("primary_key")
                if pk:
                    lines.append(f"- Primary key: {', '.join(pk)}")
                fks = keys.get("foreign_keys", [])
                for fk in fks:
                    lines.append(f"- FK: {fk.get('column')} → {fk.get('references')}")
                lines.append("")
        out_md.write_text("\n".join(lines), encoding="utf-8")


def summarise_csv_dir(
    csv_dir: Path,
    model_name: str = "azure-openai/GPT4-O",
    sample_rows: int = 5,
    out_csv: Path | None = None,
    out_json: Path | None = None,
    out_md: Path | None = None,
    read_kwargs: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """
    Public API: summarise all CSV files in a directory and write outputs.
    """
    llm = load_chat_model(model_name)  # uses your loader (Azure/OpenAI/etc.)
    csv_dir = Path(csv_dir)
    csv_paths = sorted([p for p in csv_dir.glob("*.csv") if p.is_file()])

    results: List[Dict[str, Any]] = []
    for p in csv_paths:
        try:
            print(f"[Task1] Summarising: {p.name}")
            r = summarise_csv_file(llm, p, sample_rows=sample_rows, read_kwargs=read_kwargs)
            results.append(r)
        except Exception as e:
            print(f"[Task1] Failed on {p.name}: {e}")

    write_outputs(results, out_csv, out_json, out_md)
    print(f"[Task1] Done. Tables processed: {len(results)}")
    return results


def main():
    parser = argparse.ArgumentParser(description="Task 1: Table Schema Summarisation")
    parser.add_argument("--csv_dir", required=True, help="Directory containing CSV files")
    parser.add_argument("--model", default="azure-openai/GPT4-O", help="Model string provider/name")
    parser.add_argument("--sample_rows", type=int, default=5, help="Rows to include as examples")
    parser.add_argument("--out_csv", default="data/schema_summaries.csv")
    parser.add_argument("--out_json", default="data/schema_summaries.json")
    parser.add_argument("--out_md", default="data/schema_summaries.md")
    args = parser.parse_args()

    summarise_csv_dir(
        csv_dir=Path(args.csv_dir),
        model_name=args.model,
        sample_rows=args.sample_rows,
        out_csv=Path(args.out_csv) if args.out_csv else None,
        out_json=Path(args.out_json) if args.out_json else None,
        out_md=Path(args.out_md) if args.out_md else None,
    )


if __name__ == "__main__":
    main()
