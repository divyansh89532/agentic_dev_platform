import json
import re
import ast
from typing import Any, Optional
from app.utils.watsonx_client import call_watsonx

SYSTEM_PROMPT = """
You are a senior software requirements analyst.

Your task:
- Extract domain entities
- Identify relationships between them
- State realistic assumptions
- Clearly define what is explicitly out of scope
- Provide the output in JSON format. 

OUTPUT FORMAT (STRICT):
Return a single VALID JSON object with the following structure:

{
  "entities": [
    {
      "name": "string",
      "description": "string"
    }
  ],
  "relationships": [
    {
      "from": "string",
      "to": "string",
      "type": "one-to-one | one-to-many | many-to-many",
      "through": "string | null"
    }
  ],
  "assumptions": ["string"],
  "out_of_scope": ["string"]
}

Rules:
- Output JSON only 
- Do NOT design databases
- Do NOT generate code
- Be concise and precise
- do not include any explanations or reasoning outside the JSON output
- no text before or after the JSON output
"""


def extract_last_json(text: str) -> dict:
    """
    Extracts the LAST valid JSON object from a text blob.
    This is robust against reasoning / explanations before JSON.
    """
    matches = re.findall(r"\{[\s\S]*\}", text)

    if not matches:
        raise ValueError(f"No JSON object found in output:\n{text}")

    last_json = matches[-1].strip()
    return json.loads(last_json)



def interpret_requirements(user_prompt: str) -> dict:
    """
    Uses watsonx.ai to convert vague developer input
    into structured system requirements.
    """
    print("📘 Requirements Analysis Agent running")

    llm_output = call_watsonx(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt
    )
    # print("LLM Output:", llm_output)
    
    return extract_last_json(llm_output)

result = interpret_requirements(
    "Set up backend for a SaaS app with users, organizations, and roles"
)

print(json.dumps(result))