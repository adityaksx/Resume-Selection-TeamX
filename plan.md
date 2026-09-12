# InternLoom AI Hackathon — Smart Shortlisting Engine
# UPDATED MASTER PLAN — PHASE 7 PRODUCT + AI FEATURES

## 1. Project Goal

Build an end-to-end recruiter-facing system that takes:

- 1 Job Description (JD)
- 15–18 candidate resumes

and produces:

1. A ranked list of all candidates.
2. A final score for every candidate.
3. Keyword and semantic score breakdowns.
4. Top-3 explanations.
5. Recruiter comparison between any two candidates.
6. Recruiter AI chat for questions about the current shortlist.
7. Candidate improvement recommendations.
8. JD fairness / potentially narrow phrasing analysis.
9. Robust support for PDF, DOCX and TXT inputs.
10. A polished recruiter-oriented UI.

The system's numerical ranking must remain deterministic and explainable.

---

# 2. Critical Architecture Rule

## Core ranking engine

The final ranking must NOT be decided by a generative LLM.

The core pipeline is:

```text
Document
  ↓
Text extraction
  ↓
Deterministic structured extraction
  ↓
Skill normalization
  ↓
Keyword matching
  +
Local semantic embeddings
  ↓
Deterministic score calculation
  ↓
Final ranking
```

Current final-score formula:

```text
Final Score =
    0.50 × Keyword Score
  + 0.50 × Semantic Score
```

Do not allow an LLM to modify:
- keyword score
- semantic score
- final score
- ranking position

## LLM usage

A generative LLM may be used ONLY for product features where natural-language generation/reasoning provides value:

- top-3 natural-language explanations
- recruiter chat
- resume comparison explanation
- candidate improvement advice
- JD bias / overly narrow phrasing analysis

The LLM is an explanation/advisory layer, not the ranking authority.

---

# 3. Current Completed Phases

## Phase 1
PDF parsing and basic input pipeline.

## Phase 2
Deterministic JD/resume extraction and structured data.

## Phase 3
Keyword matching, normalization and matched/missing skill evidence.

## Phase 4
Local Sentence Transformer semantic matching with requirement-level evidence.

## Phase 5
Final score and deterministic ranking.

## Phase 6
Deterministic top-3 explanation capability.

Phase 7 builds the product/AI layer on top of these completed capabilities.

---

# 4. Phase 7 Scope

Phase 7 includes:

1. Real LLM explanation layer for top 3.
2. Recruiter AI chat.
3. Two-resume comparison.
4. Candidate improvement advisor.
5. JD fairness / narrow-language analysis.
6. PDF + DOCX + TXT input support.
7. UI redesign using the provided visual reference.
8. Robust LLM fallback behavior.
9. Session-level state/history.
10. Security and regression testing.

Do not break the core ranking engine while adding these features.

---

# 5. Supported Input Formats

Both JD and resumes must support:

```text
.pdf
.docx
.txt
```

Multiple resume formats can be mixed in one upload:

```text
candidate1.pdf
candidate2.docx
candidate3.txt
candidate4.pdf
```

The downstream pipeline receives normalized plain text and should not care about source format.

## Parsers

PDF:
- PyMuPDF

DOCX:
- python-docx

TXT:
- Python standard library

Create a common document-parsing interface.

Handle:
- invalid files
- empty files
- unreadable files
- encoding issues
- malformed DOCX
- low/no extracted text

Do not remove existing PDF support.

---

# 6. LLM Service Layer

Keep all generative LLM code isolated from the ranking engine.

Recommended:

```text
app/
└── llm/
    ├── client.py
    ├── top3_explainer.py
    ├── recruiter_chat.py
    ├── comparison_explainer.py
    ├── improvement_advisor.py
    └── jd_bias_detector.py
```

Preferred provider:
- Gemini API

Configuration:

```env
GEMINI_API_KEY=
```

The API key must exist only on the server side.

Never expose it to:
- browser JavaScript
- HTML
- client-side configuration
- logs

If no API key exists:
- ranking continues to work
- deterministic explanations continue to work
- comparison continues to work
- improvement and AI chat/bias features show graceful unavailable states or deterministic fallback where possible

---

# 7. LLM Grounding Contract

Every LLM feature must receive structured evidence from the existing engine.

Do not use:

```text
Raw JD + raw resume
        ↓
LLM
        ↓
LLM decides everything
```

Use:

```text
Ranking engine
        ↓
structured evidence
        ↓
LLM
        ↓
natural-language response
```

The LLM must not:
- invent skills
- invent experience
- invent scores
- change scores
- reorder candidates
- make unsupported claims

When evidence is absent, the model should say the information was not found.

---

# 8. Top-3 AI Explanations

Use the existing ranking/evidence.

For each top-3 candidate provide the LLM with:

```text
candidate_name
rank
final_score
keyword_score
semantic_score
matched_required_skills
missing_required_skills
matched_preferred_skills
missing_preferred_skills
top_semantic_evidence
```

Ask it to generate:

- why the candidate ranked highly
- strongest evidence
- important matched skills
- important missing skills
- concise recruiter-friendly summary

It must not calculate a new score.

## Fallback

If LLM unavailable:
- use existing deterministic explanation generator

The user's ranking must not depend on LLM availability.

---

# 9. Recruiter AI Chat

Add a chat feature that understands the current shortlist.

Example questions:

```text
Why is Candidate A ranked above Candidate B?

Why is Candidate 4 only #8?

Which required skills is Candidate A missing?

Which candidates have React and Node.js?

What makes Candidate B weaker than Candidate A?

What should I ask Candidate A in an interview?

How can Candidate C improve for this JD?
```

## Chat architecture

```text
Question
   ↓
Candidate/entity identification
   ↓
Retrieve relevant structured ranking evidence
   ↓
LLM
   ↓
Natural-language answer
```

For ranking/comparison questions, provide:
- rank
- final score
- keyword score
- semantic score
- matched required skills
- missing required skills
- preferred skills
- relevant semantic evidence

The LLM must explain the stored decision.

It must not recalculate or override the ranking.

---

# 10. Chat Context

Maintain conversation history for the current session.

Example:

```text
User:
Why is Candidate A above Candidate B?

Assistant:
Candidate A has a higher final score...

User:
What required skill does B lack?

Assistant:
Candidate B is missing...
```

Support candidate references using:
- filename
- candidate name
- rank

Handle unresolved references safely.

If ambiguous, ask for clarification rather than guessing.

---

# 11. Resume Comparison Feature

Add a dedicated "Compare Candidates" view.

Allow any two ranked candidates to be selected.

Display side-by-side:

```text
Candidate A              Candidate B

Rank                     Rank
Final Score              Final Score
Keyword Score            Keyword Score
Semantic Score           Semantic Score

Required matched         Required matched
Required missing         Required missing

Preferred matched        Preferred matched
Preferred missing        Preferred missing
```

Also calculate deterministically:

- final score difference
- keyword score difference
- semantic score difference
- shared required skills
- unique required matches
- unique missing skills

Clearly identify which candidate is currently ranked higher.

## Optional AI comparison explanation

After showing deterministic comparison data, allow:

```text
Explain this comparison with AI
```

Send the structured comparison to the LLM.

The LLM may improve readability but must not choose the winner.

---

# 12. Candidate Improvement Feature

For any selected candidate, provide:

```text
How Can This Candidate Improve?
```

Use:
- JD requirements
- matched skills
- missing required skills
- missing preferred skills
- semantic evidence
- project/experience evidence

Generate sections such as:

```text
Priority Skill Gaps
Resume Evidence Gaps
Project/Experience Opportunities
Recommended Next Steps
```

Important distinction:

Do not say:

```text
"You do not know Node.js."
```

Instead:

```text
"Node.js was not explicitly found in the resume."
```

The system only knows what is evidenced in the resume.

## Deterministic fallback

When LLM unavailable:

```text
Missing required skills
→ recommend adding relevant evidence/projects if applicable
```

No unsupported claims.

---

# 13. JD Bias / Overly Narrow Phrasing Analysis

Add:

```text
JD Fairness Check
```

Use the LLM only as an advisory reviewer.

Analyze:
- subjective language
- unnecessarily narrow requirements
- potentially exclusionary wording
- unnecessary tool constraints
- potentially excessive qualifications
- internship requirements that may be unnecessarily restrictive

Example output:

```text
Potential issue:
"young and energetic"

Why it may be narrow:
This wording may unnecessarily narrow the candidate pool.

Possible alternative:
"motivated and able to work effectively in a collaborative environment."

Status:
Potential issue — human review recommended.
```

Do not claim a legal violation.

Do not automatically modify the JD.

Do not use fairness findings to alter candidate scores.

---

# 14. UI Direction

Use the user's supplied website as a visual reference.

Visual characteristics:

- pale green background
- dark blue/slate cards
- bright green accent
- Poppins-style typography
- rounded cards
- clean spacing
- split upload area
- green primary CTA
- modern recruiter dashboard

The existing reference uses:
- hero section
- split upload cards
- ranking results
- top-3 explanations
- recruiter Q&A

Adapt these ideas to the actual application.

Do not copy fake/static logic from the reference.

Do not sacrifice functionality for visual matching.

---

# 15. Main Navigation

Recommended navigation:

```text
Shortlist
Compare
Candidate Insights
Recruiter AI
JD Analysis
```

Shortlist should remain the default landing view.

---

# 16. Shortlist Page

Display:

```text
JOB
Role:
Company:
Candidates processed: 18
```

Then the full ranking table:

```text
Rank
Candidate
Final Score
Keyword Score
Semantic Score
Required Match
Missing Required
```

All candidates must remain visible.

Top 3 should receive subtle visual emphasis.

Do not hide lower-ranked candidates.

---

# 17. Candidate Details

For a selected candidate:

```text
Candidate Name
Rank
Final Score

Keyword Score
Semantic Score

Required Skills
✓ matched
✗ missing

Preferred Skills
✓ matched
✗ missing

Semantic Evidence
JD requirement
↓
best resume evidence
↓
similarity
```

Then buttons/actions:

```text
Explain with AI
How Can This Candidate Improve?
```

---

# 18. Compare Page

UI:

```text
Select Candidate A
Select Candidate B
```

Show the side-by-side comparison.

Also provide:

```text
Score Difference
Skill Difference
Semantic Difference
Shared Strengths
Unique Strengths
Gaps
```

Optional:

```text
Explain Comparison with AI
```

---

# 19. Recruiter AI Page

Create a chat-style interface.

Show suggested starter questions:

```text
Why is Candidate A ranked above Candidate B?

Why is Candidate A ranked #1?

What skills is Candidate B missing?

Which candidate has the strongest React experience?

What should I ask Candidate C in an interview?

How can Candidate D improve?
```

Use the current shortlist as context.

Do not expose internal prompts.

Do not allow the chat to modify ranking.

---

# 20. JD Analysis Page

Show:

```text
Extracted Role
Required Skills
Preferred Skills
Responsibilities
Qualifications
```

Then:

```text
Potentially Narrow / Biased Phrasing
```

For every flag show:

- phrase
- reason
- suggested alternative
- human-review notice

---

# 21. File Upload Experience

Replace PDF-only labels with:

```text
Upload Job Description
PDF, DOCX or TXT

Upload Candidate Resumes
PDF, DOCX or TXT
```

Show:
- filename
- format
- file count
- parsing status

Support mixed resume formats.

Example:

```text
✓ Rahul.pdf
✓ Priya.docx
✓ Aman.txt
⚠ Candidate4.pdf — no extractable text
```

Do not fail the entire batch because one file is invalid.

---

# 22. Performance

Do not call the LLM automatically for every candidate.

LLM calls should occur only when needed:

- top-3 explanation generation
- user asks a chat question
- user explicitly requests comparison explanation
- user requests improvement advice
- JD analysis is opened/run

Cache safe session-level LLM results when practical.

Do not rerun Sentence Transformer embeddings unnecessarily.

Keep the existing model caching.

---

# 23. Security

Requirements:

- no secrets in frontend
- no secrets in JavaScript
- no secrets in Git
- `.env` ignored
- `.env.example` committed
- server-side API client only
- sanitize user-generated display text where HTML rendering is used

Do not use unsafe `innerHTML` patterns for untrusted candidate text.

---

# 24. Data Models

Keep typed models.

Potential additions:

## CandidateResult

```text
candidate_name
filename
rank
keyword_score
semantic_score
final_score
matched_required_skills
missing_required_skills
matched_preferred_skills
missing_preferred_skills
semantic_evidence
explanation
improvement_advice
```

## Comparison

```text
candidate_a
candidate_b
score_difference
keyword_difference
semantic_difference
shared_matches
unique_matches_a
unique_matches_b
missing_a
missing_b
```

## Bias finding

```text
phrase
issue
rationale
suggested_alternative
```

## Chat

```text
role
content
```

Do not add fields unless they are required.

---

# 25. Testing

## Document tests

- PDF
- DOCX
- TXT
- mixed batch
- invalid file
- empty file
- encoding problem

## LLM client tests

Mock the provider.

Test:
- valid response
- missing API key
- API error
- timeout
- malformed response
- fallback

Never require a live API key for unit tests.

## Top-3 explanation tests

Verify:
- top 3 only
- scores unchanged
- evidence is supplied
- fallback works

## Chat tests

Test:
- ranking question
- candidate comparison
- missing candidate
- ambiguous candidate
- follow-up question
- no ranking mutation

## Comparison tests

Verify:
- score difference
- shared skills
- unique skills
- correct higher-ranked candidate

## Improvement tests

Verify:
- missing required skills appear
- unsupported claims are avoided
- fallback works

## Bias tests

Verify:
- advisory structure
- no ranking mutation
- human-review wording

---

# 26. Core Ranking Regression Test

Before and after Phase 7 AI features:

For the same JD/resumes:

```text
final scores must remain identical
ranking must remain identical
```

Adding an explanation or chat request must never change candidate ranking.

This is a mandatory regression test.

---

# 27. End-to-End Test

Test with:

```text
JD: PDF
Resume 1: PDF
Resume 2: DOCX
Resume 3: TXT
...
```

Verify:

```text
files
 ↓
parsing
 ↓
extraction
 ↓
normalization
 ↓
keyword matching
 ↓
semantic matching
 ↓
final score
 ↓
ranking
 ↓
top 3
 ↓
AI explanation
 ↓
compare
 ↓
improvement
 ↓
chat
 ↓
JD fairness analysis
```

Also run the entire application with:

```text
GEMINI_API_KEY absent
```

Core ranking must still work.

Then run with a valid key and verify AI features.

---

# 28. Acceptance Criteria

Phase 7 is complete when:

- [ ] PDF JD works.
- [ ] DOCX JD works.
- [ ] TXT JD works.
- [ ] PDF resumes work.
- [ ] DOCX resumes work.
- [ ] TXT resumes work.
- [ ] Mixed resume formats work.
- [ ] Full ranking remains available.
- [ ] Every candidate has Final/Keyword/Semantic scores.
- [ ] Top 3 have LLM explanations when API is available.
- [ ] Deterministic explanation fallback works without API.
- [ ] Any two candidates can be compared.
- [ ] Comparison is based on existing ranking evidence.
- [ ] Candidate improvement feature works.
- [ ] JD fairness analysis works.
- [ ] Recruiter AI chat works.
- [ ] Chat cannot modify ranking.
- [ ] LLM cannot modify ranking.
- [ ] API key is server-side only.
- [ ] No regression in Phases 1–6.
- [ ] Tests pass.
- [ ] UI is polished and recruiter-friendly.

---

# 29. Phase 7 Development Order

Implement in this order:

### Phase 7A
Multi-format document parsing:
- PDF
- DOCX
- TXT

### Phase 7B
Server-side Gemini client + safe configuration.

### Phase 7C
Top-3 AI explanations + deterministic fallback.

### Phase 7D
Candidate comparison.

### Phase 7E
Candidate improvement advisor.

### Phase 7F
Recruiter AI chat.

### Phase 7G
JD fairness/bias analysis.

### Phase 7H
UI redesign and integration.

### Phase 7I
Full regression + end-to-end testing.

Do not build everything in one giant change.

---

# 30. Antigravity Execution Rules

Before coding:

1. Read this plan and AGENTS.md completely.
2. Inspect the current repository.
3. Identify existing Phase 1–6 implementations.
4. Reuse existing working logic.
5. Plan the smallest safe implementation.

For every Phase 7 sub-phase:

1. implement only that sub-phase
2. add tests
3. run full test suite
4. run the app
5. smoke-test the feature
6. verify ranking has not changed
7. report what changed
8. stop for approval before the next sub-phase

Do not:
- rewrite the core ranking engine
- hard-code candidates
- let LLM scores affect ranking
- add unnecessary dependencies
- expose API keys
- break the no-LLM core matcher

---

# 31. Final Product Architecture

```text
                ┌──────────────────────┐
                │ PDF / DOCX / TXT     │
                └──────────┬───────────┘
                           ↓
                    Document Parser
                           ↓
                    Structured Data
                           ↓
                  Skill Normalization
                           ↓
             ┌─────────────┴─────────────┐
             ↓                           ↓
       Keyword Matching          Local Semantic Model
             ↓                           ↓
        Keyword Score               Semantic Score
             └─────────────┬─────────────┘
                           ↓
                    OUR SCORING CODE
                           ↓
                    FINAL RANKING
                           │
          ┌────────────────┼────────────────┐
          ↓                ↓                ↓
       TOP 3            COMPARE          INSIGHTS
          ↓                ↓                ↓
      LLM explain      deterministic      LLM advice
          │             + optional AI         │
          └────────────────┬────────────────┘
                           ↓
                    RECRUITER AI CHAT
                           │
                           ↓
                    JD FAIRNESS CHECK
```

## Non-negotiable principle

```text
LLM = explanation / advisory / conversation

Embedding model = semantic similarity

Keyword matcher = explicit skill evidence

Python scoring engine = final numerical decision

Ranking engine = source of truth
```
