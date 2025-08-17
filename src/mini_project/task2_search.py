# -*- coding: utf-8 -*-
# File: src/mini_project/task2_search.py
import os, json
from pathlib import Path

CONFIG = {
    "summaries": "outputs/summaries.jsonl",
    "query": "Which tables contain customer film rental history?",
    "topk": 5,
    "method": "embed",  # "embed" or "tfidf"
    "out": "outputs/search_demo.json",
}

def _load_summaries(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items

def _build_text(item):
    col_names = ", ".join([c["name"] for c in item.get("columns", [])])
    return f"{item['table']}\n{item.get('summary','')}\nColumns: {col_names}"

def _search_tfidf(query, corpus):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel
    vec = TfidfVectorizer(stop_words="english")
    X = vec.fit_transform(corpus)
    qv = vec.transform([query])
    scores = linear_kernel(qv, X).ravel()
    return scores

def _search_embed(query, corpus, model_name="sentence-transformers/all-MiniLM-L6-v2"):
    try:
        from sentence_transformers import SentenceTransformer, util
    except Exception as e:
        print(f"[Task2] sentence-transformers not available ({e}), falling back to TF-IDF.")
        return _search_tfidf(query, corpus)
    m = SentenceTransformer(model_name)
    embs = m.encode(corpus, convert_to_tensor=True, normalize_embeddings=True)
    q = m.encode([query], convert_to_tensor=True, normalize_embeddings=True)
    scores = util.cos_sim(q, embs).cpu().numpy().ravel()
    return scores

def run():
    items = _load_summaries(CONFIG["summaries"])
    corpus = [_build_text(x) for x in items]

    if CONFIG["method"] == "embed":
        scores = _search_embed(CONFIG["query"], corpus)
    else:
        scores = _search_tfidf(CONFIG["query"], corpus)

    ranked = sorted(
        [{"table": items[i]["table"], "score": float(scores[i])} for i in range(len(items))],
        key=lambda x: x["score"], reverse=True
    )[: int(CONFIG["topk"])]

    out_path = CONFIG["out"]
    os.makedirs(Path(out_path).parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as w:
        json.dump({"query": CONFIG["query"], "topk": ranked}, w, ensure_ascii=False, indent=2)

    print(f"[Task2] wrote {out_path}")
    for r in ranked:
        print(f"- {r['table']}: {r['score']:.4f}")

if __name__ == "__main__":
    run()
