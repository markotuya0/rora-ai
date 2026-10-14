# Rora AI v2 — Enterprise Operational Copilot Architecture

> Generated from local skill ecosystem in `~/projects/rora-ai/.claude/skills-upstream/` + full audit of `~/projects/rora-ai/`.
> Stack preserved: Python, FastAPI, PostgreSQL, LangChain/OpenAI, Next.js/React, TypeScript, Tailwind CSS.

## 0. Skill Ingestion Record (what guided this design)

| Concern | Skill loaded | Path | Doctrine applied |
|---|---|---|---|
| System architecture | `senior-architect` | `engineering-team/skills/senior-architect/SKILL.md` | ADR discipline, modular-monolith-first (1–3 devs), pattern selection table, Mermaid component/layer/deployment diagrams, dependency coupling checks |
| Retrieval / schema context | `rag-architect` | `engineering/skills/rag-architect/SKILL.md` | Corpus-driven chunking, tier-not-price model selection, every design ends with an evaluation run (precision@k/recall@k), change-one-variable retry |
| Agent loop | `agent-designer` | `engineering/skills/agent-designer/SKILL.md` | Pattern decision table (single vs supervisor vs pipeline vs swarm), validated tool schemas (`✓ Valid` gate), `agent_evaluator.py` bottleneck/cost/SLA loop, 0-critical-issues gate |
| API standards | `api-design-reviewer` | `engineering/skills/api-design-reviewer/SKILL.md` | kebab-case resources, versioned `/api/v1`, standard error envelope `{error:{code,message,details,requestId,timestamp}}`, pagination, idempotency-key, lint → breaking-change → scorecard gates |
| API testing | `api-test-suite-builder` | `engineering/skills/api-test-suite-builder/SKILL.md` | FastAPI route-decorator scan, auth matrix (401/403), validation matrix (400/422 + boundaries + injection), one describe-block per endpoint, factories not hardcoded IDs |
| Frontend | `senior-frontend` | `engineering-team/skills/senior-frontend/SKILL.md` | Next.js 14+ App Router + Server Components, TS strict, React Query API client, Vitest + Testing Library, bundle analysis |
| Visual craft | `epic-design` | `engineering-team/skills/epic-design/SKILL.md` | Cinematic depth, intentional motion, never flat-static; applied sparingly to ops dashboard (telemetry transitions, diff morphs) |
| Design tokens | `ui-design-system` | `product-team/skills/ui-design-system/SKILL.md` | Design-token generation, 8pt grid, typography scale, WCAG contrast, component system + dev handoff |
| Brand tokens | `design-system` | `markdown-html/skills/design-system/SKILL.md` | 10-question onboarding, 12 CSS custom properties in HSL, WCAG-AA 4.5:1 gate, project > global > defaults precedence |
| Review quality | `pr-review-expert` | `engineering/skills/pr-review-expert/SKILL.md` | Blast-radius analysis, 30+ item checklist, security scan (SQLi/secrets/auth), coverage-delta gate (>5% drop blocks), breaking-change detection |

UI search note: no dedicated `frontend/` or `ui-ux/` skill folder exists; closest matches used above (`senior-frontend`, `epic-design`, `ui-design-system`, `design-system`, `product-team/apple-hig-expert` family). Motion references below (Animations.Dev spring physics, Devouring Details micro-typography, InterfaceCraft ergonomic logs) are applied as design principles, not vendored skills.

## 1. Current-State Audit (ground truth, not docs claims)

- **Backend:** FastAPI + uvicorn (`api.py:20-26,169-174`). 5 routes: `GET /`, `POST /query`, `GET /history`, `GET /schema`, `GET /health`. CORS wildcard (`api.py:29-35`). Pydantic v2 models `QueryRequest` (legacy `@validator`, should be `@field_validator`) and `QueryResponse` (uses deprecated `.dict()` at `api.py:111`).
- **AI chain:** Single-shot LCEL `prompt|llm|StrOutputParser` (`api.py:47`), `ChatOllama(qwen2.5:0.5b, temperature=0)` (`api.py:39`), full `db.get_table_info()` injected (`api.py:88`). No toolkit/agent, no few-shots, no schema pruning. Globals at import = unmockable.
- **Data:** `create_db.py` → SQLite `student_grades.db`, 1 table `grades(id,name,subject,score,grade)`, 6 seed rows. No migrations, no indexes/constraints. `config.py` claims PostgreSQL-ready via `DB_URI` but code is SQLite-only.
- **Tests:** 9 methods total (5 API in `test_api.py`, 4 utils in `test_utils.py`). `test_root` asserts `"message"` but `GET /` returns `name/version/status` → will fail. API tests need live Ollama. No 20-case suite exists yet.
- **Benchmark:** `benchmark.py` has **3 hardcoded cases**, `iterations=5`, no persistence/thresholds. Docs overclaim benchmarking as observability.
- **Frontend:** Streamlit thin client (`app_v2.py`), bare `except:` swallows errors. No Next.js yet.
- **Gaps (pr-review-expert lens):** `is_safe_query` = `startswith("select")` (`utils.py:14-16`) — bypassed by `;DROP`, comments, UNION, CTE stacking. `clean_sql` strips one fence pair only. No AST parse, no allowlist, no read-only URI, no LIMIT/timeout/row-cap. `query_history=[]` unbounded in-memory (`api.py:67`). `log_query` never called. No request IDs, no structured logs, no LLM health check. `limit=-1` DoS on `/history`. Sync `def` blocks loop (docs claim async — false).

## 2. Target Architecture v2

```
┌─ Next.js App Router (TS, Tailwind, Framer Motion, React Query) ─┐
│ PromptPanel │ SQLEditor/Diff │ Telemetry │ DataTable │ Actions  │
└──────────────────────────┬─────────────────────────────────────┘
                           │ /api/v1 (versioned, see §5)
┌─ FastAPI v2 ─────────────▼─────────────────────────────────────┐
│ intent-router → schema-pruner → generator → validator → guard  │
│        │              │              │            │        │     │
│        └────── retry loop (≤2 passes, §3) ◄─────┴────────┘     │
│ operational-payload synthesizer (§4) │ regression gate (§6)    │
└──────────────┬───────────────────────┬─────────────────────────┘
               │ SQLAlchemy 2.0 (ro)   │ LangChain / OpenAI
               ▼                       ▼
        PostgreSQL (migrated)    LLM tier (Ollama dev / OpenAI prod)
```

Decision (senior-architect pattern table, team 1–3): **modular monolith**. No microservices. Extract later only on divergent scaling.

### Module layout (backend)

```
backend/
  api/v1/{query,history,schema,health,actions}.py
  core/{config,logging,request_id,rate_limit}.py
  agent/{intent_router,schema_pruner,generator,validator,guard,retry,telemetry}.py
  ops/{payloads,email_drafts,cs_tags,gtm_triggers}.py
  db/{engine,models,migrations/}
  eval/{benchmark_20.py,conftest,mocks}
```

## 3. Self-Correcting Agent Loop

Pattern (agent-designer table): **single agent + pipeline stages**, not supervisor/swarm — one bounded NL→SQL task, <5 tools. Supervisor would bottleneck; swarm is undebuggable for SQL safety.

```
Q ─► intent_router ─► schema_pruner ─► generator ─► Pydantic ─► AST guard ─► exec ─► ok?
                        │                                │          │         │      │
                        │                     fail ──────┘     fail ┘    PG error ─┘
                        │                       │               │           │
                        └─────────────────── retry (≤2, with trimmed error feedback)
```

1. **Intent router (dynamic schema pruning).** Classify: `aggregate | filter | rank | join | trend | metadata`. Then prune `get_table_info()` to only referenced tables/columns + FK edges + enum samples (rag-architect doctrine: retrieve-then-generate, never full-corpus prompt). Target: prompt schema tokens ↓60–80%, hallucinated-column rate ↓. Log `tables_pruned`, `columns_kept`.
2. **Pydantic validation.** `field_validator(strip)` on `QueryRequest`; new `GeneratedSQL(sql, tables, columns, has_limit, estimated_rows)`; `QueryParams(limit=Field(ge=1,le=100))`. Replace `.dict()` with `.model_dump()`.
3. **AST guard (`sqlglot`, fallback `sqlparse`).** Parse, then enforce: single statement; type ∈ {SELECT, WITH…SELECT}; no DDL/DML/DDL keywords; referenced tables ⊆ allowlist; `LIMIT` injected if missing (default 200, max 1000); statement timeout 5s; read-only connection (`mode=ro` / `SET TRANSACTION READ ONLY`). `is_safe_query(startswith)` is deleted, not extended.
4. **Retry loop (≤2 passes).** On (a) Pydantic fail, (b) AST reject, (c) PostgreSQL runtime error: feed back trimmed error (code + message, no secrets) + pruned schema + prior SQL, regenerate at temperature 0. After 2 failures return standard error envelope with `requestId`, `telemetry.attempts=3`, no raw traceback. Every retry is logged with latency split (router/prune/gen/validate/exec).

Telemetry per request: `{request_id, intent, tables, latency_ms{total,llm,db}, ast_verdict, attempts, rows, tokens_est}` — surfaced in UI §7.

## 4. Structured Operational Payloads

Beyond `result` rows, `POST /api/v1/query` returns:

```json
{
  "data": {"question":"…","sql_query":"…","rows":[…],"row_count":n},
  "telemetry": {"request_id":"req-…","intent":"rank","latency_ms":812,"attempts":1,"ast":"pass"},
  "actions": {
    "email_draft": {"to_role":"tutor","subject":"…","body":"…","needs_approval":true},
    "cs_tags": ["at-risk:math","praise:grade-A"],
    "gtm_triggers": [{"type":"follow-up","owner":"csm","due_in_days":3,"reason":"…"}]
  }
}
```

Rules: actions are **suggestions, never auto-executed** (commercial/bizops hard rule: route to named human). `email_draft` requires explicit `POST /api/v1/actions/approve`. CS tags drawn from closed taxonomy. No PII in logs (pr-review-expert secret scan in CI).

## 5. Backend & API Standards (api-design-reviewer)

- Version: `/api/v1/...`; URL versioning (recommended in skill). Old unversioned routes kept as 308 redirects for one release, then removed (breaking-change detector gate).
- Error envelope: `{error:{code,message,details,requestId,timestamp}}` with codes `VALIDATION_ERROR, UNSAFE_SQL, DB_ERROR, LLM_TIMEOUT, RATE_LIMITED`.
- Pagination everywhere: cursor-based for `/history`, `limit/offset` capped for query rows.
- Status codes: 400/401/403/404/422/429/500 per matrix; `429` with `Retry-After` + rate-limit headers.
- Auth: bearer JWT (even if single-tenant initially — reserves the seam); RBAC `read:query, approve:action`.
- Scorecard gate: new endpoints must grade ≥B before merge; linter clean; breaking changes need version bump.

## 6. Regression Suite Preservation (api-test-suite-builder)

Current 9 tests → **20-case pytest suite** (the number v2 promises):

- Keep all 9 (fix `test_root` assertion, migrate `@validator` → `@field_validator`, mock LLM/DB so suite runs offline).
- Add 11: unsafe `;DROP` rejected, UNION-exfil rejected, multi-statement rejected, missing-LIMIT injected, unknown-column retry succeeds on pass 2, PG-error retry succeeds, retry-exhausted returns envelope, `/history?limit=-1` → 422, oversized question → 422, empty DB result → valid empty + actions, telemetry fields present.
- Layout: `eval/test_regression_20.py`, `eval/benchmark_20.py` (extends `benchmark.py` 3→20 cases, persists JSONL with mean/p50/p99, fails CI on p99 regression >15% or any AST bypass).
- Runner: `pytest -q` in CI; `make test` updated (drop `python test_api.py` direct-run). Coverage-delta gate: drop >5% blocks merge; auth/approve paths require 100%.

## 7. Interface Craft & Component Architecture

Stack (senior-frontend): **Next.js 14+ App Router, TypeScript strict, Tailwind, React Query, Framer Motion, Vitest + Testing Library.** Design tokens (ui-design-system + design-system): 12 HSL custom properties, 8pt spacing, Inter/heading-font pairing, WCAG-AA 4.5:1 gate, `technical` style default.

Dual-panel dashboard (`/dashboard`):

```
┌─ Left: PromptPanel ────────┬─ Right: ExecutionPanel ─────────┐
│ NL input + intent badge    │ Tabs: SQL Editor | Diff | Rows  │
│ schema chips (kept tables) │ SQL editor (read-only + copy)   │
│ Run (⌘Enter), Stop         │ Diff view (attempt 1→2)         │
│ latency/AST strip          │ Telemetry (latency bars, AST)   │
│ action triggers (approve)  │ Filterable DataTable + export   │
└────────────────────────────┴─────────────────────────────────┘
```

- **Motion (Animations.Dev / epic-design, restrained):** spring-physics panel transitions (stiffness ~300, damping ~30), layout-morph tab switch, fluid telemetry bars; `prefers-reduced-motion` respected. No cinematic scrolljacking — ops tool, not marketing site.
- **Micro-detail (Devouring Details):** 1px crisp borders, `shadow-sm` only, tabular-nums for latency, mono for SQL, keyboard-first: `⌘Enter` run, `⌘.` stop, `/` focus prompt, `1/2/3` tabs.
- **Ergonomics (InterfaceCraft):** persistent execution log (requestId, attempts, ms split), filterable/sortable table with row-cap notice, approve-with-diff for email drafts, empty/error states with next action.
- Component tree: `app/dashboard/page.tsx` → `<PromptPanel/> <ExecutionPanel/>` → `<SQLEditor/> <DiffView/> <TelemetryStrip/> <DataTable/> <ActionCards/>` + `lib/api-client.ts` (typed, React Query) + `lib/tokens.css`.

Streamlit `app_v2.py` stays for one release as `/legacy-ui`, then removed.

## 8. Data & Deployment

- Migrate SQLite → **PostgreSQL** (senior-architect DB workflow: structured + relational + ACID → SQL). SQLAlchemy 2.0 + Alembic migrations, seed port, read-only role for execution, statement_timeout 5s.
- Docker: `api` + `db(postgres:16)` + `web(next)`; healthchecks on `/api/v1/health` (checks DB **and** LLM ping — fixes current gap). Non-root, `HEALTHCHECK`, slim images preserved.
- Observability: structured JSON logs with `request_id`, Prometheus `/metrics` (latency histogram, retry count, AST rejects), LangSmith optional (trace LLM only, PII redacted).

## 9. Phased Implementation Roadmap

- [ ] **Phase 0 — Stabilize (days 1–2).** Fix `test_root`, `@field_validator`, `.model_dump()`, `limit` bounds, add `requestId` + JSON logging. Gate: `pytest -q` green offline (mocked LLM/DB).
- [ ] **Phase 1 — Safety core (days 3–5).** Add `sqlglot` AST guard + LIMIT injection + read-only exec + timeout; delete `startswith` check. Gate: 4 new negative tests pass; scorecard ≥B.
- [ ] **Phase 2 — Agent loop (days 6–9).** Implement intent-router + schema-pruner + 2-pass retry + telemetry envelope. Gate: pruned-token metric logged; retry tests (PG-error→success, exhaust→envelope) pass.
- [ ] **Phase 3 — API v1 (days 10–12).** Version routes, error envelope, pagination, JWT scaffold, rate limits. Gate: api-linter clean, breaking-change detector passes, OpenAPI published.
- [ ] **Phase 4 — Postgres (days 13–15).** SQLAlchemy + Alembic + seed port + ro-role + docker-compose `db`. Gate: SQLite and PG both pass regression suite.
- [ ] **Phase 5 — Operational payloads (days 16–19).** `actions` object + approve endpoint + CS taxonomy + audit log. Gate: no auto-execute; approval flow e2e tested.
- [ ] **Phase 6 — 20-case regression (days 20–22).** Expand to 20 pytest cases + `benchmark_20.py` with JSONL + 15% p99 gate in CI. Gate: CI blocks on regression.
- [x] **Phase 7 — Next.js dashboard (days 23–30).** Scaffold App Router + tokens + components + React Query client + Framer Motion + ⌘Enter ergonomics. Gate: Vitest coverage on all components (38 tests); WCAG-AA contrast on token pairs (both themes); Streamlit demoted to `/legacy-ui`. Added: `DEMO_MODE` flag and real-data mode (`docs/DEMO_AND_REAL_DATA.md`), guided Steps view. Open: browser visual pass on a phone-width viewport; Docker compose stack not run end to end.
- [ ] **Phase 8 — Hardening & review (days 31–33).** Full pr-review-expert pass (blast radius, secrets scan, N+1, coverage delta), load test, docs. Gate: 0 critical issues (agent-designer verification loop), merge to `dev`.
