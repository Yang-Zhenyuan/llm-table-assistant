# src/retrieval_graph/io_utils.py
from __future__ import annotations
import os, json, glob, re
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd


# -------------------------
# JSON / Text I/O
# -------------------------

def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path: str, obj: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def write_text(path: str, s: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)

def append_jsonl(path: str, obj: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


# -------------------------
# CSV helpers
# -------------------------

def discover_csvs(csv_dir: str) -> List[str]:
    """Recursively find CSV files under csv_dir (case-insensitive)."""
    patterns = ["*.csv", "*.CSV"]
    res: List[str] = []
    for pat in patterns:
        res += glob.glob(os.path.join(csv_dir, pat))
        res += glob.glob(os.path.join(csv_dir, "**", pat), recursive=True)
    return sorted(set(res))

def read_csv_any(p: str) -> pd.DataFrame:
    """Try multiple encodings to read a CSV."""
    for enc in ("utf-8", "utf-8-sig", "latin1"):
        try:
            return pd.read_csv(p, encoding=enc)
        except Exception:
            pass
    # last try: default pandas behavior
    return pd.read_csv(p)

def norm_name(x: str) -> str:
    """Normalize a table/file name -> snake_case ascii [a-z0-9_]."""
    return re.sub(r"[^a-z0-9]+", "_", str(x).lower()).strip("_")

def build_table_index(csv_dir: str) -> Dict[str, str]:
    """
    Build {normalized_table_name: csv_path} from a directory (recursive).
    Table name is derived from file stem.
    """
    idx: Dict[str, str] = {}
    for p in Path(csv_dir).rglob("*.csv"):
        idx[norm_name(p.stem)] = str(p)
    return idx

def sample_rows(csv_path: str, n: int = 3) -> List[Dict[str, Any]]:
    """
    Return up to n sample rows as list[dict], with long fields truncated.
    If reading fails, return a warning row.
    """
    try:
        df = read_csv_any(csv_path).head(n)
    except Exception as e:
        return [{"_warning": f"sample_rows_failed: {e}"}]

    out: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        row: Dict[str, Any] = {}
        for c, v in r.to_dict().items():
            s = "" if pd.isna(v) else str(v)
            if len(s) > 60:
                s = s[:57] + "..."
            row[str(c)] = s
        out.append(row)
    return out
