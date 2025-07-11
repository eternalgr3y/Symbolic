# symbolic_agi/api_client.py
import os
import logging
from typing import Any, cast

from openai import APIError, AsyncOpenAI, AuthenticationError
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.create_embedding_response import CreateEmbeddingResponse

from . import config, metrics

# Initialize the client
def get_openai_client() -> AsyncOpenAI:
    """Get the OpenAI client with proper configuration."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return AsyncOpenAI(api_key=api_key)

# Global client instance
client = get_openai_client()

# Token usage tracking
usage_tracker = {
    "total_tokens": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_cost": 0.0
}

def log_token_usage(response: Any, model: str = "gpt-4-turbo-preview") -> None:
    """Log token usage from API response."""
    if hasattr(response, 'usage') and response.usage:
        usage = response.usage
        usage_tracker["total_tokens"] += usage.total_tokens
        usage_tracker["prompt_tokens"] += usage.prompt_tokens
        
        # Only log completion tokens if they exist (chat completions)
        if hasattr(usage, 'completion_tokens'):
            usage_tracker["completion_tokens"] += usage.completion_tokens
            completion_tokens = usage.completion_tokens
        else:
            # For embeddings, no completion tokens
            completion_tokens = 0
        
        # Estimate cost (adjust rates as needed)
        if "gpt-4" in model:
            prompt_cost = usage.prompt_tokens * 0.03 / 1000
            completion_cost = completion_tokens * 0.06 / 1000
        else:
            prompt_cost = usage.prompt_tokens * 0.001 / 1000
            completion_cost = completion_tokens * 0.002 / 1000
            
        total_cost = prompt_cost + completion_cost
        usage_tracker["total_cost"] += total_cost

def get_usage_report() -> dict:
    """Get current usage statistics."""
    return usage_tracker.copy()

async def monitored_chat_completion(
    client: AsyncOpenAI,
    model: str = "gpt-4-turbo-preview",
    **kwargs
) -> ChatCompletion:
    """Wrapper for chat completions with monitoring."""
    try:
        response = await client.chat.completions.create(
            model=model,
            **kwargs
        )
        
        # Log usage
        log_token_usage(response, model)
        
        # Update metrics
        if hasattr(response, 'usage') and response.usage:
            metrics.TOKEN_USAGE_TOTAL.labels(
                role="system",
                model=model,
                type="prompt"
            ).inc(response.usage.prompt_tokens)
            
            metrics.TOKEN_USAGE_TOTAL.labels(
                role="system",
                model=model,
                type="completion"
            ).inc(response.usage.completion_tokens)
        
        return response
        
    except AuthenticationError as e:
        logging.error("Authentication error: Check your API key")
        raise
    except APIError as e:
        logging.error(f"API error: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error in chat completion: {e}")
        raise

async def monitored_embedding_creation(
    client: AsyncOpenAI,
    **kwargs
) -> CreateEmbeddingResponse:
    """Wrapper for embedding creation with monitoring."""
    try:
        response = await client.embeddings.create(**kwargs)
        
        # Log usage
        if hasattr(response, 'usage'):
            log_token_usage(response, kwargs.get('model', 'text-embedding-ada-002'))
        
        return response
        
    except Exception as e:
        logging.error(f"Error creating embeddings: {e}")
        raise