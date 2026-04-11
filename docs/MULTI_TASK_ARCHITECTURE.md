# Multi-Task Intent Architecture

## Overview

WATI Conductor uses a **simplified LLM-first architecture** where the LLM directly generates executable tasks, eliminating the need for separate planning and validation layers.

## Architecture Comparison

### Traditional ReAct Pattern (v1)
```
User Input
    ↓
[Parser] LLM extracts intent
    ↓
[Planner] Rule-based plan generation
    ↓
[Validator] Check parameters
    ↓
[Executor] Execute tools
    ↓
[Response] Format output
```

**Issues:**
- Rigid action types (send_template_to_segment, send_message_to_contact, etc.)
- Cannot handle multi-task instructions
- Planner needs explicit rules for each action type
- Validator adds complexity

### Multi-Task Intent System (v2)
```
User Input
    ↓
[Parser] LLM generates tasks directly
    ↓
[Executor] Execute tasks with dependency resolution
    ↓
[Response] LLM generates natural language response
```

**Benefits:**
- ✅ Handles single or multiple tasks
- ✅ LLM decides tools and parameters
- ✅ Automatic dependency resolution
- ✅ Confidence-based filtering
- ✅ Simpler codebase

## Implementation

### 1. Intent Model

```python
# conductor/models/intent.py
class Task(BaseModel):
    tool: str                    # Tool name to execute
    params: dict                 # Tool parameters
    description: str             # Human-readable description
    confidence: float            # Task confidence (0.0-1.0)

class Intent(BaseModel):
    tasks: list[Task]            # List of tasks to execute
    overall_confidence: float    # Overall parse confidence
```

### 2. Parser (LLM-Powered)

```python
# conductor/agent/parser.py
SYSTEM_PROMPT = """
Parse user instructions into a list of tasks with tools and parameters.

Available tools:
- search_contacts: Find contacts by tag or attributes
- send_template_message_batch: Send template to multiple contacts
- create_ticket: Create support ticket
- list_templates: List all available templates
...

Examples:

User: "Find all VIP contacts and send them the welcome_wati template"
{
  "tasks": [
    {
      "tool": "search_contacts",
      "params": {"tag": "VIP"},
      "description": "Find VIP contacts",
      "confidence": 0.95
    },
    {
      "tool": "send_template_message_batch",
      "params": {
        "contacts": "$task_0.contacts",
        "template_name": "welcome_wati"
      },
      "description": "Send welcome_wati to VIP contacts",
      "confidence": 0.90
    }
  ],
  "overall_confidence": 0.92
}
"""

async def parse_intent(instruction: str) -> Intent:
    llm = get_llm(temperature=0.0)
    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"User: {instruction}")
    ])
    intent = Intent(**extract_json(response.content))
    # Filter by confidence >= 0.7
    intent.tasks = [t for t in intent.tasks if t.confidence >= 0.7]
    return intent
```

### 3. Executor (Dependency Resolution)

```python
# conductor/agent/nodes/execute.py
async def execute_node(state: AgentState) -> dict:
    results = []
    intent = state["intent"]
    trust_mode = state.get("trust_mode", False)
    
    for i, task in enumerate(intent.tasks):
        # Resolve $task_N references
        params = _resolve_params(task.params, results)
        
        # User confirmation
        if not trust_mode:
            print(f"Tool: {task.tool}")
            print(f"Description: {task.description}")
            response = input("Execute this tool? [Y/n/q]: ")
            if response == 'n':
                return {"user_rejected": True}
        
        # Execute tool
        tool = get_tool(task.tool)
        result = await tool.ainvoke(params)
        results.append({"step": i, "tool": task.tool, "result": result})
    
    return {"execution_results": results, "success": True}

def _resolve_params(params: dict, prior_results: list) -> dict:
    """Resolve $task_N.field references."""
    resolved = {}
    for key, value in params.items():
        if isinstance(value, str) and value.startswith("$task_"):
            # "$task_0.contacts" → prior_results[0]["result"]["contacts"]
            parts = value.split(".")
            task_idx = int(parts[0].replace("$task_", ""))
            result = prior_results[task_idx]["result"]
            for field in parts[1:]:
                if isinstance(result, dict) and field in result:
                    result = result[field]
            resolved[key] = result
        else:
            resolved[key] = value
    return resolved
```

### 4. Response Generator (LLM-Powered)

```python
# conductor/agent/nodes/response.py
async def response_node(state: AgentState) -> dict:
    instruction = state["instruction"]
    results = state["execution_results"]
    user_rejected = state.get("user_rejected", False)
    
    if user_rejected:
        # Generate rejection response
        llm = get_llm(temperature=0.7)
        response = await llm.ainvoke([
            SystemMessage(content="Explain why task cannot be completed..."),
            HumanMessage(content=f"User rejected tool: {state['rejected_tool']}")
        ])
        return {"final_response": response.content}
    
    # Generate success response
    llm = get_llm(temperature=0.7)
    response = await llm.ainvoke([
        SystemMessage(content="Generate natural language response..."),
        HumanMessage(content=f"Instruction: {instruction}\nResults: {results}")
    ])
    return {"final_response": response.content}
```

## Example Flows

### Single Task
```
User: "What templates do I have?"
    ↓
Parser: {tasks: [{tool: "list_templates", confidence: 0.95}]}
    ↓
Executor: list_templates() → 6 templates
    ↓
Response: "You have 6 templates: welcome_wati, shopify_order_confirm..."
```

### Multi-Task with Dependencies
```
User: "Find all VIP contacts and send them the welcome_wati template"
    ↓
Parser: {
  tasks: [
    {tool: "search_contacts", params: {tag: "VIP"}},
    {tool: "send_template_message_batch", params: {
      contacts: "$task_0.contacts",
      template_name: "welcome_wati"
    }}
  ]
}
    ↓
Executor:
  Task 0: search_contacts(tag="VIP") → {contacts: [...]}
  Task 1: send_template_message_batch(
    contacts=[...],  // Resolved from task 0
    template_name="welcome_wati"
  ) → {sent: 10}
    ↓
Response: "I found 10 VIP contacts and sent the welcome_wati template to all of them."
```

### Multiple Independent Tasks
```
User: "Search VIP contacts, create a ticket to Sam about payment, and list templates"
    ↓
Parser: {
  tasks: [
    {tool: "search_contacts", params: {tag: "VIP"}},
    {tool: "create_ticket", params: {subject: "payment", assignee: "Sam"}},
    {tool: "list_templates", params: {}}
  ]
}
    ↓
Executor:
  Task 0: search_contacts() → 10 contacts
  Task 1: create_ticket() → TKT-12345
  Task 2: list_templates() → 6 templates
    ↓
Response: "I found 10 VIP contacts, created ticket TKT-12345 for Sam, and listed 6 templates."
```

## Benefits

### 1. Flexibility
- Handles any combination of tasks
- No need to predefine action types
- LLM adapts to new tools automatically

### 2. Simplicity
- Removed 3 nodes (planner, validator, clarifier)
- Reduced codebase by ~40%
- Easier to maintain and extend

### 3. Robustness
- Confidence filtering prevents low-quality tasks
- Dependency resolution handles complex workflows
- User confirmation prevents destructive actions

### 4. Extensibility
- Add new tools → update parser prompt
- No code changes needed for new workflows
- LLM learns from examples

## Comparison Table

| Feature | v1 (ReAct) | v2 (Multi-Task) |
|---------|------------|-----------------|
| **Task Decomposition** | Rule-based planner | LLM-powered parser |
| **Action Types** | Fixed (10 types) | Dynamic (any tool) |
| **Multi-Task Support** | ❌ No | ✅ Yes |
| **Dependency Resolution** | Manual in planner | Automatic ($task_N) |
| **Confidence Filtering** | Intent-level only | Per-task filtering |
| **Code Complexity** | 6 nodes | 3 nodes |
| **Lines of Code** | ~1200 | ~700 |
| **Extensibility** | Add planner rules | Update prompt examples |

## Migration Path

If you have existing v1 code:

1. **Update Intent Model**: Replace single action with tasks list
2. **Simplify Parser**: Remove action type logic, let LLM generate tasks
3. **Remove Planner**: LLM now generates tasks directly
4. **Remove Validator**: Confidence filtering handles quality
5. **Update Executor**: Add dependency resolution
6. **Update Graph**: Remove planner/validator nodes

## Conclusion

The Multi-Task Intent System represents a paradigm shift from **rule-based orchestration** to **LLM-powered task decomposition**. By trusting the LLM to generate executable tasks directly, we achieve:

- **Simpler architecture** (3 nodes vs 6 nodes)
- **More flexibility** (handles any task combination)
- **Better extensibility** (add tools via prompt examples)
- **Cleaner code** (~40% reduction in LOC)

This architecture is ideal for AI agents that need to handle complex, multi-step workflows with minimal engineering overhead.
