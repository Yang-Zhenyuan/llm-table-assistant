"""Utility functions for the retrieval graph (OpenAI version only).

This module contains utility functions for:
- Loading the OpenAI chat model
to use only OpenAI API with configuration from `.env`.
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

# Ensure .env is loaded (for OPENAI_API_KEY, OPENAI_MODEL)
load_dotenv()

def load_chat_model(model_name: str = None) -> BaseChatModel:
    """Load an OpenAI chat model.

    Args:
        model_name (str, optional): The model name (e.g. 'gpt-4o-mini').
                                    If None, defaults to OPENAI_MODEL in .env.

    Requires:
        - OPENAI_API_KEY in environment or .env file
        - OPENAI_MODEL in environment or .env file (optional, default=gpt-4o-mini)
    """
    model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY in environment variables or .env file")

    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        temperature=0.7, #0-2 decide "creativity"
    )
