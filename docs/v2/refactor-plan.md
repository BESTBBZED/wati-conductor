# WATI Conductor v2: Interactive CLI Refactor Plan

**Goal**: Transform single-shot CLI into persistent interactive session (like Amazon Kiro)

**Current State**: One-off command execution (`python -m conductor.cli "instruction"`)  
**Target State**: REPL-style chat interface with session memory and multi-turn conversations

---

## Impact Analysis

### 🟢 Low Impact (Reusable)
- **Agent graph logic** (`conductor/agent/`) - Core ReAct flow unchanged
- **Tools** (`conductor/tools/`) - LangChain tools remain identical
- **Models** (`conductor/models/`) - Pydantic schemas reusable
- **Clients** (`conductor/clients/`) - WATI API clients unchanged

### 🟡 Medium Impact (Refactor)
- **CLI interface** (`conductor/cli.py`) - Replace Click with REPL loop
- **State management** - Add session persistence (LangGraph checkpointer)
- **Confirmation flow** - Adapt for interactive context

### 🔴 High Impact (New Components)
- **Session manager** - Handle conversation history and context
- **Streaming output** - Token-by-token display for LLM responses
- **Command parser** - Support `/help`, `/history`, `/clear` meta-commands
- **Graceful exit** - Handle Ctrl+C, `/quit`, cleanup

---

## Architecture Changes

### Current: Stateless Single-Shot
```
User Input → Agent Graph → Execute → Output → Exit
```

### Target: Stateful REPL
```
┌─────────────────────────────────────────┐
│         Interactive Session             │
│  ┌───────────────────────────────────┐  │
│  │  REPL Loop                        │  │
│  │    ↓                              │  │
│  │  Parse Input (instruction/command)│  │
│  │    ↓                              │  │
│  │  Agent Graph (with session state) │  │
│  │    ↓                              │  │
│  │  Stream Response                  │  │
│  │    ↓                              │  │
│  │  Update Session Memory            │  │
│  │    ↓                              │  │
│  │  Wait for Next Input              │  │
│  └───────────────────────────────────┘  │
│                                         │
│  Session State:                         │
│  - Conversation history                 │
│  - User preferences (trust mode, etc.)  │
│  - Execution context                    │
└─────────────────────────────────────────┘
```

---

## Phase 1: Requirements

### Functional Requirements

**FR-1: REPL Interface**
- Start interactive session with `python -m conductor.cli` (no args)
- Display welcome banner and prompt (`wati> `)
- Accept multi-line input (Ctrl+D to submit)
- Support command history (up/down arrows)

**FR-2: Meta Commands**
- `/help` - Show available commands
- `/history` - Show conversation history
- `/clear` - Clear session state
- `/trust on|off` - Toggle auto-approval
- `/quit` or Ctrl+D - Exit gracefully

**FR-3: Session Memory**
- Remember previous instructions and results
- Support follow-up questions ("send it to VIP contacts too")
- Persist session to disk (optional resume)

**FR-4: Streaming Responses**
- Stream LLM thinking process token-by-token
- Show tool execution progress in real-time
- Maintain rich formatting (colors, tables)

**FR-5: Backward Compatibility**
- Keep single-shot mode: `python -m conductor.cli "instruction"`
- Preserve `--dry-run`, `--verbose`, `--trust` flags

### Non-Functional Requirements

**NFR-1: Performance**
- Session startup < 2s
- Response latency < 500ms for first token

**NFR-2: UX**
- Clear visual separation between user/agent messages
- Graceful error handling (no stack traces in REPL)
- Keyboard shortcuts (Ctrl+C = cancel current, Ctrl+D = exit)

**NFR-3: Maintainability**
- Separate REPL logic from agent logic
- Testable session management
- Minimal changes to existing agent code

---

## Phase 2: Design

### Component Architecture

```
conductor/
├── cli.py                    # Entry point (detect mode)
├── repl/                     # NEW: Interactive mode
│   ├── __init__.py
│   ├── session.py            # Session state management
│   ├── loop.py               # Main REPL loop
│   ├── commands.py           # Meta command handlers
│   ├── streaming.py          # Token streaming utilities
│   └── ui.py                 # Rich UI components
├── agent/                    # UNCHANGED
│   ├── graph.py
│   ├── parser.py
│   ├── planner.py
│   └── nodes/
├── tools/                    # UNCHANGED
├── models/                   # MINOR: Add SessionState
└── clients/                  # UNCHANGED
```

### Key Classes

#### 1. Session Manager
```python
class Session:
    """Manages conversation state across turns."""
    
    def __init__(self, session_id: str):
        self.id = session_id
        self.history: list[Message] = []
        self.preferences: dict = {"trust_mode": False}
        self.checkpointer = MemorySaver()  # LangGraph checkpointer
    
    async def add_turn(self, user_input: str, agent_response: str):
        """Record a conversation turn."""
        
    async def get_context(self) -> dict:
        """Get relevant context for next agent invocation."""
        
    async def save(self, path: Path):
        """Persist session to disk."""
```

#### 2. REPL Loop
```python
class REPLLoop:
    """Main interactive loop."""
    
    def __init__(self, session: Session):
        self.session = session
        self.agent = create_agent_graph()
        self.running = True
    
    async def run(self):
        """Start REPL loop."""
        while self.running:
            user_input = await self.prompt()
            
            if user_input.startswith("/"):
                await self.handle_command(user_input)
            else:
                await self.handle_instruction(user_input)
    
    async def handle_instruction(self, instruction: str):
        """Process natural language instruction."""
        # Invoke agent with session context
        # Stream response
        # Update session
```

#### 3. Streaming Handler
```python
class StreamingHandler:
    """Handle token streaming from LLM."""
    
    async def stream_response(self, agent_stream):
        """Display tokens as they arrive."""
        async for chunk in agent_stream:
            if chunk["type"] == "thinking":
                console.print(chunk["content"], end="")
            elif chunk["type"] == "tool_call":
                self.display_tool_progress(chunk)
```

### State Management

**Session State Schema**:
```python
class SessionState(BaseModel):
    session_id: str
    created_at: datetime
    last_active: datetime
    conversation_history: list[ConversationTurn]
    preferences: UserPreferences
    execution_context: dict  # Last plan, results, etc.
```

**LangGraph Integration**:
- Use `MemorySaver` checkpointer for in-memory sessions
- Use `SqliteSaver` for persistent sessions (optional)
- Thread ID = session ID for conversation continuity

### UI Design

**Welcome Banner**:
```
╔══════════════════════════════════════════════════════════╗
║          WATI Conductor - Interactive Mode              ║
║  Natural language → WhatsApp automation workflows       ║
╚══════════════════════════════════════════════════════════╝

Type your instruction or /help for commands
Trust mode: OFF | Session: abc123

wati> _
```

**Conversation Flow**:
```
wati> Find all VIP contacts

🤔 Thinking...
Intent: search_contacts (confidence: 0.95)
Plan: Search contacts with tag='VIP'

⚠️  Execute 1 tool? [Y/n]: y

🔧 Executing...
  ✓ search_contacts

💬 Found 10 VIP contacts:
  • Customer 0 - 628123450000
  • Customer 5 - 628123450005
  ...

wati> Send them the renewal reminder

🤔 Thinking...
Intent: send_template_to_segment
Context: Using 10 contacts from previous search
Plan: 
  1. get_template_details('renewal_reminder')
  2. send_template_message_batch(10 contacts)

⚠️  This will send 10 messages. Proceed? [Y/n]: 
```

---

## Phase 3: Implementation Tasks

### Task 1: Create REPL Infrastructure
**Priority**: P0  
**Effort**: 2 days  
**Dependencies**: None

**Subtasks**:
- [ ] Create `conductor/repl/` module structure
- [ ] Implement `Session` class with in-memory state
- [ ] Implement `REPLLoop` with basic prompt/response
- [ ] Add signal handlers (Ctrl+C, Ctrl+D)
- [ ] Write unit tests for session management

**Acceptance Criteria**:
- Can start REPL with `python -m conductor.cli`
- Can input text and see echo response
- Ctrl+C cancels current input, Ctrl+D exits
- Session state persists across turns

---

### Task 2: Integrate Agent with Session Context
**Priority**: P0  
**Effort**: 3 days  
**Dependencies**: Task 1

**Subtasks**:
- [ ] Add LangGraph checkpointer to agent graph
- [ ] Modify agent invocation to use thread_id (session_id)
- [ ] Pass conversation history to parser node
- [ ] Update state schema to include session context
- [ ] Test multi-turn conversations

**Acceptance Criteria**:
- Agent can reference previous turns ("send it to them too")
- Session context flows through graph nodes
- Checkpointer correctly saves/loads state

---

### Task 3: Implement Meta Commands
**Priority**: P1  
**Effort**: 1 day  
**Dependencies**: Task 1

**Subtasks**:
- [ ] Create `CommandHandler` class
- [ ] Implement `/help`, `/history`, `/clear`, `/quit`
- [ ] Implement `/trust on|off` toggle
- [ ] Add command autocomplete (optional)
- [ ] Write tests for each command

**Acceptance Criteria**:
- All meta commands work as specified
- `/history` shows formatted conversation log
- `/trust on` persists in session preferences

---

### Task 4: Add Streaming Output
**Priority**: P1  
**Effort**: 2 days  
**Dependencies**: Task 2

**Subtasks**:
- [ ] Modify agent graph to support streaming
- [ ] Implement `StreamingHandler` for token display
- [ ] Add real-time tool execution progress
- [ ] Maintain rich formatting during streaming
- [ ] Test with slow LLM responses

**Acceptance Criteria**:
- LLM thinking streams token-by-token
- Tool execution shows live progress
- No visual glitches or formatting issues

---

### Task 5: Enhance UI/UX
**Priority**: P2  
**Effort**: 2 days  
**Dependencies**: Task 3, Task 4

**Subtasks**:
- [ ] Design welcome banner and prompt style
- [ ] Add visual separators between turns
- [ ] Implement typing indicators
- [ ] Add color-coded message types (user/agent/system)
- [ ] Polish error messages for REPL context

**Acceptance Criteria**:
- UI matches design mockups
- Clear visual hierarchy
- Professional appearance

---

### Task 6: Backward Compatibility
**Priority**: P0  
**Effort**: 1 day  
**Dependencies**: Task 2

**Subtasks**:
- [ ] Detect mode in `cli.py` (args present = single-shot)
- [ ] Keep existing Click command for single-shot
- [ ] Ensure all flags (`--dry-run`, etc.) still work
- [ ] Add integration tests for both modes

**Acceptance Criteria**:
- `python -m conductor.cli "instruction"` works unchanged
- All existing flags functional
- No breaking changes to current API

---

### Task 7: Session Persistence (Optional)
**Priority**: P3  
**Effort**: 1 day  
**Dependencies**: Task 1

**Subtasks**:
- [ ] Add `SqliteSaver` checkpointer option
- [ ] Implement session save/load commands
- [ ] Add session listing (`/sessions`)
- [ ] Add session resume (`/resume <id>`)

**Acceptance Criteria**:
- Sessions persist across restarts
- Can list and resume previous sessions

---

## Phase 4: Testing Strategy

### Unit Tests
- Session state management (add_turn, get_context)
- Command handlers (each meta command)
- Streaming utilities (token buffering, formatting)

### Integration Tests
- Full REPL loop with mock agent
- Multi-turn conversations with real agent
- Session persistence (save/load)

### E2E Tests
- Scripted REPL sessions (input/output pairs)
- Backward compatibility (single-shot mode)
- Error scenarios (invalid input, tool failures)

### Manual Testing Checklist
- [ ] Start REPL, run 5 instructions, exit gracefully
- [ ] Test follow-up questions ("send it to them too")
- [ ] Test all meta commands
- [ ] Test Ctrl+C during tool execution
- [ ] Test session resume after restart
- [ ] Verify single-shot mode unchanged

---

## Phase 5: Deployment

### Migration Path
1. **v1.x (current)**: Single-shot CLI only
2. **v2.0-beta**: REPL mode available, single-shot unchanged
3. **v2.0**: REPL as default, single-shot via flag
4. **v2.1**: Add session persistence, advanced features

### Docker Changes
```dockerfile
# No changes needed - both modes work in same container
CMD ["/bin/bash"]  # Keep interactive shell for REPL
```

### Documentation Updates
- Update README with REPL usage examples
- Add "Interactive Mode" section
- Document meta commands
- Add troubleshooting for REPL-specific issues

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing CLI | High | Maintain backward compatibility (Task 6) |
| Session state bugs | Medium | Comprehensive unit tests, use LangGraph checkpointer |
| Streaming performance | Low | Test with slow LLMs, add buffering |
| UX complexity | Medium | User testing, iterate on design |

---

## Success Metrics

- **Adoption**: 80% of users prefer REPL mode over single-shot
- **Performance**: < 2s session startup, < 500ms first token
- **Reliability**: Zero breaking changes to existing API
- **UX**: Positive feedback on interactive experience

---

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1 (Requirements) | 1 day | This document |
| Phase 2 (Design) | 2 days | Architecture diagrams, API specs |
| Phase 3 (Implementation) | 10 days | Working REPL mode |
| Phase 4 (Testing) | 3 days | Test suite, bug fixes |
| Phase 5 (Deployment) | 2 days | v2.0-beta release |

**Total**: ~3 weeks

---

## Open Questions

1. **Session persistence**: Default to in-memory or SQLite?
   - **Recommendation**: In-memory for v2.0, SQLite optional in v2.1

2. **Multi-line input**: How to signal end of input?
   - **Recommendation**: Ctrl+D or empty line after text

3. **Streaming granularity**: Token-level or sentence-level?
   - **Recommendation**: Token-level for thinking, sentence-level for final response

4. **Command prefix**: Use `/` or `!` or `:`?
   - **Recommendation**: `/` (matches Kiro, Slack conventions)

5. **History format**: Plain text or structured JSON?
   - **Recommendation**: Rich formatted text for display, JSON for export

---

## References

- [LangGraph Checkpointers](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [Rich REPL Examples](https://github.com/Textualize/rich/tree/master/examples)
- [Amazon Kiro CLI UX](https://docs.aws.amazon.com/kiro/)
- [Click REPL Mode](https://click.palletsprojects.com/en/8.1.x/utils/#click.prompt)
