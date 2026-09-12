# InternLoom AI Hackathon — Smart Shortlisting Engine
# NO-LLM / NLP + SEMANTIC MATCHING ARCHITECTURE

## 1. Project Goal

Build an end-to-end resume shortlisting system that takes:

- 1 Job Description (JD) PDF
- 15–18 candidate resume PDFs

and returns:

1. A ranked list of all candidates from best fit to worst fit.
2. A final score for every candidate.
3. A clear explanation for the top 3:
   - matched skills
   - missing required skills
   - score breakdown

## 2. Critical Design Decision

This implementation deliberately uses **NO LLM/API calls**.

Do not use:
- Gemini API
- OpenAI API
- Claude API
- any generative LLM
- LLM-generated scores
- LLM-generated explanations

The entire extraction, normalization, matching, scoring, ranking, and explanation pipeline must be implemented deterministically with normal code and local libraries.

This is stricter than the minimum problem requirement and avoids ambiguity during judging.

## 3. Core Architecture

```text
                 JOB DESCRIPTION PDF
                         │
                         ▼
                    PDF Parser
                         │
                         ▼
                  Raw JD Text
                         │
                         ▼
             Rule-based JD extraction
                         │
                         ▼
             Structured JD representation
                         │
                         │
18 Resume PDFs ──────────┤
        │                │
        ▼                │
    PDF Parser           │
        │                │
        ▼                │
   Raw Resume Text       │
        │                │
        ▼                │
Rule-based extraction    │
        │                │
        ▼                │
Structured Resume       │
        │                │
        └────────┬───────┘
                 ▼
          Skill normalization
                 │
          ┌──────┴───────┐
          ▼              ▼
   Keyword matching   Semantic matching
          │              │
          ▼              ▼
   Keyword score     Semantic score
          │              │
          └──────┬───────┘
                 ▼
          Deterministic scorer
                 │
                 ▼
          Rank all candidates
                 │
                 ▼
         Rule-based explanations
                 │
                 ▼
             Streamlit UI
```

## 4. Technology Stack

- Python 3.11+
- Pydantic
- Streamlit
- PyMuPDF (`fitz`)
- Python regex/text processing
- RapidFuzz for controlled fuzzy matching
- sentence-transformers for local semantic embeddings
- NumPy / scikit-learn for cosine similarity

No external LLM/API is required.

## 5. Project Structure

```text
smart-shortlisting-engine/
├── plan.md
├── AGENTS.md
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── app/
│   ├── main.py
│   ├── ui.py
│   ├── parsers/
│   │   ├── pdf_parser.py
│   │   └── text_cleaner.py
│   ├── extraction/
│   │   ├── jd_extractor.py
│   │   └── resume_extractor.py
│   ├── matching/
│   │   ├── skill_normalizer.py
│   │   ├── keyword_matcher.py
│   │   ├── semantic_matcher.py
│   │   └── scorer.py
│   ├── models/
│   │   ├── jd_models.py
│   │   ├── resume_models.py
│   │   └── result_models.py
│   └── utils/
│       ├── config.py
│       └── logging_config.py
├── data/
│   ├── jd/
│   ├── resumes/
│   └── sample_outputs/
└── tests/
    ├── test_pdf_parser.py
    ├── test_jd_extractor.py
    ├── test_resume_extractor.py
    ├── test_normalizer.py
    ├── test_keyword_matching.py
    ├── test_semantic_matching.py
    └── test_scoring.py
```

## 6. Remove the LLM Layer

The previous Phase 2 implementation introduced Gemini modules. Remove them from the active architecture:

- `app/llm/gemini_client.py`
- `app/llm/jd_extractor.py`
- `app/llm/resume_extractor.py`
- `app/llm/explanation_generator.py`

Delete them if they are no longer referenced. Otherwise remove their dependencies and ensure the production pipeline never imports or calls them.

Remove Gemini packages from `requirements.txt` if unused.

The application must run without:
- a Gemini API key
- internet access
- an LLM provider account

## 7. Rule-Based JD Extraction

Use section-heading detection and bullet/list parsing.

Recognize required headings such as:
- required skills
- requirements
- must have / must-have
- technical requirements
- required qualifications

Recognize preferred headings such as:
- preferred skills
- nice to have / nice-to-have
- good to have
- bonus skills
- desired skills

Recognize responsibility headings such as:
- responsibilities
- what you'll do
- role responsibilities
- key responsibilities
- duties

Recognize qualification/education headings such as:
- qualifications
- education
- eligibility

Stop a section at the next recognized heading. If something cannot be identified confidently, return an empty list instead of inventing data.

## 8. Skill Dictionary and Normalization

Create one central canonical skill dictionary and aliases.

Examples:

```python
SKILL_ALIASES = {
    "reactjs": "React",
    "react.js": "React",
    "react js": "React",
    "nodejs": "Node.js",
    "node js": "Node.js",
    "node.js": "Node.js",
    "mongo": "MongoDB",
    "mongo db": "MongoDB",
    "mongodb": "MongoDB",
    "restful api": "REST API",
    "restful apis": "REST API",
    "rest apis": "REST API",
    "js": "JavaScript",
}
```

Expand the dictionary using skills actually present in the provided JD/resumes.

Do not use uncontrolled fuzzy matching.

## 9. Rule-Based Resume Extraction

Recognize common headings:

- skills
- technical skills
- technologies
- tech stack
- technical expertise
- projects
- academic projects
- personal projects
- experience
- work experience
- internship / internships
- employment
- education
- academic background
- certifications / certificates

Extract:
- candidate name
- skills
- projects
- project technologies
- experience
- company/title/date text
- education
- certifications

Candidate name fallback:
1. explicit header/name if detectable
2. first meaningful header line
3. filename stem

Never fabricate a name.

## 10. Semantic Matching

The semantic requirement must be satisfied using a **local embedding model**, not a generative LLM.

Start with:

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
```

First implementation:

```text
JD responsibilities + required skills
                ↓
            JD embedding

Resume projects + experience + skills
                ↓
          Resume embedding

        cosine similarity
                ↓
      semantic score 0–100
```

Calculate cosine similarity in our own Python code.

Do not ask a model for a similarity score.

Only introduce section-level weighting after the simple version works.

## 11. Keyword Matching

For every candidate calculate:

- matched required skills
- missing required skills
- matched preferred skills
- missing preferred skills

Initial formula:

```text
required_match = matched_required / total_required
preferred_match = matched_preferred / total_preferred

Keyword Score =
    85% × required_match
  + 15% × preferred_match
```

If there are no preferred skills, use only required skill matching.

Required skills must have substantially more influence than preferred skills.

## 12. Controlled Fuzzy Matching

Use RapidFuzz only after normalization for minor spelling/format variations.

Examples that should normalize:
- NodeJS → Node.js
- Node JS → Node.js
- React.js → React
- Mongo DB → MongoDB

Explicitly prevent false positives such as:
- Java ≠ JavaScript
- C ≠ C++
- Git ≠ GitHub

unless a separate rule intentionally treats them as related, in which case that relationship must be explicit and tested.

## 13. Final Score

Initial version:

```text
Final Score =
    50% Keyword Score
  + 50% Semantic Score
```

Keep the weights in one configuration/module. Do not hard-code candidate-specific values.

Every result must expose:
- keyword_score
- semantic_score
- final_score

Do not introduce an evidence score until the base pipeline is stable.

## 14. Ranking

For each candidate:
1. parse PDF
2. clean text
3. extract structured resume
4. normalize skills
5. calculate keyword score
6. calculate semantic score
7. calculate final score
8. retain evidence

Sort descending by final score.

Use a deterministic tie-breaker:
1. higher keyword score
2. higher required-skill match count
3. candidate name

## 15. Rule-Based Top-3 Explanations

Generate explanations from templates, with no LLM.

Example:

```text
Candidate: Rahul Sharma
Final Score: 91.4

Why this candidate ranked highly:
- Matches 6 of 7 required skills.
- Matches React, Node.js, Express, MongoDB, REST API and Git.
- Resume projects contain relevant backend/API evidence.
- Semantic similarity is 93.8/100.

Missing required skills:
- Docker

Preferred skills matched:
- TypeScript
```

Only state facts present in the stored evidence.

## 16. UI

Streamlit should provide:
- JD PDF upload
- multiple resume upload
- Run Shortlist button
- ranked table for all candidates
- score breakdown
- matched/missing skills
- top-3 explanations

## 17. Testing Strategy

### Phase 1 — PDF parsing

Test:
- 1 JD PDF
- 1 resume PDF
- all supplied resumes
- invalid PDF
- empty PDF
- unusual formatting

Verify filename association, readable extracted text, and graceful failures.

### Phase 2 — Deterministic extraction

Test:
- standard JD headings
- alternate headings
- missing sections
- standard resume headings
- alternate headings
- missing experience/projects
- messy skill spellings

No LLM/API calls.

### Phase 3 — Normalization + keyword matching

Test aliases and false positives.

### Phase 4 — Semantic matching

Use synthetic high/low similarity examples. Do not hard-code unstable exact cosine values.

### Phase 5 — Scoring

Verify:
- both keyword and semantic scores affect final score
- required skills matter more than preferred skills
- missing required skills reduce ranking
- ties are deterministic

### Phase 6 — End-to-end

Run 1 JD + 18 resumes through the complete pipeline.

## 18. Development Phases

### Phase 1 — PDF pipeline

Implement only:
- PDF upload
- PDF parsing
- raw text extraction
- error handling
- basic UI display

Stop and test.

### Phase 2 — Deterministic extraction

Replace the previous Gemini Phase 2 with:
- rule-based JD extraction
- rule-based resume extraction
- Pydantic models
- skill dictionary lookup
- no LLM/API calls

Remove old Gemini code from the production path.

Stop and test.

### Phase 3 — Skill normalization + keyword matching

Implement aliases, controlled fuzzy matching, matched/missing evidence, and keyword score.

Stop and test.

### Phase 4 — Semantic matching

Implement local Sentence Transformer embeddings and cosine similarity.

Stop and test.

### Phase 5 — Ranking

Implement final score, deterministic sorting, ranking table, and score breakdown.

Stop and test.

### Phase 6 — Top-3 explanations

Implement deterministic explanation templates.

Stop and test.

### Phase 7 — Full dataset

Run the supplied resumes and review ranking quality and score spread. Tune rules based on observed errors; never hard-code expected winners.

### Phase 8 — UI polish

Add score bars, candidate details, loading states, and clear error messages.

### Phase 9 — Optional bonus

Only after the core pipeline is stable.

## 19. Antigravity Execution Rules

Before editing:
1. Read plan.md completely.
2. Inspect the current repository.
3. Identify old Gemini/LLM modules and references.
4. Plan the smallest clean migration to the no-LLM architecture.

Then work one phase at a time.

After each phase:
1. run unit tests
2. run the application
3. run a smoke test
4. fix failures
5. report what changed
6. stop for approval before the next phase

Do not:
- invent ranking values
- hard-code candidate results
- use an LLM behind the scenes
- add unnecessary dependencies
- rewrite stable code without reason
- silently change scoring weights

## 20. Definition of Done

- [ ] No LLM/API calls in production.
- [ ] No Gemini dependency in the ranking pipeline.
- [ ] JD PDF parsing works.
- [ ] 15–18 resumes can be processed.
- [ ] Deterministic JD extraction works.
- [ ] Deterministic resume extraction works.
- [ ] Skill normalization works.
- [ ] Keyword matching works.
- [ ] Semantic embedding matching works locally.
- [ ] Both keyword and semantic scores genuinely affect final ranking.
- [ ] All candidates are ranked.
- [ ] Final score shown for every candidate.
- [ ] Matched/missing skills shown.
- [ ] Top-3 explanations generated without LLM.
- [ ] Tests pass.
- [ ] End-to-end demo works without an API key.
- [ ] No hard-coded candidate ranking.

## 21. Core Principle

```text
PARSE
  ↓
EXTRACT
  ↓
NORMALIZE
  ↓
KEYWORD MATCHING
      +
SEMANTIC EMBEDDINGS
  ↓
OUR SCORING CODE
  ↓
RANKING
  ↓
RULE-BASED EXPLANATION
```

The project's main engineering contribution is the transparent hybrid matching/ranking engine.
