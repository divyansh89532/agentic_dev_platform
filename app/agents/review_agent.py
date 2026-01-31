"""
Review & Governance Agent

Reviews database designs for architectural risks and determines if human approval is needed.
Uses LangChain with watsonx.ai for reliable structured output.
"""

from app.utils.langchain_watsonx import call_llm_structured
from app.models.schemas import DatabaseDesignOutput, ReviewOutput


SYSTEM_PROMPT = """You are a technical review and governance agent for enterprise systems.

Your task:
- Review the provided database schema
- Validate normalization claims (is it truly 3NF?)
- Identify architectural risks or omissions
- Check for common issues: missing indexes, improper foreign keys, scalability concerns
- Assess whether human approval is required before proceeding

RULES:
- Do NOT redesign the schema
- Do NOT generate SQL
- Do NOT suggest new entities
- Base your review strictly on the provided design
- Be constructive and specific in your feedback

RISK LEVEL GUIDELINES:
- LOW: Schema follows best practices, minor improvements possible
- MEDIUM: Some concerns that should be addressed, but not blockers
- HIGH: Significant issues that could cause problems in production

APPROVAL GUIDELINES:
- approval_required = true if risk_level is MEDIUM or HIGH
- approval_required = true if there are security-related concerns
- approval_required = false only for LOW risk with no concerns"""


def review_database_design(db_design: DatabaseDesignOutput | dict) -> ReviewOutput:
    """
    Reviews a database design for risks and governance requirements.
    
    Args:
        db_design: Either a DatabaseDesignOutput model or a dict with the same structure.
    
    Returns:
        ReviewOutput: Validated Pydantic model with assessment, issues, risk level,
                     and approval requirement flag.
    """
    print("🔎 Review & Governance Agent running")
    
    # Convert to JSON string for the prompt
    if isinstance(db_design, DatabaseDesignOutput):
        design_json = db_design.model_dump_json(indent=2)
    else:
        import json
        design_json = json.dumps(db_design, indent=2)
    
    result = call_llm_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=design_json,
        output_schema=ReviewOutput,
        temperature=0.1,
        max_tokens=1024
    )
    
    return result


# For standalone testing
if __name__ == "__main__":
    from app.skills.validation_skill import validate_db_design
    
    locked_db_design = {
        "tables": [
            {
                "name": "users",
                "columns": [
                    {"name": "id", "type": "UUID", "constraints": ["PRIMARY KEY"]},
                    {"name": "email", "type": "VARCHAR(255)", "constraints": ["NOT NULL", "UNIQUE"]},
                    {"name": "created_at", "type": "TIMESTAMP", "constraints": ["NOT NULL"]}
                ]
            },
            {
                "name": "organizations",
                "columns": [
                    {"name": "id", "type": "UUID", "constraints": ["PRIMARY KEY"]},
                    {"name": "name", "type": "VARCHAR(255)", "constraints": ["NOT NULL"]},
                    {"name": "created_at", "type": "TIMESTAMP", "constraints": ["NOT NULL"]}
                ]
            },
            {
                "name": "roles",
                "columns": [
                    {"name": "id", "type": "UUID", "constraints": ["PRIMARY KEY"]},
                    {"name": "name", "type": "VARCHAR(100)", "constraints": ["NOT NULL", "UNIQUE"]}
                ]
            },
            {
                "name": "memberships",
                "columns": [
                    {"name": "id", "type": "UUID", "constraints": ["PRIMARY KEY"]},
                    {"name": "user_id", "type": "UUID", "constraints": ["NOT NULL", "FOREIGN KEY"]},
                    {"name": "organization_id", "type": "UUID", "constraints": ["NOT NULL", "FOREIGN KEY"]},
                    {"name": "role_id", "type": "UUID", "constraints": ["NOT NULL", "FOREIGN KEY"]}
                ]
            }
        ],
        "normalization_level": "3NF",
        "design_rationale": [
            "Many-to-many relationship between users and organizations resolved via memberships junction table",
            "Each membership has exactly one role"
        ],
        "sql_schema": "CREATE TABLE users (...); CREATE TABLE organizations (...); ..."
    }
    
    # First validate
    validation = validate_db_design(locked_db_design)
    
    if validation["is_valid"]:
        review = review_database_design(locked_db_design)
        
        print("\n🔍 REVIEW RESULT:")
        print(f"Assessment: {review.assessment}")
        print(f"Risk Level: {review.risk_level}")
        print(f"Issues: {review.issues}")
        print(f"Approval Required: {review.approval_required}")
    else:
        print(f"❌ Validation failed: {validation['issues']}")
