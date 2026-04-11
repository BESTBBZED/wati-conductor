# WATI Conductor v1 — Requirements

## Overview

An autonomous WhatsApp automation agent powered by LangGraph. Transforms natural language instructions into executable WATI API workflows, enabling non-technical users to automate WhatsApp business operations.

## Target Users

- **Primary**: Business users automating WhatsApp workflows
- **Secondary**: Developers building automation tools

## Functional Requirements

### FR-1: Natural Language Understanding
- FR-1.1: Parse user instructions into structured intent (action + target + conditions)
- FR-1.2: Extract entities: contact identifiers, tags, template names, attributes, operators
- FR-1.3: Handle multi-step instructions combining 2+ API domains
- FR-1.4: Disambiguate vague instructions by asking clarifying questions

### FR-2: API Orchestration Planning
- FR-2.1: Generate execution plan from parsed intent (sequence of API calls)
- FR-2.2: Validate plan feasibility (check for missing parameters, invalid combinations)
- FR-2.3: Optimize plan (batch operations, minimize API calls)
- FR-2.4: Support dry-run mode (preview plan without execution)

### FR-3: WATI API Integration
Must support operations across these domains:

**Contacts Domain:**
- FR-3.1: Search contacts by tag, attribute, phone number
- FR-3.2: Add/update contact attributes
- FR-3.3: Manage contact tags (add/remove)

**Messages Domain:**
- FR-3.4: Send session messages (text)
- FR-3.5: Send template messages with parameter substitution
- FR-3.6: Support both v1 and v2 template message formats

**Templates Domain:**
- FR-3.7: List available message templates
- FR-3.8: Retrieve template details (parameters, structure)

**Broadcasts Domain:**
- FR-3.9: Create and send broadcasts to segments

**Operators & Tickets Domain:**
- FR-3.10: Assign conversations to operators/teams
- FR-3.11: Create and resolve tickets

### FR-4: Execution & Error Handling
- FR-4.1: Execute API calls in planned sequence
- FR-4.2: Handle partial failures gracefully (continue, rollback, or retry)
- FR-4.3: Provide detailed error messages with recovery suggestions
- FR-4.4: Support human-in-the-loop confirmation for destructive actions
- FR-4.5: Progress reporting for multi-step operations

### FR-5: User Experience
- FR-5.1: CLI interface with rich formatting (colors, tables, progress bars)
- FR-5.2: Explain each step of the plan in plain language
- FR-5.3: Show API call details in verbose mode
- FR-5.4: Confirm destructive actions before execution
- FR-5.5: Support interactive mode (conversational follow-ups)

### FR-6: Mock/Real API Toggle
- FR-6.1: Realistic mock layer simulating WATI API responses
- FR-6.2: Mock layer clearly swappable with real API client
- FR-6.3: Mock responses include realistic delays and edge cases

## Non-Functional Requirements

### NFR-1: Performance
- Intent parsing < 2s
- Plan generation < 3s
- API call execution respects rate limits (configurable)
- Total response time for simple queries < 5s

### NFR-2: Tech Stack
- **Language**: Python 3.11+
- **LLM Framework**: LangGraph (state machine orchestration)
- **LLM Providers**: 
  - Primary: DeepSeek-V3 (cost-optimized, $0.014/1M tokens)
  - Alternative: Claude 3 Haiku/Sonnet (higher quality, $0.25-3/1M tokens)
  - Multi-model routing: Use cheap models for simple tasks, expensive for complex
- **Interface**: CLI with Rich library (formatting)
- **API Client**: httpx (async HTTP)
- **Configuration**: Pydantic Settings + .env

### NFR-3: Code Quality
- Type hints throughout (mypy strict mode)
- Pydantic models for all data contracts
- Clear separation: LLM reasoning / tool execution / state management
- Minimal dependencies (no over-engineering)

### NFR-4: Configuration
- API credentials via `.env` (never hardcoded)
- Mock/real mode toggle via environment variable
- Multi-model routing: Configure different models per task (parse, plan, clarify)
- Provider-agnostic: Switch between DeepSeek/Claude/OpenAI with zero code changes
- Configurable rate limits and timeouts
- Logging levels (DEBUG, INFO, WARNING, ERROR)

### NFR-5: Developer Experience
- Single command setup: `pip install -e .`
- Clear README with usage examples
- Structured logging with LangGraph trace visibility
- Easy to extend with new tools/API endpoints

## Use Cases

### UC-1: Bulk Tag Management
```
User: "Find all contacts tagged 'VIP' and send them the 'renewal_reminder' template with their name filled in."

Agent Plan:
1. GET /api/v1/getContacts?tag=VIP
2. For each contact:
   - GET /api/v1/getContactInfo/{number} (to get name)
   - POST /api/v1/sendTemplateMessage/{number} (with name parameter)

Execution: 
- Shows progress: "Processing 15 VIP contacts..."
- Reports: "✓ 14 sent, ✗ 1 failed (invalid template parameter)"
```

### UC-2: Conditional Assignment
```
User: "When I say 'escalate 6281234567890', assign that contact's conversation to the Support team and add the tag 'escalated'."

Agent Plan:
1. POST /api/v1/tickets/assign (whatsappNumber, teamName=Support)
2. POST /api/v1/addTag/{number} (tag=escalated)

Confirmation: "This will assign the conversation and add a tag. Proceed? (y/n)"
Execution: "✓ Conversation assigned to Support, tag 'escalated' added."
```

### UC-3: Segmented Broadcast
```
User: "Send a broadcast with the 'flash_sale' template to all contacts who have the attribute 'city' = 'Jakarta'."

Agent Plan:
1. GET /api/v1/getContacts (filter by city=Jakarta)
2. POST /api/v1/sendBroadcastToSegment (template_name=flash_sale, segmentName=Jakarta)

Dry-run preview: "This will send to ~1,200 contacts in Jakarta. Estimated cost: $X. Proceed?"
```

### UC-4: Error Recovery
```
User: "Send 'welcome_new' template to all contacts tagged 'new_signup'."

Agent Plan:
1. GET /api/v1/getContacts?tag=new_signup
2. Batch send template messages

Execution:
- "Processing 50 contacts..."
- "✗ API rate limit hit at contact 30/50"
- "Waiting 60s before retry..."
- "✓ Resumed, 20 remaining contacts sent successfully"
```

### UC-5: Ambiguity Handling
```
User: "Send a message to VIP customers about the sale."

Agent: "I need more details:
1. Which template should I use? (Available: flash_sale, vip_exclusive, general_promo)
2. Should I send to all VIP-tagged contacts, or filter by other criteria?"

User: "Use vip_exclusive, send to all VIPs."

Agent: [Proceeds with clarified plan]
```

## Success Criteria

- [ ] Agent correctly parses 90%+ of test instructions (see evals)
- [ ] Generated plans are executable and semantically correct
- [ ] Error messages are actionable (user knows what to fix)
- [ ] Dry-run mode accurately previews actions
- [ ] Mock layer responses are indistinguishable from real API (structure-wise)
- [ ] CLI output is clear and professional
- [ ] Code is readable and well-structured (passes review criteria)

## Out of Scope (v1)

- Conversational memory across sessions (stateless agent)
- Rollback mechanisms for failed multi-step operations
- Web UI / chat interface (CLI only)
- Real-time webhook handling
- Advanced scheduling (cron-like triggers)
- Multi-language support
- Authentication/authorization (assumes pre-configured API key)
- Production deployment infrastructure

## Constraints

- **LLM Costs**: Use efficient prompting, minimize token usage
- **API Coverage**: Focus on 4-5 core endpoints, not exhaustive coverage
- **Data**: Mock data is acceptable, no production backend required

## Priority Levels

**P0 (Must Have):**
- FR-1 (NLU), FR-2 (Planning), FR-3.1-3.5 (Core APIs), FR-4 (Execution), FR-5.1-5.4 (CLI UX)

**P1 (Should Have):**
- FR-3.6-3.11 (Extended APIs), FR-4.5 (Progress reporting), FR-5.5 (Interactive mode)

**P2 (Nice to Have):**
- Advanced error recovery, batch optimization, comprehensive mock edge cases
