"""
FastAPI application for the Agentic Developer Platform.

Provides REST API endpoints for:
- Full orchestration pipeline
- Individual agent/skill endpoints (for testing and watsonx Orchestrate)
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.orchestrator.orchestrator import run_orchestration, run_orchestration_continue
from app.models.schemas import (
    RequirementsOutput,
    DatabaseDesignOutput,
    ReviewOutput,
    GitStrategyOutput,
    OrchestrationResult,
    ValidationResult,
    ApprovalSubmitRequest,
    ApprovalSubmitResponse,
)
from app.utils.approval_store import submit_approval

# Import agents for individual endpoints
from app.agents.requirements_agent import interpret_requirements
from app.agents.db_architect_agent import design_database
from app.agents.review_agent import review_database_design
from app.agents.git_agent import propose_git_strategy

# Import skills
from app.skills.validation_skill import validate_db_design
from app.skills.github_push_skill import push_repo_structure_to_github

app = FastAPI(
    title="Agentic Developer Platform",
    description="AI-powered platform to streamline development setup using IBM watsonx.ai",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# =============================================================================
# REQUEST MODELS
# =============================================================================

class OrchestrateRequest(BaseModel):
    """Request model for the orchestration endpoint."""
    prompt: str
    language: Optional[str] = "python"


class OrchestrateContinueRequest(BaseModel):
    """Request model for continuing after human approval."""
    approval_token: str
    language: Optional[str] = None


class GitPushRequest(BaseModel):
    """Request to push proposed repo structure to GitHub."""
    github_token: str = Field(description="GitHub Personal Access Token (repo scope)")
    repo_full_name: str = Field(description="Repository as owner/name (e.g. myorg/my-repo)")
    branch_name: str = Field(description="Branch to create (e.g. feature/db-schema)")
    base_branch: str = Field(default="main", description="Base branch to create from")
    files: list[dict] = Field(description="List of {path: str, content: str}")
    create_repo_if_not_exists: bool = Field(default=True, description="Create repo if it doesn't exist")
    repo_private: bool = Field(default=True, description="If creating repo, make it private")


class RequirementsRequest(BaseModel):
    """Request model for requirements extraction."""
    prompt: str


class DatabaseDesignRequest(BaseModel):
    """Request model for database design."""
    requirements: dict


class ReviewRequest(BaseModel):
    """Request model for database review."""
    db_design: dict


class GitStrategyRequest(BaseModel):
    """Request model for git strategy."""
    project_type: str = "backend"
    framework: str = "fastapi"
    language: Optional[str] = "python"
    description: Optional[str] = None


class ValidationRequest(BaseModel):
    """Request model for validation."""
    db_design: dict


# =============================================================================
# MAIN ORCHESTRATION ENDPOINT
# =============================================================================

@app.post(
    "/orchestrate",
    response_model=OrchestrationResult,
    summary="Run full orchestration pipeline",
    description="Runs the pipeline. If review requires approval, returns PENDING_APPROVAL with approval_token. Submit approval via POST /approval, then call POST /orchestrate/continue."
)
def orchestrate(req: OrchestrateRequest) -> OrchestrationResult:
    """
    Execute the orchestration pipeline.
    
    - If review.approval_required: returns status=PENDING_APPROVAL and approval_token.
    - Client then: 1) POST /approval with { approval_token, approved, comments? }
                   2) POST /orchestrate/continue with { approval_token, language? }
    - language: used for repo structure and generated files (e.g. python, node, java).
    """
    try:
        return run_orchestration(req.prompt, language=req.language or "python")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/approval",
    response_model=ApprovalSubmitResponse,
    summary="Submit human approval or rejection",
    description="Call this when orchestration returned PENDING_APPROVAL. Then call POST /orchestrate/continue with the same approval_token."
)
def submit_approval_endpoint(req: ApprovalSubmitRequest) -> ApprovalSubmitResponse:
    """
    Record human's approval or rejection for a pending orchestration.
    
    After submitting, call POST /orchestrate/continue with the same approval_token
    to complete the pipeline (or get HALTED if rejected).
    """
    success, message = submit_approval(
        approval_token=req.approval_token,
        approved=req.approved,
        comments=req.comments,
        approved_by=req.approved_by,
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return ApprovalSubmitResponse(
        success=True,
        message=message,
        approval_token=req.approval_token,
    )


@app.post(
    "/orchestrate/continue",
    response_model=OrchestrationResult,
    summary="Continue after human approval",
    description="Call after POST /approval. Uses stored decision: if approved, runs Git strategy (with language) and returns SUCCESS; if rejected, returns HALTED."
)
def orchestrate_continue(req: OrchestrateContinueRequest) -> OrchestrationResult:
    """
    Continue the pipeline after human has submitted approval.
    
    Requires that POST /approval was already called with the same approval_token.
    Optional language overrides the one from the initial /orchestrate call for repo structure.
    """
    try:
        return run_orchestration_continue(
            approval_token=req.approval_token,
            language=req.language,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/git/push",
    summary="Push proposed repo structure to GitHub",
    description="Creates the repo (if needed), creates the branch, and pushes all generated files. "
                "For watsonx Orchestrate: host this app and call with github_token + git strategy payload.",
    tags=["Git"],
)
def git_push(req: GitPushRequest) -> dict:
    """
    Push the proposed repository structure (branch + files) to GitHub.

    Requires a GitHub Personal Access Token with `repo` scope.
    If repo doesn't exist, creates it (if create_repo_if_not_exists=true).
    If repo is empty (no branches), creates the branch with the first file.
    """
    result = push_repo_structure_to_github(
        github_token=req.github_token,
        repo_full_name=req.repo_full_name,
        branch_name=req.branch_name,
        base_branch=req.base_branch,
        files=req.files,
        create_repo_if_not_exists=req.create_repo_if_not_exists,
        repo_private=req.repo_private,
    )
    if not result.get("success") and result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# =============================================================================
# INDIVIDUAL AGENT ENDPOINTS (for testing & watsonx Orchestrate)
# =============================================================================

@app.post(
    "/agents/requirements",
    response_model=RequirementsOutput,
    summary="Extract requirements from prompt",
    tags=["Agents"]
)
def extract_requirements(req: RequirementsRequest) -> RequirementsOutput:
    """
    Extract structured requirements from a natural language prompt.
    
    Returns entities, relationships, assumptions, and out-of-scope items.
    """
    try:
        return interpret_requirements(req.prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/agents/database-design",
    response_model=DatabaseDesignOutput,
    summary="Design database schema",
    tags=["Agents"]
)
def design_db(req: DatabaseDesignRequest) -> DatabaseDesignOutput:
    """
    Design a database schema based on requirements.
    
    Returns tables, columns, normalization level, and SQL schema.
    """
    try:
        return design_database(req.requirements)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/agents/review",
    response_model=ReviewOutput,
    summary="Review database design",
    tags=["Agents"]
)
def review_design(req: ReviewRequest) -> ReviewOutput:
    """
    Review a database design for risks and governance requirements.
    
    Returns assessment, issues, risk level, and approval requirement.
    """
    try:
        return review_database_design(req.db_design)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/agents/git-strategy",
    response_model=GitStrategyOutput,
    summary="Propose Git strategy",
    tags=["Agents"]
)
def git_strategy(req: GitStrategyRequest) -> GitStrategyOutput:
    """
    Propose a Git branching strategy and repository structure.
    
    Returns branch name, base branch, repository structure, and action.
    """
    try:
        context = {
            "type": req.project_type,
            "framework": req.framework,
            "language": req.language or "python",
        }
        if req.description:
            context["description"] = req.description
        return propose_git_strategy(context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SKILL ENDPOINTS (deterministic, for watsonx Orchestrate)
# =============================================================================

@app.post(
    "/skills/validate",
    response_model=ValidationResult,
    summary="Validate database design",
    tags=["Skills"]
)
def validate_design(req: ValidationRequest) -> ValidationResult:
    """
    Validate a database design structure.
    
    This is a deterministic skill (no LLM) that checks for required fields.
    """
    result = validate_db_design(req.db_design)
    return ValidationResult(**result)


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health", summary="Health check")
def health_check():
    """Check if the service is running."""
    return {"status": "healthy", "service": "agentic-dev-platform"}
