"""
In-memory store for pending approvals and orchestration state.

When orchestration returns PENDING_APPROVAL, we save the intermediate state
and an approval_token. The human calls POST /approval to submit their decision,
then POST /orchestrate/continue with the token to resume.

For production, replace with Redis or a database.
"""

import uuid
from typing import Any, Optional
from dataclasses import dataclass, asdict
import json


@dataclass
class ApprovalDecision:
    """Human's approval or rejection."""
    approved: bool
    comments: Optional[str] = None
    approved_by: Optional[str] = None


@dataclass
class PendingApprovalState:
    """State saved when orchestration pauses for approval."""
    approval_token: str
    user_prompt: str
    requirements: dict  # serialized RequirementsOutput
    database_design: dict  # serialized DatabaseDesignOutput
    review: dict  # serialized ReviewOutput
    language: Optional[str] = None
    decision: Optional[ApprovalDecision] = None


# In-memory stores (use Redis/DB in production)
_pending_states: dict[str, PendingApprovalState] = {}
_approval_decisions: dict[str, ApprovalDecision] = {}


def create_pending_approval(
    user_prompt: str,
    requirements: dict,
    database_design: dict,
    review: dict,
    language: Optional[str] = None,
) -> str:
    """
    Save orchestration state and return an approval_token.
    
    Returns:
        approval_token: Use this in POST /approval and POST /orchestrate/continue
    """
    token = str(uuid.uuid4())
    state = PendingApprovalState(
        approval_token=token,
        user_prompt=user_prompt,
        language=language,
        requirements=requirements,
        database_design=database_design,
        review=review,
        decision=None,
    )
    _pending_states[token] = state
    return token


def get_pending_state(approval_token: str) -> Optional[PendingApprovalState]:
    """Get pending state by token. Returns None if not found or expired."""
    return _pending_states.get(approval_token)


def submit_approval(
    approval_token: str,
    approved: bool,
    comments: Optional[str] = None,
    approved_by: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Record human's approval or rejection.
    
    Returns:
        (success, message)
    """
    state = _pending_states.get(approval_token)
    if not state:
        return False, "Invalid or expired approval token"
    
    state.decision = ApprovalDecision(
        approved=approved,
        comments=comments,
        approved_by=approved_by,
    )
    _approval_decisions[approval_token] = state.decision
    return True, "Approval recorded. Call POST /orchestrate/continue with this token to continue."


def get_approval_decision(approval_token: str) -> Optional[ApprovalDecision]:
    """Get the recorded decision for a token."""
    state = _pending_states.get(approval_token)
    if state and state.decision:
        return state.decision
    return _approval_decisions.get(approval_token)


def consume_pending_state(approval_token: str) -> Optional[PendingApprovalState]:
    """
    Get and remove pending state (after continue has been run).
    Call this after successfully continuing so the token cannot be reused.
    """
    return _pending_states.pop(approval_token, None)
