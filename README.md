# DataDetective AI

**From Raw Data to Verified Discoveries — Autonomously.**

A local multimodal data investigation workspace built for the **Applied AI & Next-Gen Agents** hackathon track. Upload a CSV or workbook, optionally attach a chart screenshot, ask a question, and inspect the tools, queries, evidence, charts, and report produced during the investigation.

The problem: dashboards show changes, but finding the contributing segments usually takes repeated manual queries. DataDetective gives an AI model a small, validated analytical toolbox and feeds every observation back into its next decision.

## Features

- CSV / XLSX / XLS upload, preview, type detection, date coverage, missing values, duplicates, and numeric summaries.
- Bounded Gemini investigation loop with structured, Pydantic-validated actions. No prewritten sales query sequence is used in AI mode.
- Chart screenshot interpretation with structured axes, categories, dates, visible patterns, schema matches, and ambiguity disclosure.
- Parser-restricted DuckDB SQL with resource limits and no external access.
- Descriptive statistics, percentage changes, Pearson correlation, group comparisons, and IQR outlier candidates.
- Interactive Plotly line, bar, scatter, histogram, and correlation heatmap specifications from actual evidence.
- Public decision timeline, expandable SQL and evidence, exact-cell recomputation ledger, findings, limitations, follow-up suggestions, and Markdown export.
- Explicit **Offline analytics** mode: deterministic rules execute real analytics without credentials. The question and image do not control this mode. It is never represented as an autonomous agent.
- Three reproducible synthetic demo datasets and independently computed expected retail results.

## Local setup (Windows PowerShell)

Requirements: Python **3.13** (tested), Node **22+**, npm, and an optional Gemini API key. No database server is needed. Execute from `C:\Users\hp\Desktop\DataDetective`.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
cd frontend
npm ci
cd ..
```

The demo files are included. Regenerate them reproducibly if needed:

For exact dependency reproduction, install `backend/requirements-lock.txt` instead of `backend/requirements.txt`. The lock captures the environment validated in this checkout; `frontend/package-lock.json` is used by `npm ci`.

```powershell
.\.venv\Scripts\python demo\generate.py
```

Backend, terminal 1, from the project root:

```powershell
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Frontend, terminal 2:

```powershell
cd C:\Users\hp\Desktop\DataDetective\frontend
npm run dev
```

Open [the workspace](http://127.0.0.1:5173) and [interactive API documentation](http://127.0.0.1:8000/docs). Vite proxies `/api` to FastAPI. The app works without a Gemini key in Offline analytics mode.

On macOS/Linux, use `python3`, `.venv/bin/python`, and your checkout path in place of the Windows equivalents.

## Gemini configuration

Create a key in [Google AI Studio](https://aistudio.google.com/apikey). Copy the safe example and edit `.env` locally:

```powershell
Copy-Item .env.example .env
```

```dotenv
GEMINI_API_KEY=replace-with-your-key
GEMINI_MODEL=gemini-flash-latest
MAX_AGENT_STEPS=8
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Restart FastAPI and click **Reconnect**. Select **Gemini autonomous agent**. A model alias can change; use a text-and-image capable model available to your API account. Keys stay on the backend and `.env` is ignored by Git. Do not put credentials in `VITE_` variables. Agent mode sends dataset previews, schema, bounded tool results, your question, and any attached image to Google; offline mode does not.

The official `google-genai` SDK's `client.aio.models.generate_content`, `GenerateContentConfig(response_schema=...)`, and image `Part.from_bytes` interface are used. PydanticAI was intentionally omitted to keep the hackathon integration small. Reference: [Google Gen AI SDK](https://googleapis.github.io/python-genai/).

## How the agent works

```text
Question + dataset profile + optional structured vision context
    → model selects one typed action and a brief public decision
    → validate action arguments and SQL AST
    → execute analytical tool
    → persist evidence ID and timeline event
    → provide actual observation/error to the model
    → model selects a follow-up, chart, verification, or finish
    → evidence-linked report with explicit limitations
```

The model can invoke `profile_dataset`, `execute_sql`, `calculate_statistics`, `inspect_image`, `generate_chart`, and `verify_finding`. `finish` ends the analytical loop. An initial profile and optional image interpretation happen before the adaptive loop. The model's subsequent analytical steps are chosen from actual observations; its public explanation is shown in the timeline. Internal chain-of-thought is neither requested nor displayed.

Default budget: eight analytical calls (configurable 2–12), plus initial vision, profile, and final report. Model requests have a 50-second outer timeout, two model failures stop the loop, and three tool failures end exploration. Only two investigations run concurrently and four may be active/queued. No analytical success means a failed investigation, never invented results. If report generation fails after valid analytics, a transparent computed summary is used.

SQL evidence has at most 200 rows; the model sees at most 35 rows per observation, explicitly marked when omitted. All evidence is inspectable in the UI. Charts use the retained tool result rather than regenerated model data.

**Verification scope:** a numerical verification re-executes the source SQL and compares one selected cell with both its original value and the model's expected value. The ledger stores the SQL, source ID, cell, expected/actual values, and result. This verifies that cell only. Evidence-linked narrative findings and hypotheses are not automatically marked verified. Segment contributions are not proven causes.

## Multimodal behavior

PNG/JPEG files are decoded, size-checked, metadata-stripped, and resized on the backend. Gemini returns typed chart information and compares labels with real schema columns. Unknown schema matches are removed and disclosed. Ambiguities remain visible. The planner receives this context before selecting analytical tools. Visual estimates are explicitly unverified and cannot enter the numeric verification ledger without an actual SQL result. Offline mode stores the image but explicitly skips interpretation.

## Project structure / two-developer split

```text
backend/                       Developer 1
  main.py                      FastAPI REST interface
  agent/
    investigator.py            Adaptive and explicitly separate offline workflows
    prompts.py                 Tool descriptions and evidence rules
    schemas.py                 Shared Pydantic contracts
  tools/
    data_loader.py, profiler.py CSV/Excel loading and quality
    sql_engine.py              SQL AST restrictions and bounded DuckDB execution
    statistics.py              Predefined statistical operations
    vision.py                  Validated uploads and Gemini chart interpretation
    charts.py, verifier.py     Data-only chart specs and numeric recomputation
  services/
    sessions.py, reporting.py  In-memory lifecycle and report generation
  tests/                       Unit, safety, adaptive-loop and API integration tests
  requirements.txt
frontend/                      Developer 2
  src/App.tsx                  Workspace and orchestration UI
  src/components/              Upload, preview, timeline, charts, report
  src/api.ts, src/types.ts     REST client and frontend contracts
  src/styles.css               Responsive dark analytical workspace
demo/
  generate.py                  Seeded synthetic generator
  retail_sales.csv             5,292 records
  retail_preview.xlsx          300-row Excel loading sample (not the full demo)
  revenue_decline.png          Chart screenshot for multimodal investigation
  expected_findings.json       Pandas-computed ground truth
  sensor_data.csv              2,400 records, missing measurements and injected outliers
  student_performance.csv      900 synthetic observations
.env.example, .gitignore
```

Keep the REST contracts stable between developers; backend changes need not alter presentation components. FastAPI OpenAPI is the authoritative schema, with frontend types mirroring the responses.

## API

| Endpoint | Behavior |
| --- | --- |
| `GET /api/health` | Health, model name, AI configuration state |
| `POST /api/datasets` | Multipart `file`; returns dataset ID, profile and preview |
| `GET /api/demo/{name}` | Load `retail_sales`, `sensor_data`, or `student_performance` |
| `POST /api/images` | Multipart `file`; returns image ID; interpretation happens during investigation |
| `POST /api/investigations` | JSON `dataset_id`, `question`, optional `image_id`, `mode` (`agent` / `offline`); returns 202 and state |
| `GET /api/investigations/{id}` | Poll status, plan, timeline, evidence, findings, charts, report and errors |
| `GET /api/investigations/{id}/report` | Download a Markdown report with evidence appendix |

## Two-minute demo

1. **0:00–0:20** — Open the workspace. Click **Load sample data**, or upload `demo/retail_sales.csv`. Show the profile and preview.
2. **0:20–0:35** — Upload `demo/revenue_decline.png`. In Gemini mode ask: “Why did revenue decline in February? Compare regions, then investigate products in the region contributing most.”
3. **0:35–1:25** — Start investigation. Point to the activity timeline: an observed regional result should inform the model's next drill-down. Expand actual SQL and evidence. Model choices and latency vary; eight steps are a budget, not a guaranteed two-minute completion.
4. **1:25–1:50** — Show the charts, source-linked findings, and exact numeric verification ledger if the model selected verification. Explain that contributions are descriptive, not causal proof.
5. **1:50–2:00** — Show uncertainty and export the report. If Gemini is unavailable, switch to **Offline analytics** and clearly announce that this demonstrates real computation with fixed rules, not AI autonomy or vision.

Independent expected results (never passed to the planner): January revenue **633,633.45**, February **528,492.33**, change **−105,141.12 (−16.5934%)**. West contributes **−95,796.06**; West Electronics contributes **−93,225.75**. These are synthetic currency units. Each synthetic month includes **days 1–28**, so periods have equal coverage but are not complete calendar months. Use the full CSV, not the short Excel preview, for this scenario. Ground truth and the generator's known artificial mechanism are in `demo/expected_findings.json`; the mechanism is not evidence of causality available from the dataset alone.

## Validation

```powershell
.\.venv\Scripts\python -m pytest backend\tests -q
.\.venv\Scripts\python -m compileall -q backend demo
cd frontend
npm run build
```

Tests cover CSV/Excel ingestion, malformed files, inferred types, missing values, SQL attack rejection, aggregates, row bounds, percentage changes, chart values, recomputation status, evidence references, report export, tool/model failures, adaptive follow-up selection with a mocked model, and full offline API investigations across retail, sensors, and students. The controlled-model test validates orchestration; it is not a live Gemini test. See `VALIDATION.md` for the actual execution results from this build.

## Reliability, security and limitations

- Local, single-process hackathon prototype, not a public multi-tenant service. No authentication. Bind to loopback. Session IDs are random but are not an authentication mechanism.
- In-memory storage, no uploaded file paths. Raw filenames are reduced to a display basename. Two-hour expiry is enforced during API access; restart clears all data. Limits: 12 datasets, 20 images, 40 investigations, 15 MB data uploads, 5 MB images, 150,000 rows, 100 columns. XLSX expanded content is limited to 60 MB. Workbook parsing uses the first worksheet.
- SQL parsing uses `sqlglot` plus an explicit function and table allowlist, one SELECT, no recursion, at most eight table references, and no external table functions. Each execution uses an isolated DuckDB connection, 256 MB engine memory, two threads, a four-second interrupt, no extension auto-install/load, external access disabled, and locked configuration. These limits are defense in depth, not an OS sandbox for hostile public use. DuckDB temporary-directory spill is unavailable with external access disabled; oversized work fails.
- Data and image text are untrusted and explicitly separated from system instructions. No arbitrary Python, shell commands, executable JavaScript chart specs, or model-generated HTML is executed. React escapes text.
- Only actual numeric SQL cells can get a verified status. Rerunning a query verifies consistency, not correctness of metric definitions, data truth, causality, or every word of a claim. Model narrative can still be wrong; inspect sources.
- Date inference recognizes ISO date strings. Ambiguous locale formats stay categorical. Missing values are not silently imputed. Correlation is descriptive and includes assumptions. IQR flags need human interpretation.
- No live Gemini/vision validation is possible without a configured key. Invalid keys, quota limits, model changes and network issues are surfaced with bounded failures. No silent switch from AI mode to offline mode.
- Plotly is lazy-loaded because its full interactive distribution is large. Vite can warn about its chunk size; this is expected.
- No PDF export, durable history, multiple-table joins, auth, background scheduler, voice input, database connectors, or production hosting is implemented.

## Build and deployment

`npm run build` produces `frontend/dist`. For a local production-preview check use `npm run preview -- --port 5173`; Vite inherits the development `/api` proxy. For deployment, run one Uvicorn worker (sessions are process-local) behind a reverse proxy forwarding `/api`, serve the static frontend, set `GEMINI_API_KEY` only on the backend, and restrict origins. TLS, authentication, rate limiting, process isolation, durable sessions, and privacy controls are required before public hosting. This implementation is delivered locally and is not published to Sites hosting because its requested Python runtime does not run in a static site or Cloudflare Worker.

## Track fit and future work

This is an applied agent with a bounded **plan → execute → observe → re-plan → verify → report** cycle. Its differentiator is observation-dependent tool selection rather than a fixed chatbot response or dashboard query sequence. Structured chart understanding supplies additional context while exact analytical values come from computation. The offline mode is deliberately separate and is not evidence of agentic capability.

Future work: persistent investigation history, multiple datasets and joins, additional data sources, PDF/voice inputs, stronger statistical tests with validated assumptions, human-reviewed metric definitions, saved investigations, scheduled analyses, and production access control.
