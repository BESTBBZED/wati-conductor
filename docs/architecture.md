# Architecture

## High-Level Architecture

WATI Conductor is a single-process AI agent that converts natural language into WATI WhatsApp API workflows. It uses a **ReAct (Reasoning + Acting) loop** — the LLM reasons about each step, calls one tool, observes the result, and decides what to do next.

```mermaid
graph LR
    subgraph User Layer
        CLI[CLI Interface<br/>Click + Rich]
    end

    subgraph Agent Core
        GRAPH[LangGraph<br/>ReAct Loop]
        AGENT[Agent Node<br/>LLM Think + Act]
        TOOL[Tool Node<br/>Execute + Observe]
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
        LLM[LLM Provider<br/>DeepSeek v4 Pro / Claude / OpenAI]
        WATI[WATI API<br/>WhatsApp Business]
    end

    CLI -->|instruction| GRAPH
    GRAPH --> AGENT
    AGENT -->|tool call| TOOL
    TOOL -->|result| AGENT
    AGENT -->|text response| CLI

    AGENT -.->|reason + select tool| LLM

    TOOL --> REG
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
    class GRAPH,AGENT,TOOL agent
    class REG,CT,MT,TT,OT,TK tool
    class FAC,MOCK,REAL client
    class LLM,WATI external
```

## LangGraph ReAct State Machine

The agent uses a 2-node LangGraph loop implementing the standard ReAct pattern. The LLM decides one action at a time, observes the result, and continues until it responds with plain text (no tool call).

```mermaid
stateDiagram-v2
    [*] --> agent_node

    agent_node --> tool_node: LLM returns tool call
    agent_node --> [*]: LLM returns text (done)
    agent_node --> [*]: dry-run mode (stop after first thought)
    agent_node --> [*]: max iterations reached

    tool_node --> agent_node: tool result (observe)

    state agent_node {
        [*] --> BuildMessages: system prompt + history + prior tool results
        BuildMessages --> LLMCall: invoke LLM with bound tools
        LLMCall --> CheckIterations: increment iteration_count
        CheckIterations --> ReturnResponse: tool_calls or text
    }

    state tool_node {
        [*] --> CheckTrust: trust_mode?
        CheckTrust --> Confirm: trust_mode=false
        CheckTrust --> Execute: trust_mode=true
        Confirm --> Execute: user approves
        Confirm --> Rejected: user declines
        Execute --> ReturnResult: ToolMessage with result
        Rejected --> ReturnResult: ToolMessage "user rejected"
    }
```

### Node Responsibilities

| Node | File | LLM Call? | Purpose |
|---|---|---|---|
| `agent_node` | `agent/react_nodes.py` | Yes (tool calling) | Reason about current state, select one tool or respond with text |
| `tool_node` | `agent/react_nodes.py` | No | Execute the selected tool, return result as `ToolMessage` |

### State Schema (`AgentState`)

```python
class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]  # All conversation messages
    iteration_count: int          # Think-act-observe cycles completed
    trust_mode: bool              # Skip per-tool confirmation prompts
    mode: Literal["execute", "dry-run"]  # Execution mode
    user_rejected: bool           # User declined a tool execution
    rejected_tool: str            # Which tool was declined
```

The key difference from the previous architecture: instead of separate fields for intent, execution results, and errors, **everything lives in the `messages` list** as LangChain message objects (`SystemMessage`, `HumanMessage`, `AIMessage`, `ToolMessage`). This is the standard LangGraph ReAct pattern.

## ReAct Execution Flow

The LLM reasons through multi-step instructions one tool call at a time, observing each result before deciding the next action.

```mermaid
sequenceDiagram
    participant U as User
    participant CLI as CLI
    participant A as agent_node
    participant T as tool_node
    participant LLM as LLM Provider

    U->>CLI: "Find VIP contacts and send them welcome_wati"
    CLI->>A: HumanMessage + system prompt

    Note over A: Iteration 1: Think
    A->>LLM: messages + bound tools
    LLM-->>A: AIMessage with tool_call: search_contacts(tag="VIP")

    A->>T: tool_call: search_contacts
    Note over T: Confirm with user (unless trust mode)
    T-->>A: ToolMessage: {contacts: [...], total: 10}

    Note over A: Iteration 2: Observe + Think
    A->>LLM: messages (now includes search result)
    LLM-->>A: AIMessage with tool_call: send_template_message_batch(contacts=[...], template="welcome_wati")

    A->>T: tool_call: send_template_message_batch
    T-->>A: ToolMessage: {sent: 10, failed: 0}

    Note over A: Iteration 3: Observe + Respond
    A->>LLM: messages (now includes send result)
    LLM-->>A: AIMessage: "Found 10 VIP contacts and sent welcome_wati to all of them."

    Note over A: No tool call → done
    A-->>CLI: final text response
    CLI-->>U: Display response
```

### Dynamic Adaptation Example

Unlike Plan-then-Execute, the ReAct agent adapts to unexpected results:

```mermaid
sequenceDiagram
    participant U as User
    participant A as agent_node
    participant T as tool_node
    participant LLM as LLM

    U->>A: "Send welcome_wati to all premium contacts"

    A->>LLM: Think: need to find premium contacts first
    LLM-->>A: tool_call: search_contacts(tag="premium")
    A->>T: execute search
    T-->>A: {contacts: [], total: 0}

    Note over A: Observes 0 results — adapts!
    A->>LLM: Think: search returned 0 contacts
    LLM-->>A: "No premium contacts found. Would you like me to search by a different tag or attribute?"

    Note over A: No tool call → responds to user
    A-->>U: Informs user instead of blindly sending to empty list
```

## Data Flow

```mermaid
graph TD
    subgraph Input
        NL[Natural Language Instruction]
        HIST[Conversation History<br/>JSON file]
    end

    subgraph ReAct Loop
        SYS[System Prompt<br/>+ Recent Context]
        AGENT[Agent Node<br/>LLM with bound tools]
        TOOL_EXEC[Tool Node<br/>Execute + confirm]
        MSGS[Message History<br/>accumulates per loop]
    end

    subgraph Client
        MOCK_DATA[Mock Data<br/>50 contacts, 6 templates]
        WATI_API[WATI REST API]
    end

    subgraph Output
        FINAL[Final Text Response<br/>last AIMessage without tool calls]
    end

    NL --> SYS
    HIST --> SYS
    SYS --> AGENT
    AGENT -->|tool call| TOOL_EXEC
    TOOL_EXEC -->|ToolMessage| MSGS
    MSGS --> AGENT
    TOOL_EXEC --> MOCK_DATA
    TOOL_EXEC -.-> WATI_API
    AGENT -->|text response| FINAL
    FINAL --> HIST

    classDef input fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px,color:#000
    classDef react fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000
    classDef client fill:#e1f5ff,stroke:#01579b,stroke-width:2px,color:#000
    classDef output fill:#ffccbc,stroke:#d84315,stroke-width:2px,color:#000

    class NL,HIST input
    class SYS,AGENT,TOOL_EXEC,MSGS react
    class MOCK_DATA,WATI_API client
    class FINAL output
```

## Architecture Evolution

### v1 (6 nodes — rule-based planner)

```
parse → plan → validate → execute → clarify → response
```

- Fixed action types (10 predefined)
- Rule-based plan generation in `planner.py`
- Separate validation node for parameter checking
- ~1,200 lines of code

### v2 (3 nodes — LLM-first plan-then-execute)

```
parse_intent → execute_plan → generate_response
```

- LLM generates all tasks upfront via structured output
- Sequential execution with `$task_N` dependency resolution
- 2 LLM calls per instruction (parse + response)
- ~700 lines of code

### v3 (2 nodes — ReAct loop) ← **current**

```
agent_node ↔ tool_node (loop until done)
```

- LLM reasons step-by-step, one tool call at a time
- Each tool result feeds back to LLM for observation
- Dynamic replanning — adapts to unexpected results
- N LLM calls per instruction (one per think-act-observe cycle)
- ~200 lines of agent code (react_graph.py + react_nodes.py)

### Why ReAct over Plan-then-Execute

| Aspect | Plan-then-Execute (v2) | ReAct (v3) |
|---|---|---|
| Planning | Single LLM call generates ALL tasks upfront | LLM decides ONE action at a time |
| Execution | Sequential, no LLM involvement | Each tool result feeds back to LLM |
| Adaptation | None — can't adjust if tool returns unexpected results | LLM observes results and adapts dynamically |
| Error handling | Stops on first error | LLM reasons about errors and tries alternatives |
| LLM calls | 2 per instruction | N per instruction (one per cycle) |
| Code complexity | Custom parser, dependency resolver, response generator | Standard LangGraph ReAct pattern |

## LLM Provider Routing

The `llm_factory.py` module routes to different providers based on the model name in config:

```mermaid
graph LR
    CFG[Config<br/>LLM_REACT_MODEL] --> DETECT{Model name contains?}
    DETECT -->|deepseek| DS[ChatOpenAI<br/>base_url=api.deepseek.com<br/>thinking: disabled]
    DETECT -->|claude / anthropic| AN[ChatAnthropic]
    DETECT -->|gpt / openai| OA[ChatOpenAI]

    BIND[bind_tools<br/>16 WATI tools] --> REACT[ReAct LLM<br/>ready for agent_node]

    DS --> BIND
    AN --> BIND
    OA --> BIND

    classDef config fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000
    classDef provider fill:#e1f5ff,stroke:#01579b,stroke-width:2px,color:#000
    classDef bind fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#000

    class CFG config
    class DS,AN,OA provider
    class BIND,REACT bind
```

Switch providers by changing one env var — no code changes needed:

```bash
LLM_REACT_MODEL=deepseek-v4-pro    # Default, strong reasoning
LLM_REACT_MODEL=deepseek-v4-flash  # Cheaper, faster
LLM_REACT_MODEL=claude-3-5-sonnet-20241022  # Anthropic
LLM_REACT_MODEL=gpt-4o             # OpenAI
```

DeepSeek v4 models have thinking mode explicitly disabled (`{"thinking": {"type": "disabled"}}`) to avoid conflicts with temperature settings and reduce latency in the multi-call ReAct loop.

## Communication Patterns

| Pattern | Used Between | Mechanism |
|---|---|---|
| Native tool calling | Agent → LLM | `model.bind_tools(tools)` — LLM returns `tool_calls` in response |
| Tool execution | Tool node → Tools | LangChain `@tool` decorated async functions via registry |
| Client abstraction | Tools → WATI API | Protocol class (`WATIClient`) with mock/real implementations |
| Message passing | Node → Node | LangGraph `AgentState.messages` list with `add_messages` reducer |
| Conversation history | CLI → Agent | JSON file read via `history.py`, injected into system prompt |
| Human-in-the-loop | Tool node → User | Console prompt before each tool execution (unless trust mode) |
