"""LLM factory for creating configured LLM instances.

Provides ``get_react_llm`` for the ReAct agent graph and ``get_llm``
for standalone / legacy usage.
"""

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from conductor.config import settings


def _build_llm(model_name: str, temperature: float):
    """Build a raw LLM instance for the given model name.

    Args:
        model_name: Model identifier (e.g. ``deepseek-v4-pro``, ``claude-3-5-sonnet-20241022``).
        temperature: Sampling temperature.

    Returns:
        Configured LangChain chat model.

    Raises:
        ValueError: If model is unsupported or API key is missing.
    """
    if "deepseek" in model_name.lower():
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY not set in environment or .env file")
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
            extra_body={"thinking": {"type": "disabled"}},
        )

    if "claude" in model_name.lower() or "anthropic" in model_name.lower():
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment or .env file")
        return ChatAnthropic(
            model=model_name if "claude" in model_name else "claude-3-5-sonnet-20241022",
            temperature=temperature,
            api_key=settings.anthropic_api_key,
        )

    if "gpt" in model_name.lower() or "openai" in model_name.lower():
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in environment or .env file")
        return ChatOpenAI(
            model=model_name if "gpt" in model_name else "gpt-4o",
            temperature=temperature,
            api_key=settings.openai_api_key,
        )

    raise ValueError(f"Unsupported model: {model_name}")


def get_react_llm(tools: list):
    """Get the ReAct agent LLM with tools bound.

    Uses ``llm_react_model`` (default ``deepseek-v4-pro``) and binds
    the supplied LangChain tools so the model can make native tool calls.

    Args:
        tools: List of LangChain ``@tool`` decorated functions.

    Returns:
        LLM instance with tools bound via ``bind_tools``.
    """
    llm = _build_llm(settings.llm_react_model, settings.llm_temperature)
    return llm.bind_tools(tools)


def get_llm(temperature: float | None = None):
    """Get a standalone LLM instance (legacy / utility usage).

    Args:
        temperature: Override default temperature (optional).

    Returns:
        Configured LangChain LLM instance.
    """
    temp = temperature if temperature is not None else settings.llm_temperature
    return _build_llm(settings.llm_parse_model, temp)
