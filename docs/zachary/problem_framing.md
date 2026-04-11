# Problem Framing

## The Assignment

Build a chatbot that lets non-technical business users automate WhatsApp operations through natural language. They should be able to say things like "Send a welcome message to all VIP customers" without knowing anything about APIs.

## What I Focused On

**Multi-task workflows**: The interesting part isn't single commands like "find VIP contacts" - it's complex requests like "find VIP contacts AND send them a template AND create a ticket if it fails". The agent needs to break this down, execute steps in order, and pass data between steps.

**Reliability over cleverness**: I went with a plan-then-execute pattern instead of letting the LLM decide what to do at every step. One LLM call to make a plan, then deterministic execution. This is cheaper, more predictable, and easier to debug.

**Demo-friendly**: Added interactive confirmations so you can see what's about to happen. Built a mock WATI client with realistic data (50 contacts, 6 templates) so demos work without real API credentials. Saved all outputs to files so you can inspect what got sent.

## What I Skipped

**Streaming responses**: Would be nice but not critical for MVP. The agent waits for the full LLM response before showing anything.

**Web UI**: Built a CLI instead. Faster to iterate and good enough for demos. A web UI would be the obvious next step for real users.

**Advanced error recovery**: If a tool fails, the agent stops. Could add retry logic, fallbacks, or partial success handling, but that felt like over-engineering for an assignment.

**Real WATI integration**: Used mock data throughout. Would need to test rate limits, handle webhook events, and deal with production edge cases for a real deployment.

## Key Trade-offs

**WATI Sandbox API**: I registered for the sandbox and tested it on their website, but didn't integrate it into the agent. The API has strict data structure requirements (specific field formats, template approval workflows, webhook handling) that would've taken days to get right. Instead, I built a mock client that reads/writes local files. This let me iterate fast, test destructive operations safely, and demo without API credentials. The mock client follows the real API's interface, so swapping it out later is straightforward.

**Conversation history**: Keeping full history made the agent repeat old tasks. Limiting to last 2 turns fixed it but means the agent can't reference things from 3+ turns ago. Good enough for most workflows.

**Batch operations**: Added tools like `update_contact_attributes_batch` instead of making the LLM loop through contacts one by one. More tools to maintain but way more reliable.

**Prompt complexity**: Spent a lot of time on prompt engineering (don't use array indexing, distinguish queries from actions, handle temporal logic). This feels brittle but it works. A production system would probably need a more structured approach.

## What Success Looks Like

A business user can:
1. Ask "How many customers are from Beijing?" (info query)
2. Say "Upgrade them all to premium" (action with context)
3. Add "And tag them as VIP" (chained action)
4. See exactly what's about to happen before it executes
5. Get a natural language summary of what happened

All without writing code or understanding the WATI API.
