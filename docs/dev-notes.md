# Dev Notes

Build notes, problem framing, and design trade-offs from the initial development of WATI Conductor. Written by Zachary during the v1 build.

## Problem Framing

Build a chatbot that lets non-technical business users automate WhatsApp operations through natural language. They should be able to say things like "Send a welcome message to all VIP customers" without knowing anything about APIs.

### What I Focused On

**Multi-task workflows**: The interesting part isn't single commands like "find VIP contacts" — it's complex requests like "find VIP contacts AND send them a template AND create a ticket if it fails". The agent needs to break this down, execute steps in order, and pass data between steps.

**Reliability over cleverness**: I went with a plan-then-execute pattern instead of letting the LLM decide what to do at every step. One LLM call to make a plan, then deterministic execution. This is cheaper, more predictable, and easier to debug.

**Demo-friendly**: Added interactive confirmations so you can see what's about to happen. Built a mock WATI client with realistic data (50 contacts, 6 templates) so demos work without real API credentials.

### What I Skipped

- **Streaming responses**: Would be nice but not critical for MVP
- **Web UI**: CLI is faster to iterate and good enough for demos
- **Advanced error recovery**: If a tool fails, the agent stops. Could add retry/fallback but felt like over-engineering
- **Real WATI integration**: Mock data throughout. Real API has strict data structures that would take days to get right

### Key Trade-offs

**WATI Sandbox API**: Registered for the sandbox and tested it on their website, but didn't integrate it. The API has strict field formats, template approval workflows, and webhook handling that would've taken days. Instead, built a mock client that reads/writes local files. Same interface, so swapping later is straightforward.

**Conversation history**: Keeping full history made the agent repeat old tasks. Limiting to last 2 turns fixed it but means the agent can't reference things from 3+ turns ago.

**Batch operations**: Added tools like `update_contact_attributes_batch` instead of making the LLM loop through contacts one by one. More tools to maintain but way more reliable.

**Prompt complexity**: Spent ~30% of time on prompt engineering (don't use array indexing, distinguish queries from actions, handle temporal logic). Feels brittle but works.

## Build Notes

### Development Timeline

- **Hour 1**: Built the core LangGraph state machine. Used KIRO with Claude to draft the initial spec. Hit encoding bugs immediately (emoji in responses broke JSON serialization).
- **Hour 2**: Added conversation history. Realized long histories made the agent repeat old tasks. Fixed by limiting context window and adding "for context only" markers in prompts.
- **Hour 3**: Built the CLI with Rich library. Added trust mode, dual Ctrl+C handling, and auto-retry. Created batch operations for common workflows.

### Problems Solved

**Temporal Logic**: "Upgrade to premium and tag those who were regular" — the second task needs to filter on the *original* tier value, not the modified one. Fixed by having both tasks reference `$task_0.contacts` (the original search result).

**Query vs Action**: "How many customers are from Tokyo?" shouldn't trigger updates. Added prompt rules: "let me know" = info only, "upgrade" = execute action.

**Parameter Mapping**: Templates need parameters like `{{name}}`. Built auto-mapping that extracts required params from templates and fills them from contact data.

**Unicode Issues**: Emoji broke things in 3 different places (JSON serialization, file I/O, API requests). Added `remove_emoji()` helper that strips non-ASCII characters.

### What Worked Well

- Confidence filtering (≥ 0.7) reduced false positives dramatically
- Interactive confirmations made demos much better
- Batch tools eliminated complex array indexing in prompts
- Mock-first development enabled fast iteration

### What Was Annoying

- Unicode handling across 3 different failure points
- Prompt engineering took 30% of total time
- LLM sometimes generates dict when you ask for string — had to add explicit type examples

## Demo Script

### Setup

```bash
docker compose up -d
docker compose exec wati-conductor python3 main.py
```

### Demo Scenarios (in order)

1. **Enable trust mode**: `trust` — skips confirmations for smoother demo

2. **List templates**: `What templates do I have?` — shows tool calling basics

3. **Find contacts**: `Find all VIP contacts` — simple search

4. **Multi-task workflow**: `Find all VIP contacts and send them the welcome_wati template` — shows task decomposition and `$task_0.contacts` dependency

5. **Contextual follow-up**: `How many of them are from Beijing?` — uses conversation history

6. **Chained action**: `Upgrade them all to premium tier` — context-aware batch update

7. **Temporal logic** (advanced): `Find all contacts from Beijing who are not premium, upgrade them to premium, and tag those who were regular as VIP` — shows original-value filtering

8. **Query vs action**: `How many customers are from Tokyo?` — information-only, no modifications

9. **Ticket creation**: `Create a ticket to Sam about database connection error` — local ticket system

### Backup Scenarios

- **Batch tag**: `Find all contacts from Jakarta and add them to the "jakarta_campaign" tag`
- **Template with params**: `Send the ecom_presales_oct template to contact 628123450000`
- **Error handling**: `Send a template that doesn't exist to VIP contacts`
- **Dry run**: `python -m conductor.cli "Find all VIP contacts and send them the welcome_wati template" --dry-run`

### Demo Tips

- Don't rush — let people read the "Agent Thinking" section
- Point at the screen when showing task dependencies
- Emphasize trade-off reasoning for the mock API decision
- Pause 2-3 seconds between commands
- Have screenshots or video as backup if Docker fails
- The temporal logic example is the most impressive — practice explaining it clearly
