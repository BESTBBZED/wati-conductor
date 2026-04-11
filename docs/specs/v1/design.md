# WATI Conductor v1 — System Design

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLI Interface (Rich)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐│
│  │ Input Parser │  │ Output       │  │ Interactive Prompter   ││
│  │              │  │ Formatter    │  │ (confirmations)        ││
│  └──────────────┘  └──────────────┘  └────────────────────────┘│
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ invoke_agent(instruction)
┌────────────────────────────▼────────────────────────────────────┐
│                   LangGraph Agent (State Machine)                │
│                                                                  │
│  ┌────────┐   ┌─────────┐   ┌──────────┐   ┌────────┐         │
│  │ parse  │──▶│ plan    │──▶│ validate │──▶│ execute│──▶END   │
│  └────────┘   └─────────┘   └──────────┘   └────────┘         │
│       │            │              │              │              │
│       │            │              │              │              │
│       │            │              ▼              │              │
│       │            │         ┌─────────┐        │              │
│       │            │         │ clarify │        │              │
│       │            │         └─────────┘        │              │
│       │            │              │              │              │
│       │            └──────────────┘              │              │
│       │                                          │              │
│       └──────────────────────────────────────────┘              │
│                                                                  │
│  State: {instruction, intent, plan, results, errors}            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ tool calls
┌────────────────────────────▼────────────────────────────────────┐
│                      LangChain Tools                             │
│                                                                  │
│  search_contacts  │  send_template_message  │  assign_operator  │
│  get_contact_info │  send_session_message   │  create_ticket    │
│  add_contact_tag  │  list_templates         │  send_broadcast   │
│  update_attributes│  get_template_details   │                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP calls
┌────────────────────────────▼────────────────────────────────────┐
│                      WATI API Client                             │
│                                                                  │
│  ┌──────────────┐         ┌──────────────┐                     │
│  │ Real Client  │         │ Mock Client  │                     │
│  │ (httpx)      │         │ (in-memory)  │                     │
│  └──────────────┘         └──────────────┘                     │
│                                                                  │
│  Rate Limiter │ Retry Logic │ Error Mapping                     │
└──────────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. LangGraph State Machine

#### State Schema

```python
from typing import TypedDict, Literal
from pydantic import BaseModel

class AgentState(TypedDict):
    # Input
    instruction: str              # Raw user instruction
    mode: Literal["execute", "dry-run"]
    
    # Parsing
    intent: dict | None           # Structured intent from LLM
    entities: dict                # Extracted entities (contacts, tags, templates)
    
    # Planning
    plan: list[dict] | None       # Sequence of API calls
    plan_explanation: str         # Human-readable plan description
    
    # Validation
    validation_errors: list[str]  # Issues found during validation
    needs_clarification: bool     # Flag for ambiguous input
    clarification_questions: list[str]
    
    # Execution
    execution_results: list[dict] # Results from each API call
    execution_errors: list[dict]  # Errors encountered
    progress: dict                # Current execution progress
    
    # Output
    final_response: str           # Summary for user
    success: bool
```

#### Node Definitions

| Node | Input | Logic | Output |
|------|-------|-------|--------|
| `parse` | Raw instruction | LLM extracts intent + entities with structured output | State with `intent` and `entities` |
| `plan` | Intent + entities | LLM generates API call sequence, validates against tool schemas | State with `plan` and `plan_explanation` |
| `validate` | Plan | Check for missing params, invalid combinations, rate limit concerns | State with `validation_errors` or proceed flag |
| `clarify` | Validation errors | Generate clarifying questions for user | State with `clarification_questions` |
| `execute` | Validated plan | Execute tools sequentially, handle errors, report progress | State with `execution_results` and `final_response` |

#### Conditional Edges

```python
def route_after_parse(state: AgentState) -> str:
    """Route after parsing intent."""
    if not state["intent"]:
        return "clarify"  # Failed to parse, ask for clarification
    return "plan"

def route_after_validate(state: AgentState) -> str:
    """Route after plan validation."""
    if state["validation_errors"]:
        return "clarify"  # Invalid plan, need more info
    if state["mode"] == "dry-run":
        return END        # Just preview, don't execute
    return "execute"

def route_after_clarify(state: AgentState) -> str:
    """After clarification, re-parse with new info."""
    return "parse"
```

### 2. Intent Parsing Strategy

#### LLM Prompt Design

**System Prompt:**
```
You are an API orchestration planner for WATI WhatsApp Business API.
Parse user instructions into structured intent.

Available API domains:
- Contacts: search, add/update attributes, manage tags
- Messages: send text, send template messages
- Templates: list, get details
- Broadcasts: send to segments
- Operators: assign conversations, manage tickets

Output JSON with:
{
  "action": "send_template" | "search_contacts" | "assign_operator" | ...,
  "target": {"type": "contacts", "filter": {...}},
  "parameters": {...},
  "conditions": [...]
}
```

**Few-Shot Examples:**
```json
[
  {
    "user": "Find all VIP contacts and send them the renewal reminder",
    "intent": {
      "action": "send_template_to_segment",
      "target": {"type": "contacts", "filter": {"tag": "VIP"}},
      "parameters": {"template_name": "renewal_reminder"},
      "conditions": []
    }
  },
  {
    "user": "Escalate 6281234567890 to Support team",
    "intent": {
      "action": "escalate_conversation",
      "target": {"type": "contact", "phone": "6281234567890"},
      "parameters": {"team": "Support", "add_tag": "escalated"},
      "conditions": []
    }
  }
]
```

#### Structured Output Schema

```python
class Intent(BaseModel):
    action: Literal[
        "send_template_to_segment",
        "send_message_to_contact",
        "search_contacts",
        "update_contact_attributes",
        "assign_operator",
        "create_broadcast",
        "escalate_conversation"
    ]
    target: dict  # {type, filter/phone/id}
    parameters: dict
    conditions: list[dict]
    confidence: float  # 0.0-1.0
```

### 3. Plan Generation

#### Planning Logic

```python
def generate_plan(intent: Intent, entities: dict) -> list[APICall]:
    """
    Translate intent into sequence of API calls.
    
    Example:
    Intent: send_template_to_segment
    Target: contacts with tag=VIP
    Parameters: template_name=renewal_reminder
    
    Plan:
    1. GET /api/v1/getContacts?tag=VIP
    2. For each contact:
       a. GET /api/v1/getContactInfo/{number} (to get name for template param)
       b. POST /api/v1/sendTemplateMessage/{number} (with parameters)
    """
    plan = []
    
    if intent.action == "send_template_to_segment":
        # Step 1: Search contacts
        plan.append(APICall(
            tool="search_contacts",
            params={"tag": intent.target["filter"]["tag"]},
            description=f"Find contacts tagged '{intent.target['filter']['tag']}'"
        ))
        
        # Step 2: Get template details (to know required parameters)
        plan.append(APICall(
            tool="get_template_details",
            params={"template_name": intent.parameters["template_name"]},
            description=f"Get parameters for template '{intent.parameters['template_name']}'"
        ))
        
        # Step 3: For each contact, send template
        plan.append(APICall(
            tool="send_template_message_batch",
            params={
                "contacts": "$contacts_from_step_1",
                "template_name": intent.parameters["template_name"],
                "parameter_mapping": "$template_params_from_step_2"
            },
            description="Send template to all matching contacts"
        ))
    
    return plan
```

#### Plan Validation

```python
def validate_plan(plan: list[APICall]) -> list[str]:
    """Check for issues before execution."""
    errors = []
    
    # Check for missing parameters
    for call in plan:
        if "$" in str(call.params):  # Unresolved variable
            if not has_dependency(call, plan):
                errors.append(f"Missing parameter: {call.params}")
    
    # Check for rate limit concerns
    batch_size = sum(1 for c in plan if c.tool.startswith("send_"))
    if batch_size > 100:
        errors.append(f"Large batch ({batch_size} messages) may hit rate limits")
    
    # Check for destructive actions without confirmation
    if any(c.tool in ["delete_contact", "cancel_order"] for c in plan):
        if not state.get("confirmed"):
            errors.append("Destructive action requires confirmation")
    
    return errors
```

### 4. Tool Definitions

#### Tool Schema

```python
from langchain.tools import tool
from pydantic import BaseModel, Field

class SearchContactsInput(BaseModel):
    tag: str | None = Field(None, description="Filter by tag")
    attribute_name: str | None = Field(None, description="Attribute to filter by")
    attribute_value: str | None = Field(None, description="Attribute value")
    page_size: int = Field(20, description="Results per page")

@tool
async def search_contacts(
    tag: str | None = None,
    attribute_name: str | None = None,
    attribute_value: str | None = None,
    page_size: int = 20
) -> dict:
    """
    Search for contacts by tag or custom attributes.
    
    Returns list of contacts with phone numbers and basic info.
    """
    client = get_wati_client()
    
    if tag:
        return await client.get_contacts(tag=tag, page_size=page_size)
    elif attribute_name and attribute_value:
        # Filter by custom attribute (requires fetching all and filtering)
        contacts = await client.get_contacts(page_size=page_size)
        return filter_by_attribute(contacts, attribute_name, attribute_value)
    else:
        return await client.get_contacts(page_size=page_size)
```

#### Core Tools

| Tool | WATI API Endpoint | Description |
|------|-------------------|-------------|
| `search_contacts` | GET /api/v1/getContacts | Search by tag or attributes |
| `get_contact_info` | GET /api/v1/getContactInfo/{number} | Get detailed contact info |
| `add_contact_tag` | POST /api/v1/addTag/{number} | Add tag to contact |
| `remove_contact_tag` | DELETE /api/v1/removeTag/{number}/{tag} | Remove tag |
| `update_contact_attributes` | POST /api/v1/updateContactAttributes/{number} | Update custom params |
| `send_session_message` | POST /api/v1/sendSessionMessage/{number} | Send text message |
| `send_template_message` | POST /api/v2/sendTemplateMessage/{number} | Send template with params |
| `list_templates` | GET /api/v1/getMessageTemplates | List available templates |
| `get_template_details` | GET /api/v1/getMessageTemplates (filter by name) | Get template structure |
| `send_broadcast` | POST /api/v1/sendBroadcastToSegment | Send to segment |
| `assign_operator` | POST /api/v1/assignOperator/{number} | Assign to operator |
| `assign_team` | POST /api/v1/tickets/assign | Assign to team |

### 5. WATI API Client

#### Client Interface

```python
class WATIClient(Protocol):
    """Abstract interface for WATI API."""
    
    async def get_contacts(
        self, 
        tag: str | None = None, 
        page_size: int = 20
    ) -> dict: ...
    
    async def get_contact_info(self, whatsapp_number: str) -> dict: ...
    
    async def add_tag(self, whatsapp_number: str, tag: str) -> dict: ...
    
    async def send_template_message(
        self,
        whatsapp_number: str,
        template_name: str,
        parameters: list[dict]
    ) -> dict: ...
    
    # ... other methods
```

#### Real Client Implementation

```python
class RealWATIClient:
    """Production client using httpx."""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0
        )
        self.rate_limiter = AsyncLimiter(max_rate=10, time_period=1)  # 10 req/s
    
    async def get_contacts(self, tag: str | None = None, page_size: int = 20) -> dict:
        async with self.rate_limiter:
            params = {"pageSize": page_size, "pageNumber": 1}
            if tag:
                params["tag"] = tag
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/getContacts",
                params=params
            )
            response.raise_for_status()
            return response.json()
```

#### Mock Client Implementation

```python
class MockWATIClient:
    """Mock client with realistic responses."""
    
    def __init__(self):
        self.contacts_db = self._generate_mock_contacts()
        self.templates_db = self._generate_mock_templates()
        self.delay_ms = 100  # Simulate network latency
    
    async def get_contacts(self, tag: str | None = None, page_size: int = 20) -> dict:
        await asyncio.sleep(self.delay_ms / 1000)
        
        contacts = self.contacts_db
        if tag:
            contacts = [c for c in contacts if tag in c.get("tags", [])]
        
        return {
            "result": True,
            "contacts": contacts[:page_size],
            "pageInfo": {
                "pageSize": page_size,
                "pageNumber": 1,
                "totalRecords": len(contacts)
            }
        }
    
    def _generate_mock_contacts(self) -> list[dict]:
        """Generate 50 realistic mock contacts."""
        return [
            {
                "id": f"contact_{i}",
                "whatsappNumber": f"62812345{i:04d}",
                "name": f"Customer {i}",
                "tags": ["VIP"] if i % 5 == 0 else ["regular"],
                "customParams": [
                    {"name": "city", "value": "Jakarta" if i % 3 == 0 else "Surabaya"},
                    {"name": "tier", "value": "premium" if i % 5 == 0 else "standard"}
                ]
            }
            for i in range(50)
        ]
```

### 6. CLI Interface

#### Rich Formatting

```python
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

def display_plan(plan: list[APICall], mode: str):
    """Display execution plan in a table."""
    table = Table(title=f"Execution Plan ({mode} mode)")
    table.add_column("Step", style="cyan", no_wrap=True)
    table.add_column("Action", style="magenta")
    table.add_column("Description", style="green")
    
    for i, call in enumerate(plan, 1):
        table.add_row(
            str(i),
            call.tool,
            call.description
        )
    
    console.print(table)

def display_execution_progress(plan: list[APICall]):
    """Show progress bar during execution."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Executing plan...", total=len(plan))
        
        for call in plan:
            progress.update(task, description=f"Running: {call.description}")
            result = execute_tool(call)
            progress.advance(task)
            
            if result.error:
                console.print(f"[red]✗[/red] {call.description}: {result.error}")
            else:
                console.print(f"[green]✓[/green] {call.description}")

def display_final_summary(results: dict):
    """Show execution summary."""
    panel = Panel(
        f"""
[bold green]Execution Complete[/bold green]

Total steps: {results['total']}
Successful: {results['success']}
Failed: {results['failed']}

{results['summary']}
        """,
        title="Summary",
        border_style="green"
    )
    console.print(panel)
```

#### Interactive Confirmation

```python
from rich.prompt import Confirm, Prompt

def confirm_destructive_action(plan: list[APICall]) -> bool:
    """Ask user to confirm before executing."""
    console.print("\n[yellow]⚠ This action will:[/yellow]")
    for call in plan:
        if call.is_destructive:
            console.print(f"  • {call.description}")
    
    return Confirm.ask("\nProceed with execution?", default=False)

def ask_clarification(questions: list[str]) -> dict:
    """Prompt user for missing information."""
    console.print("\n[yellow]I need more information:[/yellow]")
    answers = {}
    
    for q in questions:
        answer = Prompt.ask(f"  {q}")
        answers[q] = answer
    
    return answers
```

### 7. Error Handling Strategy

#### Error Categories

| Error Type | Handling Strategy | User Message |
|------------|-------------------|--------------|
| **Parsing Error** | Ask clarifying questions | "I didn't understand X. Could you clarify...?" |
| **Validation Error** | Show specific issue + suggestion | "Missing parameter: template_name. Available templates: ..." |
| **API Rate Limit** | Exponential backoff + retry | "Rate limit hit. Waiting 60s before retry..." |
| **API 4xx Error** | Show error details + recovery steps | "Invalid phone number format. Expected: 628..." |
| **API 5xx Error** | Retry 3x, then fail gracefully | "WATI API unavailable. Please try again later." |
| **Network Timeout** | Retry with longer timeout | "Request timed out. Retrying with extended timeout..." |
| **Partial Failure** | Continue execution, report failures | "✓ 45/50 sent. ✗ 5 failed (see details below)" |

#### Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    reraise=True
)
async def execute_api_call_with_retry(call: APICall) -> dict:
    """Execute API call with automatic retry on transient errors."""
    return await wati_client.execute(call)
```

### 8. Configuration Management

#### Settings Schema

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # WATI API
    wati_base_url: str = "https://live-mt-server.wati.io"
    wati_tenant_id: str
    wati_token: str
    
    # Mode
    use_mock: bool = False
    dry_run_default: bool = False
    
    # LLM
    llm_provider: Literal["anthropic", "openai"] = "anthropic"
    llm_model: str = "claude-3-5-sonnet-20241022"
    llm_api_key: str
    llm_temperature: float = 0.0
    
    # Rate Limiting
    max_requests_per_second: int = 10
    max_concurrent_requests: int = 5
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

#### .env.example

```bash
# WATI API Configuration
WATI_TENANT_ID=your_tenant_id
WATI_TOKEN=your_api_token

# LLM Configuration
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
LLM_API_KEY=your_anthropic_key

# Mode
USE_MOCK=true
DRY_RUN_DEFAULT=false

# Rate Limiting
MAX_REQUESTS_PER_SECOND=10
MAX_CONCURRENT_REQUESTS=5

# Logging
LOG_LEVEL=INFO
```

## Data Flow: End-to-End Example

```
User: "Find all VIP contacts and send them the renewal reminder"
  │
  ▼ CLI parses input
  │
  ▼ [parse] LLM extracts intent:
  │   action: send_template_to_segment
  │   target: {type: contacts, filter: {tag: VIP}}
  │   parameters: {template_name: renewal_reminder}
  │
  ▼ [plan] Generate API call sequence:
  │   1. search_contacts(tag="VIP")
  │   2. get_template_details(name="renewal_reminder")
  │   3. send_template_message_batch(contacts=$1, template=$2)
  │
  ▼ [validate] Check plan:
  │   ✓ All parameters resolvable
  │   ✓ Template exists
  │   ⚠ Batch size unknown (depends on step 1 result)
  │
  ▼ Display plan to user (rich table)
  │
  ▼ [execute] Run tools sequentially:
  │   Step 1: search_contacts → 15 contacts found
  │   Step 2: get_template_details → requires param: {name}
  │   Step 3: send_template_message_batch → 14 sent, 1 failed
  │
  ▼ Display progress (rich progress bar)
  │
  ▼ Display final summary (rich panel)
  │   ✓ 14 messages sent
  │   ✗ 1 failed (contact_10: invalid template parameter)
```

## Testing Strategy

### Unit Tests
- Tool functions with mock API responses
- Intent parsing with various input formats
- Plan generation for each action type
- Validation logic edge cases

### Integration Tests
- Full agent flow with mock client
- Error handling scenarios
- Retry logic verification

### Manual Testing (Demo Scenarios)
1. Simple single-step action
2. Multi-step workflow with dependencies
3. Ambiguous input requiring clarification
4. Error recovery (rate limit, invalid param)
5. Dry-run mode preview

## Performance Considerations

- **Async execution**: All API calls use httpx async client
- **Batch operations**: Group similar calls when possible
- **Rate limiting**: Token bucket algorithm, configurable limits
- **Caching**: Template details cached for session duration
- **Streaming**: LLM responses streamed to CLI for perceived speed

## Security Considerations

- API tokens in `.env` only, never in code
- `.env` in `.gitignore`
- Input sanitization (prevent injection attacks)
- No sensitive data in logs (mask phone numbers, tokens)
- Mock mode for demos (no real API calls)
