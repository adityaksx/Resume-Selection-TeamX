# InternLoom AI — Smart Shortlisting Engine

An AI-powered candidate shortlisting system that ranks resumes against a job description using **hybrid matching** (keyword + semantic).

## Features

- 📄 PDF parsing for JD and resumes
- 🤖 LLM-based extraction (Gemini API)
- 🔤 Keyword matching with skill normalization
- 🧠 Semantic matching with sentence embeddings
- 📊 Transparent, evidence-based scoring
- 💡 Natural-language explanations for top 3

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up API key
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 4. Run the application
streamlit run app/main.py

# 5. Run tests
pytest tests/ -v
```

## Architecture

```
JD PDF + Resume PDFs
    → PDF Text Extraction (PyMuPDF)
    → LLM Extraction (Gemini → structured JSON)
    → Skill Normalization
    → Keyword Matching + Semantic Matching
    → Final Score (our code, not LLM)
    → Ranking
    → Top-3 Explanations (Gemini)
    → Streamlit UI
```

## Project Structure

```
app/
├── main.py              # Entry point
├── ui.py                # Streamlit interface
├── parsers/pdf_parser.py
├── llm/                 # Gemini API integrations
├── matching/            # Keyword + semantic engines
├── models/              # Pydantic data models
└── utils/               # Config, text cleaning
```
