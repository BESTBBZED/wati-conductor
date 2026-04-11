"""LLM factory for creating configured LLM instances.

In te future version, the other sections in the State Machine can make use of LLM.
"""

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from conductor.config import settings


def get_llm(temperature: float | None = None):
    """Get configured LLM instance based on settings.

    Args:
        temperature: Override default temperature (optional)

    Returns:
        Configured LangChain LLM instance (ChatOpenAI or ChatAnthropic)

    Raises:
        ValueError: If model is unsupported or API key is missing

    Example:
        >>> llm = get_llm()
        >>> response = await llm.ainvoke([HumanMessage(content="Hello")])
    """
    model_name = settings.llm_parse_model
    temp = temperature if temperature is not None else settings.llm_temperature

    if "deepseek" in model_name.lower():
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY not set in environment or .env file")
        return ChatOpenAI(
            model=model_name,
            temperature=temp,
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com"
        )

    if "claude" in model_name.lower() or "anthropic" in model_name.lower():
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment or .env file")
        return ChatAnthropic(
            model=model_name if "claude" in model_name else "claude-3-5-sonnet-20241022",
            temperature=temp,
            api_key=settings.anthropic_api_key
        )

    if "gpt" in model_name.lower() or "openai" in model_name.lower():
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in environment or .env file")
        return ChatOpenAI(
            model=model_name if "gpt" in model_name else "gpt-4o",
            temperature=temp,
            api_key=settings.openai_api_key
        )

    raise ValueError(f"Unsupported model: {model_name}")
