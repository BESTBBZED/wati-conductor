"""CLI interface for WATI Conductor — interactive REPL, single-command, KB & Skills management."""

import asyncio
import logging
import sys

import click
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from conductor.agent import create_agent_graph
from conductor.history import save_conversation_turn

console = Console()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent execution helpers
# ---------------------------------------------------------------------------


async def run_instruction(
    instruction: str,
    agent: CompiledStateGraph,
    trust: bool = False,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Execute one user instruction through the ReAct agent graph.

    Args:
        instruction: Natural language instruction.
        agent: Compiled LangGraph agent.
        trust: If True, skip per-tool confirmation prompts.
        dry_run: If True, show planned action without executing.

    Returns:
        ``(success, response_text)`` tuple.
    """
    state = {
        "messages": [HumanMessage(content=instruction)],
        "iteration_count": 0,
        "trust_mode": trust,
        "mode": "dry-run" if dry_run else "execute",
        "user_rejected": False,
        "rejected_tool": "",
    }

    try:
        result = await agent.ainvoke(state)
    except Exception as exc:
        logger.error("Agent invocation failed: %s", exc)
        console.print(f"\n[red]❌ Error: {exc}[/red]\n")
        return False, f"Error: {exc}"

    final_msg = result["messages"][-1]
    response = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
    iterations = result.get("iteration_count", 0)

    if dry_run and hasattr(final_msg, "tool_calls") and final_msg.tool_calls:
        tc = final_msg.tool_calls[0]
        console.print(f"\n[dim]🔍 Dry-run — agent would call:[/dim]")
        console.print(f"[dim]   Tool: {tc['name']}[/dim]")
        console.print(f"[dim]   Args: {tc['args']}[/dim]\n")
        return True, f"Dry-run: would call {tc['name']}"

    if response:
        console.print("\n" + "=" * 80)
        console.print("\n[bold cyan]💬 Response:[/bold cyan]\n")
        console.print(response)
        console.print(f"\n[dim]({iterations} iteration{'s' if iterations != 1 else ''})[/dim]\n")

    save_conversation_turn(instruction, response)
    return True, response


async def interactive_loop() -> None:
    """Run the interactive REPL."""
    console.print(
        Panel.fit(
            "[bold cyan]WATI Conductor - Interactive Mode[/bold cyan]\n"
            "Type your instructions naturally. Type 'quit' or 'exit' to stop.\n"
            "Type 'trust' to toggle auto-approval mode.",
            border_style="cyan",
        )
    )

    agent = create_agent_graph()
    trust_mode = False
    interrupt_count = 0

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            interrupt_count = 0

            if not user_input.strip():
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
                break

            if user_input.lower() in ("trust", "--trust"):
                trust_mode = not trust_mode
                status = "enabled ✓" if trust_mode else "disabled"
                console.print(f"\n[yellow]Trust mode {status}[/yellow]\n")
                continue

            await run_instruction(user_input, agent, trust_mode)

        except KeyboardInterrupt:
            interrupt_count += 1
            if interrupt_count == 1:
                console.print(
                    "\n\n[yellow]Interrupted. Press Ctrl+C again to exit.[/yellow]\n"
                )
                continue
            console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
            break
        except EOFError:
            console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
            break


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group(invoke_without_command=True)
@click.option("--dry-run", is_flag=True, help="Preview plan without executing")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed execution")
@click.option("--trust", is_flag=True, help="Auto-approve all tool executions")
@click.pass_context
def cli(ctx, dry_run: bool, verbose: bool, trust: bool) -> None:
    """WATI Conductor — AI agent for WhatsApp automation.

    Run without arguments for interactive mode.
    Use subcommands 'kb', 'skills', 'serve', or 'run' for specific operations.
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    ctx.ensure_object(dict)
    ctx.obj["dry_run"] = dry_run
    ctx.obj["verbose"] = verbose
    ctx.obj["trust"] = trust

    # If no subcommand, start interactive mode
    if ctx.invoked_subcommand is None:
        try:
            asyncio.run(interactive_loop())
        except KeyboardInterrupt:
            console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
            sys.exit(0)


@cli.command("run")
@click.argument("instruction")
@click.pass_context
def run_cmd(ctx, instruction: str):
    """Execute a single instruction (non-interactive)."""
    asyncio.run(_run_single_command(
        instruction, ctx.obj["dry_run"], ctx.obj["verbose"], ctx.obj["trust"]
    ))


async def _run_single_command(
    instruction: str, dry_run: bool, verbose: bool, trust: bool
) -> None:
    """Run a single instruction from the command line."""
    console.print(f"\n[bold cyan]Instruction:[/bold cyan] {instruction}\n")
    agent = create_agent_graph()
    await run_instruction(instruction, agent, trust, dry_run)


# ---------------------------------------------------------------------------
# KB commands
# ---------------------------------------------------------------------------


@cli.group()
def kb():
    """Knowledge Base management — add, list, search, remove documents."""


@kb.command("add")
@click.argument("path")
@click.option("--category", "-c", required=True, type=click.Choice(["sop", "guardrail", "domain", "faq"]))
@click.option("--tags", "-t", default="", help="Comma-separated tags")
@click.option("--always-inject", is_flag=True, help="Always include in system prompt")
def kb_add(path: str, category: str, tags: str, always_inject: bool):
    """Ingest a file or directory into the KB."""
    import os
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    async def _run():
        from conductor.db.session import async_session, init_db
        await init_db()
        async with async_session() as session:
            if os.path.isdir(path):
                from conductor.kb.ingestion import ingest_directory
                docs = await ingest_directory(session, path, category, tag_list, always_inject)
                console.print(f"[green]✓ Ingested {len(docs)} documents from {path}[/green]")
                for d in docs:
                    console.print(f"  • {d.title}")
            else:
                from conductor.kb.ingestion import ingest_file
                doc = await ingest_file(session, path, category, tag_list, always_inject)
                from sqlalchemy import select, func
                from conductor.db.models import KBChunk
                count_stmt = select(func.count()).where(KBChunk.document_id == doc.id)
                count_result = await session.execute(count_stmt)
                chunk_count = count_result.scalar() or 0
                console.print(f"[green]✓ Ingested '{doc.title}' ({chunk_count} chunks)[/green]")

    asyncio.run(_run())


@kb.command("list")
@click.option("--category", "-c", default=None, type=click.Choice(["sop", "guardrail", "domain", "faq"]))
@click.option("--tag", "-t", default=None, help="Filter by tag")
def kb_list(category: str | None, tag: str | None):
    """List KB documents."""

    async def _run():
        from conductor.db.session import async_session, init_db
        from conductor.db.models import KBDocument, KBChunk
        from sqlalchemy import select, func
        await init_db()
        async with async_session() as session:
            stmt = select(KBDocument)
            if category:
                stmt = stmt.where(KBDocument.category == category)
            if tag:
                stmt = stmt.where(KBDocument.tags.any(tag))
            stmt = stmt.order_by(KBDocument.created_at.desc())
            result = await session.execute(stmt)
            docs = result.scalars().all()

            if not docs:
                console.print("[dim]No documents found.[/dim]")
                return

            table = Table(title="KB Documents")
            table.add_column("Title", style="cyan")
            table.add_column("Category")
            table.add_column("Tags")
            table.add_column("Chunks", justify="right")
            table.add_column("Always", justify="center")

            for doc in docs:
                count_stmt = select(func.count()).where(KBChunk.document_id == doc.id)
                count_result = await session.execute(count_stmt)
                chunks = count_result.scalar() or 0
                table.add_row(
                    doc.title,
                    doc.category,
                    ", ".join(doc.tags) if doc.tags else "-",
                    str(chunks),
                    "✓" if doc.always_inject else "",
                )
            console.print(table)

    asyncio.run(_run())


@kb.command("search")
@click.argument("query")
@click.option("--top-k", "-k", default=5, help="Number of results")
@click.option("--category", "-c", default=None, type=click.Choice(["sop", "guardrail", "domain", "faq"]))
def kb_search(query: str, top_k: int, category: str | None):
    """Semantic search across KB documents."""

    async def _run():
        from conductor.db.session import async_session, init_db
        from conductor.kb.retriever import embed_text, search_similar
        await init_db()
        query_embedding = embed_text(query)
        async with async_session() as session:
            results = await search_similar(session, query_embedding, top_k, category)

        if not results:
            console.print("[dim]No results found.[/dim]")
            return

        for i, r in enumerate(results, 1):
            console.print(f"\n[bold cyan]#{i}[/bold cyan] [{r['category']}] {r['title']} (similarity: {r['similarity']:.3f})")
            console.print(f"  {r['content'][:200]}{'...' if len(r['content']) > 200 else ''}")

    asyncio.run(_run())


@kb.command("remove")
@click.argument("doc_id")
def kb_remove(doc_id: str):
    """Remove a document by ID."""
    from uuid import UUID

    async def _run():
        from conductor.db.session import async_session, init_db
        from conductor.db.models import KBDocument
        from sqlalchemy import select
        await init_db()
        async with async_session() as session:
            stmt = select(KBDocument).where(KBDocument.id == UUID(doc_id))
            result = await session.execute(stmt)
            doc = result.scalar_one_or_none()
            if not doc:
                console.print(f"[red]Document not found: {doc_id}[/red]")
                return
            title = doc.title
            await session.delete(doc)
            await session.commit()
            console.print(f"[green]✓ Removed '{title}'[/green]")

    asyncio.run(_run())


@kb.command("stats")
def kb_stats():
    """Show KB statistics."""

    async def _run():
        from conductor.db.session import async_session, init_db
        from conductor.db.models import KBDocument, KBChunk
        from sqlalchemy import select, func
        await init_db()
        async with async_session() as session:
            doc_count = (await session.execute(select(func.count(KBDocument.id)))).scalar() or 0
            chunk_count = (await session.execute(select(func.count(KBChunk.id)))).scalar() or 0

            cats = (await session.execute(
                select(KBDocument.category, func.count()).group_by(KBDocument.category)
            )).all()

        console.print(f"\n[bold]KB Statistics[/bold]")
        console.print(f"  Documents: {doc_count}")
        console.print(f"  Chunks:    {chunk_count}")
        if cats:
            console.print(f"  Categories:")
            for cat, count in cats:
                console.print(f"    {cat}: {count}")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Skills commands
# ---------------------------------------------------------------------------


@cli.group()
def skills():
    """Skills management — list, enable, disable, info."""


@skills.command("list")
def skills_list():
    """List all registered skills."""

    async def _run():
        from conductor.db.session import async_session, init_db
        from conductor.db.models import Skill
        from sqlalchemy import select
        await init_db()
        async with async_session() as session:
            from conductor.skills.registry import seed_builtin_skills
            await seed_builtin_skills(session)
            result = await session.execute(select(Skill).order_by(Skill.builtin.desc(), Skill.name))
            skills_list = result.scalars().all()

        table = Table(title="Skills")
        table.add_column("Name", style="cyan")
        table.add_column("Enabled", justify="center")
        table.add_column("Tools", justify="right")
        table.add_column("Builtin", justify="center")
        table.add_column("Description")

        for s in skills_list:
            table.add_row(
                s.name,
                "[green]✓[/green]" if s.enabled else "[red]✗[/red]",
                str(len(s.tool_names)),
                "✓" if s.builtin else "",
                s.description[:50],
            )
        console.print(table)

    asyncio.run(_run())


@skills.command("enable")
@click.argument("name")
def skills_enable(name: str):
    """Enable a skill."""

    async def _run():
        from conductor.db.session import async_session, init_db
        from conductor.skills.registry import enable_skill
        await init_db()
        async with async_session() as session:
            skill = await enable_skill(session, name)
            console.print(f"[green]✓ Enabled '{skill.name}'[/green]")

    asyncio.run(_run())


@skills.command("disable")
@click.argument("name")
def skills_disable(name: str):
    """Disable a skill."""

    async def _run():
        from conductor.db.session import async_session, init_db
        from conductor.skills.registry import disable_skill
        await init_db()
        async with async_session() as session:
            skill = await disable_skill(session, name)
            console.print(f"[yellow]✓ Disabled '{skill.name}'[/yellow]")

    asyncio.run(_run())


@skills.command("info")
@click.argument("name")
def skills_info(name: str):
    """Show detailed info about a skill."""

    async def _run():
        from conductor.db.session import async_session, init_db
        from conductor.db.models import Skill
        from sqlalchemy import select
        await init_db()
        async with async_session() as session:
            result = await session.execute(select(Skill).where(Skill.name == name))
            skill = result.scalar_one_or_none()

        if not skill:
            console.print(f"[red]Skill not found: {name}[/red]")
            return

        console.print(f"\n[bold cyan]{skill.name}[/bold cyan] v{skill.version}")
        console.print(f"  Status:  {'[green]enabled[/green]' if skill.enabled else '[red]disabled[/red]'}")
        console.print(f"  Builtin: {'yes' if skill.builtin else 'no'}")
        console.print(f"  Tools:   {', '.join(skill.tool_names)}")
        if skill.instructions:
            console.print(f"\n  [bold]Instructions:[/bold]")
            for line in skill.instructions.split("\n"):
                console.print(f"    {line}")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Serve command
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--host", default="0.0.0.0", help="Bind host")
@click.option("--port", default=8000, help="Bind port")
@click.option("--reload", is_flag=True, help="Auto-reload on changes")
def serve(host: str, port: int, reload: bool):
    """Start the FastAPI server for KB and Skills management."""
    import uvicorn
    uvicorn.run("conductor.api.main:app", host=host, port=port, reload=reload)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for interactive mode."""
    try:
        asyncio.run(interactive_loop())
    except KeyboardInterrupt:
        console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
        sys.exit(0)


if __name__ == "__main__":
    cli()
