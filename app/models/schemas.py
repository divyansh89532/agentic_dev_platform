"""
Pydantic schemas for structured LLM output.
These schemas ensure consistent JSON responses from watsonx.ai via LangChain.
"""

from pydantic import BaseModel, Field
from typing import List, Literal, Optional


# =============================================================================
# REQUIREMENTS AGENT SCHEMAS
# =============================================================================

class Entity(BaseModel):
    """A domain entity extracted from requirements."""
    name: str = Field(description="Name of the entity")
    description: str = Field(description="Brief description of what this entity represents")


class Relationship(BaseModel):
    """A relationship between two entities."""
    from_entity: str = Field(alias="from", description="Source entity name")
    to: str = Field(description="Target entity name")
    type: Literal["one-to-one", "one-to-many", "many-to-many"] = Field(
        description="Cardinality of the relationship"
    )
    through: Optional[str] = Field(
        default=None, 
        description="Junction table name for many-to-many relationships"
    )

    class Config:
        populate_by_name = True


class RequirementsOutput(BaseModel):
    """Structured requirements extracted from user input."""
    entities: List[Entity] = Field(description="List of domain entities")
    relationships: List[Relationship] = Field(description="Relationships between entities")
    assumptions: List[str] = Field(description="Assumptions made during analysis")
    out_of_scope: List[str] = Field(description="Items explicitly out of scope")


# =============================================================================
# DATABASE ARCHITECT AGENT SCHEMAS
# =============================================================================

class Column(BaseModel):
    """A database table column."""
    name: str = Field(description="Column name")
    type: str = Field(description="Data type (e.g., VARCHAR, INTEGER, UUID)")
    constraints: List[str] = Field(
        default_factory=list,
        description="Column constraints (e.g., PRIMARY KEY, NOT NULL, FOREIGN KEY)"
    )


class Table(BaseModel):
    """A database table definition."""
    name: str = Field(description="Table name")
    columns: List[Column] = Field(description="List of columns in the table")


class DatabaseDesignOutput(BaseModel):
    """Database schema design output."""
    tables: List[Table] = Field(description="List of tables in the schema")
    normalization_level: str = Field(
        default="3NF",
        description="Normalization level achieved (e.g., 1NF, 2NF, 3NF)"
    )
    design_rationale: List[str] = Field(
        description="Reasoning behind design decisions"
    )
    sql_schema: str = Field(description="SQL CREATE statements for the schema")


# =============================================================================
# REVIEW AGENT SCHEMAS
# =============================================================================

class ReviewOutput(BaseModel):
    """Review and governance assessment output."""
    assessment: str = Field(description="Overall assessment summary")
    issues: List[str] = Field(
        default_factory=list,
        description="List of identified issues or concerns"
    )
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Overall risk level of the design"
    )
    approval_required: bool = Field(
        description="Whether human approval is required before proceeding"
    )


# =============================================================================
# GIT AGENT SCHEMAS
# =============================================================================

class RepoFile(BaseModel):
    """A file to be created in the repository."""
    path: str = Field(description="File path relative to repo root (e.g., README.md, src/main.py)")
    content: str = Field(description="Full file content (for code/config) or placeholder text")


class GitStrategyOutput(BaseModel):
    """Git branching and repository strategy output with basic repo files."""
    branch_name: str = Field(description="Proposed branch name (e.g., feature/db-schema)")
    base_branch: str = Field(
        default="main",
        description="Base branch to create from (e.g., main, develop)"
    )
    repository_structure: List[str] = Field(
        description="Suggested repository folder structure (paths)"
    )
    action: str = Field(description="Description of the Git action to perform")
    files: List[RepoFile] = Field(
        default_factory=list,
        description="Basic/probable files to create (README, .gitignore, main entry, config)"
    )


# =============================================================================
# VALIDATION SCHEMAS
# =============================================================================

class ValidationResult(BaseModel):
    """Result of database design validation."""
    is_valid: bool = Field(description="Whether the design passed validation")
    issues: List[str] = Field(
        default_factory=list,
        description="List of validation issues found"
    )


# =============================================================================
# APPROVAL SCHEMAS
# =============================================================================

class ApprovalRequest(BaseModel):
    """Request for human approval."""
    review: ReviewOutput = Field(description="The review that triggered approval request")
    db_design: DatabaseDesignOutput = Field(description="The database design to approve")


class ApprovalResponse(BaseModel):
    """Response from human approval."""
    approved: bool = Field(description="Whether the design was approved")
    comments: Optional[str] = Field(
        default=None,
        description="Optional comments from the approver"
    )
    approved_by: Optional[str] = Field(default=None, description="Identifier of the approver")


# =============================================================================
# APPROVAL API SCHEMAS
# =============================================================================

class ApprovalSubmitRequest(BaseModel):
    """Request body for submitting human approval/rejection."""
    approval_token: str = Field(description="Token returned when orchestration is PENDING_APPROVAL")
    approved: bool = Field(description="True to approve, False to reject")
    comments: Optional[str] = Field(default=None, description="Optional comments from the reviewer")
    approved_by: Optional[str] = Field(default=None, description="Identifier of the approver (e.g. email)")


class ApprovalSubmitResponse(BaseModel):
    """Response after submitting approval."""
    success: bool = Field(description="Whether the approval was recorded")
    message: str = Field(description="Human-readable message")
    approval_token: str = Field(description="The approval token")


# =============================================================================
# ORCHESTRATION RESULT SCHEMA
# =============================================================================

class OrchestrationResult(BaseModel):
    """Final result of the orchestration pipeline."""
    status: Literal["SUCCESS", "FAILED", "HALTED", "PENDING_APPROVAL"] = Field(
        description="Final status: SUCCESS, FAILED, HALTED, or PENDING_APPROVAL (waiting for human)"
    )
    stage: Optional[str] = Field(
        default=None,
        description="Stage where failure/halt occurred (if applicable)"
    )
    approval_token: Optional[str] = Field(
        default=None,
        description="When status is PENDING_APPROVAL, use this token to submit approval and then call /orchestrate/continue"
    )
    requirements: Optional[RequirementsOutput] = Field(default=None)
    database_design: Optional[DatabaseDesignOutput] = Field(default=None)
    review: Optional[ReviewOutput] = Field(default=None)
    approval: Optional[ApprovalResponse] = Field(default=None)
    git: Optional[dict] = Field(default=None, description="Git strategy and execution result")
    issues: Optional[List[str]] = Field(default=None, description="Issues if failed")
