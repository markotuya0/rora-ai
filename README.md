# Rora AI — Text-to-SQL Dashboard

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/Docker-image%20builds-blue.svg)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/markotuya0/rora-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/markotuya0/rora-ai/actions)

> **Ask a question in plain English and get SQL, the answer, and a step-by-step explanation of how it was produced. Every query is checked before it runs, and it runs read-only.**

![Rora AI dashboard on desktop](images/dashboard-desktop.png)

> **Status: under active development.** The core flow works and is tested on the setup described in [Compatibility](#compatibility). Several parts are not verified yet (PostgreSQL, the full Docker Compose stack, real devices and browsers). See [Compatibility and limits](#compatibility-and-limits) before relying on it.

Rora AI is a full-stack Text-to-SQL app. It runs a local language model through [Ollama](https://ollama.com), so questions and data stay on your machine and there are no per-query API costs. Parts of this codebase were written with AI assistance (Claude Code); the tests and checks described below were run before each commit.

---

## Contents

- [What it does](#what-it-does)
- [Screenshots](#screenshots)
- [Quick start](#quick-start)
- [Using the dashboard](#using-the-dashboard)
- [Using your own data](#using-your-own-data)
- [Configuration](#configuration)
- [API](#api)
- [Editing the project](#editing-the-project)
- [Testing](#testing)
- [Compatibility and limits](#compatibility-and-limits)
- [Project structure](#project-structure)
- [Roadmap](#roadmap)
- [Author and license](#author-and-license)

---

## What it does

When you ask a question, the app works through these steps. The dashboard shows each one in its **Steps** tab.

1. **Reads the question.** A rule-based router labels the kind of question: aggregate, filter, rank, trend, join or metadata.
2. **Picks the relevant tables.** Only the tables the question names are sent to the model, which keeps prompts small and fast.
3. **Writes the SQL.** A local model (Ollama) generates a single `SELECT`. Known demo questions and repeated questions reuse stored SQL instead, so the model is not called.
4. **Checks the SQL.** The query must be a single read-only `SELECT`, touch only tables in your schema, and (in demo mode) filter on any subject the question names. A query that fails a check is sent back with the reason and retried, up to three attempts.
5. **Runs it and returns the rows.** A row limit is added if the query has none.

Other features:

- **Demo mode** with bundled student-grades data, so you can try the app with no setup beyond Ollama.
- **Real-data mode** (`DEMO_MODE=false`) that reads the schema from your own database.
- **"Your data" panel** that profiles the connected database: row counts, sample rows, and per-column statistics.
- **Approval flow** for suggested actions (email drafts, tags, follow-up triggers). Nothing runs until you approve it.
- **Keyboard-first dashboard** with motion that respects the reduced-motion setting.
- **Per-client rate limiting** and an optional JWT scaffold (off by default).

---

## Screenshots

| Desktop | Phone (390 px wide) |
|---|---|
| ![Dashboard on desktop](images/dashboard-desktop.png) | ![Dashboard on a phone](images/dashboard-mobile.png) |

Both screenshots show the empty state in demo mode: the mode banner, the closed **Your data** panel, the example questions, and the step list waiting for a question. They were captured in headless Chrome with reduced motion on, so animations are finished. They are not a recording of a query.

---

## Quick start

You need [Ollama](https://ollama.com) installed on the machine that runs the app.

### Option 1: local development (recommended to try it)

```bash
git clone https://github.com/markotuya0/rora-ai.git
cd rora-ai

# Python API
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Local model (about 4.9 GB; first pull takes a while)
ollama pull llama3.1:8b

# Demo database (creates student_grades.db)
python create_db.py

# Start the API on port 8000
uvicorn api:app --host 127.0.0.1 --port 8000
```

In a second terminal, start the dashboard:

```bash
cd web
npm install
npm run dev
```

Open **http://localhost:3000/dashboard**.

Check the API with `curl http://localhost:8000/api/v1/health`. It returns `{"status":"healthy", ...}` when the database is reachable.

### Option 2: Docker Compose

```bash
ollama pull llama3.1:8b            # on the host
docker compose up --build
```

| Service | URL | Notes |
|---|---|---|
| Dashboard | http://localhost:3000/dashboard | Next.js UI |
| API | http://localhost:8000 | Swagger at `/docs` |
| Legacy UI | http://localhost:8501 | Streamlit, kept for one release |

The API container reaches Ollama on the host through `host.docker.internal`. **This stack is not verified end to end yet.** The database it starts is an empty PostgreSQL instance with no demo data loaded, so questions will fail until you load data. See [Compatibility and limits](#compatibility-and-limits).

### Option 3: Makefile

```bash
make setup     # venv, dependencies and demo database
make api       # API on port 8000
make ui        # Streamlit UI (legacy)
make test      # backend test suite
make docker    # docker compose up --build
```

---

## Using the dashboard

The page has three areas: the **mode banner** (demo or your database), the **Your data** panel, and the **question** and **answer** panels.

1. **Ask a question.** Type one, or click an example (demo mode shows four). Press **⌘↵** on macOS or **Ctrl+Enter** elsewhere.
2. **Watch the progress.** While the model runs, the status line shows elapsed seconds. After 10 seconds it notes that the local model is slow.
3. **Read the answer.** The answer panel has four tabs:

   | Tab | Key | What it shows |
   |---|---|---|
   | Steps | `1` | Plain-language explanation of each stage (see below) |
   | SQL | `2` | The generated query, with a copy button |
   | Diff | `3` | Changes from the previous answer's SQL |
   | Rows | `4` | The rows, filterable and sortable, with CSV export and a row cap of 200 |

4. **Check the telemetry.** Below the tabs you see total time, how much schema was left out of the prompt, the safety verdict, the attempt count, and the time spent in each stage.
5. **Approve suggestions** (if any). Email drafts, tags and triggers appear as cards. **Approve** or **Reject** each one. Nothing runs until you do.

**Keyboard shortcuts** (when you are not typing in a field):

| Key | Action |
|---|---|
| `/` | Focus the question box |
| `1` `2` `3` `4` | Switch answer tabs |
| **⌘.** / **Ctrl+.** | Stop a running query |

### Reading the Steps tab

| Step | What it tells you |
|---|---|
| Understood the question | The kind of question, and what that means for the query |
| Picked the relevant tables | Which tables were used, and how much schema was left out of the prompt |
| Wrote the SQL | How it was produced: a saved example (no model call), a reused earlier answer (no model call), or the model, with the number of attempts |
| Checked it is safe | "Read-only SELECT", or the reason the query was blocked |
| Ran it | Database time and the number of rows returned |

A retry only happens when a check fails. The Steps tab says so when an answer needed one.

---

## Using your own data

Demo mode answers only from the bundled student-grades table, and it rejects questions about other data with a clear message. To query your own database, switch it off:

```bash
DEMO_MODE=false
DB_URI=postgresql://reader:secret@db.internal:5432/sales     # or sqlite:////absolute/path/to/file.db
```

In real-data mode the API reads the schema from your database, includes only the tables a question names in the prompt, and skips the demo-only checks. **The safety checks stay on.** The full setup, the read-only-user advice, and what each step means are in [docs/DEMO_AND_REAL_DATA.md](docs/DEMO_AND_REAL_DATA.md).

Check what the app can see:

```bash
curl http://localhost:8000/api/v1/config     # mode, tables, example questions
curl "http://localhost:8000/api/v1/sample?rows=3"   # what is in the database
```

---

## Configuration

Set these as environment variables, or in a `.env` file copied from `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `DEMO_MODE` | `true` | `true`: bundled demo and its checks. `false`: your own database |
| `DB_URI` | unset | Database URL. Takes precedence over `DB_PATH` when set |
| `DB_PATH` | `student_grades.db` | SQLite file used when `DB_URI` is unset |
| `LLM_MODEL` | `llama3.1:8b` | Ollama model name. Must be pulled with `ollama pull` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Where Ollama is listening |
| `LLM_TEMPERATURE` | `0` | Model temperature. Keep at 0 for repeatable SQL |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins for the browser |
| `MAX_QUERY_LENGTH` | `500` | Longest question accepted, in characters |
| `RATE_LIMIT_PER_MIN` | `60` | Requests per client per minute |
| `AUTH_ENABLED` | `false` | Turn on JWT checks for `/api/v1` routes |
| `AUTH_SECRET` | `dev-secret-change-me` | Signing key. **Change it before enabling auth** |
| `AUTH_TOKEN_TTL` | `3600` | Token lifetime in seconds |

Dashboard settings (set in the environment of `npm run dev` or the web build):

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API the dashboard calls |
| `NEXT_PUBLIC_API_TOKEN` | unset | Bearer token for `AUTH_ENABLED` deployments. It is visible to anyone who loads the page, so use a demo-scoped token only |
| `NEXT_PUBLIC_LEGACY_UI_URL` | `http://localhost:8501` | Link target on the `/legacy-ui` page |

---

## API

The versioned API lives under `/api/v1`. Interactive docs are at `/docs`. The unversioned routes (`/query`, `/history`, `/schema`, `/health`) redirect to their `/api/v1` equivalents.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/query` | Ask a question. Body: `{"question": "..."}` |
| `GET` | `/api/v1/history?limit=10&cursor=...` | Past answers, cursor-paginated |
| `GET` | `/api/v1/schema` | Schema text the model sees |
| `GET` | `/api/v1/config` | Mode, tables, example questions, model name |
| `GET` | `/api/v1/sample?rows=5` | Row counts, sample rows and column statistics |
| `GET` | `/api/v1/health` | Health check (database reachable) |
| `POST` | `/api/v1/actions/approve` | Approve or reject a suggested action |
| `GET` | `/api/v1/actions/audit-log` | Recent approval events |

Example query (demo mode):

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Average score per subject"}'
```

The response has these fields: `question`, `sql_query`, `result` (a Python-style list of row tuples as text), `timestamp`, `success`, `execution_time`, `request_id`, `telemetry` (intent, tables, safety verdict, attempts, `source` = `example` | `cache` | `model`, and timings in milliseconds), and `actions`.

Errors use one envelope: `{"error": {"code", "message", "details", "requestId", "timestamp"}}`. Codes you will see include `VALIDATION_ERROR` (422, for example a question outside the demo's data), `UNSAFE_SQL` / `BAD_REQUEST` (400), `RATE_LIMITED` (429, with a `Retry-After` header), and `DB_ERROR` (500).

---

## Editing the project

Here is where things live and how to change them.

| I want to... | Edit |
|---|---|
| Change the query pipeline (order of steps, retries, telemetry) | `rora_api/v1/routes.py`, function `_run_query` |
| Change how questions are routed, tables are picked, or subjects are checked | `agent.py` (`route_intent`, `prune_schema`, `prune_live_schema`, `missing_subject_filters`) |
| Change the SQL safety rules | `utils.py`, function `_ast_verdict` (`validate_sql` wraps it). Add rules here and cover them in `test_utils.py` |
| Change the model prompt or model options | `api.py`: the `prompt` template and the `ChatOllama(...)` call |
| Add a demo example question | `agent.py`: add to `DEMO_EXAMPLES` and to `DEMO_SAVED_SQL` (keys come from `normalize_question`). Add a test in `test_agent.py` |
| Change what the database profile shows | `db/client.py`, function `profile_database` |
| Add or change an endpoint | `rora_api/v1/routes.py` (or `rora_api/v1/actions.py`). Keep the error envelope. Add a test in `test_api.py` |
| Change the dashboard page | `web/app/dashboard/page.tsx` |
| Add a dashboard panel | `web/components/` (one file per component), tests in `web/components/__tests__/` |
| Change the API types or React Query hooks | `web/lib/api-client.ts`. Keep these in step with `rora_api/v1/routes.py` |
| Change motion timing | `web/lib/motion.ts` (one easing curve for the whole UI) |
| Change colours and spacing | `web/app/globals.css` (HSL triplets as tokens), mapped in `web/tailwind.config.ts`. Check text contrast against WCAG AA 4.5:1 after changing a colour |

Ground rules that the code relies on:

- **Model output is never trusted.** Every SQL statement goes through the guard and the table allowlist before it runs, including saved and cached SQL.
- **Results are never cached.** Only SQL is reused, and a reused query is run fresh every time.
- **Demo-only checks belong behind `DEMO_MODE`.** Do not add rules that assume the demo's table names to code that also runs in real-data mode.

---

## Testing

Backend (Python):

```bash
python -m pytest test_utils.py test_agent.py test_core.py test_db.py test_ops.py test_api.py eval/test_regression_20.py -v
# or
make test
```

Frontend (in `web/`):

```bash
npm test              # Vitest unit and component tests
npx tsc --noEmit      # type check
npm run build         # production build
```

Lint, as CI runs it:

```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

Notes on the suites:

- `eval/test_regression_20.py` uses a **mocked model**. It checks the pipeline's behaviour (safety, retries, error paths). It does **not** measure how accurate the model's SQL is.
- The tests use their own database file (`test_student_grades.db`), set in `conftest.py`, so they never change `student_grades.db`.
- CI runs the backend suite on Python 3.11 and 3.12. The frontend checks are not yet part of CI.

---

## Compatibility and limits

Rora AI is still being extended. This table is the honest state of each part.

| Area | Status | Notes |
|---|---|---|
| Python 3.12 | Tested | Local development and the backend test suite |
| Python 3.11 | In CI, not run locally | Declared in CI and the badge |
| Node.js | Tested on Node 24 (local) | The web image uses Node 20. Next.js 14 is pinned |
| Operating system | Tested on Linux | macOS and Windows are not tested |
| Browsers | Headless Chrome only | Screenshots and rendering were checked in Chrome. Safari and Firefox are not tested |
| Phone layout | Checked in headless Chrome at 390 px | Not tested on real phones |
| Ollama model `llama3.1:8b` | Default, tested | About 5 to 50 seconds per model-backed answer on a 16 GB CPU-only machine, with retries and swap making the slow end worse |
| Ollama model `llama3.2:3b` | Tested, **less reliable** | Failed a plain filter question with SQL syntax errors and dropped a column from a grouped answer. Faster, but check its answers |
| Other Ollama models | Not tested | Any model that writes SQL may work. Check the answers |
| SQLite | Tested | Demo and real-data mode |
| PostgreSQL | **Not verified** | Wired through `DB_URI` and used by the Docker Compose setup. Not yet run against a live server |
| Docker image (web) | Builds, serves `/dashboard` | Built and run locally |
| Docker Compose stack | **Not verified end to end** | Starts an empty PostgreSQL with no demo data loaded |
| Real-data SQL accuracy | Not measured | The evaluation suite mocks the model. Measure accuracy on your own data before you rely on answers |
| Authentication | Scaffold, **off by default** | JWT checks exist, but the secret and token handling are not production-reviewed |
| `NEXT_PUBLIC_API_TOKEN` | Exposes the token in the browser | Only for demo-scoped tokens |

**Known limitations to plan around:**

- Answers from a local model on a CPU can be slow. Example questions and repeated questions are answered from stored SQL and are fast (well under a second on the test machine).
- The model can write wrong SQL and the checks cannot always detect it. Real-data mode has no demo-specific checks, so review answers before you act on them.
- The results are returned as text in Python's tuple format, which the dashboard parses for the table. Unusual value types fall back to raw text.
- Fonts load from Google Fonts at runtime. Without network access, the system fonts are used.

---

## Project structure

```
rora-ai/
├── api.py                    # FastAPI app: CORS, error handlers, LLM client, legacy redirects
├── agent.py                  # Router, schema pruning, retry helpers, demo examples, saved SQL
├── utils.py                  # SQL safety: validate_sql, ensure_limit, clean_sql
├── config.py                 # Environment configuration
├── rora_api/                 # Versioned API package
│   ├── v1/routes.py          # /api/v1 query pipeline, history, schema, config, sample
│   ├── v1/actions.py         # Approve and audit-log endpoints
│   └── core/                 # Auth scaffold, rate limiting, pagination, error envelope
├── db/                       # SQLAlchemy engine, read-only client, profiler, models, Alembic migrations
├── ops/                      # Action synthesis (email, tags, triggers) and audit log
├── eval/                     # Regression tests and benchmark scripts
├── web/                      # Next.js dashboard (App Router, Tailwind, Framer Motion, React Query)
│   ├── app/dashboard/        # The dashboard page
│   ├── components/           # Prompt, execution tabs, guided steps, tables, data profile
│   ├── lib/                  # API client and hooks, parser, diff, motion tokens
│   └── hooks/                # Keyboard shortcuts, elapsed time
├── app_v2.py                 # Streamlit UI (legacy)
├── docs/DEMO_AND_REAL_DATA.md  # Demo mode, real-data setup, the guided view, slow answers
├── images/                   # Screenshots used in this README
├── test_*.py                 # Backend tests
├── conftest.py               # Points tests at a separate database file
├── docker-compose.yml        # API, PostgreSQL, web, legacy Streamlit
├── Dockerfile                # API image
├── Makefile                  # Development commands
├── requirements.txt          # Pinned Python dependencies
├── ARCHITECTURE_v2.md        # Design and phase roadmap
├── DEPLOYMENT.md             # Deployment notes
└── CONTRIBUTING.md           # Contribution guidelines
```

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md). It covers environment variables, Docker, and cloud options (AWS, GCP, Azure, Heroku, Railway). The cloud sections are general guides and are not tested against this project.

---

## Roadmap

- [x] FastAPI REST API under `/api/v1`, with OpenAPI docs
- [x] LangChain + Ollama local model integration
- [x] Read-only SQL guard with a table allowlist and a subject check
- [x] Retries with feedback, and telemetry for every answer
- [x] Demo mode and real-data mode (`DEMO_MODE=false`)
- [x] Saved answers and a SQL cache for fast repeat questions
- [x] Next.js dashboard with a guided Steps view, keyboard shortcuts, and motion
- [x] Data profile ("Your data") for the connected database
- [x] Approval flow for suggested actions, with an audit log
- [x] Per-client rate limiting
- [x] Docker image for the dashboard; Docker Compose service definitions
- [x] GitHub Actions CI for the backend
- [ ] Verify the full Docker Compose stack end to end (load data into PostgreSQL)
- [ ] Verify PostgreSQL against a live server
- [ ] CI job for the frontend (tests, type check, build)
- [ ] Browser check on real phones and on Safari and Firefox
- [ ] Measure SQL accuracy on a fixed set of real questions with the real model
- [~] JWT authentication: scaffold, off by default, not production-reviewed
- [~] Query result export: CSV in the dashboard, JSON not yet
- [ ] Redis caching for shared deployments
- [ ] Multi-database support (MySQL, MSSQL)
- [ ] Data visualisation charts
- [ ] LangSmith observability

---

## Author and license

**Mark Otuya**, Full-Stack and AI Engineer

- Portfolio: [markotuya.netlify.app](https://markotuya.netlify.app)
- LinkedIn: [linkedin.com/in/mark-chukwu](https://linkedin.com/in/mark-chukwu)
- GitHub: [@markotuya0](https://github.com/markotuya0)

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

Released under the MIT License. See [LICENSE](LICENSE).
