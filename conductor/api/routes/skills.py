"""Skills management API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from conductor.db.models import Skill
from conductor.db.session import get_session
from conductor.skills.registry import (
    enable_skill,
    disable_skill,
    get_active_skills,
    get_active_tool_names,
)

router = APIRouter()


# --- Pydantic schemas ---


class CreateSkillRequest(BaseModel):
    """Request body for creating a custom skill."""

    name: str
    description: str = ""
    tool_names: list[str] = []
    instructions: str = ""
    depends_on: list[str] = []


class UpdateSkillRequest(BaseModel):
    """Request body for updating a skill."""

    enabled: bool | None = None
    description: str | None = None
    instructions: str | None = None
    tool_names: list[str] | None = None


# --- Routes ---


@router.get("")
async def list_skills(session: AsyncSession = Depends(get_session)):
    """List all registered skills with their status."""
    stmt = select(Skill).order_by(Skill.builtin.desc(), Skill.name)
    result = await session.execute(stmt)
    skills = result.scalars().all()

    return {
        "skills": [
            {
                "name": s.name,
                "version": s.version,
                "description": s.description,
                "enabled": s.enabled,
                "builtin": s.builtin,
                "tool_count": len(s.tool_names),
                "tool_names": s.tool_names,
            }
            for s in skills
        ],
        "total": len(skills),
    }


@router.post("")
async def create_skill(
    request: CreateSkillRequest,
    session: AsyncSession = Depends(get_session),
):
    """Register a new custom skill."""
    # Check name uniqueness
    stmt = select(Skill).where(Skill.name == request.name)
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Skill '{request.name}' already exists")

    skill = Skill(
        name=request.name,
        description=request.description,
        enabled=True,
        tool_names=request.tool_names,
        instructions=request.instructions,
        depends_on=request.depends_on,
        builtin=False,
    )
    session.add(skill)
    await session.commit()
    await session.refresh(skill)

    return {"name": skill.name, "id": str(skill.id), "status": "created"}


@router.get("/active/tools")
async def get_active_tools_endpoint(session: AsyncSession = Depends(get_session)):
    """Get resolved tool list from all enabled skills."""
    tool_names = await get_active_tool_names(session)
    return {"tools": tool_names, "total": len(tool_names)}


@router.get("/{name}")
async def get_skill(name: str, session: AsyncSession = Depends(get_session)):
    """Get skill details by name."""
    stmt = select(Skill).where(Skill.name == name)
    result = await session.execute(stmt)
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")

    return {
        "name": skill.name,
        "version": skill.version,
        "description": skill.description,
        "enabled": skill.enabled,
        "builtin": skill.builtin,
        "tool_names": skill.tool_names,
        "instructions": skill.instructions,
        "depends_on": skill.depends_on,
        "created_at": skill.created_at.isoformat() if skill.created_at else None,
    }


@router.patch("/{name}")
async def update_skill(
    name: str,
    request: UpdateSkillRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update a skill (enable/disable, edit instructions)."""
    if request.enabled is True:
        skill = await enable_skill(session, name)
    elif request.enabled is False:
        skill = await disable_skill(session, name)
    else:
        stmt = select(Skill).where(Skill.name == name)
        result = await session.execute(stmt)
        skill = result.scalar_one_or_none()
        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")

    # Apply other updates
    if request.description is not None:
        skill.description = request.description
    if request.instructions is not None:
        skill.instructions = request.instructions
    if request.tool_names is not None:
        skill.tool_names = request.tool_names

    await session.commit()
    await session.refresh(skill)

    return {"name": skill.name, "enabled": skill.enabled, "status": "updated"}


@router.delete("/{name}")
async def delete_skill(name: str, session: AsyncSession = Depends(get_session)):
    """Delete a non-builtin skill."""
    stmt = select(Skill).where(Skill.name == name)
    result = await session.execute(stmt)
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    if skill.builtin:
        raise HTTPException(status_code=403, detail="Cannot delete builtin skills")

    await session.delete(skill)
    await session.commit()
    return {"deleted": name}
