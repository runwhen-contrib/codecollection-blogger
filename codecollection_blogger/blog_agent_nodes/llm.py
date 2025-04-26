"""Module containing shared LLM configuration and initialization."""

import os
from langchain_openai import ChatOpenAI

# Configuration constants
MODEL_NAME = "gpt-4-turbo-preview"
TEMPERATURE = 0.7
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30


def initialize_llm(response_format: str = "json_object") -> ChatOpenAI:
    """Initialize and return the LLM instance.

    Args:
        response_format: The format to request from the LLM. Defaults to "json_object".
                       Set to None to disable JSON formatting.

    Returns:
        ChatOpenAI: Configured LLM instance

    Raises:
        ValueError: If OPENAI_API_KEY environment variable is not set
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    kwargs = {
        "api_key": api_key,
        "model": MODEL_NAME,
        "temperature": TEMPERATURE,
        "max_retries": MAX_RETRIES,
        "request_timeout": REQUEST_TIMEOUT,
    }

    if response_format:
        kwargs["model_kwargs"] = {"response_format": {"type": response_format}}

    return ChatOpenAI(**kwargs)
