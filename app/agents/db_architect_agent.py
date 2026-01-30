from app.utils.watsonx_client import call_watsonx
import json
import re

SYSTEM_PROMPT = """
You are a senior database architect designing enterprise SaaS systems.

Your task:
- Design a relational database schema
- Use the provided requirements ONLY
- Normalize the schema up to Third Normal Form (3NF)
- Introduce junction tables when required
- Derive tables from entities and relationships
- Clearly explain your design decisions

OUTPUT FORMAT (STRICT):
Return a single VALID JSON object with the following structure:

{
  "tables": [
    {
      "name": "string",
      "columns": [
        {
          "name": "string",
          "type": "string",
          "constraints": ["string"]
        }
      ]
    }
  ],
  "normalization_level": "3NF",
  "design_rationale": ["string"],
  "sql_schema": "string"
}

RULES:
- Do NOT include explanations outside JSON
- Do NOT invent new entities
- Do NOT design authentication or authorization tables
- Membership MUST be modeled as a junction table
- Output JSON ONLY
"""

def extract_last_json(text: str) -> dict:
    matches = re.findall(r"\{[\s\S]*\}", text)
    if not matches:
        raise ValueError(f"No JSON found in output:\n{text}")
    return json.loads(matches[-1])

def design_database(requirements: dict) -> dict:
    print("🗄️ Database Architect Agent running")

    llm_output = call_watsonx(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=json.dumps(requirements, indent=2)
    )

    return extract_last_json(llm_output)


if __name__ == "__main__":
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
    print("\n✅ DATABASE DESIGN OUTPUT:\n")
    print(result)
