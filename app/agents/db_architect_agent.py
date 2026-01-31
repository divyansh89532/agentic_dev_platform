"""
Database Architect Agent

Designs relational database schemas based on structured requirements.
Uses LangChain with watsonx.ai for reliable structured output.
"""

from app.utils.langchain_watsonx import call_llm_structured
from app.models.schemas import RequirementsOutput, DatabaseDesignOutput


SYSTEM_PROMPT = """You are a senior database architect designing enterprise SaaS systems.

Your task:
- Design a relational database schema based on the provided requirements
- Normalize the schema to Third Normal Form (3NF)
- Create junction tables for many-to-many relationships
- Derive tables from entities and relationships
- Include appropriate data types and constraints

RULES:
- Use the provided requirements ONLY
- Do NOT invent new entities
- Do NOT design authentication or authorization tables unless specified
- Include PRIMARY KEY, FOREIGN KEY, NOT NULL constraints as appropriate
- Use standard SQL data types (UUID, VARCHAR, INTEGER, TIMESTAMP, etc.)
- Provide complete CREATE TABLE statements in sql_schema"""


def design_database(requirements: RequirementsOutput | dict) -> DatabaseDesignOutput:
    """
    Designs a database schema from structured requirements.
    
    Args:
        requirements: Either a RequirementsOutput model or a dict with the same structure.
    
    Returns:
        DatabaseDesignOutput: Validated Pydantic model with tables, normalization level,
                             design rationale, and SQL schema.
    """
    print("🗄️ Database Architect Agent running")
    
    # Convert to JSON string for the prompt
    if isinstance(requirements, RequirementsOutput):
        requirements_json = requirements.model_dump_json(indent=2, by_alias=True)
    else:
        import json
        requirements_json = json.dumps(requirements, indent=2)
    
    result = call_llm_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=requirements_json,
        output_schema=DatabaseDesignOutput,
        temperature=0.1,
        max_tokens=2048  # Larger for SQL schema
    )
    
    return result


# For standalone testing
if __name__ == "__main__":
    # Test with locked requirements
    locked_requirements = {
        "entities": [
            {"name": "User", "description": "SaaS application user"},
            {"name": "Organization", "description": "SaaS application organization"},
            {"name": "Role", "description": "Predefined role within an organization"},
            {"name": "Membership", "description": "User's membership in an organization with a specific role"}
        ],
        "relationships": [
            {"from": "User", "to": "Organization", "type": "many-to-many", "through": "Membership"},
            {"from": "Membership", "to": "User", "type": "many-to-one", "through": None},
            {"from": "Membership", "to": "Organization", "type": "many-to-one", "through": None},
            {"from": "Membership", "to": "Role", "type": "many-to-one", "through": None}
        ],
        "assumptions": [
            "Roles are predefined and managed outside the scope of user-organization relationships"
        ],
        "out_of_scope": [
            "User authentication and authorization mechanisms",
            "Role creation and management"
        ]
    }

    result = design_database(locked_requirements)
    
    print("\n✅ DATABASE DESIGN OUTPUT:")
    print(f"Tables: {[t.name for t in result.tables]}")
    print(f"Normalization: {result.normalization_level}")
    print(f"Rationale: {result.design_rationale}")
    
    print("\n📄 SQL Schema:")
    print(result.sql_schema)
