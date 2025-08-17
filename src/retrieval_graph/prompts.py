# -*- coding: utf-8 -*-
"""
Created on Sun Aug 17 05:35:10 2025

@author: LENOVO
"""

# # ---- Task 1: Table Schema Summarisation Prompt ----
# SCHEMA_SUMMARY_PROMPT = """You are a data analyst who explains database tables to non-experts.
# Given a table's name, inferred column types, basic stats, and a few sample rows,
# produce a concise, user-friendly summary.

# Output strictly as compact JSON with the following keys:
# - table: string (table name, without extension)
# - summary: string (2–3 sentences: what the table represents, the grain, typical usage)
# - columns: list of {name: string, description: string} (plain-English meaning of each column)
# - keys: optional {primary_key?: [str], foreign_keys?: [{column: str, references: str}]}

# Rules:
# - Do not just restate column names; explain their meaning.
# - If possible, infer primary/foreign keys from names (e.g., *_id) and value patterns.
# - Capture time units/amount units if obvious.
# - Keep it neutral, avoid speculation if unclear.
# """

# TABLE_MATCH_PROMPT = """..."""
# EVAL_PROMPT = """..."""


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


TABLE_MATCH_PROMPT = """Given the user query and N candidate table summaries,
pick the K most relevant tables and briefly justify why (one phrase each)."""

EVAL_PROMPT = """Rate relevance 1–5 (1=irrelevant, 5=highly relevant) between a user query and a single table summary.
Return: 'score: <1-5>' on the first line, and one-sentence reason on the second line."""
