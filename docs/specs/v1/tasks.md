# WATI Conductor v1 — Implementation Tasks

## Task Overview

| # | Task | Est. | Depends On | Priority | Status |
|---|------|------|------------|----------|--------|
| 1 | Project scaffolding + dependencies | 15min | — | P0 | ✅ DONE |
| 2 | Pydantic models + type definitions | 20min | 1 | P0 | ✅ DONE |
| 3 | Mock WATI client | 30min | 2 | P0 | ✅ DONE |
| 4 | Real WATI client (httpx) | 20min | 2 | P1 | TODO |
| 5 | LangChain tool definitions | 30min | 2, 3 | P0 | ✅ DONE |
| 6 | Intent parsing (LLM) | 25min | 2 | P0 | ✅ DONE |
| 7 | Plan generation logic | 30min | 6 | P0 | ✅ DONE |
| 8 | LangGraph state machine | 40min | 5, 6, 7 | P0 | ✅ DONE |
| 9 | CLI interface (Rich) | 30min | 8 | P0 | ✅ DONE |
| 10 | Error handling + retry logic | 20min | 4, 8 | P1 | TODO |
| 11 | Demo scenarios + testing | 20min | 9 | P0 | TODO |

**Total Estimated Time:** ~4 hours (with buffer)

**Critical Path:** 1 → 2 → 3 → 5 → 6 → 7 → 8 → 9 → 11

---

## Task 1: Project Scaffolding + Dependencies

**Goal:** Runnable project skeleton with all dependencies installed.

**Deliverables:**
```
wati-conductor/
├── pyproject.toml          # Poetry/pip dependencies
├── README.md               # Setup instructions
├── .env.example            # Template for configuration
├── .gitignore              # Python + .env
├── conductor/
│   ├── __init__.py
│   ├── __main__.py         # CLI entry point
│   └── config.py           # Settings (Pydantic)
└── tests/
    └── __init__.py
```

**Dependencies:**
```toml
[tool.poetry.dependencies]
python = "^3.11"
langchain = "^0.3.0"
langgraph = "^0.2.0"
langchain-anthropic = "^0.2.0"
httpx = "^0.27.0"
pydantic = "^2.0"
pydantic-settings = "^2.0"
rich = "^13.0"
tenacity = "^9.0"
python-dotenv = "^1.0"
```

**Completion Criteria:**
- [ ] `pip install -e .` installs all dependencies
- [ ] `python -m conductor --help` shows CLI help
- [ ] `.env.example` documents all required variables

---

## Task 2: Pydantic Models + Type Definitions

**Goal:** Type-safe data contracts for all components.

**Deliverables:** `conductor/models/`

```
models/
├── __init__.py
├── intent.py       # Intent, Entity, ParsedInstruction
├── plan.py         # APICall, ExecutionPlan, ValidationError
├── wati.py         # Contact, Template, Message, Broadcast
└── state.py        # AgentState (LangGraph state)
```

**Key Models:**

```python
# intent.py
class Intent(BaseModel):
    action: Literal[
        "send_template_to_segment",
        "send_message_to_contact",
        "search_contacts",
        "update_contact_attributes",
        "assign_operator",
        "escalate_conversation"
    ]
    target: dict
    parameters: dict
    conditions: list[dict]
    confidence: float

# plan.py
class APICall(BaseModel):
    tool: str
    params: dict
    description: str
    is_destructive: bool = False
    depends_on: list[int] = []  # Indices of prior steps

class ExecutionPlan(BaseModel):
    steps: list[APICall]
    explanation: str
    estimated_api_calls: int
    requires_confirmation: bool

# wati.py
class Contact(BaseModel):
    id: str
    whatsapp_number: str
    name: str | None
    tags: list[str]
    custom_params: dict[str, str]

class Template(BaseModel):
    name: str
    language: str
    parameters: list[str]
    category: str

# state.py
class AgentState(TypedDict):
    instruction: str
    mode: Literal["execute", "dry-run"]
    intent: Intent | None
    plan: ExecutionPlan | None
    validation_errors: list[str]
    needs_clarification: bool
    clarification_questions: list[str]
    execution_results: list[dict]
    execution_errors: list[dict]
    final_response: str
    success: bool
```

**Completion Criteria:**
- [ ] All models importable and validated with sample data
- [ ] Enums cover all action types from requirements
- [ ] Models have docstrings and examples

---

## Task 3: Mock WATI Client

**Goal:** Realistic mock API responses for development and demo.

**Deliverables:** `conductor/clients/mock.py`

**Details:**
- 50 mock contacts with realistic data (names, phone numbers, tags, attributes)
- 10 mock templates (renewal_reminder, flash_sale, vip_exclusive, etc.)
- Mock responses match real WATI API structure exactly
- Configurable delay (50-200ms) to simulate network latency
- Support all core endpoints from requirements

**Mock Data Generation:**

```python
class MockWATIClient:
    def __init__(self):
        self.contacts = self._generate_contacts()
        self.templates = self._generate_templates()
        self.delay_ms = 100
    
    def _generate_contacts(self) -> list[Contact]:
        """Generate 50 realistic contacts."""
        return [
            Contact(
                id=f"contact_{i}",
                whatsapp_number=f"62812345{i:04d}",
                name=f"Customer {i}",
                tags=["VIP"] if i % 5 == 0 else ["regular"],
                custom_params={
                    "city": "Jakarta" if i % 3 == 0 else "Surabaya",
                    "tier": "premium" if i % 5 == 0 else "standard"
                }
            )
            for i in range(50)
        ]
    
    async def get_contacts(
        self, 
        tag: str | None = None,
        page_size: int = 20
    ) -> dict:
        """Mock GET /api/v1/getContacts"""
        await asyncio.sleep(self.delay_ms / 1000)
        
        contacts = self.contacts
        if tag:
            contacts = [c for c in contacts if tag in c.tags]
        
        return {
            "result": True,
            "contacts": [c.model_dump() for c in contacts[:page_size]],
            "pageInfo": {
                "pageSize": page_size,
                "pageNumber": 1,
                "totalRecords": len(contacts)
            }
        }
```

**Completion Criteria:**
- [ ] All core endpoints implemented (contacts, messages, templates, operators)
- [ ] Responses match real API structure (verified against WATI docs)
- [ ] Edge cases handled (empty results, invalid params)
- [ ] Async interface with realistic delays

---

## Task 4: Real WATI Client (httpx)

**Goal:** Production-ready HTTP client for WATI API.

**Deliverables:** `conductor/clients/real.py`

**Details:**
- Async httpx client with proper headers (Authorization: Bearer)
- Rate limiting (token bucket, configurable)
- Retry logic for transient errors (network, timeout)
- Error mapping (WATI API errors → user-friendly messages)
- Request/response logging (debug mode)

**Implementation:**

```python
from httpx import AsyncClient, HTTPStatusError
from tenacity import retry, stop_after_attempt, wait_exponential

class RealWATIClient:
    def __init__(self, base_url: str, token: str, rate_limit: int = 10):
        self.base_url = base_url
        self.client = AsyncClient(
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0
        )
        self.rate_limiter = AsyncLimiter(rate_limit, 1.0)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        reraise=True
    )
    async def get_contacts(
        self,
        tag: str | None = None,
        page_size: int = 20
    ) -> dict:
        """GET /api/v1/getContacts"""
        async with self.rate_limiter:
            params = {"pageSize": page_size, "pageNumber": 1}
            if tag:
                params["tag"] = tag
            
            try:
                response = await self.client.get(
                    f"{self.base_url}/api/v1/getContacts",
                    params=params
                )
                response.raise_for_status()
                return response.json()
            except HTTPStatusError as e:
                raise WATIAPIError.from_response(e.response)
```

**Completion Criteria:**
- [ ] All core endpoints implemented
- [ ] Rate limiting works (tested with burst requests)
- [ ] Retry logic handles transient errors
- [ ] Error messages are user-friendly

---

## Task 5: LangChain Tool Definitions

**Goal:** Tool wrappers for LangGraph agent to call.

**Deliverables:** `conductor/tools/`

```
tools/
├── __init__.py
├── contacts.py     # search_contacts, get_contact_info, add_tag, update_attributes
├── messages.py     # send_session_message, send_template_message
├── templates.py    # list_templates, get_template_details
├── operators.py    # assign_operator, assign_team
└── broadcasts.py   # send_broadcast
```

**Tool Example:**

```python
from langchain.tools import tool

@tool
async def search_contacts(
    tag: str | None = None,
    attribute_name: str | None = None,
    attribute_value: str | None = None,
    page_size: int = 20
) -> dict:
    """
    Search for WhatsApp contacts by tag or custom attributes.
    
    Args:
        tag: Filter contacts by tag (e.g., "VIP", "new_signup")
        attribute_name: Custom attribute to filter by (e.g., "city")
        attribute_value: Value for the attribute (e.g., "Jakarta")
        page_size: Maximum number of results to return
    
    Returns:
        Dictionary with 'contacts' list and 'pageInfo'
    """
    client = get_wati_client()
    return await client.get_contacts(
        tag=tag,
        page_size=page_size
    )

@tool
async def send_template_message(
    whatsapp_number: str,
    template_name: str,
    parameters: dict[str, str]
) -> dict:
    """
    Send a WhatsApp template message to a contact.
    
    Args:
        whatsapp_number: Contact's WhatsApp number (e.g., "6281234567890")
        template_name: Name of the approved template (e.g., "renewal_reminder")
        parameters: Template parameters as key-value pairs (e.g., {"name": "John"})
    
    Returns:
        Dictionary with 'result' and 'messageId'
    """
    client = get_wati_client()
    
    # Convert parameters to WATI API format
    params_list = [
        {"name": f"body_{i+1}", "value": v}
        for i, v in enumerate(parameters.values())
    ]
    
    return await client.send_template_message(
        whatsapp_number=whatsapp_number,
        template_name=template_name,
        parameters=params_list
    )
```

**Completion Criteria:**
- [ ] 8-10 core tools implemented
- [ ] Tool descriptions are clear and LLM-friendly
- [ ] All tools have proper type hints and docstrings
- [ ] Tools delegate to client (mock or real)

---

## Task 6: Intent Parsing (LLM)

**Goal:** Extract structured intent from natural language.

**Deliverables:** `conductor/agent/parser.py`

**Details:**
- LLM call with structured output (Anthropic tool use or JSON mode)
- Few-shot examples for common patterns
- Confidence scoring
- Fallback to clarification on low confidence

**Implementation:**

```python
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate

PARSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an API orchestration planner for WATI WhatsApp Business API.
Parse user instructions into structured intent.

Available actions:
- send_template_to_segment: Send template to contacts matching criteria
- send_message_to_contact: Send text message to specific contact
- search_contacts: Find contacts by tag or attributes
- update_contact_attributes: Modify contact custom parameters
- assign_operator: Assign conversation to operator/team
- escalate_conversation: Escalate + tag + assign

Output JSON with:
{{
  "action": "<action_type>",
  "target": {{"type": "contacts|contact", "filter": {{...}}}},
  "parameters": {{...}},
  "confidence": 0.0-1.0
}}

Examples:
User: "Find all VIP contacts and send them the renewal reminder"
{{
  "action": "send_template_to_segment",
  "target": {{"type": "contacts", "filter": {{"tag": "VIP"}}}},
  "parameters": {{"template_name": "renewal_reminder"}},
  "confidence": 0.95
}}

User: "Escalate 6281234567890 to Support"
{{
  "action": "escalate_conversation",
  "target": {{"type": "contact", "phone": "6281234567890"}},
  "parameters": {{"team": "Support", "add_tag": "escalated"}},
  "confidence": 0.9
}}
"""),
    ("user", "{instruction}")
])

async def parse_intent(instruction: str) -> Intent:
    """Parse natural language instruction into structured intent."""
    llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)
    
    chain = PARSE_PROMPT | llm
    response = await chain.ainvoke({"instruction": instruction})
    
    # Extract JSON from response
    intent_data = extract_json(response.content)
    
    return Intent(**intent_data)
```

**Completion Criteria:**
- [ ] Parses all demo scenarios correctly
- [ ] Returns confidence scores
- [ ] Handles ambiguous input gracefully
- [ ] Few-shot examples cover common patterns

---

## Task 7: Plan Generation Logic

**Goal:** Translate intent into executable API call sequence.

**Deliverables:** `conductor/agent/planner.py`

**Details:**
- Rule-based plan generation for each action type
- Dependency resolution (step N needs output from step M)
- Validation (missing params, invalid combinations)
- Human-readable explanation

**Implementation:**

```python
def generate_plan(intent: Intent) -> ExecutionPlan:
    """Generate API call sequence from intent."""
    
    if intent.action == "send_template_to_segment":
        return _plan_send_template_to_segment(intent)
    elif intent.action == "escalate_conversation":
        return _plan_escalate_conversation(intent)
    # ... other action types
    
    raise ValueError(f"Unknown action: {intent.action}")

def _plan_send_template_to_segment(intent: Intent) -> ExecutionPlan:
    """Plan for sending template to contact segment."""
    steps = []
    
    # Step 1: Search contacts
    steps.append(APICall(
        tool="search_contacts",
        params={"tag": intent.target["filter"]["tag"]},
        description=f"Find contacts tagged '{intent.target['filter']['tag']}'"
    ))
    
    # Step 2: Get template details
    steps.append(APICall(
        tool="get_template_details",
        params={"template_name": intent.parameters["template_name"]},
        description=f"Get parameters for template '{intent.parameters['template_name']}'"
    ))
    
    # Step 3: Send template to each contact
    steps.append(APICall(
        tool="send_template_message_batch",
        params={
            "contacts": "$step_0.contacts",  # Reference to step 0 output
            "template_name": intent.parameters["template_name"],
            "parameters": "$step_1.parameters"  # Reference to step 1 output
        },
        description="Send template to all matching contacts",
        depends_on=[0, 1]
    ))
    
    return ExecutionPlan(
        steps=steps,
        explanation=f"Find {intent.target['filter']['tag']} contacts and send them the {intent.parameters['template_name']} template",
        estimated_api_calls=len(steps),
        requires_confirmation=True  # Bulk send requires confirmation
    )
```

**Completion Criteria:**
- [ ] Plans generated for all action types
- [ ] Dependencies correctly tracked
- [ ] Validation catches common errors
- [ ] Explanations are clear and accurate

---

## Task 8: LangGraph State Machine

**Goal:** Orchestrate agent flow with state management.

**Deliverables:** `conductor/agent/graph.py` + `conductor/agent/nodes/`

**Graph Structure:**

```python
from langgraph.graph import StateGraph, END

def create_agent_graph() -> StateGraph:
    """Create the agent state machine."""
    
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("parse", parse_node)
    graph.add_node("plan", plan_node)
    graph.add_node("validate", validate_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("execute", execute_node)
    
    # Add edges
    graph.set_entry_point("parse")
    
    graph.add_conditional_edges(
        "parse",
        route_after_parse,
        {"plan": "plan", "clarify": "clarify"}
    )
    
    graph.add_edge("plan", "validate")
    
    graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {"execute": "execute", "clarify": "clarify", END: END}
    )
    
    graph.add_edge("execute", END)
    graph.add_edge("clarify", END)  # Clarification ends flow, user must re-invoke
    
    return graph.compile()
```

**Node Implementations:**

```python
# nodes/parse.py
async def parse_node(state: AgentState) -> AgentState:
    """Parse user instruction into structured intent."""
    try:
        intent = await parse_intent(state["instruction"])
        return {**state, "intent": intent}
    except Exception as e:
        return {
            **state,
            "needs_clarification": True,
            "clarification_questions": [
                "I couldn't understand your instruction. Could you rephrase it?",
                f"Error: {str(e)}"
            ]
        }

# nodes/plan.py
async def plan_node(state: AgentState) -> AgentState:
    """Generate execution plan from intent."""
    plan = generate_plan(state["intent"])
    return {**state, "plan": plan}

# nodes/validate.py
async def validate_node(state: AgentState) -> AgentState:
    """Validate plan before execution."""
    errors = validate_plan(state["plan"])
    
    if errors:
        return {
            **state,
            "validation_errors": errors,
            "needs_clarification": True,
            "clarification_questions": [
                f"Issue: {error}" for error in errors
            ]
        }
    
    return state

# nodes/execute.py
async def execute_node(state: AgentState) -> AgentState:
    """Execute the plan."""
    results = []
    errors = []
    
    for i, step in enumerate(state["plan"].steps):
        try:
            result = await execute_tool(step, results)  # Pass prior results for dependencies
            results.append(result)
        except Exception as e:
            errors.append({"step": i, "error": str(e)})
    
    success = len(errors) == 0
    final_response = format_execution_summary(results, errors)
    
    return {
        **state,
        "execution_results": results,
        "execution_errors": errors,
        "final_response": final_response,
        "success": success
    }
```

**Completion Criteria:**
- [ ] Graph compiles without errors
- [ ] All nodes implemented
- [ ] Conditional routing works correctly
- [ ] State updates propagate properly

---

## Task 9: CLI Interface (Rich)

**Goal:** User-friendly command-line interface.

**Deliverables:** `conductor/cli.py`

**Features:**
- Rich formatting (colors, tables, panels)
- Progress bars for multi-step execution
- Interactive confirmations
- Verbose mode (show API details)
- Dry-run mode

**Implementation:**

```python
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer()
console = Console()

@app.command()
def run(
    instruction: str = typer.Argument(..., help="Natural language instruction"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview plan without executing"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed API calls"),
    mock: bool = typer.Option(True, "--mock", help="Use mock API client")
):
    """Execute a WATI automation instruction."""
    
    # Initialize agent
    agent = create_agent_graph()
    
    # Run agent
    state = {
        "instruction": instruction,
        "mode": "dry-run" if dry_run else "execute"
    }
    
    console.print(f"\n[bold]Instruction:[/bold] {instruction}\n")
    
    with console.status("[bold green]Parsing instruction..."):
        result = asyncio.run(agent.ainvoke(state))
    
    # Display results
    if result["needs_clarification"]:
        console.print("[yellow]⚠ Need clarification:[/yellow]")
        for q in result["clarification_questions"]:
            console.print(f"  • {q}")
        return
    
    # Display plan
    display_plan(result["plan"], result["mode"])
    
    if result["mode"] == "dry-run":
        console.print("\n[dim]Dry-run mode: no actions executed[/dim]")
        return
    
    # Confirm if needed
    if result["plan"].requires_confirmation:
        if not typer.confirm("\nProceed with execution?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    # Execute
    console.print("\n[bold]Executing...[/bold]\n")
    display_execution_progress(result["execution_results"], result["execution_errors"])
    
    # Summary
    display_final_summary(result)

def display_plan(plan: ExecutionPlan, mode: str):
    """Display execution plan as a table."""
    table = Table(title=f"Execution Plan ({mode} mode)")
    table.add_column("Step", style="cyan", no_wrap=True)
    table.add_column("Action", style="magenta")
    table.add_column("Description", style="green")
    
    for i, step in enumerate(plan.steps, 1):
        table.add_row(str(i), step.tool, step.description)
    
    console.print(table)
    console.print(f"\n[dim]{plan.explanation}[/dim]")

if __name__ == "__main__":
    app()
```

**Completion Criteria:**
- [ ] `conductor run "instruction"` works end-to-end
- [ ] `--dry-run` shows plan without executing
- [ ] `--verbose` shows API call details
- [ ] Interactive confirmations work
- [ ] Output is clear and professional

---

## Task 10: Error Handling + Retry Logic

**Goal:** Graceful degradation and recovery.

**Deliverables:** Error handling throughout codebase

**Key Areas:**
1. API client retry logic (tenacity)
2. Rate limit handling (exponential backoff)
3. Partial failure handling (continue execution, report failures)
4. User-friendly error messages

**Implementation:**

```python
# clients/errors.py
class WATIAPIError(Exception):
    """Base exception for WATI API errors."""
    
    @classmethod
    def from_response(cls, response: httpx.Response):
        """Create error from HTTP response."""
        if response.status_code == 429:
            return RateLimitError("Rate limit exceeded. Please wait before retrying.")
        elif response.status_code == 401:
            return AuthenticationError("Invalid API token.")
        elif response.status_code == 404:
            return NotFoundError(f"Resource not found: {response.url}")
        else:
            return cls(f"API error: {response.status_code} - {response.text}")

# agent/executor.py
async def execute_tool_with_recovery(
    step: APICall,
    prior_results: list[dict]
) -> dict:
    """Execute tool with error recovery."""
    try:
        return await execute_tool(step, prior_results)
    except RateLimitError as e:
        console.print(f"[yellow]⚠ Rate limit hit. Waiting 60s...[/yellow]")
        await asyncio.sleep(60)
        return await execute_tool(step, prior_results)  # Retry once
    except WATIAPIError as e:
        console.print(f"[red]✗ API error: {e}[/red]")
        raise
    except Exception as e:
        console.print(f"[red]✗ Unexpected error: {e}[/red]")
        raise
```

**Completion Criteria:**
- [ ] Rate limit errors trigger retry with backoff
- [ ] Partial failures don't crash entire execution
- [ ] Error messages are actionable
- [ ] Retry logic tested with mock failures

---

## Task 11: Demo Scenarios + Testing

**Goal:** Verify all functionality with realistic scenarios.

**Deliverables:**
- `examples/` directory with demo scripts
- `tests/` with unit and integration tests
- Demo video recording

**Demo Scenarios:**

1. **Simple search:**
   ```bash
   conductor run "Find all VIP contacts"
   ```

2. **Bulk template send:**
   ```bash
   conductor run "Send renewal_reminder template to all VIP contacts"
   ```

3. **Conditional assignment:**
   ```bash
   conductor run "Escalate 6281234567890 to Support team"
   ```

4. **Dry-run mode:**
   ```bash
   conductor run "Send flash_sale to all Jakarta contacts" --dry-run
   ```

5. **Error handling:**
   ```bash
   conductor run "Send invalid_template to VIP contacts"
   # Should show error: template not found
   ```

**Testing:**

```python
# tests/test_parser.py
async def test_parse_simple_instruction():
    intent = await parse_intent("Find all VIP contacts")
    assert intent.action == "search_contacts"
    assert intent.target["filter"]["tag"] == "VIP"

# tests/test_planner.py
def test_plan_send_template_to_segment():
    intent = Intent(
        action="send_template_to_segment",
        target={"type": "contacts", "filter": {"tag": "VIP"}},
        parameters={"template_name": "renewal_reminder"},
        confidence=0.9
    )
    plan = generate_plan(intent)
    assert len(plan.steps) == 3
    assert plan.steps[0].tool == "search_contacts"
    assert plan.requires_confirmation == True

# tests/test_integration.py
async def test_full_flow_with_mock():
    agent = create_agent_graph()
    result = await agent.ainvoke({
        "instruction": "Find all VIP contacts",
        "mode": "execute"
    })
    assert result["success"] == True
    assert len(result["execution_results"]) > 0
```

**Completion Criteria:**
- [ ] All 5 demo scenarios work correctly
- [ ] Unit tests pass (parser, planner, tools)
- [ ] Integration test passes (full flow)
- [ ] Demo video recorded (3-5 minutes)

---

## Post-Implementation Checklist

- [ ] README.md with setup instructions and examples
- [ ] .env.example with all required variables
- [ ] Code formatted (black, isort)
- [ ] Type hints throughout (mypy passes)
- [ ] Docstrings for all public functions
- [ ] Demo video recorded
- [ ] Write-up document created (architecture, trade-offs, V2 roadmap)

---

## V2 Roadmap (Out of Scope for v1)

- [ ] Conversational memory (multi-turn interactions)
- [ ] Rollback mechanisms for failed operations
- [ ] Web UI (chat interface)
- [ ] Real-time webhook handling
- [ ] Advanced scheduling (cron-like triggers)
- [ ] Multi-language support
- [ ] Authentication/authorization
- [ ] Comprehensive test suite (>80% coverage)
- [ ] Production deployment (Docker, k8s)
- [ ] LangSmith tracing integration
- [ ] Batch optimization (parallel API calls)
- [ ] Custom tool creation (user-defined workflows)
