# WATI Conductor v2 — Vision & Roadmap

This directory contains forward-looking documentation for future versions of WATI Conductor.

## Documents

### 📝 [vision.md](./vision.md)
**Build notes, trade-offs, and V2 roadmap**

Contains reflections from v1 implementation:
- Time allocation breakdown
- Prioritization decisions (what was built vs. skipped)
- Technical decisions & rationale:
  - LangGraph vs. LangChain Agents
  - Multi-model routing (DeepSeek vs. Claude)
  - Mock-first development
  - CLI vs. Web UI
- Challenges & solutions encountered
- API coverage analysis
- Testing strategy
- **V2 roadmap** (prioritized features)
- Lessons learned
- Self-assessment against evaluation criteria

## V2 Feature Roadmap

### High Priority (Next 3 hours)
- Real API client implementation
- Conversational memory (multi-turn interactions)
- Rollback mechanisms for failed operations
- Comprehensive error handling

### Medium Priority (Next 6 hours)
- Web UI (chat interface)
- Batch optimization (parallel API calls)
- Advanced scheduling (cron-like triggers)
- LangSmith tracing integration

### Low Priority (Future)
- Multi-language support
- Authentication/authorization
- Admin dashboard
- Production deployment (k8s, CI/CD)

## Purpose

This directory serves as:
1. **Learning resource**: Understand trade-offs made in v1
2. **Planning document**: Prioritized features for v2
3. **Decision log**: Why certain approaches were chosen
4. **Roadmap**: Clear path from v1 to production-ready v2

## When to Read This

- **After implementing v1**: To understand what was intentionally skipped
- **Before planning v2**: To see prioritized next steps
- **When making architectural decisions**: To learn from v1 trade-offs
- **For context on v1 limitations**: To understand scope boundaries

---

**Note**: v1 is a 3-hour MVP demo. v2 is the path to production-ready system.
