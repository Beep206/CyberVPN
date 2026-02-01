# Battle Test Results: CrewAI vs Claude Code Agents

## Test Setup
- **Feature**: JWT Auth Microservice (5 endpoints: register, login, me, refresh, token/verify)
- **Stack**: FastAPI + SQLAlchemy async + SQLite + Pydantic v2 + python-jose + passlib
- **Model**: Claude Opus 4.5 (both approaches)
- **PRD**: Identical shared requirements document

---

## Timing Comparison

| Metric | CrewAI | Claude Code Agents |
|--------|--------|--------------------|
| **Total wall-clock time** | ~134s (single-agent mode) | ~30s |
| **Setup time** | 4 failed attempts, ~40min debugging | 0 (works out of the box) |
| **Lines of code generated** | 346 lines | 422 lines |
| **Files generated** | 9 files (+ 9 duplicate in wrong dir) | 9 files + __init__.py |
| **All endpoints working** | Yes (7/7 tests) | Yes (7/7 tests) |

---

## Evaluation Scores (1-10)

| # | Criteria | Weight | CrewAI | Claude Code Agents | Notes |
|---|----------|--------|--------|---------------------|-------|
| 1 | **Planning Quality** | 15% | 8 | 7 | CrewAI CEO produced detailed 6-phase plan; Agents went straight to code |
| 2 | **Code Completeness** | 20% | 9 | 10 | Both work; Agents added `is_active` check in login, `__init__.py`, bcrypt pin |
| 3 | **Code Quality** | 20% | 7 | 9 | CrewAI: no `__init__.py`, deprecated utcnow; Agents: `timezone.utc`, better typing |
| 4 | **Speed** | 10% | 3 | 10 | ~134s vs ~30s; CrewAI needed 4 attempts to even run |
| 5 | **Test Coverage** | 15% | 0 | 0 | Neither produced tests (not requested explicitly) |
| 6 | **Production Readiness** | 10% | 7 | 8 | Agents: bcrypt version pin, ConfigDict, docstrings |
| 7 | **Developer Experience** | 10% | 2 | 10 | CrewAI: OAuth fails, hierarchical mode breaks, agent naming issues |

### Weighted Scores
- **CrewAI**: 8×0.15 + 9×0.20 + 7×0.20 + 3×0.10 + 0×0.15 + 7×0.10 + 2×0.10 = **5.6/10**
- **Claude Code Agents**: 7×0.15 + 10×0.20 + 9×0.20 + 10×0.10 + 0×0.15 + 8×0.10 + 10×0.10 = **7.65/10**

---

## Detailed Analysis

### CrewAI Strengths
1. **Structured planning** — CEO agent produced a thorough 6-phase execution plan with deliverables checklist
2. **Multi-department perspective** — Engineering + Product crews analyze from different angles
3. **Governance/RACI** — Framework for decision approval (though not used in this test)
4. **Architectural awareness** — Reads existing codebase context before generating

### CrewAI Weaknesses
1. **OAuth incompatible** — LiteLLM strips OAuth tokens, requires separate API key
2. **Hierarchical mode broken** — `tool_use`/`tool_result` pairing bug in CrewAI 1.9.x
3. **Agent delegation fragile** — Coworker name matching fails silently
4. **Sequential mode needs manual agent assignment** — Every task must have explicit `agent=`
5. **Slow** — Extended thinking budget + multi-crew overhead = 4.5x slower
6. **Duplicate files** — Agent wrote files to wrong nested directory AND correct directory
7. **No `__init__.py`** — Missing package init file
8. **Deprecated APIs** — Used `datetime.utcnow()` instead of `datetime.now(timezone.utc)`

### Claude Code Agents Strengths
1. **Zero setup** — Works immediately, no configuration needed
2. **Fast** — Direct API calls, no orchestration overhead
3. **Code quality** — Better typing, modern Python idioms, bcrypt compatibility pin
4. **Reliable** — First attempt worked, no debugging needed
5. **File system native** — Writes files directly, no tool wrapping needed
6. **`__init__.py` included** — Proper Python package structure

### Claude Code Agents Weaknesses
1. **No planning phase** — Went straight to code without explicit architecture review
2. **Single perspective** — No multi-department analysis (only backend-dev)
3. **Less structured output** — No formal execution plan or deliverables checklist

---

## Issues Encountered

### CrewAI Issues (4 failed attempts before success)
1. **Attempt 1**: OAuth token rejected as `invalid x-api-key` (401)
2. **Attempt 2**: `Manager agent should not have tools` in hierarchical mode
3. **Attempt 3**: `tool_use` ids without `tool_result` blocks (400 API error)
4. **Attempt 4**: `Sequential process error: Agent is missing in task`
5. **Attempt 5 (simplified)**: Single-agent mode — SUCCESS in 134s

### Claude Code Agents Issues
- None. First attempt produced working code.

---

## Verdict

**Claude Code Agents wins decisively** for this use case (isolated microservice development).

CrewAI's multi-agent orchestration adds significant complexity and failure modes without proportional benefit for straightforward coding tasks. Its value proposition is better suited for:
- Complex cross-department decisions requiring multiple perspectives
- Architectural planning where structured governance matters
- Scenarios where the planning output itself is the deliverable

For **write code that works**, Claude Code agents are faster, more reliable, and produce higher-quality output.

### When to Use Each

| Use Case | Recommended |
|----------|-------------|
| Write a microservice | Claude Code Agents |
| Implement a feature | Claude Code Agents |
| Fix a bug | Claude Code Agents |
| Architecture review | CrewAI (planning mode) |
| Multi-department decision | CrewAI |
| Compliance/security audit | CrewAI |
| Pricing strategy | CrewAI |
