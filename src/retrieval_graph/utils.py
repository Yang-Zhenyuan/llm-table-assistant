"""Utility functions for the retrieval graph (OpenAI version only).

This module contains utility functions for:
- Handling messages (extracting text content)
- Formatting documents as XML
- Loading the OpenAI chat model

Original file had Azure support and extra logic, but this version is simplified
to use only OpenAI API with configuration from `.env`.
"""

from typing import Optional
from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

# Ensure .env is loaded (for OPENAI_API_KEY, OPENAI_MODEL)
load_dotenv()


def get_message_text(msg: AnyMessage) -> str:
    """Extract the text content from a LangChain message.

    Supports:
    - String content
    - Dict content (expects 'text' field)
    - List of content parts (string or dict)
    """
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()


def _format_doc(doc: Document) -> str:
    """Format a single document as XML with metadata attributes."""
    metadata = doc.metadata or {}
    meta = "".join(f" {k}={v!r}" for k, v in metadata.items())
    if meta:
        meta = f" {meta}"
    return f"<document{meta}>\n{doc.page_content}\n</document>"


def format_docs(docs: Optional[list[Document]]) -> str:
    """Format a list of documents as XML.

    Example:
        <documents>
        <document source='file1'> ... </document>
        <document source='file2'> ... </document>
        </documents>
    """
    if not docs:
        return "<documents></documents>"
    formatted = "\n".join(_format_doc(doc) for doc in docs)
    return f"<documents>\n{formatted}\n</documents>"


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
        temperature=0,
    )
