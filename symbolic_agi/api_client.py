# symbolic_agi/api_client.py
"""
Initializes and provides a shared, monitored asynchronous OpenAI client.
"""

import os
from typing import Any, cast

from openai import APIError, AsyncOpenAI
from openai.types.chat import ChatCompletion
from openai.types.create_embedding_response import CreateEmbeddingResponse

from . import config, metrics


def get_openai_client() -> AsyncOpenAI:
    """
    Initializes and returns a singleton instance of the AsyncOpenAI client.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    return AsyncOpenAI(api_key=api_key)


# Shared client instance
client = get_openai_client()


async def monitored_chat_completion(role: str, **kwargs: Any) -> ChatCompletion:
    """
    A wrapper around the OpenAI client's chat completion create method
    that records Prometheus metrics for latency, token usage, and errors.
    It selects a model tier based on the cognitive role of the request.
    """
    high_stakes_roles = {"planner", "qa", "meta"}
    model_to_use = (
        config.HIGH_STAKES_MODEL if role in high_stakes_roles else config.FAST_MODEL
    )

    try:
        with metrics.API_CALL_LATENCY.labels(model=model_to_use).time():
            response = cast(
                ChatCompletion,
                await client.chat.completions.create(model=model_to_use, **kwargs),
            )

        if response.usage:
            metrics.LLM_TOKEN_USAGE.labels(model=model_to_use, type="prompt").inc(
                response.usage.prompt_tokens
            )
            metrics.LLM_TOKEN_USAGE.labels(model=model_to_use, type="completion").inc(
                response.usage.completion_tokens
            )

        return response
    except APIError as e:
        error_type = type(e).__name__
        metrics.API_CALL_ERRORS.labels(
            model=model_to_use, error_type=error_type
        ).inc()
        raise e


async def monitored_embedding_creation(**kwargs: Any) -> CreateEmbeddingResponse:
    """
    A wrapper around the OpenAI client's embedding create method
    that records Prometheus metrics.
    """
    model_name = kwargs.get("model", "unknown")
    try:
        with metrics.API_CALL_LATENCY.labels(model=model_name).time():
            response: CreateEmbeddingResponse = await client.embeddings.create(**kwargs)

        if response.usage:
            metrics.LLM_TOKEN_USAGE.labels(model=model_name, type="prompt").inc(
                response.usage.prompt_tokens
            )
            completion_tokens = response.usage.total_tokens - response.usage.prompt_tokens
            metrics.LLM_TOKEN_USAGE.labels(model=model_name, type="completion").inc(
                completion_tokens
            )

        return response
    except APIError as e:
        error_type = type(e).__name__
        metrics.API_CALL_ERRORS.labels(model=model_name, error_type=error_type).inc()
        raise e
