# WATI Conductor v1 — Specification Documents

This directory contains the complete specification for the WATI Conductor AI agent project.

## Document Structure

### 📋 [requirements.md](./requirements.md)
**What we're building and why**

- Overview and value proposition
- Target users
- Functional requirements (FR-1 through FR-6)
- Non-functional requirements (performance, tech stack, code quality)
- Use cases with examples
- Success criteria
- Out of scope items

**Read this first** to understand the problem space and scope.

---

### 🏗️ [design.md](./design.md)
**How we're building it**

- Architecture overview (ASCII diagram)
- Component design:
  - LangGraph state machine (nodes, edges, state schema)
  - Intent parsing strategy (LLM prompts, structured output)
  - Plan generation logic (action types → API sequences)
  - Tool definitions (LangChain tools wrapping WATI API)
  - WATI API client (real + mock implementations)
  - CLI interface (Rich formatting, progress bars)
- Data flow examples
- Error handling strategy
- Configuration management
- Security considerations

**Read this second** to understand the technical architecture.

---

### ✅ [tasks.md](./tasks.md)
**Step-by-step implementation plan**

- Task overview table (11 tasks, ~4 hours total)
- Critical path: 1 → 2 → 3 → 5 → 6 → 7 → 8 → 9 → 11
- Detailed breakdown for each task:
  - Goal
  - Deliverables (file structure)
  - Implementation details (code examples)
  - Completion criteria
- Post-implementation checklist

**Use this as your implementation guide** — follow tasks in order.

---

## V2 Vision & Roadmap

See [../v2/vision.md](../v2/vision.md) for:
- Build notes and time allocation
- Technical decisions & rationale
- Challenges & solutions
- V2 roadmap (prioritized features)
- Lessons learned
- Self-assessment

---

## Quick Start

1. **Understand the problem**: Read [requirements.md](./requirements.md)
2. **Learn the architecture**: Read [design.md](./design.md)
3. **Start building**: Follow [tasks.md](./tasks.md) step-by-step
4. **Explore V2 vision**: Review [../v2/vision.md](../v2/vision.md) for future roadmap

## Key Concepts

### Agent Flow
```
User Instruction
    ↓
[Parse] → Extract structured intent (LLM)
    ↓
[Plan] → Generate API call sequence
    ↓
[Validate] → Check for errors, missing params
    ↓
[Execute] → Run tools, handle errors, report progress
    ↓
Final Response
```

### Tech Stack
- **Language**: Python 3.11+
- **Agent Framework**: LangGraph (state machine)
- **LLM**: Claude 3.5 Sonnet (tool calling)
- **CLI**: Rich (formatting)
- **HTTP Client**: httpx (async)
- **Validation**: Pydantic

### Core Components
1. **Intent Parser**: Natural language → structured intent
2. **Plan Generator**: Intent → API call sequence
3. **Tool Executor**: Execute tools with error handling
4. **CLI Interface**: Rich formatting, progress bars, confirmations

## Product Overview

This specification defines WATI Conductor, an AI agent for automating WhatsApp business workflows through natural language.

**Deliverables:**
1. Working demo (GitHub repo)
2. Demo video (3-5 minutes)
3. Technical documentation

## Design Philosophy

### Product Principles
- **Clarity over cleverness**: Explicit is better than implicit
- **Usability over features**: Polished core functionality > incomplete feature set
- **Extensibility over optimization**: Easy to add new tools/actions

### Quality Over Quantity
- Focus on 3-4 core action types (not exhaustive API coverage)
- Implement 6-8 essential tools (not all 20+ endpoints)
- Demonstrate orchestration capability, not API wrapper completeness

### Open-Ended Exploration
- Creative liberty in agent behavior (e.g., dry-run mode, confirmations)
- Original ideas in error handling (e.g., retry with backoff, partial failure reporting)
- Thoughtful UX choices (e.g., progress bars, rich formatting)

## Success Metrics

- [ ] Agent correctly parses 90%+ of test instructions
- [ ] Generated plans are executable and semantically correct
- [ ] Error messages are actionable
- [ ] Dry-run mode accurately previews actions
- [ ] CLI output is clear and professional
- [ ] Code is readable and well-structured

## Next Steps

After reading these specs:

1. **Set up project**: Follow Task 1 in [tasks.md](./tasks.md)
2. **Implement core**: Tasks 2-8 (models, client, tools, agent)
3. **Build CLI**: Task 9 (Rich interface)
4. **Test & demo**: Task 11 (scenarios, video)
5. **Document**: README, write-up, video

**Estimated total time:** 3-4 hours

---

## Questions?

If anything is unclear:
1. Check [design.md](./design.md) for technical details
2. Check [../v2/vision.md](../v2/vision.md) for rationale
3. Review the WATI API documentation for endpoint details

**Let's build something great! 🚀**
