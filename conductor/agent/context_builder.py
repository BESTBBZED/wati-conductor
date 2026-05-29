"""Context builder — assembles enriched system prompt from KB and active skills."""

import logging

from conductor.config import settings
from conductor.db.session import async_session
from conductor.kb.retriever import embed_text, search_similar, get_always_inject_guardrails
from conductor.skills.registry import get_active_skills

logger = logging.getLogger(__name__)


async def build_enriched_prompt(
    base_prompt: str,
    user_instruction: str,
) -> str:
    """Build enriched system prompt with KB context and skill instructions.

    Sections appended (in order):
    1. Active skill instructions
    2. Always-on guardrails
    3. Retrieved KB context (semantic match to user instruction)

    Falls back to base_prompt if DB is unavailable.

    Args:
        base_prompt: The base system prompt text.
        user_instruction: The user's current instruction for semantic retrieval.

    Returns:
        Enriched system prompt string.
    """
    if not settings.kb_enabled and not settings.skills_enabled:
        return base_prompt

    parts = [base_prompt]

    try:
        async with async_session() as session:
            # Skill instructions
            if settings.skills_enabled:
                active_skills = await get_active_skills(session)
                skill_instructions = [
                    f"### {s.name}\n{s.instructions}"
                    for s in active_skills
                    if s.instructions
                ]
                if skill_instructions:
                    parts.append(
                        "\n## Active Skill Guidelines\n" + "\n\n".join(skill_instructions)
                    )

            if settings.kb_enabled:
                # Always-on guardrails
                guardrails = await get_always_inject_guardrails(session)
                if guardrails:
                    parts.append(
                        "\n## Guardrails (MUST follow)\n"
                        + "\n".join(f"- {g}" for g in guardrails)
                    )

                # Semantic retrieval
                if user_instruction:
                    query_embedding = embed_text(user_instruction)
                    docs = await search_similar(
                        session, query_embedding, top_k=settings.kb_top_k
                    )
                    if docs:
                        context = "\n\n".join(
                            f"[{d['category']}] {d['content']}" for d in docs
                        )
                        parts.append(f"\n## Relevant Knowledge\n{context}")

    except Exception as exc:
        logger.warning("KB/Skills enrichment failed, using base prompt: %s", exc)
        return base_prompt

    return "\n".join(parts)
