# Build Notes

## What I Built

An AI agent that translates natural language into WATI WhatsApp API workflows. Users can say things like "Find all VIP contacts and send them the welcome template" and the agent figures out what API calls to make.

## Core Design

**ReAct Pattern with LangGraph**: The agent has a simple flow:
1. Parse user input into tasks (one LLM call)
2. Execute tasks sequentially (no LLM, just API calls)
3. Generate response (one LLM call)

This is way cheaper than letting the LLM decide what to do at every step.

**Multi-Task Decomposition**: Complex requests get broken down automatically. "Find VIP contacts and send them a template" becomes two tasks: search_contacts → send_template_message_batch. Tasks can reference previous results using `$task_0.contacts`.

**Conversation Memory**: Simple file-based history. Keeps last 2 turns to avoid context pollution. Had to strip emoji from history because Anthropic's API chokes on Unicode surrogate pairs.

## Development Timeline

**Hour 1**: Built the core LangGraph state machine. Used KIRO with Claude to draft the initial spec. Hit encoding bugs immediately (emoji in responses broke JSON serialization).

**Hour 2**: Added conversation history. Realized long histories made the agent repeat old tasks instead of focusing on new requests. Fixed by limiting context window and adding explicit "for context only" markers in prompts.

**Hour 3**: Built the CLI with Rich library. Added trust mode (skip confirmations), dual Ctrl+C handling, and auto-retry on failures. Created batch operations for common workflows (tag multiple contacts, update attributes in bulk).

## Key Problems Solved

**Temporal Logic**: "Upgrade to premium and tag those who were regular" - the second task needs to filter on the *original* tier value, not the modified one. Fixed by having both tasks reference `$task_0.contacts` (the original search result).

**Query vs Action**: "How many customers are from Tokyo?" shouldn't trigger updates. Added prompt rules: "let me know" = info only, "upgrade" = execute action.

**Parameter Mapping**: Templates need parameters like `{{name}}`. Built auto-mapping that extracts required params from templates and fills them from contact data.

**Mock-First Development**: Real WATI API has rate limits. Built a comprehensive mock client with 50 contacts and 6 templates. Mock messages get saved to files so you can inspect what would've been sent.

## What Worked Well

- **Confidence filtering** (only execute tasks with confidence >= 0.7) reduced a loooooot of False POSTIVIES
- **Interactive confirmations** made demos way better - people can see what's about to happen
- **Batch tools** eliminated the need for complex array indexing in prompts

## What Was Annoying

- Unicode handling. Emoji broke things in 3 different places (JSON serialization, file I/O, API requests)
- Prompt engineering took 30% of the time. Had to handle edge cases like "don't use array indexing", "don't repeat completed tasks", "filter on original values not modified ones"
- LLM sometimes generates dict when you ask for string. Had to add explicit type examples in prompts.

## If I Had More Time

- Streaming responses (currently waits for full LLM response)
- Nice Web UI for non-technical users
- LangSmith tracing for debugging
- Test with real WATI API
