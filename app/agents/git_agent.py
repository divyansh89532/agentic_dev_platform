from app.utils.watsonx_client import call_watsonx
import json
import re

SYSTEM_PROMPT = """
You are a Git strategy and repository governance agent.

Your task:
- Propose a safe Git branch name
- Suggest a minimal backend repository structure
- Follow industry-standard naming conventions

RULES:
- Do NOT generate code
- Do NOT modify files
- Do NOT assume CI/CD
- Assume this is an early-stage backend project

OUTPUT FORMAT (STRICT):
Return a single VALID JSON object with:

{
  "branch_name": "string",
  "base_branch": "string",
  "repository_structure": ["string"],
  "action": "string"
}

Output JSON ONLY.
"""

def extract_last_json(text: str) -> dict:
    matches = re.findall(r"\{[\s\S]*\}", text)
    if not matches:
        raise ValueError(f"No JSON found in output:\n{text}")
    return json.loads(matches[-1])

def propose_git_strategy(project_context: dict) -> dict:
    print("🌿 Git Strategy Agent running")

    llm_output = call_watsonx(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=json.dumps(project_context, indent=2)
    )

    return extract_last_json(llm_output)


if __name__ == "__main__":
    approved_context = {
        "approved": True,
        "project_context": {
            "type": "backend",
            "framework": "fastapi"
        }
    }

    result = propose_git_strategy(approved_context["project_context"])
    print("\n🌿 GIT STRATEGY OUTPUT:\n", result)