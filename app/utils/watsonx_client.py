from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.credentials import Credentials
from dotenv import load_dotenv

import os

load_dotenv()

# --- CONFIGURATION ---
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL = os.getenv("WATSONX_URL")  # e.g. https://us-south.ml.cloud.ibm.com
MODEL_ID = os.getenv("WATSONX_MODEL_ID", "granite-13b-chat-v2")

# ---------------------

credentials = Credentials(
    api_key=WATSONX_API_KEY,
    url=WATSONX_URL
)

model = ModelInference(
    model_id=MODEL_ID,
    credentials=credentials,
    project_id=WATSONX_PROJECT_ID
)

def call_watsonx(system_prompt: str, user_prompt: str) -> str:
    """
    Generic reasoning call for all agents.
    """

    prompt = f"""
SYSTEM:
{system_prompt}

USER:
{user_prompt}
"""

    response = model.generate_text(
        prompt=prompt,
        params={
            "decoding_method": "greedy",
            "temperature": 0.1,
            "max_new_tokens": 1024,
            "response_format": { "type": "json_object" }
        }
    )

    return response
