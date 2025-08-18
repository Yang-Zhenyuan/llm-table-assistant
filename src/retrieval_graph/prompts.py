# -*- coding: utf-8 -*-
"""
Created on Sun Aug 17 05:35:10 2025

@author: LENOVO
"""



# prompts.py
SCHEMA_SUMMARY_PROMPT = """
You are a senior data analyst. Produce a STRICT JSON object ONLY in the EXACT shape below.
Your goal is to help another analyst quickly understand a table's PURPOSE and how to use it.

Required JSON shape:
{
  "table": "<table_name>",
  "summary": "<2–3 sentences stating what the table represents (its PURPOSE) and typical use cases.>",
  "columns": [
    {"name": "<column_name>", "description": "<plain-English meaning of this column>"},
    ...
  ]
}

Rules:
- Output ONLY JSON (no markdown fence, no extra commentary, no extra keys).
- Base your descriptions on the column names and sample rows provided.
- If a column name is ambiguous, infer cautiously from the samples.
- Keep each column description short (≤1 sentence).
"""


TABLE_MATCH_PROMPT = """You are a meticulous data analyst.
Given a user query and a list of candidate table summaries, select the K most relevant tables.

Return ONLY a strict JSON object with this shape:
{
  "query": "<echo query>",
  "choices": [
    {"table": "<table_name>", "score": <1-5>, "reason": "<short phrase, <=15 words>"},
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