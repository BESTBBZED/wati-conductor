"""KB tools — agent-accessible tools for runtime knowledge base queries."""

from langchain_core.tools import tool

from conductor.db.session import async_session
from conductor.kb.retriever import embed_text, search_similar, get_always_inject_guardrails


@tool
async def search_knowledge(query: str, category: str | None = None) -> str:
    """Search the knowledge base for relevant SOPs, guidelines, or domain info.

    Use this when you need additional context about procedures, rules, or
    reference data that wasn't provided in the system prompt.

    Args:
        query: Natural language search query.
        category: Optional filter — one of 'sop', 'guardrail', 'domain', 'faq'.

    Returns:
        Formatted search results with relevant knowledge chunks.
    """
    query_embedding = embed_text(query)
    async with async_session() as session:
        results = await search_similar(
            session, query_embedding, top_k=5, category=category
        )

    if not results:
        return "No relevant knowledge found."

    lines = []
    for r in results:
        lines.append(f"[{r['category']}] (similarity: {r['similarity']:.2f})\n{r['content']}")
    return "\n---\n".join(lines)


@tool
async def get_guardrails() -> str:
    """Get all active guardrails that must be followed.

    Use this to check constraints before performing sensitive operations
    like batch messaging or contact modifications.

    Returns:
        List of guardrail rules that must be followed.
    """
    async with async_session() as session:
        guardrails = await get_always_inject_guardrails(session)

    if not guardrails:
        return "No guardrails configured."

    return "\n".join(f"- {g}" for g in guardrails)
