"""Streamlit UI for the Smart Shortlisting Engine.

Phase 2: Upload PDFs → extract text → LLM extraction → structured display.
"""

import logging

import streamlit as st

from app.parsers.pdf_parser import extract_text_from_uploaded_file, PDFParsingError
from app.llm.jd_extractor import extract_jd
from app.llm.resume_extractor import extract_resume
from app.matching.skill_normalizer import normalize_skills
from app.models.jd_models import JobDescription
from app.models.resume_models import Resume

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
        "Upload a **Job Description** and **Candidate Resumes** to find the best matches."
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
            help="Upload 15-18 candidate resume PDFs.",
        )

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


def display_resume(resume: Resume) -> None:
    """Display structured resume extraction results inside an expander."""
    cols = st.columns([1, 1])
    with cols[0]:
        if resume.skills:
            st.markdown("**Skills:**")
            st.markdown(", ".join(resume.skills))
        if resume.contact.email:
            st.markdown(f"**Email:** {resume.contact.email}")
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


def run_pipeline(jd_file, resume_files: list) -> None:
    """Run the Phase 2 pipeline: parse → extract → normalize → display."""
    # --- Step 1: PDF Text Extraction ---
    st.header("Step 1: PDF Text Extraction")

    jd_text = None
    if jd_file is not None:
        with st.spinner("Extracting JD text..."):
            try:
                jd_text = extract_text_from_uploaded_file(jd_file)
                st.success(f"✅ JD text extracted — {len(jd_text):,} characters")
            except PDFParsingError as e:
                st.error(f"❌ JD extraction failed: {e}")
                return
            except Exception as e:
                st.error(f"❌ Unexpected error reading JD: {e}")
                return

    resume_texts: dict[str, str] = {}
    if resume_files:
        progress = st.progress(0, text="Extracting resume text...")
        for i, resume_file in enumerate(resume_files):
            try:
                text = extract_text_from_uploaded_file(resume_file)
                resume_texts[resume_file.name] = text
            except PDFParsingError as e:
                st.warning(f"⚠️ Skipped '{resume_file.name}': {e}")
            except Exception as e:
                st.warning(f"⚠️ Error reading '{resume_file.name}': {e}")
            progress.progress(
                (i + 1) / len(resume_files),
                text=f"Extracted {i + 1}/{len(resume_files)} resumes...",
            )
        progress.empty()
        st.success(f"✅ Extracted text from {len(resume_texts)}/{len(resume_files)} resumes")

    if not jd_text or not resume_texts:
        st.error("Need both JD and at least one resume to continue.")
        return

    st.divider()

    # --- Step 2: LLM Structured Extraction ---
    st.header("Step 2: LLM Structured Extraction")

    # JD extraction
    jd: JobDescription | None = None
    with st.spinner("🤖 Extracting structured JD via Gemini..."):
        try:
            jd = extract_jd(jd_text)
            # Normalize JD skills
            jd.required_skills = normalize_skills(jd.required_skills)
            jd.preferred_skills = normalize_skills(jd.preferred_skills)
            st.success("✅ JD structured extraction complete")
        except Exception as e:
            st.error(f"❌ JD extraction failed: {e}")
            logger.exception("JD extraction error")
            return

    # Resume extraction
    resumes: dict[str, Resume] = {}
    progress = st.progress(0, text="Extracting structured resumes via Gemini...")
    for i, (name, text) in enumerate(resume_texts.items()):
        with st.spinner(f"🤖 Extracting {name}..."):
            try:
                resume = extract_resume(text)
                # Normalize resume skills
                resume.skills = normalize_skills(resume.skills)
                # Also normalize project technologies
                for proj in resume.projects:
                    proj.technologies = normalize_skills(proj.technologies)
                resumes[name] = resume
            except Exception as e:
                st.warning(f"⚠️ Failed to extract '{name}': {e}")
                logger.exception("Resume extraction error for %s", name)
        progress.progress(
            (i + 1) / len(resume_texts),
            text=f"Extracted {i + 1}/{len(resume_texts)} resumes...",
        )
    progress.empty()
    st.success(f"✅ Extracted {len(resumes)}/{len(resume_texts)} resumes")

    # Store in session state for future phases
    st.session_state["jd"] = jd
    st.session_state["resumes"] = resumes

    st.divider()

    # --- Step 3: Display Results ---
    st.header("Step 3: Extraction Results")

    display_jd(jd)

    st.divider()
    st.subheader(f"📑 Extracted Resumes ({len(resumes)} candidates)")
    for name, resume in resumes.items():
        with st.expander(f"📝 {resume.candidate_name} ({name})", expanded=False):
            display_resume(resume)


def run_ui() -> None:
    """Main UI entry point."""
    setup_page()

    jd_file, resume_files = upload_section()

    st.divider()

    # Run button
    can_run = jd_file is not None and len(resume_files) > 0
    run_clicked = st.button(
        "🚀 RUN SHORTLIST",
        type="primary",
        disabled=not can_run,
        use_container_width=True,
    )

    if not can_run:
        st.info("Upload a JD and at least one resume to begin.")

    if run_clicked:
        run_pipeline(jd_file, resume_files)


if __name__ == "__main__":
    run_ui()
