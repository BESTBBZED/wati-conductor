# Knowledge Base & Skills Guide

> Usage guide for the KB and Skills system in WATI Conductor.

## Overview

The Knowledge Base (KB) stores business knowledge — SOPs, guardrails, and domain docs — that the agent retrieves via semantic search to make better decisions. Skills are named bundles of tools + instructions that control what the agent can do.

## Prerequisites

```bash
# Start PostgreSQL with pgvector
docker compose up -d postgres

# Start the API server
poetry run uvicorn conductor.api.main:app --host 0.0.0.0 --port 8000
```

## Knowledge Base

### Ingesting Documents

```bash
# Single file
curl -X POST http://localhost:8000/api/kb/documents/file \
  -H "Content-Type: application/json" \
  -d '{"file_path": "./data/kb/sops/batch-messaging.md", "category": "sop", "tags": ["messaging"]}'

# Directory (bulk)
curl -X POST http://localhost:8000/api/kb/documents/directory \
  -H "Content-Type: application/json" \
  -d '{"dir_path": "./data/kb/sops", "category": "sop"}'

# Raw text
curl -X POST http://localhost:8000/api/kb/documents/text \
  -H "Content-Type: application/json" \
  -d '{"title": "Rate Limit", "content": "Max 500 messages per batch.", "category": "guardrail", "always_inject": true}'
```

### Searching

```bash
curl -X POST http://localhost:8000/api/kb/search \
  -H "Content-Type: application/json" \
  -d '{"query": "VIP contact handling", "top_k": 3}'
```

### Categories

| Category | Purpose | Retrieval Method |
|----------|---------|-----------------|
| `sop` | Operating procedures | Semantic search per instruction |
| `guardrail` | Hard constraints | Always injected + semantic |
| `domain` | Reference data | Semantic search per instruction |
| `faq` | Common Q&A | Semantic search per instruction |

### How It Integrates with the Agent

1. User sends an instruction
2. `ContextBuilder` embeds the instruction and searches pgvector for relevant chunks
3. Always-inject guardrails are prepended unconditionally
4. Top-K results are injected into the system prompt
5. Agent reasons with full business context

## Skills Management

### List Skills

```bash
curl http://localhost:8000/api/skills
```

### Enable/Disable

```bash
# Disable
curl -X PATCH http://localhost:8000/api/skills/tickets \
  -H "Content-Type: application/json" -d '{"enabled": false}'

# Check active tools
curl http://localhost:8000/api/skills/active/tools
```

### Create Custom Skill

```bash
curl -X POST http://localhost:8000/api/skills \
  -H "Content-Type: application/json" \
  -d '{
    "name": "marketing",
    "description": "Marketing campaign tools",
    "tool_names": ["send_template_message_batch", "list_templates"],
    "instructions": "Check opt-in before sending. No sends outside 9-18."
  }'
```

### Built-in Skills (5)

| Skill | Tools | Description |
|-------|-------|-------------|
| `contacts` | 8 | Search, tag, attribute management |
| `messaging` | 2 | Session messages + template broadcasts |
| `templates` | 2 | Browse and inspect templates |
| `operators` | 2 | Assign to operators/teams |
| `tickets` | 2 | Create and resolve tickets |

## Configuration

In `.env`:

```bash
KB_ENABLED=true                    # Enable KB retrieval
KB_EMBEDDING_MODEL=all-MiniLM-L6-v2  # 384-dim, fast
KB_TOP_K=5                         # Chunks per query
SKILLS_ENABLED=true                # Enable dynamic skill resolution
```

## Sample KB Content

Pre-built content in `data/kb/`:

```
data/kb/
├── guardrails/limits.md       # Batch limits, rate limits
├── sops/
│   ├── batch-messaging.md     # 5-step batch procedure
│   ├── vip-handling.md        # VIP contact rules
│   └── contact-management.md  # Search/tag/update
└── domain/
    ├── template-catalog.md    # Template reference
    └── team-structure.md      # Teams and routing
```

## Graceful Degradation

- If PostgreSQL is unavailable, the agent falls back to its base system prompt
- If `KB_ENABLED=false`, no retrieval occurs — agent uses static prompt only
- If `SKILLS_ENABLED=false`, all 16 tools are available (legacy behavior)
