# ChatGPT Comparison — Tables 10 / 11

This document records the prompt templates used to query GPT-4 (via the OpenAI
API) for the Tables 10 and 11 comparison in the paper.

Model: **gpt-4o** (snapshot used in experiments)
API: OpenAI Chat Completions v1

---

## Few-shot summarization prompt (Table 10 — SubSumE)

The prompt gives the model the intent, the example summaries, and asks it to
generate a new summary for the target document. Three examples are provided
(matching `num_examples=3` in our experiment setup).

```
SYSTEM:
You are an expert document summarizer. Given a user's intent and a set of
example summaries they have written, write a new summary of the target
document that matches the user's intent and style.

USER:
Intent: {intent}

Example summaries (written by the same user, for different documents):
Example 1 (document: {example_1_doc}):
{example_1_text}

Example 2 (document: {example_2_doc}):
{example_2_text}

Example 3 (document: {example_3_doc}):
{example_3_text}

Now write a summary of the following document in the same style:
Document ({target_doc}):
{target_doc_text}

Summary:
```

**Filling the template:**
- `{intent}` — from `userInput_N.json["intent"]`
- `{example_i_doc}` — `state_name` of the i-th example summary
- `{example_i_text}` — concatenated sentences of the i-th example summary
- `{target_doc}` — state name of the test document
- `{target_doc_text}` — full raw text of the target document (from `RawWikiFiles2023/`)

---

## TPC-H supplier description prompt (Table 11)

For the TPC-H experiment, the model is asked to select a bundle of suppliers
given a natural-language description of the desired bundle properties.

```
SYSTEM:
You are a procurement assistant. Given a list of candidate suppliers and a
description of a desired bundle (learned from example purchases), select the
best bundle of suppliers that satisfies the described criteria.

USER:
Desired bundle criteria (learned from past purchases):
- Price score range:        {price_min:.2f} – {price_max:.2f}
- Availability score range: {avail_min:.2f} – {avail_max:.2f}
- Region America score:     {ra_min:.2f} – {ra_max:.2f}
- Region Europe score:      {re_min:.2f} – {re_max:.2f}
- Balance score range:      {bal_min:.2f} – {bal_max:.2f}
- Bundle size:              {count_min} – {count_max} suppliers

Candidate suppliers (supplier_id, price_score, availability_score,
region_america, region_europe, balance_score):
{candidate_table}

Return only a comma-separated list of supplier IDs that form the best
bundle satisfying the above criteria. Do not explain.
```

---

## Notes

- Temperature was set to 0 for reproducibility.
- If the model returned an empty or invalid response, the result was recorded
  as a failed generation (CSR = 0, ROUGE = 0).
- The OpenAI library version used: `openai>=1.0.0` (new client API).
