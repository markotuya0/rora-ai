# Demo mode and your own data

Rora AI runs in one of two modes, chosen by one flag.

| | `DEMO_MODE=true` (default) | `DEMO_MODE=false` |
|---|---|---|
| Data | Bundled student grades (`student_grades.db`) | Your database (`DB_URI` or `DB_PATH`) |
| Schema | Hardcoded `grades` table, pruned by demo rules | Read live from your database, pruned by the tables a question names |
| Out-of-scope check | Rejects questions about data the demo lacks (e.g. customers) with a 422 | Off: every question goes to the model |
| Subject check | A named subject (Math, History, Science) must appear in the SQL | Off |
| Example questions | Shown in the UI | Hidden |
| Safety guard | On | **On** (read-only SELECT, only tables in your schema, LIMIT injection) |

## Configuration

```bash
# Use your own database
DEMO_MODE=false
DB_URI=postgresql://reader:secret@db.internal:5432/sales   # or sqlite:////abs/path/to.db

# Keep the demo
DEMO_MODE=true              # default
DB_PATH=student_grades.db   # used when DB_URI is not set
```

`DB_URI` takes precedence over `DB_PATH`. Note that `docker-compose.yml` sets `DB_URI` for the
bundled Postgres; to point the stack at your database, override that variable.

## Connecting your own database

1. **Use a read-only database user.** The SQL guard blocks writes, but a read-only role is the
   defence that does not depend on parsing. Grant `SELECT` on the tables you want to expose and nothing else.
2. Set `DEMO_MODE=false` and `DB_URI` as above, then start the API.
3. Check what the API sees:
   ```bash
   curl -s localhost:8000/api/v1/config
   ```
   `tables` lists the tables the model can query. Anything not listed is rejected by the guard.
4. Open the dashboard. The banner under the header lists your tables.

The model only sees the schema for tables your question names, so large databases stay cheap to query.
If the question names no table, the full schema is sent instead.

## The guided view

Each answer has a **Steps** tab (key `1`) that explains what happened, in order:

1. **Understood the question**: the intent the router chose (aggregate, filter, rank, trend, join, metadata).
2. **Picked the relevant tables**: which tables were used, and how much schema was left out of the prompt.
3. **Wrote the SQL**: how many attempts it took. A retry happens only when a safety or subject check fails.
4. **Checked it is safe**: read-only verdict, or the reason the query was blocked.
5. **Ran it**: database time and row count.

The steps come from data the API already returns, so the guide costs no extra model calls.

Other tabs: SQL (key `2`), Diff against the previous run (`3`), Rows (`4`).

## Limits

- Real-data mode relies on the model writing correct SQL for your schema. There are no
  demo-specific checks in that mode, so review answers before acting on them.
- The model runs locally through Ollama. Set `LLM_MODEL` to a model you have pulled.
- Action cards (email drafts, tags, triggers) are generated for any mode but need approval before anything runs.

## Why answers can be slow

The model runs on your machine through Ollama, usually on the CPU. A basic question can take several seconds, or much longer when the machine is short on memory: the model's memory gets paged to disk and every call slows down.

What the app does to reduce this:

- **Saved answers (demo mode).** The four example questions have stored SQL. They skip the model entirely, so they return in well under a second. The result still comes from a live query.
- **Reused answers.** A question asked before, against the same schema, reuses its SQL and skips the model. Only the SQL is cached. Results are always fresh, and the safety checks still run.
- **Smaller context.** The model window is capped at 2048 tokens, because the prompts are short. This uses less memory.

The guided view says which path an answer took: a saved example, a reused answer, or a model call.

To choose a model, set `LLM_MODEL` to one you have pulled with `ollama pull`. The default is `llama3.1:8b`. A smaller model such as `llama3.2:3b` is faster but was less reliable in testing: it failed a plain filter question with SQL syntax errors and dropped a column from a grouped answer. Check the answers on your own data before you rely on either model.
