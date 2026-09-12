"""Streamlit UI for the InternLoom Smart Shortlisting Engine (Phase 7 Recruiter Product).

Features:
- Multi-format document parsing (PDF, DOCX, TXT) with mixed batch support
- Modern recruiter dashboard aesthetic (pale green, dark slate cards, emerald accents, Poppins typography)
- 5 Main Navigation Views:
    1. 📋 Shortlist (Full ranking table + Top 3 prominent cards)
    2. ⚖️ Compare Candidates (Side-by-side metrics, deltas & AI comparison)
    3. 🔍 Candidate Insights (Deep dive + "How Can This Candidate Improve?")
    4. 🤖 Recruiter AI (Evidence-grounded shortlist Q&A chat)
    5. 📄 JD Analysis (Requirements review & JD Fairness / Inclusivity Check)
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st

from app.extraction.jd_extractor import extract_jd
from app.extraction.resume_extractor import extract_resume
from app.llm.client import is_gemini_available
from app.llm.comparison_explainer import explain_comparison_with_ai
from app.llm.improvement_advisor import generate_candidate_improvement_advice
from app.llm.jd_bias_detector import analyze_jd_fairness
from app.llm.recruiter_chat import chat_with_recruiter
from app.llm.top3_explainer import generate_ai_candidate_explanation
from app.matching.comparator import compare_candidates
from app.matching.pipeline import shortlist_candidates
from app.matching.skill_normalizer import normalize_skills
from app.models.comparison_models import CandidateComparison
from app.models.fairness_models import JDFairnessReport
from app.models.jd_models import JobDescription
from app.models.result_models import CandidateResult, RankingResult
from app.models.resume_models import Resume
from app.parsers.document_parser import (
    DocumentParsingError,
    extract_text_from_uploaded_document,
)

logger = logging.getLogger(__name__)

# --- Custom Styling: Modern Recruiter Dashboard ---
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
}

/* Page Background */
.stApp {
    background-color: #f6faf6;
}

/* Header & Banner */
.hero-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    color: #ffffff;
    padding: 2.2rem 2.5rem;
    border-radius: 16px;
    margin-bottom: 1.8rem;
    box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15);
    border-left: 6px solid #10b981;
}

.hero-title {
    font-size: 2.2rem;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 0.4rem;
    letter-spacing: -0.5px;
}

.hero-subtitle {
    font-size: 1.05rem;
    color: #cbd5e1;
    font-weight: 400;
    line-height: 1.5;
}

/* Slate Cards */
.dark-card {
    background-color: #1e293b;
    color: #f8fafc;
    padding: 1.5rem;
    border-radius: 14px;
    margin-bottom: 1rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    border: 1px solid #334155;
}

.metric-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    text-align: center;
}

/* Badges */
.badge-match {
    background-color: #d1fae5;
    color: #065f46;
    padding: 0.25rem 0.6rem;
    border-radius: 9999px;
    font-weight: 500;
    font-size: 0.82rem;
    display: inline-block;
    margin: 2px;
}

.badge-miss {
    background-color: #fee2e2;
    color: #991b1b;
    padding: 0.25rem 0.6rem;
    border-radius: 9999px;
    font-weight: 500;
    font-size: 0.82rem;
    display: inline-block;
    margin: 2px;
}

.badge-pref {
    background-color: #e0e7ff;
    color: #3730a3;
    padding: 0.25rem 0.6rem;
    border-radius: 9999px;
    font-weight: 500;
    font-size: 0.82rem;
    display: inline-block;
    margin: 2px;
}

/* Green Primary Buttons */
div.stButton > button:first-child[kind="primary"] {
    background-color: #10b981;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 0.65rem 1.4rem;
    font-weight: 600;
    font-size: 1rem;
    transition: all 0.2s ease;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

div.stButton > button:first-child[kind="primary"]:hover {
    background-color: #059669;
    box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4);
    transform: translateY(-1px);
}
</style>
"""


def setup_page() -> None:
    """Configure Streamlit layout, metadata, and custom styling."""
    st.set_page_config(
        page_title="InternLoom | Smart Shortlisting Engine",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header() -> None:
    """Render the dashboard hero banner."""
    ai_status = "🟢 Gemini AI Active" if is_gemini_available() else "⚪ Local ML Mode (Offline)"
    st.markdown(
        f"""
        <div class="hero-header">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div class="hero-title">🎯 InternLoom Smart Shortlisting Engine</div>
                    <div class="hero-subtitle">
                        Explainable candidate ranking powered by canonical skill extraction and local sentence embeddings.<br>
                        <strong>Zero LLM score alteration</strong> — deterministic scoring with AI-powered advisory insights.
                    </div>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 500;">
                    {ai_status}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def upload_section() -> tuple:
    """Render split document upload cards supporting PDF, DOCX, and TXT."""
    st.subheader("📁 Upload Documents (PDF, DOCX, TXT)")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📄 Job Description**")
        jd_file = st.file_uploader(
            "Upload single JD file",
            type=["pdf", "docx", "txt"],
            key="jd_upload",
            help="Upload a single Job Description document (PDF, DOCX, or plain text).",
        )
        if jd_file:
            st.caption(f"✓ `{jd_file.name}` ({jd_file.type or 'unknown format'})")

    with col2:
        st.markdown("**📑 Candidate Resumes**")
        resume_files = st.file_uploader(
            "Upload candidate resumes (mixed formats supported)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="resume_upload",
            help="Upload candidate resume files (recommended 15-18). Mixed PDF, DOCX, and TXT accepted.",
        )
        if resume_files:
            st.caption(f"✓ {len(resume_files)} file(s) selected")

    return jd_file, resume_files


def run_pipeline(jd_file, resume_files: list) -> None:
    """Run document extraction, skill normalization, scoring, ranking, and explanation."""
    if not jd_file or not resume_files:
        st.error("Please upload both a Job Description and at least one Candidate Resume.")
        return

    # 1. Parse JD
    jd_text = None
    with st.spinner("Extracting Job Description text..."):
        try:
            jd_text = extract_text_from_uploaded_document(jd_file)
        except DocumentParsingError as e:
            st.error(f"❌ Failed to parse JD: {e}")
            return
        except Exception as e:
            st.error(f"❌ Unexpected JD reading error: {e}")
            return

    # 2. Extract structured JD
    jd: JobDescription | None = None
    try:
        jd = extract_jd(jd_text)
        jd.required_skills = normalize_skills(jd.required_skills)
        jd.preferred_skills = normalize_skills(jd.preferred_skills)
    except Exception as e:
        st.error(f"❌ Structured JD extraction failed: {e}")
        logger.exception("JD extraction error")
        return

    # 3. Parse and extract Resumes (resilient batch handling)
    resumes: dict[str, Resume] = {}
    progress_bar = st.progress(0, text="Extracting and parsing candidate documents...")

    for i, r_file in enumerate(resume_files):
        fname = r_file.name
        # Handle duplicates in filename
        if fname in resumes:
            fname = f"{fname}_{i+1}"

        try:
            r_text = extract_text_from_uploaded_document(r_file)
            resume = extract_resume(r_text, filename=fname)
            resume.skills = normalize_skills(resume.skills)
            for proj in resume.projects:
                proj.technologies = normalize_skills(proj.technologies)
            resumes[fname] = resume
        except DocumentParsingError as e:
            st.warning(f"⚠️ Skipped unreadable file '{r_file.name}': {e}")
        except Exception as e:
            st.warning(f"⚠️ Error parsing '{r_file.name}': {e}")

        progress_bar.progress((i + 1) / len(resume_files), text=f"Processed {i + 1}/{len(resume_files)} resumes...")

    progress_bar.empty()

    if not resumes:
        st.error("No resumes could be successfully extracted. Please verify file formats.")
        return

    # 4. Hybrid Matching and Ranking Pipeline
    with st.spinner(f"🚀 Ranking {len(resumes)} candidates across keyword and local semantic models..."):
        try:
            ranking = shortlist_candidates(jd, resumes)
        except Exception as e:
            st.error(f"❌ Shortlisting pipeline error: {e}")
            logger.exception("Pipeline execution failed")
            return

    # Persist in session state
    st.session_state["jd"] = jd
    st.session_state["resumes"] = resumes
    st.session_state["ranking"] = ranking
    st.session_state["chat_history"] = []
    st.success(f"✅ Successfully ranked {len(ranking.candidates)} candidates for '{jd.role_title or 'Job'}'!")


# ==============================================================================
# VIEW 1: SHORTLIST (Full Ranking Table + Top 3 Prominent Highlights)
# ==============================================================================
def render_shortlist_view(ranking: RankingResult, jd: JobDescription) -> None:
    """Render the primary shortlist overview."""
    st.subheader("🏆 Shortlist Overview & Candidate Ranking")

    # 1. Summary Metrics
    scores = [c.final_score for c in ranking.candidates]
    top_score = max(scores)
    lowest_score = min(scores)
    avg_score = sum(scores) / len(scores)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("👥 Candidates Evaluated", len(ranking.candidates))
    m2.metric("⭐ Top Final Score", f"{top_score:.2f}")
    m3.metric("📊 Average Score", f"{avg_score:.2f}")
    m4.metric("📉 Lowest Score", f"{lowest_score:.2f}")

    st.markdown("---")

    # 2. Prominent Top-3 Cards
    st.subheader("🏅 Top 3 Shortlist Highlights")
    st.caption("Detailed explainability derived strictly from stored evidence (AI or deterministic fallback).")

    top_3 = ranking.top_3
    medals = ["🥇", "🥈", "🥉"]

    for idx, cand in enumerate(top_3):
        medal = medals[idx] if idx < len(medals) else f"#{idx+1}"
        with st.container():
            c_header1, c_header2 = st.columns([3, 1])
            with c_header1:
                st.markdown(f"### {medal} #{cand.rank} {cand.candidate_name}")
                st.caption(f"**Filename:** `{cand.filename or 'N/A'}` | **Keyword:** {cand.keyword_score:.2f} | **Semantic:** {cand.semantic_score:.2f}")
            with c_header2:
                st.metric("Final Score", f"{cand.final_score:.2f} / 100")

            # Skills preview tags
            st.markdown(
                f"**Matched Required ({len(cand.matched_required_skills)}/{len(cand.matched_required_skills) + len(cand.missing_required_skills)}):** "
                + " ".join(f"<span class='badge-match'>{s}</span>" for s in cand.matched_required_skills),
                unsafe_allow_html=True,
            )
            if cand.missing_required_skills:
                st.markdown(
                    "**Missing Required:** " + " ".join(f"<span class='badge-miss'>{s}</span>" for s in cand.missing_required_skills),
                    unsafe_allow_html=True,
                )

            if cand.explanation:
                with st.expander(f"📋 View Explanation for #{cand.rank} {cand.candidate_name}", expanded=False):
                    st.markdown(cand.explanation)
            st.markdown("<hr style='margin: 1.2rem 0; border-color: #e2e8f0;'>", unsafe_allow_html=True)

    # 3. Full Shortlist Table
    st.subheader(f"📋 Complete Shortlist Ranking ({len(ranking.candidates)} Candidates)")
    st.caption("Final Score = 50% Keyword Score + 50% Semantic Score. Deterministic tie-breaking ensures strict reproducibility.")

    rows = []
    for c in ranking.candidates:
        rows.append(
            {
                "Rank": f"#{c.rank}",
                "Candidate": c.candidate_name,
                "Final Score": f"{c.final_score:.2f}",
                "Keyword": f"{c.keyword_score:.2f}",
                "Semantic": f"{c.semantic_score:.2f}",
                "Matched Req": f"{len(c.matched_required_skills)}/{len(c.matched_required_skills) + len(c.missing_required_skills)}",
                "Missing Req": ", ".join(c.missing_required_skills) if c.missing_required_skills else "None",
                "Filename": c.filename or "N/A",
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ==============================================================================
# VIEW 2: CANDIDATE COMPARISON
# ==============================================================================
def render_compare_view(ranking: RankingResult) -> None:
    """Render side-by-side comparison between any two candidates."""
    st.subheader("⚖️ Compare Two Candidates")
    st.caption("Side-by-side analysis of scores, skill overlaps, and unique strengths calculated deterministically.")

    if len(ranking.candidates) < 2:
        st.info("At least 2 candidates are required to perform a comparison.")
        return

    candidate_names = [f"#{c.rank} - {c.candidate_name}" for c in ranking.candidates]

    col1, col2 = st.columns(2)
    with col1:
        sel_a_str = st.selectbox("Select Candidate A:", options=candidate_names, index=0)
    with col2:
        default_b_idx = 1 if len(candidate_names) > 1 else 0
        sel_b_str = st.selectbox("Select Candidate B:", options=candidate_names, index=default_b_idx)

    rank_a = int(sel_a_str.split()[0].replace("#", ""))
    rank_b = int(sel_b_str.split()[0].replace("#", ""))

    cand_a = next((c for c in ranking.candidates if c.rank == rank_a), ranking.candidates[0])
    cand_b = next((c for c in ranking.candidates if c.rank == rank_b), ranking.candidates[1])

    if cand_a.candidate_name == cand_b.candidate_name:
        st.warning("Please select two distinct candidates to compare.")
        return

    comp: CandidateComparison = compare_candidates(cand_a, cand_b)

    # Winner banner
    higher = comp.higher_ranked_candidate
    delta_score = abs(comp.final_score_difference)
    st.success(
        f"🏆 **{higher}** is currently ranked higher by a score margin of **+{delta_score:.2f} points**."
    )

    # Side-by-side score comparison
    c_a, c_mid, c_b = st.columns([4, 2, 4])

    with c_a:
        st.markdown(f"### #{cand_a.rank} {cand_a.candidate_name}")
        st.metric("Final Score", f"{cand_a.final_score:.2f}")
        st.caption(f"Keyword: {cand_a.keyword_score:.2f} | Semantic: {cand_a.semantic_score:.2f}")
        st.markdown(
            "**Matched Required:** " + (" ".join(f"<span class='badge-match'>{s}</span>" for s in cand_a.matched_required_skills) if cand_a.matched_required_skills else "None"),
            unsafe_allow_html=True,
        )
        st.markdown(
            "**Missing Required:** " + (" ".join(f"<span class='badge-miss'>{s}</span>" for s in cand_a.missing_required_skills) if cand_a.missing_required_skills else "None"),
            unsafe_allow_html=True,
        )

    with c_mid:
        st.markdown("#### Score Deltas")
        st.metric("Final Delta", f"{comp.final_score_difference:+.2f}")
        st.metric("Keyword Delta", f"{comp.keyword_score_difference:+.2f}")
        st.metric("Semantic Delta", f"{comp.semantic_score_difference:+.2f}")

    with c_b:
        st.markdown(f"### #{cand_b.rank} {cand_b.candidate_name}")
        st.metric("Final Score", f"{cand_b.final_score:.2f}")
        st.caption(f"Keyword: {cand_b.keyword_score:.2f} | Semantic: {cand_b.semantic_score:.2f}")
        st.markdown(
            "**Matched Required:** " + (" ".join(f"<span class='badge-match'>{s}</span>" for s in cand_b.matched_required_skills) if cand_b.matched_required_skills else "None"),
            unsafe_allow_html=True,
        )
        st.markdown(
            "**Missing Required:** " + (" ".join(f"<span class='badge-miss'>{s}</span>" for s in cand_b.missing_required_skills) if cand_b.missing_required_skills else "None"),
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Detailed Skill Breakdown
    st.subheader("🧩 Skill Overlap & Asymmetric Gaps")
    sk1, sk2, sk3 = st.columns(3)
    with sk1:
        st.markdown(f"**Shared Required Skills ({len(comp.shared_required_skills)}):**")
        st.write(", ".join(comp.shared_required_skills) if comp.shared_required_skills else "None")
    with sk2:
        st.markdown(f"**Unique to {cand_a.candidate_name} ({len(comp.unique_required_a)}):**")
        st.write(", ".join(comp.unique_required_a) if comp.unique_required_a else "None")
    with sk3:
        st.markdown(f"**Unique to {cand_b.candidate_name} ({len(comp.unique_required_b)}):**")
        st.write(", ".join(comp.unique_required_b) if comp.unique_required_b else "None")

    st.markdown("---")

    # AI Comparison Explanation Action
    if st.button("🤖 Explain Comparison with AI", type="primary"):
        with st.spinner("Analyzing candidate comparison..."):
            explanation = explain_comparison_with_ai(comp)
            st.markdown(explanation)


# ==============================================================================
# VIEW 3: CANDIDATE INSIGHTS & IMPROVEMENT ADVISOR
# ==============================================================================
def render_candidate_insights_view(ranking: RankingResult, jd: JobDescription) -> None:
    """Render single-candidate drill-down and career improvement recommendations."""
    st.subheader("🔍 Candidate Deep Dive & Improvement Advisor")

    candidate_options = [f"#{c.rank} - {c.candidate_name} ({c.final_score:.2f})" for c in ranking.candidates]
    selected_option = st.selectbox("Select Candidate to Inspect:", options=candidate_options, index=0)

    rank_sel = int(selected_option.split()[0].replace("#", ""))
    candidate = next((c for c in ranking.candidates if c.rank == rank_sel), ranking.candidates[0])

    # Score Card
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("⭐ Final Score", f"{candidate.final_score:.2f} / 100")
    sc2.metric("🔑 Keyword Score", f"{candidate.keyword_score:.2f} / 100")
    sc3.metric("🧠 Semantic Score", f"{candidate.semantic_score:.2f} / 100")

    st.markdown("---")

    # Skills Breakdown
    col_req, col_pref = st.columns(2)
    with col_req:
        st.markdown("#### 🎯 Required Skills")
        if candidate.matched_required_skills:
            st.markdown("**Matched:** " + " ".join(f"<span class='badge-match'>{s}</span>" for s in candidate.matched_required_skills), unsafe_allow_html=True)
        else:
            st.warning("No required skills matched.")

        if candidate.missing_required_skills:
            st.markdown("**Missing:** " + " ".join(f"<span class='badge-miss'>{s}</span>" for s in candidate.missing_required_skills), unsafe_allow_html=True)
        else:
            st.info("No missing required skills! 🎉")

    with col_pref:
        st.markdown("#### ⭐ Preferred Skills")
        if candidate.matched_preferred_skills:
            st.markdown("**Matched:** " + " ".join(f"<span class='badge-pref'>{s}</span>" for s in candidate.matched_preferred_skills), unsafe_allow_html=True)
        else:
            st.caption("None matched")

        if candidate.missing_preferred_skills:
            st.markdown("**Missing:** " + ", ".join(candidate.missing_preferred_skills))

    # Semantic Evidence
    if candidate.semantic_evidence:
        st.markdown("#### 🧬 Requirement-Level Semantic Evidence")
        for i, ev in enumerate(candidate.semantic_evidence[:3], start=1):
            with st.expander(f"Requirement {i}: {ev.get('requirement')} (Similarity: {ev.get('similarity_score', round(float(ev.get('similarity', 0))*100, 1))}%)", expanded=(i == 1)):
                st.markdown(f"**Best Resume Evidence:** {ev.get('best_matching_evidence') or '*(No matching text chunk)*'}")
                st.progress(float(ev.get("similarity", 0.0)))

    st.markdown("---")

    # Actions: AI Explanation & Improvement Advice
    act_col1, act_col2 = st.columns(2)
    with act_col1:
        if st.button(f"📋 Generate AI Explanation for #{candidate.rank} {candidate.candidate_name}", use_container_width=True):
            with st.spinner("Generating explanation..."):
                expl = generate_ai_candidate_explanation(candidate)
                st.markdown(expl)

    with act_col2:
        if st.button(f"💡 How Can {candidate.candidate_name} Improve?", type="primary", use_container_width=True):
            with st.spinner("Analyzing skill gaps and building career recommendations..."):
                advice = generate_candidate_improvement_advice(candidate, jd)
                st.markdown(advice)


# ==============================================================================
# VIEW 4: RECRUITER AI CHAT
# ==============================================================================
def render_recruiter_chat_view(ranking: RankingResult, jd: JobDescription) -> None:
    """Render interactive recruiter chat interface grounded in the active shortlist."""
    st.subheader("🤖 Recruiter AI Assistant")
    st.caption(
        "Ask questions about the shortlist, candidate trade-offs, and interview questions. "
        "All answers are grounded strictly in extracted evidence without modifying rankings."
    )

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Quick prompt suggestions
    st.markdown("**Suggested Questions:**")
    q_col1, q_col2, q_col3 = st.columns(3)
    with q_col1:
        if st.button("Why is #1 ranked above #2?", use_container_width=True):
            st.session_state["pending_chat_prompt"] = "Why is #1 ranked above #2?"
    with q_col2:
        if st.button("What skills is #2 missing?", use_container_width=True):
            st.session_state["pending_chat_prompt"] = "What skills is #2 missing?"
    with q_col3:
        if st.button("Interview questions for #1?", use_container_width=True):
            st.session_state["pending_chat_prompt"] = "What technical interview questions should I ask Candidate #1 based on their project evidence?"

    # Display chat conversation history
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_query = st.chat_input("Ask a question about the candidate shortlist...")
    if "pending_chat_prompt" in st.session_state and st.session_state["pending_chat_prompt"]:
        user_query = st.session_state.pop("pending_chat_prompt")

    if user_query:
        # Display user message
        st.session_state["chat_history"].append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing shortlist context..."):
                response = chat_with_recruiter(
                    message=user_query,
                    history=st.session_state["chat_history"][:-1],
                    ranking=ranking,
                    jd=jd,
                )
                st.markdown(response)
        st.session_state["chat_history"].append({"role": "assistant", "content": response})


# ==============================================================================
# VIEW 5: JD & FAIRNESS ANALYSIS
# ==============================================================================
def render_jd_analysis_view(jd: JobDescription) -> None:
    """Render extracted JD specifications and advisory fairness / inclusivity audit."""
    st.subheader("📄 Job Description & Inclusivity Analysis")

    # Extracted Summary
    st.markdown(f"### {jd.role_title or 'Job Title'} — {jd.company or 'Company'}")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Required Skills:**")
        for s in jd.required_skills:
            st.markdown(f"- {s}")
    with c2:
        st.markdown("**Preferred Skills:**")
        for s in jd.preferred_skills:
            st.markdown(f"- {s}")

    if jd.responsibilities:
        with st.expander("Responsibilities", expanded=False):
            for r in jd.responsibilities:
                st.markdown(f"- {r}")

    if jd.qualifications:
        with st.expander("Qualifications", expanded=False):
            for q in jd.qualifications:
                st.markdown(f"- {q}")

    st.markdown("---")

    # Fairness & Inclusivity Audit
    st.subheader("🛡️ JD Fairness & Language Inclusivity Check")
    st.caption(
        "Identifies subjective jargon, narrow requirements, or restrictive criteria that may discourage diverse applicants. "
        "Advisory recommendations only — does not alter candidate rankings or modify the original JD."
    )

    if st.button("🔍 Run Fairness & Inclusivity Analysis", type="primary"):
        with st.spinner("Scanning Job Description for potential language constraints..."):
            report: JDFairnessReport = analyze_jd_fairness(jd)

            st.info(f"**Summary:** {report.overall_summary}")

            if not report.findings:
                st.success("✅ No significantly narrow or exclusionary phrasing detected in this Job Description.")
            else:
                for idx, finding in enumerate(report.findings, start=1):
                    with st.container():
                        st.markdown(f"#### Finding {idx}: `{finding.phrase}`")
                        st.markdown(f"**Category:** {finding.issue}")
                        st.markdown(f"**Rationale:** {finding.rationale}")
                        st.markdown(f"**Suggested Alternative:** *\"{finding.suggested_alternative}\"*")
                        st.warning(f"⚠️ {finding.human_review_warning}")
                        st.divider()

            st.caption(f"ℹ️ {report.disclaimer}")


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
def run_ui() -> None:
    """Main application loop."""
    setup_page()
    render_header()

    # Upload Section
    jd_file, resume_files = upload_section()

    can_run = jd_file is not None and bool(resume_files)
    run_clicked = st.button(
        "🚀 RUN SHORTLISTING PIPELINE",
        type="primary",
        disabled=not can_run,
        use_container_width=True,
    )

    if not can_run and "ranking" not in st.session_state:
        st.info("Upload a Job Description and candidate resumes above to start.")

    if run_clicked:
        run_pipeline(jd_file, resume_files)

    # Render Dashboard if shortlist results are available
    if "ranking" in st.session_state and st.session_state["ranking"] is not None:
        ranking: RankingResult = st.session_state["ranking"]
        jd: JobDescription = st.session_state["jd"]

        st.divider()

        # Navigation Tabs
        tab_shortlist, tab_compare, tab_insights, tab_chat, tab_jd = st.tabs(
            [
                "📋 Shortlist",
                "⚖️ Compare Candidates",
                "🔍 Candidate Insights",
                "🤖 Recruiter AI",
                "📄 JD Analysis",
            ]
        )

        with tab_shortlist:
            render_shortlist_view(ranking, jd)

        with tab_compare:
            render_compare_view(ranking)

        with tab_insights:
            render_candidate_insights_view(ranking, jd)

        with tab_chat:
            render_recruiter_chat_view(ranking, jd)

        with tab_jd:
            render_jd_analysis_view(jd)


if __name__ == "__main__":
    run_ui()
