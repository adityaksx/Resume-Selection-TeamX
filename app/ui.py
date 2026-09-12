"""Streamlit UI for the InternLoom Smart Shortlisting Engine.

The UI layer owns presentation/orchestration only. Ranking remains owned by the
Python matching pipeline; AI features are optional and server-side.
"""

from __future__ import annotations

import html
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


CUSTOM_CSS = """
<style>
:root {
    --loom-bg: #eff5eb;
    --loom-green: #8cc34f;
    --loom-green-hover: #7ab040;
    --loom-slate: #253d47;
    --loom-white: #ffffff;
    --loom-border: rgba(37, 61, 71, 0.10);
    --loom-muted: #64748b;
}

/* Keep selectors limited to stable Streamlit test IDs / root classes. */
.stApp {
    background: var(--loom-bg);
}

.block-container {
    max-width: 1400px;
    padding-top: 1.4rem;
    padding-bottom: 3rem;
}

header[data-testid="stHeader"] {
    background: transparent;
}

.loom-hero {
    background: var(--loom-slate);
    border-radius: 20px;
    padding: 1.7rem 1.8rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 14px 32px rgba(37, 61, 71, 0.12);
    border-left: 6px solid var(--loom-green);
}

.loom-kicker {
    color: var(--loom-green);
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 1.1px;
    margin-bottom: 0.35rem;
}

.loom-title {
    color: #ffffff;
    font-size: 2.15rem;
    font-weight: 700;
    line-height: 1.16;
    margin: 0;
}

.loom-subtitle {
    color: #d7e0e5;
    font-size: 0.95rem;
    line-height: 1.55;
    margin-top: 0.55rem;
    max-width: 950px;
}

.loom-status {
    display: inline-block;
    margin-top: 0.9rem;
    padding: 0.35rem 0.7rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.10);
    color: #ffffff;
    font-size: 0.76rem;
    font-weight: 600;
}

.loom-rank-card {
    background: var(--loom-white);
    border: 1px solid var(--loom-border);
    border-radius: 16px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.8rem;
    box-shadow: 0 6px 18px rgba(37, 61, 71, 0.045);
}

.loom-top1 { border-left: 5px solid #d4af37; }
.loom-top2 { border-left: 5px solid #94a3b8; }
.loom-top3 { border-left: 5px solid #b87333; }

.score-pill {
    display: inline-block;
    padding: 0.3rem 0.65rem;
    border-radius: 9px;
    background: #eef8e3;
    color: var(--loom-slate);
    font-weight: 700;
    font-size: 0.84rem;
    white-space: nowrap;
}

.badge {
    display: inline-block;
    padding: 0.22rem 0.52rem;
    border-radius: 999px;
    margin: 0.1rem 0.12rem 0.1rem 0;
    font-size: 0.74rem;
    font-weight: 600;
}

.badge-match { background: #dcfce7; color: #166534; }
.badge-miss { background: #fee2e2; color: #991b1b; }
.badge-pref { background: #e0e7ff; color: #3730a3; }

.small-muted {
    color: var(--loom-muted);
    font-size: 0.8rem;
}

.section-note {
    color: var(--loom-muted);
    font-size: 0.84rem;
    margin-top: -0.3rem;
    margin-bottom: 0.75rem;
}

[data-testid="stFileUploaderDropzone"] {
    border-radius: 12px;
}

[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}

@media (max-width: 900px) {
    .loom-title { font-size: 1.65rem; }
    .loom-hero { padding: 1.35rem; }
}
</style>
"""


@st.cache_data(show_spinner=False)
def _gemini_available_cached() -> bool:
    """Cache the configuration check so every rerun does not repeat it."""
    try:
        return bool(is_gemini_available())
    except Exception:
        logger.exception("Gemini availability check failed")
        return False


def _safe(text: Any) -> str:
    return html.escape(str(text or ""))


def _badges(items: list[str], css_class: str, empty: str = "None") -> str:
    if not items:
        return f"<span class='small-muted'>{_safe(empty)}</span>"
    return " ".join(
        f"<span class='badge {css_class}'>{_safe(item)}</span>" for item in items
    )


def _init_state() -> None:
    defaults = {
        "jd": None,
        "resumes": {},
        "ranking": None,
        "chat_history": [],
        "pending_chat_prompt": None,
        "jd_fairness_report": None,
        "comparison_ai_cache": {},
        "improvement_cache": {},
        "candidate_ai_explanation": None,
        "selected_view": "Shortlist",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def setup_page() -> None:
    st.set_page_config(
        page_title="InternLoom | Smart Shortlisting Engine",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _init_state()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header() -> None:
    ai_active = _gemini_available_cached()
    ai_status = "Gemini AI Active" if ai_active else "Local ML Mode"
    status_dot = "●" if ai_active else "○"

    st.markdown(
        f"""
        <section class="loom-hero">
            <div class="loom-kicker">EXPLAINABLE AI RECRUITING</div>
            <div class="loom-title">InternLoom Smart Shortlisting Engine</div>
            <div class="loom-subtitle">
                Rank every candidate using explicit keyword matching + local semantic matching,
                then use AI only for recruiter-facing explanations and advisory features.
            </div>
            <div class="loom-status">{status_dot} {ai_status}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def upload_section() -> tuple[Any, list[Any]]:
    st.markdown("### Upload Job & Candidate Documents")
    st.markdown(
        "<div class='section-note'>Accepted: PDF, DOCX and TXT. Mixed resume formats are supported.</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("#### Job Description")
        jd_file = st.file_uploader(
            "Upload one JD",
            type=["pdf", "docx", "txt"],
            key="jd_upload",
            help="One Job Description in PDF, DOCX or TXT format.",
        )
        if jd_file is not None:
            st.caption(f"Loaded: {jd_file.name}")

    with col2:
        st.markdown("#### Candidate Resumes")
        resume_files = st.file_uploader(
            "Upload multiple resumes",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="resume_upload",
            help="Upload your candidate batch. PDF, DOCX and TXT may be mixed.",
        )
        if resume_files:
            st.caption(f"Loaded {len(resume_files)} resume(s)")

    return jd_file, resume_files


def _run_pipeline(jd_file, resume_files: list) -> None:
    if not jd_file or not resume_files:
        st.error("Please upload one Job Description and at least one resume.")
        return

    with st.status("Running shortlisting pipeline...", expanded=True) as status:
        st.write("1/4 Extracting Job Description text")
        try:
            jd_text = extract_text_from_uploaded_document(jd_file)
        except DocumentParsingError as exc:
            status.update(label="JD parsing failed", state="error")
            st.error(f"JD parsing failed: {exc}")
            return
        except Exception as exc:
            status.update(label="JD parsing failed", state="error")
            st.error(f"Unexpected JD parsing error: {exc}")
            logger.exception("JD parsing failure")
            return

        st.write("2/4 Extracting structured JD")
        try:
            jd = extract_jd(jd_text)
            jd.required_skills = normalize_skills(jd.required_skills)
            jd.preferred_skills = normalize_skills(jd.preferred_skills)
        except Exception as exc:
            status.update(label="JD extraction failed", state="error")
            st.error(f"JD extraction failed: {exc}")
            logger.exception("JD extraction failure")
            return

        st.write("3/4 Processing candidate documents")
        resumes: dict[str, Resume] = {}
        failures: list[str] = []
        progress = st.progress(0, text="Processing resumes...")

        for i, uploaded in enumerate(resume_files, start=1):
            original_name = uploaded.name
            filename = original_name
            if filename in resumes:
                filename = f"{filename}_{i}"

            try:
                text = extract_text_from_uploaded_document(uploaded)
                resume = extract_resume(text, filename=filename)
                resume.skills = normalize_skills(resume.skills)
                for project in resume.projects:
                    project.technologies = normalize_skills(project.technologies)
                resumes[filename] = resume
            except DocumentParsingError as exc:
                failures.append(f"{original_name}: {exc}")
            except Exception as exc:
                failures.append(f"{original_name}: {exc}")
                logger.exception("Resume processing failure: %s", original_name)

            progress.progress(
                i / len(resume_files),
                text=f"Processed {i}/{len(resume_files)}",
            )

        progress.empty()

        if not resumes:
            status.update(label="No usable resumes", state="error")
            st.error("No resume could be processed.")
            return

        if failures:
            with st.expander(f"Skipped documents ({len(failures)})"):
                for failure in failures:
                    st.write(f"- {failure}")

        st.write("4/4 Calculating keyword + semantic scores")
        try:
            ranking = shortlist_candidates(jd, resumes)
        except Exception as exc:
            status.update(label="Ranking failed", state="error")
            st.error(f"Shortlisting pipeline failed: {exc}")
            logger.exception("Pipeline failure")
            return

        status.update(
            label=f"Completed — ranked {len(ranking.candidates)} candidates",
            state="complete",
        )

    st.session_state["jd"] = jd
    st.session_state["resumes"] = resumes
    st.session_state["ranking"] = ranking
    st.session_state["chat_history"] = []
    st.session_state["pending_chat_prompt"] = None
    st.session_state["jd_fairness_report"] = None
    st.session_state["comparison_ai_cache"] = {}
    st.session_state["improvement_cache"] = {}
    st.session_state["candidate_ai_explanation"] = None
    st.success(f"Shortlisting complete for **{jd.role_title or 'this role'}**.")


def _score_metrics(candidate: CandidateResult) -> None:
    a, b, c = st.columns(3)
    a.metric("Final Score", f"{candidate.final_score:.2f}/100")
    b.metric("Keyword", f"{candidate.keyword_score:.2f}/100")
    c.metric("Semantic", f"{candidate.semantic_score:.2f}/100")


def _render_candidate_skills(candidate: CandidateResult) -> None:
    left, right = st.columns(2)
    with left:
        st.markdown("**Required skills matched**")
        st.markdown(
            _badges(candidate.matched_required_skills, "badge-match"),
            unsafe_allow_html=True,
        )
        st.markdown("**Required skills missing**")
        st.markdown(
            _badges(candidate.missing_required_skills, "badge-miss"),
            unsafe_allow_html=True,
        )
    with right:
        st.markdown("**Preferred skills matched**")
        st.markdown(
            _badges(candidate.matched_preferred_skills, "badge-pref"),
            unsafe_allow_html=True,
        )
        st.markdown("**Preferred skills missing**")
        st.markdown(
            _badges(candidate.missing_preferred_skills, "badge-miss"),
            unsafe_allow_html=True,
        )


def render_shortlist_view(ranking: RankingResult, jd: JobDescription) -> None:
    st.subheader("Shortlist Overview")

    if not ranking.candidates:
        st.info("No candidates are available.")
        return

    scores = [c.final_score for c in ranking.candidates]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Candidates", len(ranking.candidates))
    m2.metric("Highest", f"{max(scores):.2f}")
    m3.metric("Average", f"{sum(scores) / len(scores):.2f}")
    m4.metric("Lowest", f"{min(scores):.2f}")

    st.markdown("### Top 3")
    st.caption(
        "AI explanations are optional. Numerical ranking is always produced by the deterministic scoring engine."
    )

    top_classes = ["loom-top1", "loom-top2", "loom-top3"]
    for idx, candidate in enumerate(ranking.top_3):
        card_class = top_classes[min(idx, 2)]
        c1, c2 = st.columns([5, 1.2], vertical_alignment="center")
        with c1:
            st.markdown(
                f"**#{candidate.rank} {_safe(candidate.candidate_name)}**",
                unsafe_allow_html=True,
            )
            st.caption(
                f"{candidate.filename or 'No filename'} · "
                f"Keyword {candidate.keyword_score:.2f} · "
                f"Semantic {candidate.semantic_score:.2f}"
            )
        with c2:
            st.markdown(
                f"<div class='score-pill'>{candidate.final_score:.2f}/100</div>",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<div class='loom-rank-card {card_class}' style='margin-top:-3.2rem; padding:0; border:none; box-shadow:none; background:transparent;'></div>",
            unsafe_allow_html=True,
        )
        with st.expander(f"View top-{idx + 1} explanation and evidence", expanded=False):
            st.markdown(candidate.explanation or "No explanation stored yet.")
            _render_candidate_skills(candidate)

    st.markdown("### Full Ranking")
    st.caption("Every uploaded candidate is shown. Final Score = 50% Keyword + 50% Semantic.")

    rows = []
    for candidate in ranking.candidates:
        req_total = len(candidate.matched_required_skills) + len(
            candidate.missing_required_skills
        )
        rows.append(
            {
                "Rank": candidate.rank,
                "Candidate": candidate.candidate_name,
                "Final Score": round(candidate.final_score, 2),
                "Keyword": round(candidate.keyword_score, 2),
                "Semantic": round(candidate.semantic_score, 2),
                "Required": (
                    f"{len(candidate.matched_required_skills)}/{req_total}"
                    if req_total
                    else "N/A"
                ),
                "Missing Required": len(candidate.missing_required_skills),
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn(width="small"),
            "Final Score": st.column_config.NumberColumn(format="%.2f"),
            "Keyword": st.column_config.NumberColumn(format="%.2f"),
            "Semantic": st.column_config.NumberColumn(format="%.2f"),
        },
    )


def _find_candidate(ranking: RankingResult, label: str) -> CandidateResult:
    rank = int(label.split("#", 1)[1].split(" ", 1)[0])
    return next(c for c in ranking.candidates if c.rank == rank)


def render_compare_view(ranking: RankingResult) -> None:
    st.subheader("Compare Two Candidates")
    st.caption("Comparison uses the same stored scores and skill evidence as the ranking.")

    if len(ranking.candidates) < 2:
        st.info("At least two candidates are required.")
        return

    labels = [f"#{c.rank} {c.candidate_name}" for c in ranking.candidates]
    col_a, col_b = st.columns(2)
    with col_a:
        selected_a = st.selectbox("Candidate A", labels, index=0, key="compare_a")
    with col_b:
        selected_b = st.selectbox(
            "Candidate B",
            labels,
            index=min(1, len(labels) - 1),
            key="compare_b",
        )

    cand_a = _find_candidate(ranking, selected_a)
    cand_b = _find_candidate(ranking, selected_b)
    if cand_a.rank == cand_b.rank:
        st.warning("Select two different candidates.")
        return

    comparison: CandidateComparison = compare_candidates(cand_a, cand_b)
    higher = cand_a if cand_a.final_score >= cand_b.final_score else cand_b
    st.success(
        f"Current ranking: **#{higher.rank} {higher.candidate_name}** is higher by "
        f"{abs(cand_a.final_score - cand_b.final_score):.2f} points."
    )

    left, mid, right = st.columns([4, 2, 4])
    with left:
        st.markdown(f"### #{cand_a.rank} {cand_a.candidate_name}")
        _score_metrics(cand_a)
        _render_candidate_skills(cand_a)
    with mid:
        st.markdown("### Differences")
        st.metric("Final", f"{cand_a.final_score - cand_b.final_score:+.2f}")
        st.metric("Keyword", f"{cand_a.keyword_score - cand_b.keyword_score:+.2f}")
        st.metric("Semantic", f"{cand_a.semantic_score - cand_b.semantic_score:+.2f}")
    with right:
        st.markdown(f"### #{cand_b.rank} {cand_b.candidate_name}")
        _score_metrics(cand_b)
        _render_candidate_skills(cand_b)

    st.markdown("### Shared and Unique Required Skills")
    s1, s2, s3 = st.columns(3)
    s1.markdown(f"**Shared ({len(comparison.shared_required_skills)})**")
    s1.write(", ".join(comparison.shared_required_skills) or "None")
    s2.markdown(f"**Unique to {cand_a.candidate_name} ({len(comparison.unique_required_a)})**")
    s2.write(", ".join(comparison.unique_required_a) or "None")
    s3.markdown(f"**Unique to {cand_b.candidate_name} ({len(comparison.unique_required_b)})**")
    s3.write(", ".join(comparison.unique_required_b) or "None")

    if _gemini_available_cached():
        cache_key = f"{cand_a.rank}:{cand_b.rank}"
        if st.button("Explain Comparison with AI", type="primary", key="compare_ai"):
            with st.spinner("Generating evidence-grounded comparison..."):
                st.session_state["comparison_ai_cache"][cache_key] = (
                    explain_comparison_with_ai(comparison)
                )
        if cache_key in st.session_state.get("comparison_ai_cache", {}):
            st.markdown(st.session_state["comparison_ai_cache"][cache_key])
    else:
        st.info("Gemini AI is unavailable. Deterministic comparison is still available.")


def render_candidate_insights_view(ranking: RankingResult, jd: JobDescription) -> None:
    st.subheader("Candidate Insights")
    labels = [f"#{c.rank} {c.candidate_name}" for c in ranking.candidates]
    selected = st.selectbox("Select Candidate", labels, key="insight_candidate")
    candidate = _find_candidate(ranking, selected)

    st.markdown(f"### #{candidate.rank} {candidate.candidate_name}")
    _score_metrics(candidate)
    _render_candidate_skills(candidate)

    st.markdown("### Semantic Evidence")
    if candidate.semantic_evidence:
        for i, evidence_item in enumerate(candidate.semantic_evidence[:6], start=1):
            requirement = evidence_item.get("requirement", "")
            evidence = evidence_item.get("best_matching_evidence", "") or "No matching evidence"
            similarity = float(evidence_item.get("similarity", 0.0))
            with st.expander(
                f"Requirement {i} · {similarity * 100:.1f}%",
                expanded=(i == 1),
            ):
                st.markdown(f"**JD requirement:** {requirement}")
                st.markdown(f"**Best resume evidence:** {evidence}")
                st.progress(
                    max(0.0, min(1.0, similarity)),
                    text=f"Similarity: {similarity * 100:.1f}%",
                )
    else:
        st.info("No semantic evidence is available for this candidate.")

    st.markdown("### Candidate Actions")
    c1, c2 = st.columns(2)
    with c1:
        if _gemini_available_cached():
            if st.button(
                "Generate AI Explanation",
                type="primary",
                use_container_width=True,
                key="candidate_explain",
            ):
                with st.spinner("Generating explanation..."):
                    st.session_state["candidate_ai_explanation"] = (
                        generate_ai_candidate_explanation(candidate)
                    )
            if st.session_state.get("candidate_ai_explanation"):
                st.markdown(st.session_state["candidate_ai_explanation"])
        else:
            st.markdown(candidate.explanation or "AI explanation unavailable.")

    with c2:
        cache_key = f"{candidate.rank}"
        if st.button(
            "How Can This Candidate Improve?",
            type="primary",
            use_container_width=True,
            key="candidate_improve",
        ):
            with st.spinner("Building improvement recommendations..."):
                if _gemini_available_cached():
                    result = generate_candidate_improvement_advice(candidate, jd)
                else:
                    missing = candidate.missing_required_skills
                    result = (
                        "### Priority improvement areas\n\n"
                        + (
                            "- " + "\n- ".join(missing)
                            if missing
                            else "- No explicit required-skill gaps were found."
                        )
                    )
                st.session_state["improvement_cache"][cache_key] = result
        if cache_key in st.session_state.get("improvement_cache", {}):
            st.markdown(st.session_state["improvement_cache"][cache_key])


def render_recruiter_chat_view(ranking: RankingResult, jd: JobDescription) -> None:
    st.subheader("Recruiter AI")
    st.caption("Ask about rankings, candidate differences, evidence, gaps, or interview questions.")

    ai_active = _gemini_available_cached()
    if not ai_active:
        st.warning("Gemini AI is not configured. The deterministic shortlist remains available.")

    suggestions = [
        "Why is #1 ranked above #2?",
        "What required skills is #2 missing?",
        "Compare #1 and #3.",
        "How can #4 improve?",
    ]

    suggestion_cols = st.columns(len(suggestions))
    for i, suggestion in enumerate(suggestions):
        with suggestion_cols[i]:
            if st.button(
                suggestion,
                use_container_width=True,
                key=f"chat_suggestion_{i}",
            ):
                st.session_state["pending_chat_prompt"] = suggestion

    for message in st.session_state["chat_history"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    query = st.chat_input("Ask about the current shortlist...", key="recruiter_chat_input")
    if not query:
        query = st.session_state.pop("pending_chat_prompt", None)
    if not query:
        return

    st.session_state["chat_history"].append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        if not ai_active:
            response = (
                "Gemini AI is unavailable. I can still answer via deterministic "
                "comparisons when supported by the current evidence."
            )
        else:
            with st.spinner("Analyzing shortlist evidence..."):
                response = chat_with_recruiter(
                    message=query,
                    history=st.session_state["chat_history"][:-1],
                    ranking=ranking,
                    jd=jd,
                )
        st.markdown(response)

    st.session_state["chat_history"].append(
        {"role": "assistant", "content": response}
    )


def render_jd_analysis_view(jd: JobDescription) -> None:
    st.subheader("JD Analysis")
    st.markdown(f"### {_safe(jd.role_title or 'Job Description')}", unsafe_allow_html=True)
    if jd.company:
        st.markdown(f"**Company:** {_safe(jd.company)}", unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        st.markdown("**Required Skills**")
        st.markdown(_badges(jd.required_skills, "badge-match"), unsafe_allow_html=True)
    with right:
        st.markdown("**Preferred Skills**")
        st.markdown(_badges(jd.preferred_skills, "badge-pref"), unsafe_allow_html=True)

    if jd.responsibilities:
        with st.expander("Responsibilities"):
            for item in jd.responsibilities:
                st.markdown(f"- {item}")
    if jd.qualifications:
        with st.expander("Qualifications"):
            for item in jd.qualifications:
                st.markdown(f"- {item}")

    st.markdown("### JD Fairness & Narrowness Check")
    st.caption("Advisory only. Findings never change candidate scores or rankings.")

    if not _gemini_available_cached():
        st.info("Configure GEMINI_API_KEY to run the AI fairness analysis.")
        return

    if st.button("Run JD Fairness Check", type="primary", key="jd_fairness"):
        with st.spinner("Reviewing JD language..."):
            try:
                st.session_state["jd_fairness_report"] = analyze_jd_fairness(jd)
            except Exception as exc:
                logger.exception("JD fairness analysis failed")
                st.error(f"Fairness analysis failed: {exc}")

    report: JDFairnessReport | None = st.session_state.get("jd_fairness_report")
    if not report:
        return

    st.info(report.overall_summary)
    if not report.findings:
        st.success("No potentially narrow phrasing was detected.")
    else:
        for index, finding in enumerate(report.findings, start=1):
            st.markdown(f"#### Finding {index}: {_safe(finding.phrase)}")
            st.markdown(f"**Category:** {finding.issue}")
            st.markdown(f"**Why review it:** {finding.rationale}")
            st.markdown(f"**Possible alternative:** {finding.suggested_alternative}")
            st.warning(finding.human_review_warning)
    if report.disclaimer:
        st.caption(report.disclaimer)


def run_ui() -> None:
    setup_page()
    render_header()
    jd_file, resume_files = upload_section()

    can_run = jd_file is not None and bool(resume_files)
    if st.button(
        "Run Smart Shortlisting",
        type="primary",
        disabled=not can_run,
        use_container_width=True,
        key="run_shortlisting",
    ):
        _run_pipeline(jd_file, resume_files)

    ranking: RankingResult | None = st.session_state.get("ranking")
    jd: JobDescription | None = st.session_state.get("jd")
    if ranking is None or jd is None:
        st.info("Upload a Job Description and candidate resumes to start the shortlist.")
        return

    st.divider()

    tabs = st.tabs([
        "Shortlist",
        "Compare",
        "Candidate Insights",
        "Recruiter AI",
        "JD Analysis",
    ])

    with tabs[0]:
        render_shortlist_view(ranking, jd)
    with tabs[1]:
        render_compare_view(ranking)
    with tabs[2]:
        render_candidate_insights_view(ranking, jd)
    with tabs[3]:
        render_recruiter_chat_view(ranking, jd)
    with tabs[4]:
        render_jd_analysis_view(jd)


if __name__ == "__main__":
    run_ui()
