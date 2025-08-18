# -*- coding: utf-8 -*-
"""
Created on Sun Aug 18 09:12:10 2025

@author: LENOVO
"""
# File: src/mini_project/task1_schema_summary.py
"""
Simplified output for Task 1.

Change highlights:
- Output a single pretty JSON array (NOT JSONL).
- Only include: table, summary, columns[{name, description}].
- The summary MUST state the table's purpose.

Keeps the previous discovery + debug list behavior.
"""

import os, re, glob, json
from pathlib import Path
import pandas as pd

# -----------------------
# Minimal utilities
# -----------------------
def get_chat_model(name: str):
    #统一获取 chat 模型，优先用项目内 loader，失败再尝试本地 utils。
    try:
        from retrieval_graph.utils import load_chat_model as _loader
        return _loader(name)
    except Exception:
        try:
            from utils import load_chat_model as _loader2
            return _loader2(name)
        except Exception:
            return None

def get_schema_prompt():
    #获取 Task1 的提示词；若无则用内置默认
    try:
        from retrieval_graph.prompts import SCHEMA_SUMMARY_PROMPT as P
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
    "csv_dir": os.path.join(os.path.dirname(__file__), "data"),   # CSV 目录
    "out": os.path.join("outputs", "task1", "schema_summaries.json"), # 输出 JSON 数组
    "sample_rows": 5,                            # 提示给 LLM 的样例行数
    "use_llm": True,
    "llm_name": "gpt-4o-mini",
    "lower_table": True,                         # 是否把表名统一小写
}

# -----------------------
# File helpers
# -----------------------
def discover_csvs(csv_dir: str):
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

# -----------------------
# Core logic
# -----------------------
def simple_fallback(table: str, df: pd.DataFrame) -> dict:
    #无 LLM 时的兜底：满足提交结构即可
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
    """让模型直接返回严格 JSON；只传必要信息以减少冗余。"""
    payload = {
        "table": table,
        "columns": [str(c) for c in df.columns],             # 仅列名
        "sample_rows": df.head(sample_rows).to_dict(orient="records"),  # 少量样例行
    }
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
    ]
    resp = llm.invoke(messages)
    txt = getattr(resp, "content", str(resp)).strip()
    # 剥离可能的围栏
    if "{" in txt and "}" in txt:
        txt = txt[txt.find("{"): txt.rfind("}")+1]
    obj = json.loads(txt)

    # 归一化与兜底
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
