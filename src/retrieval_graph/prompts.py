# -*- coding: utf-8 -*-
"""
Created on Sun Aug 17 05:35:10 2025

@author: LENOVO
"""



# prompts.py
SCHEMA_SUMMARY_PROMPT = """
Your task is to describe this schema clearly and concisely for data analysis. Produce a STRICT JSON object ONLY in the EXACT shape below.

Required JSON shape:
{
  "table": "<table_name>",
  "summary": "<2–3 sentences describing what the table represents, its PURPOSE, and typical analytical use cases.>",
  "columns": [
    {"name": "<column_name>", "description": "<plain-English meaning of this column, inferred from name and sample rows if available>"},
    ...
  ]
}

Rules:
- Output ONLY JSON (no markdown fence, no extra commentary, no extra keys).
- Go beyond rephrasing: explain what the table is ABOUT, not just column names.
- If a column name is ambiguous, use sample rows (if provided) to infer cautiously.
- Keep each column description short (≤1 sentence).
"""


TABLE_MATCH_PROMPT = """You are a meticulous data analyst.
Given a user query and a list of candidate table summaries, select the K most relevant tables.

Scoring scale:
5 = Fully relevant. The table directly satisfies the query.
4 = Mostly relevant. Covers the main intent but may miss minor fields or constraints.
3 = Partially relevant. Provides some useful context but not sufficient alone.
2 = Weakly relevant. Only tangentially connected to the query.
1 = Irrelevant. No meaningful connection to the query.

Return ONLY a strict JSON object with this shape:
{
  "query": "<echo query>",
  "choices": [
    {"table": "<table_name>", "score": <1-5>, "reason": "<short phrase, <=20 words>"},
    ...
  ]
}

Rules:
- Choose exactly K entries in "choices".
- Higher score = more relevant.
- Keep reasons short and specific (column names or key fields help).
- Do NOT invent tables that were not provided.
- Prefer tables whose summaries/columns directly support the query constraints.
"""




EVAL_PROMPT = """You are a rigorous data analyst.
Judge how relevant ONE candidate table is to the given user query.

Scoring scale:
5 = Fully aligned. This table alone contains the key fields needed to answer the query.
4 = Mostly aligned. It answers the main intent but might miss minor constraints/fields.
3 = Partially related. Provides context/partial info; likely needs joins with other tables.
2 = Weakly related. Only tangentially related to the topic.
1 = Irrelevant.

Instructions:
- Base your decision on the provided table summary, column list, and the 3 sample rows.
- Think about whether the table has the exact entities, filters, and measures needed.
- Be concise and concrete in explanations.
- Output STRICT JSON ONLY with keys:
  { "query": str, "table": str, "relevance_rating": 1-5, "sufficient_to_answer": true/false,
    "why": [short bullets], "missing_info": [fields/constraints not found],
    "irrelevant_info": [fields that are off-topic for this query] }
- No markdown fences, no extra keys, no comments.
"""