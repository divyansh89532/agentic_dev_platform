"""
Validation Skill - Database schema validation.

This is a deterministic skill (no LLM) that validates database designs
for structural correctness before proceeding with reviews.
"""

from typing import Union
from app.models.schemas import DatabaseDesignOutput, ValidationResult


def validate_db_design(db_design: Union[DatabaseDesignOutput, dict]) -> dict:
    """
    Lightweight structural validation of database design.
    
    Checks for:
    - Required keys (tables, normalization_level, design_rationale, sql_schema)
    - Non-empty tables list
    - Proper normalization level
    
    This is NOT an LLM-powered validation - it's deterministic.
    
    Args:
        db_design: Either a DatabaseDesignOutput model or a dict with the same structure.
    
    Returns:
        Dictionary with:
            - is_valid: bool
            - issues: list of validation issues found
    """
    # Convert Pydantic model to dict if needed
    if isinstance(db_design, DatabaseDesignOutput):
        db_design = db_design.model_dump()
    
    required_keys = [
        "tables",
        "normalization_level",
        "design_rationale",
        "sql_schema"
    ]

    issues = []

    # Check required keys
    for key in required_keys:
        if key not in db_design:
            issues.append(f"Missing required key: {key}")

    # Check normalization level
    if db_design.get("normalization_level") != "3NF":
        issues.append("Schema is not explicitly marked as 3NF")

    # Check tables exist
    if not db_design.get("tables"):
        issues.append("No tables defined")
    else:
        # Validate each table has required fields
        for i, table in enumerate(db_design.get("tables", [])):
            if not table.get("name"):
                issues.append(f"Table {i+1} is missing a name")
            if not table.get("columns"):
                issues.append(f"Table '{table.get('name', i+1)}' has no columns defined")
            else:
                # Check each column has required fields
                for j, col in enumerate(table.get("columns", [])):
                    if not col.get("name"):
                        issues.append(f"Column {j+1} in table '{table.get('name')}' is missing a name")
                    if not col.get("type"):
                        issues.append(f"Column '{col.get('name', j+1)}' in table '{table.get('name')}' is missing a type")

    # Check SQL schema is not empty
    if not db_design.get("sql_schema") or db_design.get("sql_schema", "").strip() == "":
        issues.append("SQL schema is empty")

    return {
        "is_valid": len(issues) == 0,
        "issues": issues
    }


def validate_db_design_strict(db_design: Union[DatabaseDesignOutput, dict]) -> ValidationResult:
    """
    Same as validate_db_design but returns a Pydantic model.
    
    Use this when you need type safety with the result.
    """
    result = validate_db_design(db_design)
    return ValidationResult(**result)


# For standalone testing
if __name__ == "__main__":
    # Test with valid design
    valid_design = {
        "tables": [
            {
                "name": "users",
                "columns": [
                    {"name": "id", "type": "UUID", "constraints": ["PRIMARY KEY"]},
                    {"name": "email", "type": "VARCHAR(255)", "constraints": ["NOT NULL"]}
                ]
            }
        ],
        "normalization_level": "3NF",
        "design_rationale": ["Users table follows 3NF"],
        "sql_schema": "CREATE TABLE users (id UUID PRIMARY KEY, email VARCHAR(255) NOT NULL);"
    }
    
    print("Testing valid design:")
    result = validate_db_design(valid_design)
    print(f"  is_valid: {result['is_valid']}")
    print(f"  issues: {result['issues']}")
    
    # Test with invalid design
    invalid_design = {
        "tables": [],
        "normalization_level": "2NF"
    }
    
    print("\nTesting invalid design:")
    result = validate_db_design(invalid_design)
    print(f"  is_valid: {result['is_valid']}")
    print(f"  issues: {result['issues']}")
