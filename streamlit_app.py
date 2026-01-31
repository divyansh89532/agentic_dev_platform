"""
Streamlit UI for the Agentic Developer Platform

Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import json
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.orchestrator.orchestrator import run_orchestration, run_orchestration_continue
from app.utils.approval_store import submit_approval
from app.skills.github_push_skill import push_repo_structure_to_github
from app.models.schemas import (
    OrchestrationResult,
    RequirementsOutput,
    DatabaseDesignOutput,
    ReviewOutput,
    GitStrategyOutput,
)


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Agentic Developer Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a cleaner look
st.markdown("""
<style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header { color: #666; margin-bottom: 2rem; }
    .stage-card {
        padding: 1rem 1.25rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        background: #f8f9fa;
        margin-bottom: 1rem;
    }
    .status-success { color: #28a745; font-weight: 600; }
    .status-failed { color: #dc3545; font-weight: 600; }
    .status-halted { color: #ffc107; font-weight: 600; }
    .status-pending { color: #17a2b8; font-weight: 600; }
    .entity-badge { display: inline-block; padding: 0.25rem 0.5rem; margin: 0.2rem; background: #e3f2fd; border-radius: 4px; font-size: 0.9rem; }
    div[data-testid="stExpander"] { border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown("## 🧠 Agentic Dev Platform")
    st.markdown("---")
    st.markdown("""
    **Pipeline:**
    1. 📘 Requirements
    2. 🗄️ Database design
    3. ✅ Validation
    4. 🔎 Review
    5. 🧑‍⚖️ Approval
    6. 🌿 Git strategy
    7. 📂 Git (simulated)
    """)
    st.markdown("---")
    st.markdown("**Powered by:** IBM watsonx.ai + LangChain")
    st.markdown("---")
    
    # Quick prompts
    st.markdown("### Quick prompts")
    if st.button("SaaS users & orgs", use_container_width=True):
        st.session_state.quick_prompt = "Set up backend for a SaaS app with users, organizations, and roles"
        st.rerun()
    if st.button("Blog with posts", use_container_width=True):
        st.session_state.quick_prompt = "Build a simple blog with users, posts, and comments"
        st.rerun()
    if st.button("E-commerce products", use_container_width=True):
        st.session_state.quick_prompt = "E-commerce backend: products, categories, orders, and customers"
        st.rerun()
    st.markdown("---")
    st.markdown("### 🔐 GitHub (optional)")
    st.markdown("To **push** the proposed repo to GitHub, set:")
    gh_token = st.text_input(
        "GitHub token (PAT)",
        type="password",
        placeholder="ghp_...",
        help="Personal Access Token with repo scope. Not stored.",
        key="sidebar_gh_token",
    )
    if gh_token:
        st.session_state.github_token = gh_token
    else:
        st.session_state.pop("github_token", None)
    gh_repo = st.text_input(
        "Repo (owner/name)",
        placeholder="myorg/my-repo",
        help="If repo doesn't exist, will be created.",
        key="sidebar_gh_repo",
    )
    if gh_repo:
        st.session_state.github_repo = gh_repo.strip()
    else:
        st.session_state.pop("github_repo", None)
    create_if_not_exists = st.checkbox(
        "Create repo if it doesn't exist",
        value=True,
        help="If checked, creates the repo when not found.",
        key="sidebar_create_repo",
    )
    st.session_state.create_repo_if_not_exists = create_if_not_exists


# =============================================================================
# HELPERS
# =============================================================================

def pydantic_to_dict(obj):
    """Convert Pydantic model to dict for display."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "model_dump_json"):
        return json.loads(obj.model_dump_json())
    return obj


def render_requirements(req: RequirementsOutput | None):
    if req is None:
        return
    st.markdown("#### Entities")
    for e in req.entities:
        st.markdown(f'- **{e.name}**: {e.description}')
    st.markdown("#### Relationships")
    for r in req.relationships:
        through = f" (via {r.through})" if r.through else ""
        st.markdown(f'- {r.from_entity} → {r.to}: **{r.type}**{through}')
    st.markdown("#### Assumptions")
    for a in req.assumptions:
        st.markdown(f'- {a}')
    st.markdown("#### Out of scope")
    for o in req.out_of_scope:
        st.markdown(f'- {o}')


def render_db_design(db: DatabaseDesignOutput | None):
    if db is None:
        return
    st.markdown(f"**Normalization:** {db.normalization_level}")
    st.markdown("#### Tables")
    for t in db.tables:
        with st.expander(f"📋 {t.name}"):
            for c in t.columns:
                constraints = ", ".join(c.constraints) if c.constraints else "—"
                st.markdown(f"- `{c.name}` **{c.type}** — {constraints}")
    st.markdown("#### Design rationale")
    for r in db.design_rationale:
        st.markdown(f'- {r}')
    st.markdown("#### SQL schema")
    st.code(db.sql_schema, language="sql")


def render_review(review: ReviewOutput | None):
    if review is None:
        return
    risk_color = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}
    st.markdown(f"**Risk level:** :{risk_color.get(review.risk_level, 'gray')}[{review.risk_level}]")
    st.markdown(f"**Approval required:** {'Yes' if review.approval_required else 'No'}")
    st.markdown(f"**Assessment:** {review.assessment}")
    if review.issues:
        st.markdown("**Issues:**")
        for i in review.issues:
            st.markdown(f'- {i}')


def render_git(git_dict: dict | None):
    if git_dict is None:
        return
    strategy = git_dict.get("strategy", {})
    execution = git_dict.get("execution", {})
    st.markdown(f"**Branch:** `{strategy.get('branch_name', '—')}` (from `{strategy.get('base_branch', 'main')}`)")
    st.markdown(f"**Action:** {strategy.get('action', '—')}")
    st.markdown("**Repository structure:**")
    for path in strategy.get("repository_structure", []):
        st.markdown(f'- `{path}`')
    files = strategy.get("files", [])
    if files:
        st.markdown("**Generated files:**")
        for f in files:
            path = f.get("path", "?")
            content = f.get("content", "")
            ext = path.split(".")[-1] if "." in path else "text"
            lang = "python" if ext == "py" else "json" if ext in ("json", "jsonc") else "text"
            if path.endswith(".md"):
                lang = "markdown"
            with st.expander(f"📄 {path}"):
                st.code(content, language=lang)
    st.markdown("**Execution:**")
    st.json(execution)


# =============================================================================
# MAIN UI
# =============================================================================

st.markdown('<p class="main-header">Agentic Developer Platform</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Describe what you want to build — get requirements, DB schema, review, and Git strategy in one run.</p>', unsafe_allow_html=True)

# Prompt input
default_prompt = getattr(st.session_state, "quick_prompt", "")
user_prompt = st.text_area(
    "What do you want to build?",
    value=default_prompt,
    height=100,
    placeholder="e.g. Set up backend for a SaaS app with users, organizations, and roles. Include membership with roles."
)

# Language for repo structure and generated files
language = st.selectbox(
    "Repo language (for Git structure & generated files)",
    options=["python", "node", "java", "go"],
    index=0,
    help="Used when generating branch name, folder structure, and basic files (README, .gitignore, main file)."
)

col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    run_button = st.button("🚀 Run orchestration", type="primary", use_container_width=True)
with col2:
    show_json = st.checkbox("Show raw JSON", value=False)

st.markdown("---")

# Clear pending/continue state when starting a new run
if run_button and user_prompt.strip():
    st.session_state.pop("continue_result", None)
    st.session_state.pop("pending_result", None)
    st.session_state.pop("pending_approval_token", None)
    st.session_state.pop("pending_approval_language", None)
    st.session_state.pop("approval_error", None)

# Run orchestration
if run_button and user_prompt.strip():
    progress_placeholder = st.empty()
    result_placeholder = st.empty()
    
    with progress_placeholder.container():
        st.markdown("### Running pipeline...")
        progress = st.progress(0, text="Starting...")
        
        steps = [
            "Extracting requirements...",
            "Designing database schema...",
            "Validating schema...",
            "Reviewing design...",
            "Checking approval...",
            "Proposing Git strategy...",
            "Simulating Git...",
            "Done!"
        ]
        
        try:
            progress.progress(10, text=steps[0])
            result: OrchestrationResult = run_orchestration(user_prompt.strip(), language=language)
            progress.progress(100, text=steps[-1])
        except Exception as e:
            progress.progress(100, text="Error")
            st.error(f"Orchestration failed: {str(e)}")
            st.exception(e)
            result = None
    
    progress_placeholder.empty()
    
    if result is not None:
        with result_placeholder.container():
            # Status banner
            status_class = {
                "SUCCESS": "status-success",
                "FAILED": "status-failed",
                "HALTED": "status-halted",
                "PENDING_APPROVAL": "status-pending",
            }.get(result.status, "")
            st.markdown(f"### Status: <span class='{status_class}'>{result.status}</span>", unsafe_allow_html=True)
            
            if result.status == "PENDING_APPROVAL" and result.approval_token:
                st.session_state.pending_approval_token = result.approval_token
                st.session_state.pending_approval_language = language
                st.session_state.pending_result = result  # keep result for display
            elif result.status != "PENDING_APPROVAL" and "pending_approval_token" in st.session_state:
                # Clear pending state once we have final result
                st.session_state.pop("pending_approval_token", None)
                st.session_state.pop("pending_approval_language", None)
                st.session_state.pop("pending_result", None)
            
            if result.stage:
                st.info(f"Stopped at stage: **{result.stage}**")
            if result.issues:
                st.error("**Issues:**")
                for issue in result.issues:
                    st.markdown(f"- {issue}")
            
            # Human approval form when PENDING_APPROVAL
            if result.status == "PENDING_APPROVAL" and result.approval_token:
                if st.session_state.get("approval_error"):
                    st.error(st.session_state["approval_error"])
                st.markdown("---")
                st.markdown("#### 🧑‍⚖️ Human approval required")
                st.markdown("Review the **Database design** and **Review** tabs above, then approve or reject below.")
                appr_col1, appr_col2 = st.columns(2)
                with appr_col1:
                    approved = st.radio("Decision", ["Approve", "Reject"], horizontal=True) == "Approve"
                with appr_col2:
                    comments = st.text_input("Comments (optional)", placeholder="e.g. Looks good / Please add index on email")
                if st.button("Submit decision and continue", type="primary"):
                    try:
                        submit_approval(
                            approval_token=result.approval_token,
                            approved=approved,
                            comments=comments.strip() or None,
                            approved_by="streamlit-user",
                        )
                        cont_result = run_orchestration_continue(
                            result.approval_token,
                            language=st.session_state.get("pending_approval_language", "python"),
                        )
                        st.session_state.continue_result = cont_result
                        st.session_state.pop("approval_error", None)
                        st.rerun()
                    except Exception as e:
                        st.session_state.approval_error = str(e)
                        st.error(f"Failed to continue pipeline: {e}")
                        st.exception(e)
            
            st.markdown("---")
            
            # Stage results in tabs
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📘 Requirements",
                "🗄️ Database design",
                "🔎 Review",
                "🌿 Git",
                "📄 Raw result"
            ])
            
            with tab1:
                if result.requirements:
                    render_requirements(result.requirements)
                    if show_json:
                        st.markdown("---")
                        st.json(pydantic_to_dict(result.requirements))
                else:
                    st.info("No requirements (pipeline did not reach this stage).")
            
            with tab2:
                if result.database_design:
                    render_db_design(result.database_design)
                    if show_json:
                        st.markdown("---")
                        st.json(pydantic_to_dict(result.database_design))
                else:
                    st.info("No database design (pipeline did not reach this stage).")
            
            with tab3:
                if result.review:
                    render_review(result.review)
                    if result.approval:
                        st.markdown("---")
                        st.markdown("**Approval:**")
                        st.markdown(f"- Approved: **{result.approval.approved}**")
                        if result.approval.comments:
                            st.markdown(f"- Comments: {result.approval.comments}")
                    if show_json:
                        st.markdown("---")
                        st.json(pydantic_to_dict(result.review))
                else:
                    st.info("No review (pipeline did not reach this stage).")
            
            with tab4:
                if result.git:
                    render_git(result.git)
                    if show_json:
                        st.markdown("---")
                        st.json(result.git)
                else:
                    st.info("No Git strategy (pipeline did not reach this stage).")
            
            with tab5:
                # Full result as JSON (convert Pydantic models)
                full_dict = {
                    "status": result.status,
                    "stage": result.stage,
                    "issues": result.issues,
                    "requirements": pydantic_to_dict(result.requirements),
                    "database_design": pydantic_to_dict(result.database_design),
                    "review": pydantic_to_dict(result.review),
                    "approval": pydantic_to_dict(result.approval),
                    "git": result.git,
                }
                st.json(full_dict)

elif run_button and not user_prompt.strip():
    st.warning("Please enter a description of what you want to build.")

# Pending approval: show same UI from session so "Submit decision and continue" runs on next click
# (When user clicks that button, Streamlit reruns with run_button=False; this branch ensures we still show the form.)
elif st.session_state.get("pending_result"):
    result = st.session_state.pending_result
    st.markdown(f"### Status: <span class='status-pending'>PENDING_APPROVAL</span>", unsafe_allow_html=True)
    st.info("Human approval required. Review below and submit your decision.")
    if st.session_state.get("approval_error"):
        st.error(st.session_state["approval_error"])
    st.markdown("---")
    st.markdown("#### 🧑‍⚖️ Human approval required")
    st.markdown("Review the **Database design** and **Review** tabs below, then approve or reject.")
    appr_col1, appr_col2 = st.columns(2)
    with appr_col1:
        approved = st.radio("Decision", ["Approve", "Reject"], horizontal=True, key="approval_radio") == "Approve"
    with appr_col2:
        comments = st.text_input("Comments (optional)", placeholder="e.g. Looks good", key="approval_comments")
    if st.button("Submit decision and continue", type="primary", key="approval_submit"):
        try:
            submit_approval(
                approval_token=result.approval_token,
                approved=approved,
                comments=comments.strip() or None,
                approved_by="streamlit-user",
            )
            with st.spinner("Running Git strategy and generating repo structure..."):
                cont_result = run_orchestration_continue(
                    result.approval_token,
                    language=st.session_state.get("pending_approval_language", "python"),
                )
            st.session_state.continue_result = cont_result
            st.session_state.pop("pending_result", None)
            st.session_state.pop("pending_approval_token", None)
            st.session_state.pop("pending_approval_language", None)
            st.session_state.pop("approval_error", None)
            st.rerun()
        except Exception as e:
            st.session_state.approval_error = str(e)
            st.error(f"Failed to continue pipeline: {e}")
            st.exception(e)
    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📘 Requirements", "🗄️ Database design", "🔎 Review", "🌿 Git", "📄 Raw result"])
    with tab1:
        if result.requirements:
            render_requirements(result.requirements)
        else:
            st.info("No requirements.")
    with tab2:
        if result.database_design:
            render_db_design(result.database_design)
        else:
            st.info("No database design.")
    with tab3:
        if result.review:
            render_review(result.review)
        else:
            st.info("No review.")
    with tab4:
        st.info("Git strategy will appear after you approve and continue.")
    with tab5:
        full_dict = {
            "status": result.status,
            "stage": result.stage,
            "approval_token": result.approval_token,
            "requirements": pydantic_to_dict(result.requirements),
            "database_design": pydantic_to_dict(result.database_design),
            "review": pydantic_to_dict(result.review),
        }
        st.json(full_dict)

# Show result from "continue after approval" (kept until user runs again or clicks Start over)
elif st.session_state.get("continue_result"):
    cr = st.session_state.continue_result
    st.success("Approval recorded. Pipeline continued. Git strategy and repo structure are below.")
    if st.button("↩️ Start over", help="Clear this result and return to the prompt"):
        st.session_state.pop("continue_result", None)
        st.session_state.pop("git_push_result", None)
        st.rerun()
    status_class = {"SUCCESS": "status-success", "HALTED": "status-halted", "FAILED": "status-failed"}.get(cr.status, "")
    st.markdown(f"### Status: <span class='{status_class}'>{cr.status}</span>", unsafe_allow_html=True)
    if cr.issues:
        st.error("**Issues:**")
        for issue in cr.issues:
            st.markdown(f"- {issue}")
    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📘 Requirements", "🗄️ Database design", "🔎 Review", "🌿 Git", "📄 Raw result"])
    with tab1:
        if cr.requirements:
            render_requirements(cr.requirements)
        else:
            st.info("No requirements in this result.")
    with tab2:
        if cr.database_design:
            render_db_design(cr.database_design)
        else:
            st.info("No database design in this result.")
    with tab3:
        if cr.review:
            render_review(cr.review)
        if cr.approval:
            st.markdown("**Approval:**")
            st.markdown(f"- Approved: **{cr.approval.approved}**")
            if cr.approval.comments:
                st.markdown(f"- Comments: {cr.approval.comments}")
        else:
            st.info("No review in this result.")
    with tab4:
        if cr.git:
            render_git(cr.git)
            # Push to GitHub section (only when we have git strategy with files)
            strategy = cr.git.get("strategy", {})
            files = strategy.get("files", [])
            branch_name = strategy.get("branch_name", "")
            base_branch = strategy.get("base_branch", "main")
            if files and branch_name:
                st.markdown("---")
                st.markdown("#### 📤 Push to GitHub")
                st.caption("Set your GitHub token and repo in the sidebar. Will create repo if it doesn't exist.")
                push_repo = st.text_input(
                    "Repository (owner/name)",
                    value=st.session_state.get("github_repo", ""),
                    placeholder="myorg/my-repo",
                    key="push_gh_repo",
                )
                push_token = st.session_state.get("github_token", "")
                if st.button("Push to GitHub", type="primary", key="push_gh_btn"):
                    if not push_token:
                        st.error("Set your GitHub token in the sidebar first.")
                    elif not push_repo or "/" not in push_repo:
                        st.error("Enter a valid repo as owner/name (e.g. myorg/my-repo).")
                    else:
                        with st.spinner("Creating branch and pushing files..."):
                            push_result = push_repo_structure_to_github(
                                github_token=push_token,
                                repo_full_name=push_repo.strip(),
                                branch_name=branch_name,
                                base_branch=base_branch,
                                files=[{"path": f.get("path", ""), "content": f.get("content", "")} for f in files],
                                create_repo_if_not_exists=st.session_state.get("create_repo_if_not_exists", True),
                                repo_private=True,
                            )
                            st.session_state.git_push_result = push_result
                        st.rerun()
                if st.session_state.get("git_push_result"):
                    pr = st.session_state.git_push_result
                    if pr.get("success"):
                        st.success(f"Pushed to GitHub: {pr.get('files_count', 0)} files on branch `{branch_name}`.")
                        st.markdown(f"**URL:** [{pr.get('url', '')}]({pr.get('url', '')})")
                        st.json({k: v for k, v in pr.items() if k != "error"})
                    else:
                        st.error(pr.get("error", "Push failed."))
        else:
            st.info("No Git strategy (rejected or not reached).")
    with tab5:
        full_dict = {
            "status": cr.status,
            "stage": cr.stage,
            "issues": cr.issues,
            "requirements": pydantic_to_dict(cr.requirements),
            "database_design": pydantic_to_dict(cr.database_design),
            "review": pydantic_to_dict(cr.review),
            "approval": pydantic_to_dict(cr.approval),
            "git": cr.git,
        }
        st.json(full_dict)

else:
    st.info("👆 Enter a prompt above and click **Run orchestration** to see the pipeline in action. Use the sidebar for quick prompts.")
