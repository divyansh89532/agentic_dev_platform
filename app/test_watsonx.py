"""
Test script for watsonx.ai integration.

Tests both raw LLM calls and structured output.
"""

from app.utils.langchain_watsonx import call_llm_raw, call_llm_structured
from app.models.schemas import RequirementsOutput

# Test 1: Raw LLM call
print("=" * 60)
print("TEST 1: Raw LLM Call")
print("=" * 60)

SYSTEM_PROMPT = "You are a senior software architect."
USER_PROMPT = "Explain why database normalization matters in one paragraph."

response = call_llm_raw(SYSTEM_PROMPT, USER_PROMPT)
print(response)

# Test 2: Structured output
print("\n" + "=" * 60)
print("TEST 2: Structured Output")
print("=" * 60)

REQUIREMENTS_PROMPT = """You are a senior software requirements analyst.

Your task:
- Extract domain entities
- Identify relationships between them
- State realistic assumptions
- Clearly define what is explicitly out of scope"""

result = call_llm_structured(
    system_prompt=REQUIREMENTS_PROMPT,
    user_prompt="Build a simple blog with users and posts",
    output_schema=RequirementsOutput
)

print(f"\nEntities: {[e.name for e in result.entities]}")
print(f"Relationships: {len(result.relationships)}")
print(f"Assumptions: {result.assumptions}")
print(f"\nFull JSON output:")
print(result.model_dump_json(indent=2))
