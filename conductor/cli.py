"""CLI interface for WATI Conductor."""

import asyncio
import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from conductor.agent import create_agent_graph
from conductor.history import save_conversation_turn

console = Console()


async def run_instruction(instruction: str, agent, trust: bool = False) -> tuple[bool, str]:
    """Run a single instruction and return (success, response)."""
    
    state = {
        "instruction": instruction,
        "mode": "dry-run",
        "trust_mode": trust,
        "intent": None,
        "execution_results": [],
        "execution_errors": [],
        "final_response": "",
        "success": False,
        "user_rejected": False
    }
    
    max_retries = 2
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            # Run agent
            result = await agent.ainvoke(state)
            
            # Show thinking
            intent = result.get("intent")
            
            if intent:
                console.print(f"\n[dim]🤔 Agent Thinking:[/dim]\n")
                console.print(f"[dim]Tasks: {len(intent.tasks)} (confidence: {intent.overall_confidence:.2f})[/dim]")
                for i, task in enumerate(intent.tasks):
                    console.print(f"[dim]  {i+1}. {task.description} (confidence: {task.confidence:.2f})[/dim]")
            
            # Execute plan
            if intent and intent.tasks:
                console.print("\n[bold]🔧 Tool Execution:[/bold]")
                console.print(f"Plan has {len(intent.tasks)} task(s). Will execute one at a time.\n")
                
                # Execute
                state["mode"] = "execute"
                result = await agent.ainvoke(state)
                
                if trust:
                    console.print("[green]✓ Auto-approved (trust mode)[/green]")
                
                # Check if user rejected
                if result.get("user_rejected"):
                    console.print("[yellow]⚠ Tool execution rejected by user[/yellow]\n")
                else:
                    console.print("[green]✓ Completed[/green]\n")
            
            # Get response
            response = result.get("final_response", "")
            if response:
                console.print("=" * 80)
                console.print("\n[bold cyan]💬 Response:[/bold cyan]\n")
                console.print(response)
                console.print()
            
            # Save to history
            save_conversation_turn(instruction, response)
            
            return True, response
            
        except Exception as e:
            retry_count += 1
            if retry_count <= max_retries:
                console.print(f"\n[yellow]⚠ Error occurred: {str(e)}[/yellow]")
                console.print(f"[yellow]Retrying... (attempt {retry_count}/{max_retries})[/yellow]\n")
                await asyncio.sleep(1)
            else:
                console.print(f"\n[red]❌ Failed after {max_retries} retries: {str(e)}[/red]")
                console.print("[yellow]Something went wrong. Please try rephrasing your request.[/yellow]\n")
                return False, f"Error: {str(e)}"
    
    return False, "Max retries exceeded"


async def interactive_loop():
    """Run interactive CLI loop."""
    console.print(Panel.fit(
        "[bold cyan]WATI Conductor - Interactive Mode[/bold cyan]\n"
        "Type your instructions naturally. Type 'quit' or 'exit' to stop.\n"
        "Type 'trust' to toggle auto-approval mode.",
        border_style="cyan"
    ))
    
    # Create agent once
    agent = create_agent_graph()
    trust_mode = False
    
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            if not user_input.strip():
                continue
            
            # Check for commands
            if user_input.lower() in ["quit", "exit", "q"]:
                console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
                break
            
            if user_input.lower() in ["trust", "--trust"]:
                trust_mode = not trust_mode
                status = "enabled ✓" if trust_mode else "disabled"
                console.print(f"\n[yellow]Trust mode {status}[/yellow]\n")
                continue
            
            # Run instruction
            success, response = await run_instruction(user_input, agent, trust_mode)
            
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted. Type 'quit' to exit or continue with another request.[/yellow]\n")
            continue
        except EOFError:
            console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
            break


@click.command()
@click.argument("instruction", required=False)
@click.option("--dry-run", is_flag=True, help="Preview plan without executing")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed execution")
@click.option("--trust", is_flag=True, help="Auto-approve all tool executions")
def run(instruction: str, dry_run: bool, verbose: bool, trust: bool):
    """Execute a WATI automation instruction.
    
    If no instruction is provided, starts interactive mode.
    """
    if not instruction:
        # No instruction provided, start interactive mode
        try:
            asyncio.run(interactive_loop())
        except KeyboardInterrupt:
            console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
            sys.exit(0)
    else:
        # Single command mode (legacy)
        asyncio.run(_run_single_command(instruction, dry_run, verbose, trust))


async def _run_single_command(instruction: str, dry_run: bool, verbose: bool, trust: bool):
    """Run a single command (legacy mode)."""
    console.print(f"\n[bold cyan]Instruction:[/bold cyan] {instruction}\n")
    
    agent = create_agent_graph()
    success, response = await run_instruction(instruction, agent, trust)


def main():
    """Main entry point for interactive mode."""
    try:
        asyncio.run(interactive_loop())
    except KeyboardInterrupt:
        console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
        sys.exit(0)


if __name__ == "__main__":
    run()
