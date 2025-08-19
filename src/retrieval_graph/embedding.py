# -*- coding: utf-8 -*-
"""
Created on Sun Aug 19 23:25:15 2025

@author: LENOVO
"""
from typing import List, Dict
import os, math
from openai import OpenAI

def _build_table_corpus_from_summaries(summaries: List[Dict], max_cols: int = 16) -> Dict[str, str]:
    """
    Convert each table into a short text: table name + summary + a few column names.
    Return {table_name: text}.
    """
    corpus: Dict[str, str] = {}
    for it in summaries:
        tname = (it.get("table") or it.get("name") or "").strip()
        if not tname:
            continue
        summ = (it.get("summary") or "").strip()
        cols = it.get("columns") or []
        col_names = []
        for c in cols[:max_cols]:
            if isinstance(c, dict):
                n = (c.get("name") or "").strip()
                if n:
                    col_names.append(n)
            elif isinstance(c, str):
                col_names.append(c)
        text = f"table: {tname}\nsummary: {summ}\ncolumns: {', '.join(col_names)}"
        corpus[tname] = text
    return corpus

def _cosine(a: List[float], b: List[float]) -> float:
    """
    Cosine similarity
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / math.sqrt(na * nb)

def _embed_texts(client: OpenAI, model: str, texts: List[str]) -> List[List[float]]:
    """
    Call the OpenAI API to get embeddings for a list of texts.
    """
    resp = client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]

def embed_rank_tables(
    summaries: List[Dict],
    query: str,
    embedding_model: str = "text-embedding-3-small",
    k: int = 5,
):
    """
    Rank tables using embeddings, return [{"table": str, "score": float}] without reason.
    """
    corpus = _build_table_corpus_from_summaries(summaries)
    if not corpus:
        return []

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    table_names = list(corpus.keys())
    table_texts = [corpus[t] for t in table_names]

    vecs = _embed_texts(client, embedding_model, [query] + table_texts)
    qvec, tvecs = vecs[0], vecs[1:]

    scored = [{"table": name, "score": _cosine(qvec, v)}
              for name, v in zip(table_names, tvecs)]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]
