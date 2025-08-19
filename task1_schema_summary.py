# -*- coding: utf-8 -*-
"""
Created on Sun Aug 18 09:12:10 2025

@author: LENOVO
"""
"""
Simplified output for Task 1.

- Output a JSON(NOT JSONL).
- Only include: table, summary, columns[{name, description}].
- The summary MUST state the table's purpose.

"""

import os, re, glob, json
from pathlib import Path
import pandas as pd


def get_chat_model(name: str):
    """
    Unified chat model loader: try project loader first, then fall back to local utils
    """
    try:
        from src.retrieval_graph.utils import load_chat_model as _loader
        return _loader(name)
    except Exception:
        try:
            from utils import load_chat_model as _loader2
            return _loader2(name)
        except Exception:
            return None


def get_schema_prompt():
    """
    Get the Task1 prompt; provide a default one if missing
    """
    try:
        from src.retrieval_graph.prompts import SCHEMA_SUMMARY_PROMPT as P
        return P
    except Exception:
        try:
            from prompts import SCHEMA_SUMMARY_PROMPT as P2
            return P2
        except Exception:
            return (
                "You are a senior data analyst. Produce STRICT JSON ONLY with keys: "
                '{"table": str, "summary": str, "columns": [{"name": str, "description": str}, ...]}. '
                "The summary MUST explain the table's PURPOSE and typical use in 2–3 sentences. "
                "Use column names and sample rows to infer meanings. No extra keys, no markdown."
            )

CONFIG = {
    "csv_dir": os.path.join(os.path.dirname(__file__), "data"),   # CSV
    "out": os.path.join("outputs", "task1", "schema_summaries.json"), # output JSON
    "sample_rows": 5,                            # Number of sample rows shown to the LLM to help infer semantics
    "use_llm": True,
    "llm_name": "gpt-4o-mini",
    "lower_table": True,                         # lower case
}


"""
    File operation
"""
def discover_csvs(csv_dir: str):
    """
    Recursively find all CSV files (case-insensitive) under the given directory
    """
    paths = []
    for pat in ("*.csv", "*.CSV"):
        paths += glob.glob(os.path.join(csv_dir, pat))
        paths += glob.glob(os.path.join(csv_dir, "**", pat), recursive=True)
    return sorted(set(paths))

def read_csv_any(p: str) -> pd.DataFrame:
    for enc in ("utf-8", "utf-8-sig", "latin1"):
        try:
            return pd.read_csv(p, encoding=enc)
        except Exception:
            pass
    return pd.read_csv(p)  # 最后一次按默认再试


def simple_fallback(table: str, df: pd.DataFrame) -> dict:
    """
    Fallback summary used when the LLM is not available
    """
    return {
        "table": table,
        "summary": (
            f"The `{table}` table stores records related to {table}. "
            f"It is typically used for lookups and joins involving `{table}`, "
            f"helping analysts understand attributes of `{table}` entries."
        ),
        "columns": [{"name": str(c), "description": f"Column '{c}'"} for c in df.columns]
    }


def llm_structured_summary(llm, prompt: str, table: str, df: pd.DataFrame, sample_rows: int) -> dict:
    """
    Generate a structured table summary using the LLM.
    Includes column names and a few sample rows to help infer semantics.
    """
    payload = {
        "table": table,
        "columns": [str(c) for c in df.columns],             # columns only
        "sample_rows": df.head(sample_rows).to_dict(orient="records"),
        # row = 5. If available, include a few rows of sample data in the prompt to help infer semantics.
    }
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
    ]
    resp = llm.invoke(messages)
    txt = getattr(resp, "content", str(resp)).strip()
    # trim response to valid JSON (between the first '{' and last '}')
    if "{" in txt and "}" in txt:
        txt = txt[txt.find("{"): txt.rfind("}")+1]
    obj = json.loads(txt)

    # normalize fields
    t = obj.get("table") or table
    cols_out = obj.get("columns") or []
    cols_out = [{"name": str(c.get("name","")), "description": str(c.get("description","")).strip()}
                for c in cols_out]
    if not cols_out:
        cols_out = [{"name": str(c), "description": f"Column '{c}'"} for c in df.columns]

    summ = str(obj.get("summary","")).strip()
    if not summ:
        summ = simple_fallback(t, df)["summary"]

    return {"table": t, "summary": summ, "columns": cols_out}

def main():
    csv_dir = CONFIG["csv_dir"]
    out_path = Path(CONFIG["out"])
    sample_n = int(CONFIG["sample_rows"])

    csv_paths = discover_csvs(csv_dir)
    debug_list = Path("outputs/_debug_task1_files_found.txt")
    debug_list.parent.mkdir(parents=True, exist_ok=True)
    debug_list.write_text("\n".join(csv_paths), encoding="utf-8")

    if not csv_paths:
        raise FileNotFoundError(
            f"[Task1] No CSV found under '{csv_dir}'. See {debug_list} for search result."
        )

    llm = get_chat_model(CONFIG["llm_name"]) if CONFIG["use_llm"] else None
    prompt = get_schema_prompt()

    records = []
    for p in csv_paths:
        fname = os.path.basename(p)
        table = re.sub(r"\.csv$", "", fname, flags=re.I)
        table = re.sub(r"^sakila_", "", table, flags=re.I)
        try:
            df = read_csv_any(p)
        except Exception as e:
            print(f"[Task1] Skip {p}: {e}")
            continue

        try:
            if llm:
                rec = llm_structured_summary(llm, prompt, table, df, sample_n)
            else:
                rec = simple_fallback(table, df)
        except Exception as e:
            print(f"[Task1] LLM failed on {table}: {e} -> fallback.")
            rec = simple_fallback(table, df)

        if CONFIG["lower_table"]:
            rec["table"] = str(rec["table"]).lower()

        records.append(rec)
        print("OK:", rec["table"])

    if not records:
        raise RuntimeError("[Task1] 0 tables processed. Check CSV files & encodings.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"[Task1] wrote {out_path} ({len(records)} tables)")
    print(f"[Task1] CSV list saved to {debug_list}")

if __name__ == "__main__":
    main()
