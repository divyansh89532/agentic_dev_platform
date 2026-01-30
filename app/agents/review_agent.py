from app.utils.watsonx_client import call_watsonx
import json
import re
from datetime import datetime,timezone
from app.skills.validation_skill import validate_db_design
from app.skills.approval_skill import request_approval



SYSTEM_PROMPT = """
You are a technical review and governance agent for enterprise systems.

Your task:
- Review the provided database schema
- Validate normalization claims
- Identify architectural risks or omissions
- Assess whether human approval is required

RULES:
- Do NOT redesign the schema
- Do NOT generate SQL
- Do NOT suggest new entities
- Base your review strictly on the provided design

OUTPUT FORMAT (STRICT):
Return a single VALID JSON object with:

{
  "assessment": "string",
  "issues": ["string"],
  "risk_level": "LOW | MEDIUM | HIGH",
  "approval_required": true
}

Output JSON ONLY.
"""

def extract_last_json(text: str) -> dict:
    matches = re.findall(r"\{[\s\S]*\}", text)
    if not matches:
        raise ValueError(f"No JSON found in output:\n{text}")
    return json.loads(matches[-1])

def review_database_design(db_design: dict) -> dict:
    print("🔎 Review & Governance Agent running")

    llm_output = call_watsonx(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=json.dumps(db_design, indent=2)
    )

    return extract_last_json(llm_output)


if __name__ == "__main__":
    
    locked_db_design = {
        "tables": [
            {"name": "Users", "columns": []},
            {"name": "Organizations", "columns": []},
            {"name": "Roles", "columns": []},
            {"name": "Memberships", "columns": []}
        ],
        "normalization_level": "3NF",
        "design_rationale": [
            "Many-to-many relationship resolved via junction table"
        ],
        "sql_schema": "CREATE TABLE ..."
    }
    validation = validate_db_design(locked_db_design)

    if validation["is_valid"]:

        review = review_database_design(locked_db_design)
        print("\n🔍 REVIEW RESULT:\n", review)

        if review.get("approval_required"):
            approval = request_approval(review)
            print("\n✅ APPROVAL RESULT:\n", approval)
    else:
        print( 
        {
        "assessment": "Schema failed structural validation",
        "issues": validation["issues"],
        "risk_level": "HIGH",
        "approval_required": True
        })
