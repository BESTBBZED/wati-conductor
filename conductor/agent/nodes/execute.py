"""Execute node - runs parsed tasks against WATI tools with optional user confirmation."""

from conductor.models.state import AgentState
from conductor.tools.registry import get_tool


async def execute_node(state: AgentState) -> dict:
    """Execute each task from the parsed intent sequentially.

    Resolves inter-task references (e.g. ``$task_0.contacts``), prompts
    for user confirmation unless trust mode is on, and stops on first error.
    """
    results = []
    errors = []
    intent = state["intent"]
    trust_mode = state.get("trust_mode", False)

    # The intent is constrained by a pydantic validation model
    for i, task in enumerate(intent.tasks):
        try:
            # Get the tool
            tool = get_tool(task.tool)

            # Resolve parameters (handle $task_N references)
            params = _resolve_params(task.params, results)

            # Print tool execution
            print(f"Tool: {task.tool}")

            # Ask for confirmation if not in trust mode
            if not trust_mode:
                print(f"Description: {task.description}")
                print(f"Parameters: {params}")
                response = input("Execute this tool? [Y/n/q]: ").strip().lower()

                if response == 'q':
                    return {
                        "execution_results": results,
                        "execution_errors": errors,
                        "success": False,
                        "user_rejected": True,
                        "rejected_tool": task.tool
                    }
                elif response == 'n':
                    return {
                        "execution_results": results,
                        "execution_errors": errors,
                        "success": False,
                        "user_rejected": True,
                        "rejected_tool": task.tool
                    }
                print()

            # Execute tool
            result = await tool.ainvoke(params)
            results.append({"step": i, "tool": task.tool, "result": result})

        except Exception as e:
            errors.append({"step": i, "tool": task.tool, "error": str(e)})
            break

    success = len(errors) == 0

    return {
        "execution_results": results,
        "execution_errors": errors,
        "success": success,
        "user_rejected": False
    }


def _resolve_params(params: dict, prior_results: list) -> dict:
    """Replace ``$task_N.field`` references with actual values from earlier results.

    Args:
        params: Raw parameter dict that may contain ``$task_N`` references.
        prior_results: List of prior execution result dicts.

    Returns:
        New dict with references resolved to concrete values.
    """
    resolved = {}
    for key, value in params.items():
        if isinstance(value, str) and value.startswith("$task_"):
            # Extract task index
            parts = value.split(".")
            task_ref = parts[0]  # e.g., "$task_0"
            task_idx = int(task_ref.replace("$task_", ""))

            if task_idx < len(prior_results):
                result = prior_results[task_idx]["result"]

                # Navigate to nested field if specified
                if len(parts) > 1:
                    for field in parts[1:]:
                        if isinstance(result, dict) and field in result:
                            result = result[field]
                        else:
                            # Field not found, keep original reference
                            result = value
                            break
                resolved[key] = result
            else:
                resolved[key] = value
        else:
            resolved[key] = value
    return resolved
