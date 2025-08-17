# -*- coding: utf-8 -*-
# File: src/mini_project/task1_schema_summary.py
import os, re, glob, json
from pathlib import Path
import pandas as pd

try:
    from retrieval_graph.utils import load_chat_model
except Exception:
    load_chat_model = None

try:
    from retrieval_graph.prompts import SCHEMA_SUMMARY_PROMPT
except Exception:
    try:
        from retrieval_graph.prompts_additions import SCHEMA_SUMMARY_PROMPT
    except Exception:
        SCHEMA_SUMMARY_PROMPT = (
            "You are a senior data analyst. Summarize a database table for other analysts. "
            "First: one short paragraph stating what the table represents. "
            "Then: explain each column briefly. Keep it 4–8 sentences total."
        )

CONFIG = {
    "csv_dir": "data",
    "out": "outputs/summaries.jsonl",
    "sample_rows": 5,
    "use_llm": False,
    "llm_name": "openai/gpt-4o-mini",
}

def _profile_columns(df: pd.DataFrame):
    cols = []
    n = len(df)
    for c in df.columns:
        s = df[c]
        cols.append({
            "name": str(c),
            "dtype": str(s.dtype),
            "null_frac": float(s.isna().mean() if n else 0.0),
            "unique_frac": float((s.nunique(dropna=True) / n) if n else 0.0),
            "sample_values": [str(x) for x in s.dropna().astype(str).unique().tolist()[:3]],
        })
    return cols

def _simple_summary(table: str, cols: list[dict], sample_rows: list[dict]) -> str:
    names = ", ".join(f"{c['name']}({c['dtype']})" for c in cols)
    pk = next((c["name"] for c in cols if c["name"].lower() in (f"{table}_id", "id")), None)
    fks = [c["name"] for c in cols if c["name"].lower().endswith("_id") and c["name"] != pk]
    fk_txt = (" Common join keys: " + ", ".join(fks) + ".") if fks else ""
    return (f"Table `{table}` stores records related to `{table}` entities. "
            f"It has {len(cols)} columns: {names}. "
            + (f"The primary key is likely `{pk}`." if pk else "") + fk_txt)

def _llm_summary(llm, table: str, cols: list[dict], sample_rows: list[dict]) -> str:
    payload = {
        "table": table,
        "columns": [
            {"name": c["name"], "dtype": c["dtype"],
             "null_frac": round(c["null_frac"], 3),
             "unique_frac": round(c["unique_frac"], 3),
             "sample_values": c["sample_values"]} for c in cols
        ],
        "sample_rows": sample_rows[:3],
    }
    messages = [
        {"role": "system", "content": SCHEMA_SUMMARY_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
    ]
    resp = llm.invoke(messages)
    return getattr(resp, "content", str(resp)).strip()

def run():
    csv_dir = CONFIG["csv_dir"]
    out_path = CONFIG["out"]
    sample_n = int(CONFIG["sample_rows"])
    os.makedirs(Path(out_path).parent, exist_ok=True)

    llm = None
    if CONFIG["use_llm"]:
        if load_chat_model is None:
            print("[Task1] load_chat_model not available, falling back to rule-based summary.")
        else:
            llm = load_chat_model(CONFIG["llm_name"])

    with open(out_path, "w", encoding="utf-8") as w:
        for p in sorted(glob.glob(os.path.join(csv_dir, "*.csv"))):
            name = os.path.basename(p)
            table = re.sub(r"\.csv$", "", name, flags=re.I)
            table = re.sub(r"^sakila_", "", table, flags=re.I).lower()

            df = pd.read_csv(p)
            cols = _profile_columns(df)
            rows = df.sample(n=min(sample_n, len(df)), random_state=42).to_dict(orient="records")

            if llm is not None:
                try:
                    summary = _llm_summary(llm, table, cols, rows)
                except Exception as e:
                    summary = _simple_summary(table, cols, rows) + f" [LLM fallback: {e}]"
            else:
                summary = _simple_summary(table, cols, rows)

            w.write(json.dumps({
                "table": table,
                "csv_path": p,
                "columns": cols,
                "sample_rows": rows,
                "summary": summary
            }, ensure_ascii=False) + "\n")

    print(f"[Task1] wrote {out_path}")

if __name__ == "__main__":
    run()
