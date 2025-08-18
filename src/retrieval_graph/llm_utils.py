# src/retrieval_graph/llm_utils.py
from __future__ import annotations
import os, json, re
from typing import Any, Dict, Optional, Union
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage
from langchain_openai import ChatOpenAI
# 自动加载 .env（可选）
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# 兼容：若你有自定义 utils.load_chat_model，就优先用
_load_from_utils = None
try:
    from retrieval_graph.utils import load_chat_model as _load_from_utils  # 若存在
except Exception:
    try:
        from utils import load_chat_model as _load_from_utils  # 兼容根目录 utils.py
    except Exception:
        _load_from_utils = None

try:
    from openai import OpenAI  # openai>=1.0
except Exception:
    OpenAI = None  # type: ignore


def _json_loads_safely(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, flags=re.S)
        if not m:
            raise ValueError(f"LLM did not return JSON. Raw:\n{text[:400]}...")
        return json.loads(m.group(0))


def chat_json(
    system: str,
    user: Union[str, Dict[str, Any]],
    *,
    model: Optional[str] = None,
    temperature: float = 0.0,
) -> Dict[str, Any]:
    """
    统一 JSON 聊天调用：
    - 优先使用你项目内的 load_chat_model（LangChain）
    - 否则回退到 openai 官方 SDK，并强制 JSON 响应
    """
    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload = json.dumps(user, ensure_ascii=False) if not isinstance(user, str) else user

    # LangChain 路径
    if _load_from_utils is not None:
        llm = _load_from_utils(model)
        resp = llm.invoke([
            {"role": "system", "content": system},
            {"role": "user", "content": payload},
        ])
        text = getattr(resp, "content", str(resp)).strip()
        return _json_loads_safely(text)

    # openai 官方 SDK
    if OpenAI is None:
        raise RuntimeError("Need openai>=1.0 or provide utils.load_chat_model")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": payload},
        ],
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content or "{}"
    return _json_loads_safely(text)


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
