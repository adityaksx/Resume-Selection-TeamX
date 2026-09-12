"""Streamlit UI for the Smart Shortlisting Engine.

Phase 5: Upload PDFs → deterministic extraction → hybrid matching → final score & ranking display.
"""

from __future__ import annotations

import logging
import pandas as pd
import streamlit as st

from app.extraction.jd_extractor import extract_jd
from app.extraction.resume_extractor import extract_resume
from app.matching.pipeline import shortlist_candidates
from app.matching.skill_normalizer import normalize_skills
from app.models.jd_models import JobDescription
from app.models.result_models import CandidateResult, RankingResult
from app.models.resume_models import Resume
from app.parsers.pdf_parser import PDFParsingError, extract_text_from_uploaded_file

logger = logging.getLogger(__name__)


def setup_page() -> None:
    """Configure the Streamlit page layout and header."""
    st.set_page_config(
        page_title="Smart Shortlisting Engine",
        page_icon="🎯",
        layout="wide",
    )
    st.title("🎯 Smart Shortlisting Engine")
    st.markdown(
        "Upload a **Job Description PDF** and **Candidate Resume PDFs** to score and rank applicants "
        "using transparent keyword and local semantic matching — **100% deterministic, zero LLM calls**."
    )
    st.divider()


def upload_section() -> tuple:
    """Render file upload widgets and return uploaded files.

    Returns:
        Tuple of (jd_file, resume_files) where jd_file is a single
        UploadedFile or None, and resume_files is a list of UploadedFiles.
    """
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📄 Job Description")
        jd_file = st.file_uploader(
            "Upload JD (PDF)",
            type=["pdf"],
            key="jd_upload",
            help="Upload a single Job Description PDF.",
        )

    with col2:
        st.subheader("📑 Candidate Resumes")
        resume_files = st.file_uploader(
            "Upload Resumes (PDF)",
            type=["pdf"],
            accept_multiple_files=True,
            key="resume_upload",
            help="Upload candidate resume PDFs (recommended 15-18).",
        )

    # UI safety guidance on candidate count
    if resume_files:
        count = len(resume_files)
        if count < 15:
            st.info(f"ℹ️ Uploaded **{count}** resume(s). Hackathon target dataset is 15–18 resumes.")
        elif count > 18:
            st.info(f"ℹ️ Uploaded **{count}** resumes (target dataset is 15–18). All will be processed.")

    return jd_file, resume_files


def display_jd(jd: JobDescription) -> None:
    """Display structured JD extraction results."""
    st.subheader("📄 Extracted Job Description")

    if jd.role_title:
        st.markdown(f"**Role:** {jd.role_title}")
    if jd.company:
        st.markdown(f"**Company:** {jd.company}")

    col1, col2 = st.columns(2)
    with col1:
        if jd.required_skills:
            st.markdown("**Required Skills:**")
            for skill in jd.required_skills:
                st.markdown(f"- {skill}")
    with col2:
        if jd.preferred_skills:
            st.markdown("**Preferred Skills:**")
            for skill in jd.preferred_skills:
                st.markdown(f"- {skill}")

    if jd.responsibilities:
        with st.expander("Responsibilities", expanded=False):
            for r in jd.responsibilities:
                st.markdown(f"- {r}")

    if jd.qualifications:
        with st.expander("Qualifications", expanded=False):
            for q in jd.qualifications:
                st.markdown(f"- {q}")

    with st.expander("Raw JD Text", expanded=False):
        st.text(jd.raw_text[:3000] + ("\n\n... [truncated]" if len(jd.raw_text) > 3000 else ""))


def display_resume_details(resume: Resume) -> None:
    """Display structured resume extraction details."""
    cols = st.columns([1, 1])
    with cols[0]:
        if resume.skills:
            st.markdown("**Skills:**")
            st.markdown(", ".join(resume.skills))
        if resume.contact.email:
            st.markdown(f"**Email:** {resume.contact.email}")
        if resume.contact.phone:
            st.markdown(f"**Phone:** {resume.contact.phone}")
    with cols[1]:
        if resume.education:
            st.markdown("**Education:**")
            for edu in resume.education:
                parts = [p for p in [edu.degree, edu.institution, edu.duration] if p]
                st.markdown(f"- {' — '.join(parts)}")

    if resume.experience:
        st.markdown("**Experience:**")
        for exp in resume.experience:
            header = " — ".join(p for p in [exp.role, exp.company, exp.duration] if p)
            st.markdown(f"- **{header}**")
            if exp.description:
                st.caption(exp.description[:200])

    if resume.projects:
        st.markdown("**Projects:**")
        for proj in resume.projects:
            techs = f" ({', '.join(proj.technologies)})" if proj.technologies else ""
            st.markdown(f"- **{proj.name or 'Unnamed'}**{techs}")
            if proj.description:
                st.caption(proj.description[:200])


def display_ranking_results(ranking: RankingResult) -> None:
    """Display the full candidate ranking table, score distribution, and detailed breakdown."""
    st.header("🏆 Candidate Rankings & Score Breakdown")

    if not ranking.candidates:
        st.warning("No candidates were ranked.")
        return

    # 1. Summary Metrics
    scores = [c.final_score for c in ranking.candidates]
    top_score = max(scores)
    lowest_score = min(scores)
    avg_score = sum(scores) / len(scores)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Candidates", len(ranking.candidates))
    m2.metric("Highest Final Score", f"{top_score:.2f}")
    m3.metric("Average Final Score", f"{avg_score:.2f}")
    m4.metric("Lowest Final Score", f"{lowest_score:.2f}")

    st.markdown("---")

    # 2. Prominent Full Ranking Table
    st.subheader(f"📋 Ranked Shortlist ({len(ranking.candidates)} Candidates)")
    st.caption("Final Score = 50% Keyword Score + 50% Local Semantic Score. Tie-breakers: Keyword Score → Matched Required Skills → Name.")

    table_rows = []
    for c in ranking.candidates:
        table_rows.append(
            {
                "Rank": f"#{c.rank}",
                "Candidate": c.candidate_name,
                "Final Score": f"{c.final_score:.2f}",
                "Keyword Score": f"{c.keyword_score:.2f}",
                "Semantic Score": f"{c.semantic_score:.2f}",
                "Matched Req": f"{len(c.matched_required_skills)}",
                "Missing Req": f"{len(c.missing_required_skills)}",
                "Filename": c.filename or "N/A",
            }
        )

    df_ranking = pd.DataFrame(table_rows)
    st.dataframe(
        df_ranking,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # 3. Detailed Candidate Inspection
    st.subheader("🔍 Candidate Deep Dive & Score Breakdown")
    candidate_options = [
        f"#{c.rank} - {c.candidate_name} (Final: {c.final_score:.2f} | KW: {c.keyword_score:.2f} | Sem: {c.semantic_score:.2f})"
        for c in ranking.candidates
    ]
    selected_option = st.selectbox(
        "Select candidate to inspect detailed evidence:",
        options=candidate_options,
        index=0,
    )

    selected_rank = int(selected_option.split()[0].replace("#", ""))
    selected_candidate = next((c for c in ranking.candidates if c.rank == selected_rank), ranking.candidates[0])

    # Candidate score card
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("⭐ Final Score", f"{selected_candidate.final_score:.2f} / 100")
    sc2.metric("🔑 Keyword Score", f"{selected_candidate.keyword_score:.2f} / 100")
    sc3.metric("🧠 Semantic Score", f"{selected_candidate.semantic_score:.2f} / 100")

    # Matched and missing skills breakdown
    col_req, col_pref = st.columns(2)
    with col_req:
        st.markdown("#### 🎯 Required Skills")
        if selected_candidate.matched_required_skills:
            st.markdown("**Matched:**")
            st.success(", ".join(selected_candidate.matched_required_skills))
        else:
            st.warning("None matched")

        if selected_candidate.missing_required_skills:
            st.markdown("**Missing:**")
            st.error(", ".join(selected_candidate.missing_required_skills))
        else:
            st.info("No missing required skills! 🎉")

    with col_pref:
        st.markdown("#### ⭐ Preferred Skills")
        if selected_candidate.matched_preferred_skills:
            st.markdown("**Matched:**")
            st.info(", ".join(selected_candidate.matched_preferred_skills))
        else:
            st.caption("No preferred skills matched")

        if selected_candidate.missing_preferred_skills:
            st.markdown("**Missing:**")
            st.caption(", ".join(selected_candidate.missing_preferred_skills))

    # Semantic Evidence Breakdown
    if selected_candidate.semantic_evidence:
        st.markdown("#### 🧬 Requirement-Level Semantic Evidence")
        st.caption(
            "Each JD requirement is embedded using sentence-transformers and matched against the candidate's "
            "most relevant project/experience chunk using cosine similarity."
        )

        for i, ev in enumerate(selected_candidate.semantic_evidence, start=1):
            with st.expander(
                f"**Requirement {i}:** {ev['requirement']} — **Similarity: {ev.get('similarity_score', round(ev['similarity']*100, 1))}%**",
                expanded=(i <= 3),
            ):
                st.markdown(f"**JD Requirement:** {ev['requirement']}")
                st.markdown(f"**Best Resume Evidence:** {ev['best_matching_evidence'] or '*(No matching text chunk)*'}")
                st.progress(
                    float(ev["similarity"]),
                    text=f"Cosine Similarity: {ev['similarity']:.4f} ({ev.get('similarity_score', round(ev['similarity']*100, 1))}%)",
                )


def run_pipeline(jd_file, resume_files: list) -> None:
    """Run the complete Phase 1-5 pipeline: parse → extract → match → score → rank → display."""
    if not jd_file or not resume_files:
        st.error("Please upload both a Job Description and at least one Resume.")
        return

    # --- Step 1: PDF Text Extraction ---
    st.header("Step 1: PDF Text Extraction")

    jd_text = None
    with st.spinner("Extracting JD text..."):
        try:
            jd_text = extract_text_from_uploaded_file(jd_file)
            st.success(f"✅ JD text extracted ({len(jd_text):,} characters)")
        except PDFParsingError as e:
            st.error(f"❌ JD parsing error: {e}")
            return
        except Exception as e:
            st.error(f"❌ Unexpected error reading JD: {e}")
            return

    resume_texts: dict[str, str] = {}
    progress = st.progress(0, text="Extracting resume text...")
    for i, resume_file in enumerate(resume_files):
        try:
            text = extract_text_from_uploaded_file(resume_file)
            # Handle duplicate filenames gracefully
            filename = resume_file.name
            if filename in resume_texts:
                filename = f"{filename}_{i+1}"
            resume_texts[filename] = text
        except PDFParsingError as e:
            st.warning(f"⚠️ Skipped '{resume_file.name}': {e}")
        except Exception as e:
            st.warning(f"⚠️ Error reading '{resume_file.name}': {e}")
        progress.progress(
            (i + 1) / len(resume_files),
            text=f"Extracted {i + 1}/{len(resume_files)} resumes...",
        )
    progress.empty()

    if not resume_texts:
        st.error("Could not extract text from any uploaded resume. Please verify the files.")
        return

    st.success(f"✅ Extracted text from {len(resume_texts)}/{len(resume_files)} resumes")
    st.divider()

    # --- Step 2: Deterministic Extraction ---
    st.header("Step 2: Deterministic Extraction (Rule-Based & NLP)")

    jd: JobDescription | None = None
    with st.spinner("⚙️ Extracting structured JD..."):
        try:
            jd = extract_jd(jd_text)
            jd.required_skills = normalize_skills(jd.required_skills)
            jd.preferred_skills = normalize_skills(jd.preferred_skills)
            st.success(f"✅ Extracted JD: '{jd.role_title or 'Job Description'}' ({len(jd.required_skills)} required skills)")
        except Exception as e:
            st.error(f"❌ JD extraction failed: {e}")
            logger.exception("JD extraction error")
            return

    resumes: dict[str, Resume] = {}
    progress = st.progress(0, text="Extracting structured resumes...")
    for i, (name, text) in enumerate(resume_texts.items()):
        try:
            resume = extract_resume(text, filename=name)
            resume.skills = normalize_skills(resume.skills)
            for proj in resume.projects:
                proj.technologies = normalize_skills(proj.technologies)
            resumes[name] = resume
        except Exception as e:
            st.warning(f"⚠️ Failed to extract '{name}': {e}")
            logger.exception("Resume extraction error for %s", name)
        progress.progress(
            (i + 1) / len(resume_texts),
            text=f"Parsed {i + 1}/{len(resume_texts)} resumes...",
        )
    progress.empty()
    st.success(f"✅ Structured extraction complete for {len(resumes)} candidates")
    st.divider()

    # --- Step 3: Hybrid Scoring & Ranking ---
    st.header("Step 3: Keyword & Semantic Scoring Engine")

    ranking: RankingResult | None = None
    with st.spinner("🚀 Scoring candidates across keyword and local semantic models..."):
        try:
            ranking = shortlist_candidates(jd, resumes)
            st.success("✅ Hybrid scoring and ranking complete!")
        except Exception as e:
            st.error(f"❌ Shortlisting pipeline failed: {e}")
            logger.exception("Shortlisting pipeline error")
            return

    # Store state
    st.session_state["jd"] = jd
    st.session_state["resumes"] = resumes
    st.session_state["ranking"] = ranking

    st.divider()

    # --- Step 4: Display Results ---
    display_ranking_results(ranking)

    st.divider()
    with st.expander("📄 View Extracted Job Description Details", expanded=False):
        display_jd(jd)

    with st.expander(f"📑 View All Extracted Candidate Data ({len(resumes)})", expanded=False):
        for name, resume in resumes.items():
            with st.expander(f"📝 {resume.candidate_name} ({name})", expanded=False):
                display_resume_details(resume)


def run_ui() -> None:
    """Main UI entry point."""
    setup_page()

    jd_file, resume_files = upload_section()

    st.divider()

    # Run button
    can_run = jd_file is not None and bool(resume_files)
    run_clicked = st.button(
        "🚀 RUN SHORTLIST",
        type="primary",
        disabled=not can_run,
        use_container_width=True,
    )

    if not can_run:
        st.info("Upload a JD PDF and candidate resume PDFs above to begin.")

    if run_clicked:
        run_pipeline(jd_file, resume_files)


if __name__ == "__main__":
    run_ui()
