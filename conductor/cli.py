"""CLI interface for WATI Conductor — interactive REPL and single-command mode."""

import asyncio
import logging
import sys

import click
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from conductor.agent import create_agent_graph
from conductor.history import save_conversation_turn

console = Console()
logger = logging.getLogger(__name__)


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

    # The last message is the agent's final text response
    final_msg = result["messages"][-1]
    response = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
    iterations = result.get("iteration_count", 0)

    # Dry-run: show what the agent would do
    if dry_run and hasattr(final_msg, "tool_calls") and final_msg.tool_calls:
        tc = final_msg.tool_calls[0]
        console.print(f"\n[dim]🔍 Dry-run — agent would call:[/dim]")
        console.print(f"[dim]   Tool: {tc['name']}[/dim]")
        console.print(f"[dim]   Args: {tc['args']}[/dim]\n")
        return True, f"Dry-run: would call {tc['name']}"

    # Show response
    if response:
        console.print("\n" + "=" * 80)
        console.print("\n[bold cyan]💬 Response:[/bold cyan]\n")
        console.print(response)
        console.print(f"\n[dim]({iterations} iteration{'s' if iterations != 1 else ''})[/dim]\n")

    save_conversation_turn(instruction, response)
    return True, response


async def interactive_loop() -> None:
    """Run the interactive REPL — reads instructions in a loop until the user quits."""
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


@click.command()
@click.argument("instruction", required=False)
@click.option("--dry-run", is_flag=True, help="Preview plan without executing")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed execution")
@click.option("--trust", is_flag=True, help="Auto-approve all tool executions")
def run(instruction: str, dry_run: bool, verbose: bool, trust: bool) -> None:
    """Execute a WATI automation instruction.

    If no instruction is provided, starts interactive mode.
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    if not instruction:
        try:
            asyncio.run(interactive_loop())
        except KeyboardInterrupt:
            console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
            sys.exit(0)
    else:
        asyncio.run(_run_single_command(instruction, dry_run, verbose, trust))


async def _run_single_command(
    instruction: str, dry_run: bool, verbose: bool, trust: bool
) -> None:
    """Run a single instruction from the command line (non-interactive)."""
    console.print(f"\n[bold cyan]Instruction:[/bold cyan] {instruction}\n")
    agent = create_agent_graph()
    await run_instruction(instruction, agent, trust, dry_run)


def main() -> None:
    """Main entry point for interactive mode."""
    try:
        asyncio.run(interactive_loop())
    except KeyboardInterrupt:
        console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
        sys.exit(0)


if __name__ == "__main__":
    run()
