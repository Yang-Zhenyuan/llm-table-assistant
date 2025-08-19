# Phrasing styles

**<u>In schema_summaries, "summary" gives a short description of what the whole table is about and how it is used.</u>**

I tried two different phrasing styles

- **schema_summaries_1 **gave a short and accurate summary, closely matching the table structure (e.g., names and last update).
- **schema_summaries_2 ** produced a longer summary with extra details (e.g., identifiers, use in casting queries), but sometimes added information not directly in the schema.

## schema_summaries_1

prompt

```python
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
```

result

```python
llm_table_assistant\z_outputs-example\task1\schema_summaries_1.json

"summary": "The actor table stores information about actors, including their names and the last time their records were updated. It is typically used in databases related to film or entertainment to manage actor data.",
```

## schema_summaries_2

prompt

```python
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
```

2.result

```python
llm_table_assistant\z_outputs-example\task1\schema_summaries_2.json

"summary": "The 'actor' table contains information about actors in a database, including their unique identifiers and names. This table is used for managing and analyzing actor data in film and entertainment applications, facilitating queries related to casting and performance records.",
```

