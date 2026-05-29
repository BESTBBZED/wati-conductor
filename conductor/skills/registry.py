"""Skills registry — CRUD, builtin seeding, and active tool resolution."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from conductor.db.models import Skill

logger = logging.getLogger(__name__)

# Built-in skill definitions
BUILTIN_SKILLS = [
    {
        "name": "contacts",
        "version": "1.0",
        "description": "Contact search, tagging, and attribute management",
        "tool_names": [
            "search_contacts",
            "get_contact_info",
            "add_contact_tag",
            "add_contact_tag_batch",
            "remove_contact_tag",
            "remove_contact_tag_batch",
            "update_contact_attributes",
            "update_contact_attributes_batch",
        ],
        "instructions": (
            "When managing contacts:\n"
            "- Confirm before batch operations affecting more than 50 contacts\n"
            "- Never remove 'vip' or 'do-not-contact' tags without explicit confirmation\n"
            "- Show a preview of affected contacts before executing batch updates"
        ),
    },
    {
        "name": "messaging",
        "version": "1.0",
        "description": "Send session messages and template broadcasts",
        "tool_names": [
            "send_session_message",
            "send_template_message_batch",
        ],
        "instructions": (
            "When sending messages:\n"
            "- Verify template status is 'approved' before sending\n"
            "- Confirm with user before sending to more than 100 contacts\n"
            "- Never send marketing templates outside business hours (9:00-18:00)"
        ),
    },
    {
        "name": "templates",
        "version": "1.0",
        "description": "Browse and inspect message templates",
        "tool_names": [
            "list_templates",
            "get_template_details",
        ],
        "instructions": "",
    },
    {
        "name": "operators",
        "version": "1.0",
        "description": "Assign conversations to operators and teams",
        "tool_names": [
            "assign_operator",
            "assign_team",
        ],
        "instructions": (
            "When assigning operators:\n"
            "- VIP contacts must be assigned to 'senior-support' team\n"
            "- Check operator availability before assigning"
        ),
    },
    {
        "name": "tickets",
        "version": "1.0",
        "description": "Create and resolve support tickets",
        "tool_names": [
            "create_ticket",
            "resolve_ticket",
        ],
        "instructions": (
            "When managing tickets:\n"
            "- Never auto-resolve VIP tickets without manual confirmation\n"
            "- Always include a resolution summary when resolving"
        ),
    },
]


async def seed_builtin_skills(session: AsyncSession) -> int:
    """Insert builtin skills if they don't exist.

    Args:
        session: Async DB session.

    Returns:
        Number of skills seeded.
    """
    seeded = 0
    for skill_data in BUILTIN_SKILLS:
        stmt = select(Skill).where(Skill.name == skill_data["name"])
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            skill = Skill(
                name=skill_data["name"],
                version=skill_data["version"],
                description=skill_data["description"],
                enabled=True,
                tool_names=skill_data["tool_names"],
                instructions=skill_data["instructions"],
                depends_on=[],
                builtin=True,
            )
            session.add(skill)
            seeded += 1

    if seeded:
        await session.commit()
        logger.info("Seeded %d builtin skills.", seeded)
    return seeded


async def get_active_skills(session: AsyncSession) -> list[Skill]:
    """Get all enabled skills.

    Args:
        session: Async DB session.

    Returns:
        List of enabled Skill objects.
    """
    stmt = select(Skill).where(Skill.enabled.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_active_tool_names(session: AsyncSession) -> list[str]:
    """Get tool names from all enabled skills.

    Args:
        session: Async DB session.

    Returns:
        Deduplicated list of tool function names.
    """
    skills = await get_active_skills(session)
    tool_names: set[str] = set()
    for skill in skills:
        tool_names.update(skill.tool_names)
    return sorted(tool_names)


async def enable_skill(session: AsyncSession, name: str) -> Skill:
    """Enable a skill by name.

    Args:
        session: Async DB session.
        name: Skill name.

    Returns:
        Updated Skill object.

    Raises:
        ValueError: If skill not found.
    """
    stmt = select(Skill).where(Skill.name == name)
    result = await session.execute(stmt)
    skill = result.scalar_one_or_none()

    if not skill:
        raise ValueError(f"Skill not found: {name}")

    skill.enabled = True
    await session.commit()
    await session.refresh(skill)
    logger.info("Enabled skill: %s", name)
    return skill


async def disable_skill(session: AsyncSession, name: str) -> Skill:
    """Disable a skill by name.

    Args:
        session: Async DB session.
        name: Skill name.

    Returns:
        Updated Skill object.

    Raises:
        ValueError: If skill not found.
    """
    stmt = select(Skill).where(Skill.name == name)
    result = await session.execute(stmt)
    skill = result.scalar_one_or_none()

    if not skill:
        raise ValueError(f"Skill not found: {name}")

    skill.enabled = False
    await session.commit()
    await session.refresh(skill)
    logger.info("Disabled skill: %s", name)
    return skill
