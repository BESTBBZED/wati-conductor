"""Execute node - run the plan steps."""

from conductor.models.state import AgentState
from conductor.tools.registry import get_tool


async def execute_node(state: AgentState) -> dict:
    """Execute the tasks from intent."""
    results = []
    errors = []
    intent = state["intent"]
    trust_mode = state.get("trust_mode", False)

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
    """Resolve $task_N references in parameters."""
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
