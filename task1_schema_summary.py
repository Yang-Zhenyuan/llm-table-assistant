#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re, sys
from pathlib import Path
import pandas as pd

# 让 src/ 布局可直接 import
ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT / "src"))

from retrieval_graph.io_utils import discover_csvs, read_csv_any, write_json
from retrieval_graph.llm_utils import chat_json
from dotenv import load_dotenv
load_dotenv()

# 优先使用 prompts.py 中的提示词，缺失时回退到内置
try:
    from retrieval_graph.prompts import SCHEMA_SUMMARY_PROMPT as SCHEMA_PROMPT
except Exception:
    SCHEMA_PROMPT = (
        "You are a senior data analyst. Produce STRICT JSON ONLY with keys: "
        '{"table": str, "summary": str, "columns": [{"name": str, "description": str}]}. '
        "The summary MUST explain the table's PURPOSE in 2–3 sentences."
    )

CSV_DIR = os.getenv("CSV_DIR", str(ROOT / "data"))
OUT_PATH = str(ROOT / "outputs" / "schema_summaries.json")
SAMPLE_ROWS = int(os.getenv("SAMPLE_ROWS", 5))
LOWER_TABLE = True


def _fallback(table: str, df: pd.DataFrame) -> dict:
    return {
        "table": table,
        "summary": (
            f"The `{table}` table stores records related to {table}. "
            f"It is typically used for lookups and joins involving `{table}`."
        ),
        "columns": [{"name": str(c), "description": f"Column '{c}'"} for c in df.columns],
    }


def _summarise_one(path: str) -> dict:
    table = re.sub(r"\.csv$", "", Path(path).name, flags=re.I)
    df = read_csv_any(path)
    payload = {
        "table": table,
        "columns": [str(c) for c in df.columns],
        "sample_rows": df.head(SAMPLE_ROWS).to_dict(orient="records"),
    }
    try:
        obj = chat_json(SCHEMA_PROMPT, payload)
        t = (obj.get("table") or table).strip()
        cols = obj.get("columns") or []
        cols = [{"name": str(c.get("name", "")), "description": str(c.get("description", "")).strip()} for c in cols]
        if not cols:
            cols = [{"name": str(c), "description": f"Column '{c}'"} for c in df.columns]
        summ = (obj.get("summary") or "").strip() or _fallback(t, df)["summary"]
        if LOWER_TABLE:
            t = t.lower()
        return {"table": t, "summary": summ, "columns": cols}
    except Exception:
        return _fallback(table.lower() if LOWER_TABLE else table, df)


def main():
    csv_paths = discover_csvs(CSV_DIR)
    if not csv_paths:
        raise FileNotFoundError(f"No CSV found under '{CSV_DIR}'")

    records = []
    for p in csv_paths:
        rec = _summarise_one(p)
        print("OK:", rec["table"])
        records.append(rec)

    write_json(OUT_PATH, records)
    print(f"[Task1] wrote {OUT_PATH} ({len(records)} tables)")


if __name__ == "__main__":
    main()
