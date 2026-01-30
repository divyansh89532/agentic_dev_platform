def validate_db_design(db_design: dict) -> dict:
    """
    Lightweight structural validation.
    No reasoning, no redesign.
    """

    required_keys = [
        "tables",
        "normalization_level",
        "design_rationale",
        "sql_schema"
    ]

    issues = []

    for key in required_keys:
        if key not in db_design:
            issues.append(f"Missing required key: {key}")

    if db_design.get("normalization_level") != "3NF":
        issues.append("Schema is not explicitly marked as 3NF")

    if not db_design.get("tables"):
        issues.append("No tables defined")

    return {
        "is_valid": len(issues) == 0,
        "issues": issues
    }
