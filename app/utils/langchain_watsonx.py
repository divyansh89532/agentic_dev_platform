"""
LangChain wrapper for IBM watsonx.ai with structured output support.

Includes retry logic for agents: LLM output can sometimes be malformed
(e.g. unterminated string in JSON), so we retry with backoff.
"""

import logging
import time
from langchain_ibm import ChatWatsonx
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
import os

load_dotenv()

logger = logging.getLogger(__name__)

# Type variable for generic structured output
T = TypeVar("T", bound=BaseModel)


def get_chat_model(
    temperature: float = 0.1,
    max_tokens: int = 1024,
    model_id: Optional[str] = None
) -> ChatWatsonx:
    """
    Get a ChatWatsonx instance configured for the project.
    
    Args:
        temperature: Sampling temperature (0.0-1.0). Lower = more deterministic.
        max_tokens: Maximum tokens to generate.
        model_id: Override the default model ID.
    
    Returns:
        Configured ChatWatsonx instance.
    """
    return ChatWatsonx(
        model_id=model_id or os.getenv("WATSONX_MODEL_ID", "ibm/granite-34b-code-instruct"),
        url=os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
        project_id=os.getenv("WATSONX_PROJECT_ID"),
        apikey=os.getenv("WATSONX_API_KEY"),
        params={
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    )


# Default retry config for all agents
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY_SECONDS = 2.0


def call_llm_structured(
    system_prompt: str,
    user_prompt: str,
    output_schema: Type[T],
    temperature: float = 0.1,
    max_tokens: int = 1024,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> T:
    """
    Call watsonx.ai with structured output using LangChain.
    
    Retries on failure (e.g. malformed JSON, unterminated string) so agents
    are more resilient. Each retry uses a slightly higher temperature to
    encourage different output.
    
    Args:
        system_prompt: System instructions for the LLM.
        user_prompt: User input/query.
        output_schema: Pydantic model class defining the expected output structure.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens to generate.
        max_retries: Number of attempts (including first try).
        retry_delay_seconds: Delay between retries.
    
    Returns:
        Validated Pydantic model instance.
    
    Raises:
        Last exception if all retries fail.
    """
    last_error: Optional[Exception] = None
    
    for attempt in range(1, max_retries + 1):
        try:
            # Slightly higher temperature on retries to get different output
            temp = temperature if attempt == 1 else min(0.5, temperature + 0.1 * attempt)
            chat = get_chat_model(temperature=temp, max_tokens=max_tokens)
            structured_llm = chat.with_structured_output(output_schema)
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}")
            ])
            chain = prompt | structured_llm
            result = chain.invoke({"input": user_prompt})
            return result
        except Exception as e:
            last_error = e
            logger.warning(
                "Agent call failed (attempt %d/%d): %s",
                attempt, max_retries, str(e),
                exc_info=False,
            )
            if attempt < max_retries:
                time.sleep(retry_delay_seconds)
    
    if last_error is not None:
        raise last_error
    raise RuntimeError("call_llm_structured failed with no exception")


def call_llm_raw(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 1024,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> str:
    """
    Call watsonx.ai and return raw text response.
    
    Retries on failure (e.g. API errors, timeouts).
    
    Args:
        system_prompt: System instructions for the LLM.
        user_prompt: User input/query.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens to generate.
        max_retries: Number of attempts.
        retry_delay_seconds: Delay between retries.
    
    Returns:
        Raw text response from the LLM.
    """
    last_error: Optional[Exception] = None
    
    for attempt in range(1, max_retries + 1):
        try:
            temp = temperature if attempt == 1 else min(0.5, temperature + 0.1 * attempt)
            chat = get_chat_model(temperature=temp, max_tokens=max_tokens)
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}")
            ])
            chain = prompt | chat
            result = chain.invoke({"input": user_prompt})
            return result.content
        except Exception as e:
            last_error = e
            logger.warning(
                "Raw LLM call failed (attempt %d/%d): %s",
                attempt, max_retries, str(e),
                exc_info=False,
            )
            if attempt < max_retries:
                time.sleep(retry_delay_seconds)
    
    if last_error is not None:
        raise last_error
    raise RuntimeError("call_llm_raw failed with no exception")
