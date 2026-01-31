"""
Requirements Analysis Agent

Extracts structured requirements from natural language user input.
Uses LangChain with watsonx.ai for reliable structured output.
"""

from app.utils.langchain_watsonx import call_llm_structured
from app.models.schemas import RequirementsOutput


SYSTEM_PROMPT = """You are a senior software requirements analyst.

Your task:
- Extract domain entities from the user's request
- Identify relationships between entities
- State realistic assumptions
- Clearly define what is explicitly out of scope

RULES:
- Do NOT design databases
- Do NOT generate code
- Be concise and precise
- Focus only on business domain entities and their relationships
- Infer reasonable assumptions based on common patterns
- Explicitly state what you are NOT including"""


def interpret_requirements(user_prompt: str) -> RequirementsOutput:
    """
    Converts vague developer input into structured system requirements.
    
    Args:
        user_prompt: Natural language description of what the user wants to build.
    
    Returns:
        RequirementsOutput: Validated Pydantic model with entities, relationships,
                          assumptions, and out_of_scope items.
    
    Example:
        >>> result = interpret_requirements("Build a SaaS app with users and orgs")
        >>> print(result.entities)
        [Entity(name='User', description='...'), Entity(name='Organization', description='...')]
    """
    print("📘 Requirements Analysis Agent running")
    
    result = call_llm_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        output_schema=RequirementsOutput,
        temperature=0.1,
        max_tokens=1024
    )
    
    return result


# For standalone testing
if __name__ == "__main__":
    result = interpret_requirements(
        "Set up backend for a SaaS app with users, organizations, and roles"
    )
    
    print("\n✅ REQUIREMENTS OUTPUT:")
    print(f"Entities: {[e.name for e in result.entities]}")
    print(f"Relationships: {len(result.relationships)}")
    print(f"Assumptions: {result.assumptions}")
    print(f"Out of Scope: {result.out_of_scope}")
    
    # Export as JSON (for debugging)
    print("\n📄 JSON Output:")
    print(result.model_dump_json(indent=2))
