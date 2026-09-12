# InternLoom AI Hackathon — Smart Shortlisting Engine

## 1. Project Goal

Build an end-to-end system that takes:

- 1 Job Description (JD) PDF
- 15–18 candidate resume PDFs

and returns:

1. A ranked list of **all candidates**, best fit to worst fit.
2. A final score for every candidate.
3. A short, evidence-based explanation for the **top 3 candidates**:
   - matched skills/requirements
   - missing required skills
4. A working demo UI.

### Critical judging requirement

The ranking **must genuinely use both**:

- keyword matching
- semantic matching

Do **not** send a JD + resume to an LLM and ask it for a score. The final score and ranking must be calculated by our own matching/scoring pipeline.

---

# 2. High-Level Architecture

```text
                    ┌────────────────────┐
                    │   Job Description  │
                    │        PDF         │
                    └─────────┬──────────┘
                              │
                              ▼
                       PDF Text Parser
                              │
                              ▼
                        Gemini API
                    JD extraction/normalization
                              │
                              ▼
                   Structured JD JSON
                              │
                              │
18 Resume PDFs ───────────────┤
       │                      │
       ▼                      │
 PDF Text Parser              │
       │                      │
       ▼                      │
 Gemini API                   │
 Resume extraction/           │
 normalization                │
       │                      │
       ▼                      │
 Structured Resume JSON       │
       │                      │
       └──────────────┬───────┘
                      ▼
              Matching Engine
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
   Keyword Matching       Semantic Embeddings
          │                       │
          ▼                       ▼
   Keyword Score            Semantic Score
          │                       │
          └───────────┬───────────┘
                      ▼
               Final Score
                      │
                      ▼
                Rank all 18
                      │
                      ▼
                   Top 3
                      │
                      ▼
                 Gemini API
             Explanation generation
                      │
                      ▼
                  Streamlit UI
```

---

# 3. Recommended Tech Stack

## Backend / Core

- Python 3.11+
- FastAPI (optional if Streamlit alone is enough)
- Pydantic

## PDF parsing

- PyMuPDF (`fitz`)

## LLM

- Google Gemini API
- Use structured JSON output where possible
- Keep the API key in `.env`

## Semantic matching

- `sentence-transformers`
- Start with `all-MiniLM-L6-v2`
- `scikit-learn` for cosine similarity

## Keyword matching

- Python
- normalized skill dictionary
- regex
- RapidFuzz for fuzzy matching

## UI

- Streamlit

## Configuration

- `python-dotenv`

---

# 4. Project Structure

Create this structure:

```text
smart-shortlisting-engine/
│
├── app/
│   ├── main.py
│   ├── ui.py
│   │
│   ├── parsers/
│   │   └── pdf_parser.py
│   │
│   ├── llm/
│   │   ├── gemini_client.py
│   │   ├── jd_extractor.py
│   │   ├── resume_extractor.py
│   │   └── explanation_generator.py
│   │
│   ├── matching/
│   │   ├── keyword_matcher.py
│   │   ├── semantic_matcher.py
│   │   ├── skill_normalizer.py
│   │   └── scorer.py
│   │
│   ├── models/
│   │   ├── jd_models.py
│   │   ├── resume_models.py
│   │   └── result_models.py
│   │
│   └── utils/
│       ├── text_cleaner.py
│       └── config.py
│
├── data/
│   ├── jd/
│   ├── resumes/
│   └── sample_outputs/
│
├── tests/
│   ├── test_pdf_parser.py
│   ├── test_normalizer.py
│   ├── test_keyword_matching.py
│   ├── test_semantic_matching.py
│   └── test_scoring.py
│
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── plan.md
```

---

# 5. Data Models

## Job Description JSON

The JD extractor should produce something close to:

```json
{
  "role_title": "Junior Full Stack Developer Intern",
  "company": "TechNova Solutions",
  "required_skills": [
    "JavaScript",
    "React",
    "Node.js",
    "Express",
    "MongoDB",
    "REST API",
    "Git"
  ],
  "preferred_skills": [
    "TypeScript",
    "Docker",
    "AWS"
  ],
  "responsibilities": [
    "Build web applications",
    "Develop REST APIs",
    "Work with databases",
    "Fix bugs",
    "Collaborate using Git"
  ],
  "qualifications": [
    "B.Tech/B.E. in Computer Science",
    "Strong programming fundamentals"
  ]
}
```

Do not assume every JD has every field. Missing fields should become empty arrays or `null`.

---

# 6. Resume JSON

Every resume should be converted into structured data:

```json
{
  "candidate_name": "Candidate Name",
  "contact": {
    "email": "",
    "phone": ""
  },
  "skills": [
    "JavaScript",
    "React",
    "Node.js",
    "MongoDB",
    "Git"
  ],
  "experience": [
    {
      "role": "Software Developer Intern",
      "company": "ABC Technologies",
      "duration": "3 months",
      "description": "..."
    }
  ],
  "projects": [
    {
      "name": "E-commerce Platform",
      "technologies": [
        "React",
        "Node.js",
        "Express",
        "MongoDB"
      ],
      "description": "Built REST APIs..."
    }
  ],
  "education": [
    {
      "degree": "B.Tech Computer Science",
      "institution": "XYZ University",
      "duration": "2024-2028"
    }
  ],
  "certifications": []
}
```

If information is absent, do not invent it.

---

# 7. LLM Responsibilities

## LLM Job 1: JD extraction

Input:
- raw JD text

Output:
- structured JD JSON

The LLM should identify:
- role
- required skills
- preferred skills
- responsibilities
- qualifications

It should not produce the final candidate ranking.

## LLM Job 2: Resume extraction

Input:
- raw resume text

Output:
- structured resume JSON

It should identify:
- candidate name
- skills
- project technologies
- experience
- education
- certifications

## LLM Job 3: Explanation

Only after our code has calculated scores.

Input should include evidence such as:

```json
{
  "candidate": "Candidate A",
  "final_score": 91.4,
  "keyword_score": 89.0,
  "semantic_score": 93.8,
  "matched_required_skills": [
    "React",
    "Node.js",
    "Express",
    "MongoDB",
    "REST API",
    "Git"
  ],
  "missing_required_skills": [],
  "matched_preferred_skills": [
    "Docker"
  ],
  "missing_preferred_skills": [
    "TypeScript",
    "AWS"
  ]
}
```

The LLM must explain only the supplied evidence and must not invent qualifications or experience.

---

# 8. Skill Normalization

Build a normalization layer before matching.

Examples:

```text
ReactJS
React.js
React JS
-> React

NodeJS
Node.js
Node JS
-> Node.js

Mongo
Mongo DB
-> MongoDB

RESTful API
REST APIs
REST API development
-> REST API
```

Use a controlled alias dictionary plus fuzzy matching.

Example:

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
    "restful api": "REST API",
    "rest apis": "REST API"
}
```

Do not allow fuzzy matching to create unsafe/incorrect matches. Review thresholds.

---

# 9. Keyword Matching

Keyword matching must be explicit and auditable.

For each candidate calculate:

```text
matched required skills
missing required skills
matched preferred skills
```

Start with:

```text
required match = matched required / total required
preferred match = matched preferred / total preferred
```

Recommended initial keyword score:

```text
Keyword Score =
    85% × Required Skill Match
  + 15% × Preferred Skill Match
```

If there are no preferred skills, use only the required skill score.

Important:
- Missing a required skill should hurt substantially.
- Missing a preferred skill should hurt less.
- Exact/normalized technology matches should be rewarded.
- Project evidence can strengthen a skill match.

---

# 10. Semantic Matching

Use embeddings rather than asking the LLM to provide a similarity score.

Generate embeddings for:

1. JD overall text
2. JD responsibilities
3. JD required skills
4. Resume overall text
5. Resume projects
6. Resume experience

Start simple:

```text
JD relevant text
        ↓
embedding

Resume relevant text
        ↓
embedding

cosine similarity
        ↓
semantic score
```

Initial implementation:

```python
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer("all-MiniLM-L6-v2")
```

Convert cosine similarity into a 0–100 score.

Do not overcomplicate this initially. Get the complete pipeline working first.

---

# 11. Final Scoring

Start with an easy-to-explain formula:

```text
Final Score =
    50% Keyword Score
  + 50% Semantic Score
```

After testing, optionally improve to:

```text
Final Score =
    45% Keyword Score
  + 45% Semantic Score
  + 10% Evidence Score
```

Where Evidence Score considers whether important skills are demonstrated in projects/experience rather than appearing only as a raw skill list.

Keep all component scores visible in the UI.

Example:

```text
Candidate 01
Keyword Score: 89.0
Semantic Score: 93.8
Evidence Score: 90.0
Final Score: 91.4
```

Do not hard-code candidate scores.

---

# 12. Ranking

For every uploaded resume:

1. Parse PDF.
2. Clean text.
3. Extract structured resume.
4. Normalize skills.
5. Calculate keyword score.
6. Calculate semantic score.
7. Calculate final score.
8. Store matched/missing evidence.

Then:

```python
candidates.sort(
    key=lambda candidate: candidate.final_score,
    reverse=True
)
```

Return all candidates from highest to lowest.

---

# 13. Explanation Generation

Generate explanations only for the top 3.

Example output:

```text
Candidate 1 — Score: 91.4

Why ranked highly:
- Strong match for React, Node.js, Express, MongoDB and REST APIs.
- Relevant project experience demonstrates backend API development.
- Git experience is present.
- High semantic similarity with the role responsibilities.

Missing:
- TypeScript was not found.
- AWS was not found.

Keyword Score: 89.0
Semantic Score: 93.8
```

The explanation must be grounded in stored evidence.

---

# 14. UI Requirements

Build a simple Streamlit interface.

## Screen

```text
SMART SHORTLISTING ENGINE

Upload Job Description
[Choose PDF]

Upload Resumes
[Choose multiple PDFs]

[ RUN SHORTLIST ]
```

After processing:

```text
RANK | CANDIDATE | FINAL SCORE | KEYWORD | SEMANTIC
-----------------------------------------------------
1    | Candidate A | 91.4      | 89.0    | 93.8
2    | Candidate B | 86.9      | 84.0    | 89.8
3    | Candidate C | 81.7      | 78.5    | 84.9
...
18   | Candidate R | 32.4      | 25.0    | 39.8
```

Click/select a candidate to view:
- matched skills
- missing skills
- score components

Show detailed explanations for the top 3.

---

# 15. Explainability Requirements

Every score should be traceable to evidence.

Store something like:

```json
{
  "candidate_name": "Candidate A",
  "keyword_score": 89.0,
  "semantic_score": 93.8,
  "final_score": 91.4,
  "matched_required_skills": [
    "React",
    "Node.js",
    "Express",
    "MongoDB",
    "REST API",
    "Git"
  ],
  "missing_required_skills": [],
  "matched_preferred_skills": [
    "Docker"
  ],
  "missing_preferred_skills": [
    "TypeScript",
    "AWS"
  ]
}
```

This is important for the judges.

---

# 16. Testing Strategy

First test with 3–5 synthetic resumes.

Create:
- 1 very strong candidate
- 1 strong candidate
- 1 medium candidate
- 1 weak candidate
- 1 very weak candidate

Verify the ordering.

Then test all 18 supplied resumes.

Check:

### Test 1 — Exact skills

Resume contains:
```text
React, Node.js, MongoDB
```

JD contains:
```text
React, Node.js, MongoDB
```

Keyword score should be high.

### Test 2 — Semantic equivalence

JD:
```text
Develop REST APIs with Node.js.
```

Resume:
```text
Created backend services using Express.
```

Semantic matching should detect useful similarity.

### Test 3 — Missing required skill

JD requires:
```text
React
Node.js
MongoDB
```

Resume has:
```text
React
```

Required skill score must drop significantly.

### Test 4 — Optional skill

Missing Docker should not hurt as much as missing Node.js.

### Test 5 — Formatting variation

Test:
```text
NodeJS
Node.js
Node JS
```

They should normalize to one canonical skill.

---

# 17. Performance / API Efficiency

Avoid unnecessary LLM calls.

For each run:

```text
1 JD extraction call
18 resume extraction calls
Top 3 explanation calls
```

Potentially cache extracted JSON so rerunning the ranking does not require re-parsing every resume.

Embedding models should run locally when practical.

Recommended flow:

```text
Upload files
    ↓
Check cache
    ↓
Only process new/changed files
    ↓
Run matching
```

---

# 18. API Key Security

Use:

```text
.env
```

Example:

```env
GEMINI_API_KEY=your_key_here
```

Load it through environment variables.

`.gitignore` must contain:

```text
.env
__pycache__/
.venv/
*.pyc
```

Never commit the actual API key.

Provide `.env.example`:

```env
GEMINI_API_KEY=
```

---

# 19. Error Handling

Handle:

- invalid PDF
- scanned/non-extractable PDF
- empty resume
- malformed LLM JSON
- API failure
- rate limit
- missing API key
- duplicate resume
- fewer than expected resumes
- missing JD

The app should show a clear error instead of crashing.

For malformed JSON from the LLM:
1. retry once with a stricter JSON prompt
2. validate with Pydantic
3. fail gracefully if still invalid

---

# 20. Bonus Features

Only implement after the core pipeline works.

## Bonus A — JD bias detection

Detect phrases that may be unnecessarily exclusionary or overly narrow.

Example:

```text
Potentially narrow phrasing:
"young energetic candidate"

Reason:
May unnecessarily restrict otherwise qualified candidates.
```

Do not make strong legal claims. Present it as a potential bias/narrowness flag.

## Bonus B — Recruiter Q&A

Example:

```text
Why is Candidate A ranked above Candidate B?
```

Answer using the already-calculated evidence.

Do not recalculate rankings inside the chatbot.

## Bonus C — Messy resume handling

Improve handling of:
- inconsistent section names
- date formats
- typos
- unusual formatting
- missing sections

---

# 21. Development Phases

## Phase 1 — Working skeleton

Implement:

- project structure
- Streamlit page
- PDF upload
- PDF text extraction
- display extracted text

Do not add advanced AI yet.

## Phase 2 — LLM extraction

Implement:

- JD extraction
- resume extraction
- JSON validation
- skill normalization

Test on a few files.

## Phase 3 — Keyword engine

Implement:

- required skill matching
- preferred skill matching
- aliases
- fuzzy matching
- keyword score
- evidence storage

## Phase 4 — Semantic engine

Implement:

- embeddings
- cosine similarity
- semantic score

## Phase 5 — Ranking

Implement:

- final score
- sorting
- all-candidate ranking
- score breakdown

## Phase 6 — Top-3 explanations

Implement:

- evidence package
- Gemini explanation generation
- top-3 display

## Phase 7 — Real dataset testing

Run against all supplied resumes.

Inspect:
- obvious false positives
- obvious false negatives
- unexpected ordering
- score distribution

## Phase 8 — UI polish

Add:
- ranking table
- score bars
- candidate details
- top-3 explanation cards

## Phase 9 — Optional bonus

Only after everything above works.

---

# 22. Demo Flow for Judges

During the demo:

1. Upload the sample JD.
2. Upload all 18 resumes.
3. Click `RUN SHORTLIST`.
4. Show the full ranking.
5. Show a candidate's:
   - keyword score
   - semantic score
   - final score
   - matched skills
   - missing skills
6. Open the top 3 explanations.
7. Explain the architecture:
   - Gemini extracts/normalizes information.
   - Keyword matcher performs explicit matching.
   - Sentence Transformer performs semantic matching.
   - Our scoring code combines both.
   - Gemini turns the stored evidence into natural-language explanations.
8. Be ready to explain the scoring formula.

---

# 23. What NOT to Build

Do not make the core pipeline:

```text
JD + Resume
     ↓
LLM
     ↓
"Score = 87"
```

Do not hard-code the expected ranking.

Do not use only keyword search.

Do not use only embeddings.

Do not make the chatbot decide the ranking.

Do not spend most of the hackathon on UI.

Do not add bonus features before the core ranking works.

---

# 24. Acceptance Criteria

The project is considered complete when all of these work:

- [ ] Upload 1 JD PDF.
- [ ] Upload 15–18 resume PDFs.
- [ ] Parse all PDFs.
- [ ] Extract structured JD information.
- [ ] Extract structured resume information.
- [ ] Normalize skills.
- [ ] Calculate keyword score for every candidate.
- [ ] Calculate semantic score for every candidate.
- [ ] Combine scores in our own code.
- [ ] Rank every candidate.
- [ ] Show final score for every candidate.
- [ ] Show matched/missing skills.
- [ ] Generate top-3 explanations.
- [ ] Run end-to-end from the UI.
- [ ] No hard-coded ranking.
- [ ] API key stored securely.

---

# 25. Suggested Initial Milestone

Build this first:

```text
JD PDF
  ↓
text extraction
  ↓
Gemini structured JD

Resume PDF
  ↓
text extraction
  ↓
Gemini structured Resume

Structured data
  ↓
keyword matching
  ↓
embedding similarity
  ↓
final score
  ↓
ranking table
```

Do not start with bonus features.

The official problem statement explicitly recommends getting a basic end-to-end pipeline working first and improving it afterward.

---

# 26. Antigravity Instructions

When implementing this plan:

1. Work incrementally.
2. Do not rewrite the entire project unnecessarily.
3. Create the folder structure first.
4. Run the application after each major phase.
5. Keep functions modular.
6. Use type hints.
7. Validate LLM outputs using Pydantic.
8. Add tests for scoring and normalization.
9. Never expose API keys.
10. Keep the ranking deterministic for the same extracted inputs.
11. Log score components for debugging.
12. Keep the final ranking logic in normal Python code, not inside the LLM prompt.

At each phase, verify the implementation before moving to the next phase.

---

# 27. Final Target

The final application should demonstrate:

```text
UNSTRUCTURED PDFs
       ↓
LLM EXTRACTION + NORMALIZATION
       ↓
STRUCTURED DATA
       ↓
┌─────────────────────┐
│ KEYWORD MATCHING    │
│         +           │
│ SEMANTIC MATCHING   │
└─────────┬───────────┘
          ↓
     OWN SCORING LOGIC
          ↓
    RANK ALL CANDIDATES
          ↓
       TOP 3
          ↓
     LLM EXPLANATIONS
```

The central engineering contribution is the **hybrid ranking engine**, not the chatbot.
