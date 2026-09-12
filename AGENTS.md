# AGENTS.md — InternLoom Smart Shortlisting Engine

## Critical rule

This project intentionally uses NO LLM.

Never call:
- Gemini
- OpenAI
- Claude
- any generative LLM API

The application must work without an API key and without an LLM provider.

## Allowed ML component

A local Sentence Transformer embedding model is allowed for semantic matching.

Semantic score must be calculated by our Python code using cosine similarity.

## Ranking rule

The final ranking must be calculated by our code.

Required components:
1. keyword matching
2. semantic embedding matching

Do not ask any model to assign a candidate score.

## Extraction

JD and resume extraction must be deterministic/rule-based:
- section heading detection
- regex/text parsing
- canonical skill dictionary
- aliases
- controlled fuzzy matching

Do not hallucinate missing information.

## Explanations

Use deterministic templates populated from stored evidence.

Do not call an LLM to write explanations.

## Development

Read plan.md before making changes.

Work phase-by-phase.

After each phase:
- run tests
- run the app
- smoke test
- fix failures
- stop and report before beginning the next phase

## Code quality

- Python 3.11+
- type hints
- Pydantic models
- modular functions
- clear names
- no unnecessary abstractions
- deterministic ranking
- no hard-coded candidate scores
- no hard-coded expected ranking

## Migration requirement

The previous implementation added Gemini/LLM modules during Phase 2.

Remove Gemini from the active architecture. Do not merely leave the old implementation wired into the app.

## Environment

The production app must run without an API key. Remove unused Gemini dependencies and configuration after migration.

## Semantic matching rule

Different wording with similar meaning must be handled with local embeddings, not by trying to rewrite the resume into JD wording.

Use Sentence Transformers for embeddings and cosine similarity in Python. Prefer requirement-level JD-to-resume evidence matching.

## NLP libraries

Use spaCy for controlled phrase/section matching and RapidFuzz only for conservative spelling/format variations.

Do not treat fuzzy matching as semantic understanding.
