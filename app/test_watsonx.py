from app.utils.watsonx_client import call_watsonx

SYSTEM_PROMPT = "You are a senior software architect."
USER_PROMPT = "Explain why database normalization matters in one paragraph."

print(call_watsonx(SYSTEM_PROMPT, USER_PROMPT))
