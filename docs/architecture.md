# Architecture

## High-Level Architecture

WATI Conductor is a single-process AI agent that converts natural language into WATI WhatsApp API workflows. The LLM handles both instruction parsing and response generation; everything in between is deterministic.

```mermaid
graph LR
    subgraph User Layer
        CLI[CLI Interface<br/>Click + Rich]
    end

    subgraph Agent Core
        GRAPH[LangGraph<br/>State Machine]
        PARSE[Parser Node<br/>LLM → Intent]
        EXEC[Execute Node<br/>Tool Runner]
        RESP[Response Node<br/>LLM → Text]
    end

    subgraph Tool Layer
        REG[Tool Registry]
        CT[Contact Tools]
        MT[Message Tools]
        TT[Template Tools]
        OT[Operator Tools]
        TK[Ticket Tools]
    end

    subgraph Client Layer
        FAC[Client Factory]
        MOCK[Mock Client<br/>Local JSON]
        REAL[Real Client<br/>httpx → WATI API]
    end

    subgraph External
        LLM[LLM Provider<br/>DeepSeek / Claude / OpenAI]
        WATI[WATI API<br/>WhatsApp Business]
    end

    CLI -->|instruction| GRAPH
    GRAPH --> PARSE
    PARSE -->|Intent| EXEC
    EXEC -->|results| RESP
    RESP -->|text| CLI

    PARSE -.->|structured output| LLM
    RESP -.->|summarise| LLM

    EXEC --> REG
    REG --> CT & MT & TT & OT & TK
    CT & MT & TT & OT --> FAC
    FAC -->|USE_MOCK=true| MOCK
    FAC -->|USE_MOCK=false| REAL
    REAL -.-> WATI

    classDef user fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px,color:#000
    classDef agent fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000
    classDef tool fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#000
    classDef client fill:#e1f5ff,stroke:#01579b,stroke-width:2px,color:#000
    classDef external fill:#ffccbc,stroke:#d84315,stroke-width:2px,color:#000

    class CLI user
    class GRAPH,PARSE,EXEC,RESP agent
    class REG,CT,MT,TT,OT,TK tool
    class FAC,MOCK,REAL client
    class LLM,WATI external
```

## LangGraph State Machine

The agent uses a 3-node LangGraph graph. This is a deliberate simplification from the original v1 design (6 nodes) — the LLM handles planning directly, eliminating separate planner, validator, and clarifier nodes.

```mermaid
stateDiagram-v2
    [*] --> parse_intent

    parse_intent --> execute_plan: confidence >= 0.7 AND mode != dry-run
    parse_intent --> generate_response: confidence < 0.7 OR dry-run

    execute_plan --> generate_response: always

    generate_response --> [*]

    state parse_intent {
        [*] --> BuildPrompt: inject tool schemas + history
        BuildPrompt --> LLMCall: structured output → Intent
        LLMCall --> FilterTasks: drop tasks with confidence < 0.7
    }

    state execute_plan {
        [*] --> NextTask
        NextTask --> ResolveDeps: replace $task_N refs
        ResolveDeps --> Confirm: trust_mode=false
        ResolveDeps --> RunTool: trust_mode=true
        Confirm --> RunTool: user approves
        Confirm --> Rejected: user declines
        RunTool --> NextTask: more tasks
        RunTool --> Done: all tasks complete
        Rejected --> Done
    }

    state generate_response {
        [*] --> FormatResults
        FormatResults --> LLMSummarise: generate conversational reply
    }
```

### Node Responsibilities

| Node | File | LLM Call? | Purpose |
|---|---|---|---|
| `parse_intent` | `agent/parser.py` | Yes (structured output) | Decompose instruction into `Intent` with `Task[]` |
| `execute_plan` | `agent/nodes/execute.py` | No | Run tools sequentially, resolve `$task_N` references |
| `generate_response` | `agent/nodes/response.py` | Yes | Summarise results as natural language |

### State Schema (`AgentState`)

```python
class AgentState(TypedDict, total=False):
    instruction: str                    # User's natural language input
    mode: Literal["execute", "dry-run"] # Execution mode
    trust_mode: bool                    # Skip confirmations
    intent: Intent | None               # Parsed tasks from LLM
    execution_results: list[dict]       # Tool outputs per step
    execution_errors: list[dict]        # Errors per step
    user_rejected: bool                 # User declined a tool
    rejected_tool: str                  # Which tool was declined
    final_response: str                 # LLM-generated reply
    success: bool                       # Overall success flag
```

## Multi-Task Execution Flow

The key innovation is inter-task dependency resolution via `$task_N.field` references. The LLM generates these references during parsing; the executor resolves them at runtime.

```mermaid
sequenceDiagram
    participant U as User
    participant CLI as CLI
    participant P as parse_intent
    participant E as execute_plan
    participant T as Tools
    participant R as generate_response
    participant LLM as LLM Provider

    U->>CLI: "Find VIP contacts and send them welcome_wati"
    CLI->>P: instruction + history

    P->>LLM: system prompt + tool schemas + instruction
    LLM-->>P: Intent JSON (2 tasks)

    Note over P: Task 0: search_contacts(tag="VIP")<br/>Task 1: send_template_message_batch(<br/>  contacts="$task_0.contacts",<br/>  template_name="welcome_wati")

    P->>E: Intent with 2 tasks

    E->>T: search_contacts(tag="VIP")
    T-->>E: {contacts: [...], total: 10}

    Note over E: Resolve $task_0.contacts → actual contact list

    E->>T: send_template_message_batch(contacts=[...], template_name="welcome_wati")
    T-->>E: {sent: 10, failed: 0}

    E->>R: execution_results

    R->>LLM: instruction + results
    LLM-->>R: "I found 10 VIP contacts and sent the welcome_wati template to all of them."

    R-->>CLI: final_response
    CLI-->>U: Display response
```

## Data Flow

```mermaid
graph TD
    subgraph Input
        NL[Natural Language Instruction]
        HIST[Conversation History<br/>JSON file]
    end

    subgraph Parsing
        PROMPT[System Prompt<br/>+ Tool Schemas]
        INTENT[Intent Model<br/>tasks + confidence]
    end

    subgraph Execution
        RESOLVE[Dependency Resolution<br/>$task_N → actual values]
        TOOLS[Tool Invocations<br/>via registry]
        RESULTS[Execution Results<br/>list of dicts]
    end

    subgraph Client
        MOCK_DATA[Mock Data<br/>50 contacts, 6 templates]
        WATI_API[WATI REST API]
    end

    subgraph Output
        LLM_RESP[LLM Response Generation]
        FINAL[Conversational Reply]
    end

    NL --> PROMPT
    HIST --> PROMPT
    PROMPT --> INTENT
    INTENT --> RESOLVE
    RESOLVE --> TOOLS
    TOOLS --> MOCK_DATA
    TOOLS -.-> WATI_API
    MOCK_DATA --> RESULTS
    WATI_API -.-> RESULTS
    RESULTS --> LLM_RESP
    NL --> LLM_RESP
    LLM_RESP --> FINAL
    FINAL --> HIST

    classDef input fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px,color:#000
    classDef parse fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000
    classDef exec fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#000
    classDef client fill:#e1f5ff,stroke:#01579b,stroke-width:2px,color:#000
    classDef output fill:#ffccbc,stroke:#d84315,stroke-width:2px,color:#000

    class NL,HIST input
    class PROMPT,INTENT parse
    class RESOLVE,TOOLS,RESULTS exec
    class MOCK_DATA,WATI_API client
    class LLM_RESP,FINAL output
```

## Architecture Evolution: v1 → v2

### v1 (6 nodes — rule-based planner)

```
parse → plan → validate → execute → clarify → response
```

- Fixed action types (10 predefined)
- Rule-based plan generation in `planner.py`
- Separate validation node for parameter checking
- Clarification node for ambiguous input
- ~1,200 lines of code

### v2 (3 nodes — LLM-first)

```
parse → execute → response
```

- Dynamic tool selection (any registered tool)
- LLM generates tasks directly with structured output
- Confidence filtering replaces validation
- ~700 lines of code (~40% reduction)

The planner, validator, and clarifier nodes still exist in `agent/nodes/` but are no longer wired into the graph. They remain as reference code.

## LLM Provider Routing

The `llm_factory.py` module routes to different providers based on the model name in config:

```mermaid
graph LR
    CFG[Config<br/>LLM_PARSE_MODEL] --> DETECT{Model name contains?}
    DETECT -->|deepseek| DS[ChatOpenAI<br/>base_url=api.deepseek.com]
    DETECT -->|claude / anthropic| AN[ChatAnthropic]
    DETECT -->|gpt / openai| OA[ChatOpenAI]

    classDef config fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000
    classDef provider fill:#e1f5ff,stroke:#01579b,stroke-width:2px,color:#000

    class CFG config
    class DS,AN,OA provider
```

Switch providers by changing one env var — no code changes needed:

```bash
LLM_PARSE_MODEL=deepseek-chat      # Default, cheapest ($0.014/1M tokens)
LLM_PARSE_MODEL=claude-3-5-sonnet-20241022  # Higher quality
LLM_PARSE_MODEL=gpt-4o             # OpenAI alternative
```

## Communication Patterns

| Pattern | Used Between | Mechanism |
|---|---|---|
| Structured output | Parser → LLM | Pydantic model via `with_structured_output(Intent)` |
| Tool invocation | Executor → Tools | LangChain `@tool` decorated async functions |
| Client abstraction | Tools → WATI API | Protocol class (`WATIClient`) with mock/real implementations |
| State passing | Node → Node | LangGraph `AgentState` TypedDict |
| Conversation history | CLI → Parser | JSON file read via `history.py` |
