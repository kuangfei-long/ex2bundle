# ChatGPT-4o Comparison — §5.4 (LLM-based summarization performance)

This document records the prompt templates used to query GPT-4o for the
LLM-based summarization comparison reported in §5.4 of the paper.

Model: **gpt-4o** (snapshot used in experiments)
Interface: GPT-4o web UI — the **target document is provided as a file
attachment** (not pasted inline) along with the example snippets in the
prompt body. Temperature was the UI default. No automated runner is
included; queries were issued manually.

The §5.4 comparison covers two regimes:

| Setting | Dataset | Intent type | Section |
|---|---|---|---|
| Focused intent | SubSumE (2 intents) | specific information need | §5.4 (Focused intent) |
| Generic intent | CNN/DailyMail (4 categories: Politics, Crime, Sports, Lifestyle) | open-ended news summary | §5.4 (Generic intent) |

The TPC-H GPT-4o supplier-selection comparison was removed from the current
draft and is no longer reported in §5.4. The prompt template for it remains
at the bottom of this file for reference.

---

## §5.4 Focused intent — SubSumE

The user message gives the model the intent and the example snippets, and
asks it to extract a snippet from the target document that matches the
user's intent and style. The target document itself is **attached as a
file** in the GPT-4o web UI (rather than pasted into the prompt) to mirror
the regular usage pattern an end-user would adopt.

```
SYSTEM:
You are an expert document summarizer. Given a user's intent and a set of
example snippets they have written, extract a new snippet from the
attached target document that matches the user's intent and style.

USER:
Intent: {intent}

Example snippets (written by the same user, for different documents):
Example 1 (document: {example_1_doc}):
{example_1_text}

Example 2 (document: {example_2_doc}):
{example_2_text}

Example 3 (document: {example_3_doc}):
{example_3_text}

The target document is attached as a file ({target_doc}). Extract a
snippet from it in the same style as the examples above.
```

**Filling the template:**
- `{intent}` — from `userInput_N.json["intent"]`
- `{example_i_doc}` — `state_name` of the i-th example summary
- `{example_i_text}` — concatenated sentences of the i-th example summary
- `{target_doc}` — state name of the test document
- Target document content — uploaded as a `.txt` file attachment in the UI

The two intents reported in the paper are the two with the most distinct
specificity profiles: a more-specific intent (Intent 1) and a less-specific
intent (Intent 2).

---

## §5.4 Generic intent — CNN/DailyMail

For each of the four categories (Politics, Crime, Sports, Lifestyle), the
paper draws 100 articles from the ACL2020 split, uses 5 articles as user
examples and 3 as target. The prompt is the few-shot variant of the
SubSumE prompt above; the "intent" field is omitted because CNN/DailyMail
highlights are open-ended news summaries rather than focused information
needs.

```
SYSTEM:
You are an expert news summarizer. Given a few example highlight summaries
written for different articles, write a highlight summary of the target
article in the same style.

USER:
Example highlight summaries:
Example 1:
{example_1_highlight}

Example 2:
{example_2_highlight}

...

Example 5:
{example_5_highlight}

The target article is attached as a file. Write a highlight summary of
it in the same style as the examples above.
```

**Filling the template:**
- `{example_i_highlight}` — the human-written highlight string from the
  CNN/DailyMail article in the example pool
- Target article content — uploaded as a `.txt` file attachment in the UI

---

## Reference: TPC-H supplier selection prompt (removed from §5.4)

This prompt was used in an earlier draft of the paper to compare GPT-4o
against Ex2Bundle on the TPC-H supplier-selection task. The current draft
no longer reports this comparison in §5.4. The template is preserved here
for reference and to support the technical-report version of the
experiment.

```
SYSTEM:
You are a procurement assistant. Given a list of candidate suppliers and a
description of a desired bundle (learned from example purchases), select the
best bundle of suppliers that satisfies the described criteria.

USER:
Desired bundle criteria (learned from past purchases):
- Price score range:        {price_min:.2f} – {price_max:.2f}
- Availability score range: {avail_min:.2f} – {avail_max:.2f}
- Region Europe score:      {re_min:.2f} – {re_max:.2f}
- Region America score:     {ra_min:.2f} – {ra_max:.2f}
- Balance score range:      {bal_min:.2f} – {bal_max:.2f}
- Bundle size:              {count_min} – {count_max} suppliers

Candidate suppliers (supplier_id, price_score, availability_score,
region_europe, region_america, balance_score):
{candidate_table}

Return only a comma-separated list of supplier IDs that form the best
bundle satisfying the above criteria. Do not explain.
```

---

## Notes

- All queries were issued manually through the GPT-4o web UI; the target
  document / article was uploaded as a file attachment rather than pasted
  inline.
- If the model returned an empty or invalid response, the result was
  recorded as a failed generation (CSR = 0, ROUGE = 0).
- No OpenAI API client is required to reproduce the §5.4 numbers — only
  access to the GPT-4o web UI.
