"""
Orchestrator for the Agentic Developer Platform

Coordinates the flow of:
1. Requirements extraction
2. Database schema design
3. Validation
4. Review & governance
5. Human approval (if needed) -> returns PENDING_APPROVAL + token; human calls POST /approval then POST /orchestrate/continue
6. Git strategy proposal (with language; includes repo files)
7. Git execution (simulated)
"""

from app.agents.requirements_agent import interpret_requirements
from app.agents.db_architect_agent import design_database
from app.agents.review_agent import review_database_design
from app.agents.git_agent import propose_git_strategy

from app.skills.validation_skill import validate_db_design
from app.skills.github_skill import create_branch

from app.utils.approval_store import (
    create_pending_approval,
    get_pending_state,
    get_approval_decision,
    consume_pending_state,
)

from app.models.schemas import (
    RequirementsOutput,
    DatabaseDesignOutput,
    ReviewOutput,
    GitStrategyOutput,
    OrchestrationResult,
    ApprovalResponse,
)


def run_orchestration(
    user_prompt: str,
    language: str | None = "python",
) -> OrchestrationResult:
    """
    Runs the orchestration pipeline until completion or until human approval is needed.

    If review.approval_required is True, saves state and returns status=PENDING_APPROVAL
    with approval_token. The client must:
    1. POST /approval with { approval_token, approved, comments? }
    2. POST /orchestrate/continue with { approval_token, language? }

    Args:
        user_prompt: Natural language description of what the user wants to build.
        language: Language/framework for repo structure (e.g. "python", "node", "java"). Used when continuing after approval.

    Returns:
        OrchestrationResult: SUCCESS, FAILED, HALTED, or PENDING_APPROVAL (with approval_token).
    """
    print("\n🧠 ORCHESTRATION STARTED\n")

    # 1️⃣ Requirements Agent
    try:
        requirements: RequirementsOutput = interpret_requirements(user_prompt)
        print("✅ Requirements captured")
    except Exception as e:
        return OrchestrationResult(
            status="FAILED",
            stage="requirements",
            issues=[f"Failed to interpret requirements: {str(e)}"],
        )

    # 2️⃣ Database Architect Agent
    try:
        db_design: DatabaseDesignOutput = design_database(requirements)
        print("✅ Database designed")
    except Exception as e:
        return OrchestrationResult(
            status="FAILED",
            stage="database_design",
            requirements=requirements,
            issues=[f"Failed to design database: {str(e)}"],
        )

    # 3️⃣ Validation Skill (deterministic)
    validation_result = validate_db_design(db_design.model_dump())
    if not validation_result["is_valid"]:
        return OrchestrationResult(
            status="FAILED",
            stage="validation",
            requirements=requirements,
            database_design=db_design,
            issues=validation_result["issues"],
        )
    print("✅ Validation passed")

    # 4️⃣ Review & Governance Agent (LLM)
    try:
        review: ReviewOutput = review_database_design(db_design)
        print("🔎 Review completed")
    except Exception as e:
        return OrchestrationResult(
            status="FAILED",
            stage="review",
            requirements=requirements,
            database_design=db_design,
            issues=[f"Failed to review design: {str(e)}"],
        )

    # 5️⃣ Human approval (API-driven)
    if review.approval_required:
        approval_token = create_pending_approval(
            user_prompt=user_prompt,
            requirements=requirements.model_dump(),
            database_design=db_design.model_dump(),
            review=review.model_dump(),
            language=language,
        )
        print("⏸️ Pending human approval — use approval_token with POST /approval then POST /orchestrate/continue")
        return OrchestrationResult(
            status="PENDING_APPROVAL",
            stage="approval",
            approval_token=approval_token,
            requirements=requirements,
            database_design=db_design,
            review=review,
        )

    # No approval needed — continue to Git
    return _run_git_and_finish(
        requirements=requirements,
        db_design=db_design,
        review=review,
        approval=None,
        language=language,
    )


def run_orchestration_continue(
    approval_token: str,
    language: str | None = "python",
) -> OrchestrationResult:
    """
    Continues orchestration after human approval. Call this after POST /approval.

    Loads pending state by approval_token, checks approval decision:
    - If rejected -> returns HALTED with review/design for reference.
    - If approved -> runs Git strategy (with language) and simulated Git, returns SUCCESS.

    Args:
        approval_token: Token returned when status was PENDING_APPROVAL.
        language: Language for repo structure (e.g. "python", "node", "java"). Overrides stored value if provided.

    Returns:
        OrchestrationResult: SUCCESS (with git) or HALTED (rejected).
    """
    state = get_pending_state(approval_token)
    if not state:
        return OrchestrationResult(
            status="FAILED",
            stage="approval",
            issues=["Invalid or expired approval token"],
        )

    decision = get_approval_decision(approval_token)
    if not decision:
        return OrchestrationResult(
            status="FAILED",
            stage="approval",
            issues=["No approval decision recorded. Call POST /approval first."],
        )

    # Rehydrate models from stored dicts
    requirements = RequirementsOutput.model_validate(state.requirements)
    db_design = DatabaseDesignOutput.model_validate(state.database_design)
    review = ReviewOutput.model_validate(state.review)
    approval = ApprovalResponse(
        approved=decision.approved,
        comments=decision.comments,
        approved_by=decision.approved_by,
    )

    if not decision.approved:
        consume_pending_state(approval_token)
        return OrchestrationResult(
            status="HALTED",
            stage="approval",
            requirements=requirements,
            database_design=db_design,
            review=review,
            approval=approval,
            issues=["Design rejected by reviewer"],
        )

    # Approved — run Git strategy and finish
    lang = language or state.language or "python"
    result = _run_git_and_finish(
        requirements=requirements,
        db_design=db_design,
        review=review,
        approval=approval,
        language=lang,
    )
    consume_pending_state(approval_token)
    return result


def _run_git_and_finish(
    requirements: RequirementsOutput,
    db_design: DatabaseDesignOutput,
    review: ReviewOutput,
    approval: ApprovalResponse | None,
    language: str | None = "python",
) -> OrchestrationResult:
    """Run Git strategy (with language) and simulated Git; return SUCCESS result."""
    # Map language to framework for git agent
    framework_map = {
        "python": "fastapi",
        "node": "express",
        "nodejs": "express",
        "java": "spring-boot",
        "go": "gin",
    }
    lang = (language or "python").lower()
    framework = framework_map.get(lang, "fastapi" if lang == "python" else lang)

    project_context = {
        "type": "backend",
        "framework": framework,
        "language": lang,
        "description": f"Backend with entities: {', '.join(e.name for e in requirements.entities)}",
    }

    try:
        git_strategy: GitStrategyOutput = propose_git_strategy(project_context)
        print("🌿 Git strategy proposed")
    except Exception as e:
        return OrchestrationResult(
            status="FAILED",
            stage="git_strategy",
            requirements=requirements,
            database_design=db_design,
            review=review,
            approval=approval,
            issues=[f"Failed to propose git strategy: {str(e)}"],
        )

    git_result = create_branch(
        repo_name="agentic-dev-platform",
        branch_name=git_strategy.branch_name,
        base_branch=git_strategy.base_branch,
    )

    print("\n🎉 ORCHESTRATION COMPLETE\n")

    return OrchestrationResult(
        status="SUCCESS",
        requirements=requirements,
        database_design=db_design,
        review=review,
        approval=approval,
        git={
            "strategy": git_strategy.model_dump(),
            "execution": git_result,
        },
    )


if __name__ == "__main__":
    result = run_orchestration(
        "Set up backend for a SaaS app with users, organizations, and roles",
        language="python",
    )
    print("\n📊 ORCHESTRATION RESULT:")
    print(f"Status: {result.status}")
    if result.approval_token:
        print(f"Approval token: {result.approval_token}")
    if result.status == "SUCCESS" and result.git:
        print(f"Git branch: {result.git['strategy']['branch_name']}")
        print(f"Files: {len(result.git['strategy'].get('files', []))}")
