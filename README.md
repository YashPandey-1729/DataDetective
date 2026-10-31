# DataDetective AI

**From Raw Data to Verified Discoveries — Autonomously.**

A local multimodal data investigation workspace built for the **Applied AI & Next-Gen Agents** hackathon track. Upload a CSV or workbook, optionally attach a chart screenshot, ask a question, and inspect the tools, queries, evidence, charts, and report produced during the investigation.

The problem: dashboards show changes, but finding the contributing segments usually takes repeated manual queries. DataDetective gives an AI model a small, validated analytical toolbox and feeds every observation back into its next decision.

For the takeover review see [AUDIT.md](AUDIT.md), current test evidence in [VALIDATION.md](VALIDATION.md), and the presentation/preflight instructions in [demo/DEMO_GUIDE.md](demo/DEMO_GUIDE.md). With the backend running, `python demo/check_demo.py --mode offline --format csv` (or `--format xlsx`) checks the actual upload-to-report workflow against independent synthetic ground truth. `--mode agent` uses the selected cloud or local model. Add `--model ollama:gemma4:e4b` for local Gemma.

## Features

- CSV / XLSX / XLS upload, preview, type detection, date coverage, missing values, duplicates, and numeric summaries.
- Select cloud Gemini 3.5 Flash-Lite or local Gemma 4 through Ollama for each investigation. Local Gemma needs no Google API key.
- Bounded investigation loop with structured, Pydantic-validated tool actions and actual computed observations. No prewritten sales query sequence is used in AI mode.
- Chart screenshot interpretation with structured axes, categories, dates, visible patterns, schema matches, and ambiguity disclosure.
- Parser-restricted DuckDB SQL with resource limits and no external access.
- Descriptive statistics including sum, mean, median, sample standard deviation and min/max; exact modes with frequencies and tie disclosure; percentage changes, Pearson correlation, group comparisons and IQR outlier candidates.
- Expanded statistics library: **29 operations and 116 named functions**, covering Excel's statistical reference and ToolPak families, including hypothesis tests, ANOVA, multiple regression, distributions, confidence intervals, sampling, FFT and forecasting. Agent discovery and a direct calculation API are documented in [STATISTICAL_TOOLS.md](STATISTICAL_TOOLS.md), including Excel compatibility differences.
- Interactive Plotly line, bar, scatter, histogram, and correlation heatmap specifications from actual evidence.
- Public decision timeline, expandable SQL and evidence, exact-cell recomputation ledger, findings, limitations, follow-up suggestions, and PDF export.
- Explicit **Offline analytics** mode: deterministic rules execute real analytics without credentials. The question and image do not control this mode. It is never represented as an autonomous agent.
- Three reproducible synthetic demo datasets and independently computed expected retail results.

## Local setup (Windows PowerShell)

If dependencies are already installed, start both servers with one command from the project root:

```powershell
.\scripts\run_app.ps1
```

Open http://127.0.0.1:5173 and keep that terminal open. The launcher reuses healthy DataDetective services already running on ports 8000 and 5173, avoiding duplicate-server port errors. Ctrl+C stops only processes started by this launcher. Reused servers remain running; restart their original terminals to load backend code changes. If another application occupies either port, the launcher reports the conflict before starting either server. It does not install packages, start Ollama or download models. `-Check` verifies local prerequisites without starting services. Server logs are written to the ignored `runtime` directory.

After loading a dataset, the **Statistics workbench** provides calculations without any AI key or downloaded model. Choose an analysis and the required columns, then Calculate. It exposes the installed operation/function catalog; advanced methods and Excel functions accept named JSON parameters with visible schemas. Supplied-parameter calculations and simulations are labeled separately from uploaded-data observations. Export result downloads the calculation as JSON; these manual results are separate from the AI investigation report.

Requirements: Python **3.13** (tested), Node **22.6+** (Node 25 tested; frontend tests use built-in TypeScript stripping), npm, and an optional Gemini API key. No database server is needed. Execute from the project root.

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
cd frontend
npm run dev
```

Open [the workspace](http://127.0.0.1:5173) and [interactive API documentation](http://127.0.0.1:8000/docs). Vite proxies `/api` to FastAPI. The app works without a Gemini key using local Gemma or Offline analytics.

On macOS/Linux, use `python3`, `.venv/bin/python`, and your checkout path in place of the Windows equivalents.

## Cloud Gemini configuration

Create a key in [Google AI Studio](https://aistudio.google.com/apikey). Copy `.env.example` to `.env` if you do not already have one, then set `GEMINI_API_KEY`. `GEMINI_MODEL=gemini-3.5-flash-lite` remains the cloud default. Restart FastAPI, click **Reconnect**, select **Autonomous AI agent**, then choose Gemini in **AI model**.

Keys stay on the backend and `.env` is ignored by Git. Do not put credentials in `VITE_` variables. Gemini receives the question, dataset context, bounded tool results, and any attached image.

The official `google-genai` SDK uses `response_json_schema`. Strict object constraints are preserved; array-length caps are omitted from the transmitted schema to avoid Gemini's nested-schema complexity limit, while Pydantic enforces the full schema locally. See [Google structured outputs](https://ai.google.dev/gemini-api/docs/generate-content/structured-output).

## Local Gemma configuration

Install [Ollama for Windows](https://ollama.com/download/windows), then run from the project root:

```powershell
.\scripts\start_local_gemma.ps1 -Pull
```

The script also supports a portable Ollama executable at `runtime/ollama/ollama.exe`. For that installation it keeps models in the ignored `runtime/models` directory. It starts a hidden local service when needed, binds to loopback, disables Ollama cloud features for the child process, and downloads `gemma4:e4b`. An already running Ollama service is reused. Downloading the runtime/model requires internet; investigation requests use the local service.

Settings in the root `.env` (defaults shown):

```dotenv
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma4:e4b
OLLAMA_CONTEXT_LENGTH=8192
OLLAMA_TIMEOUT_SECONDS=180
```

Restart FastAPI and click **Reconnect**. Choose **Autonomous AI agent → Gemma 4 · Local (Ollama)**. The backend checks that Ollama is running and the configured model is downloaded. No Google API key is required. Questions, images, analytical actions, and report generation use local Ollama. Hosted Gemma has been removed; there is no cloud fallback. Only loopback Ollama addresses and local `gemma4:` tags are accepted. Redirects and environment HTTP proxies are disabled for model requests.

The default E4B download is about 6.6 GB. Model memory also includes context and image processing. On smaller machines, try `gemma4:e2b`: set `OLLAMA_MODEL` in `.env`, run `ollama pull gemma4:e2b`, and restart FastAPI. When using the PowerShell launcher with a different model, also set `$env:OLLAMA_MODEL='gemma4:e2b'` before `-Pull`. Larger contexts increase memory use; overlarge prompts and truncated responses fail explicitly. Local model quality and speed depend on the model and hardware.

Local E4B is experimental for complex investigations. A live regional example completed with image-guided SQL, a chart, a recomputed total, and an explicitly labeled computed report after the model omitted valid measurements. The full monthly retail comparison returned partial results because the model repeatedly generated incorrect date-format SQL. Gemini remains the validated default for that demo. Do not assume equivalent analytical quality when switching models.

Both providers return actions and reports through strict Pydantic validation and use the same guarded SQL, statistics, chart, and evidence verification tools. The selected model is fixed in investigation state and appears in reports and PDF exports. Ollama receives JSON Schema through `/api/chat` with streaming and thinking disabled; images are sent as base64. See [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs) and [vision](https://docs.ollama.com/capabilities/vision).

Local actions use a separate required-argument schema for each tool. Statistics requires an explicit `operation` and its column/input fields; SQL requires a nonempty `sql` argument. `summary` includes sum, mean, median, sample standard deviation, min/max and count. Use `mode` for modal values and frequencies: tied values are returned as rows, and the scalar mode is null when no unique mode exists. Missing values and numeric infinities are excluded; mode values are compared exactly without rounding. Chart and verification evidence IDs are restricted to eligible retained results. Local planner observations show at most five rows per result to leave room for these contracts; full retained evidence remains available in the UI.

SQL functions are restricted to approved calculations, alongside the single-dataset table restrictions and DuckDB's disabled external access. This limits the capabilities of generated SQL; it does not prescribe the analytical queries. `MODE(column ORDER BY column)` is supported and selects one modal value deterministically when tied. The statistics `mode` operation returns all tied modes, capped at 200 with truncation disclosed.

To request SQL explicitly, ask: **Use execute_sql to summarize trip_distance and total_amount, then run a second SQL query to inspect the largest total_amount values. Generate a chart and verify a computed value.** Substitute your actual column names. The model chooses the queries and DuckDB executes them under the existing read-only restrictions. After updating backend code, restart FastAPI, re-upload your dataset, and start a new investigation.

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

Default budget: eight model-selected steps (configurable 2–12), plus initial vision, profile, final report, and at most two transparent artifact-finalization calls. Finish requires at least two distinct successful dataset analytical actions, a chart and a numerical verification when numeric SQL evidence exists. If the model omits artifacts, system finalization can chart and recompute existing evidence; those events are explicitly labeled and never introduce a fixed analytical query sequence. Resource-limited work is returned as `partial`, not complete. Each Gemini request attempt has a 50-second outer timeout; local Ollama requests default to 180 seconds, including model loading. Temporary rate limits with a provider-supplied retry delay allow at most two pauses of up to 60 seconds, shown in the timeline; long quota delays and non-retryable errors fail without those retries. Two model failures stop the loop, and three tool failures end exploration. Only two investigations run concurrently and four may be active/queued. No analytical success means a failed investigation, never invented results. If report generation fails or supplies no valid numerical measurements after valid analytics, a computed summary is used.

SQL evidence has at most 200 rows. Planner context bounds cell text, rows, and total prompt size; truncation is disclosed. Full retained evidence is inspectable in the UI. Charts use the retained tool result rather than regenerated model data.

While an investigation is queued or running, **Stop investigation** replaces the start button. Stopping cancels the backend job and prevents further analytical/model steps. Completed evidence remains visible; when analytical results exist, a computed partial report can be exported without another model request. Stopping before any analysis returns `cancelled` with no invented report. An already-finished investigation is left intact. An in-flight provider request may still be processed or billed, and a calculation already running in a worker thread may finish under its existing limits.

**Export PDF** downloads a paginated report with exact measurements, static charts, source references, the verification ledger, limitations and execution notices. Export runs locally without another AI request. Evidence previews are capped at 4,000 characters per result and 40,000 overall, with omissions disclosed; dataset preview rows and duplicated chart arrays are excluded from the appendix. Full retained evidence remains in the workspace. Historical Markdown examples remain in `demo`, but new exports and the demo preflight produce PDF.

**Verification scope:** model reports provide typed measurements (`evidence_id`, `row`, `field`, `value`). The server resolves every displayed report number against an actual SQL/statistical cell, attaches source-row labels, and rejects mismatched values. Digits in model numerical prose are withheld in favor of computed measurements. Numeric-free prose is still interpretation and may be wrong. Values supplied by the model to the percentage-change helper cannot become dataset-backed findings. Numerical verification re-executes source SQL and matches the result row by its other fields, rather than assuming stable row order. Ambiguous matches remain inconclusive. The ledger stores SQL, source ID, cell, expected/actual values, and status. This verifies consistency of that cell only. Segment contributions are not proven causes, and SQL metric definitions still need review.

## Multimodal behavior

PNG/JPEG files are decoded, size-checked, metadata-stripped, and resized on the backend. The selected model returns typed chart information and compares labels with real schema columns. Unknown schema matches are removed and disclosed. Ambiguities remain visible. The planner receives this context before selecting analytical tools. Visual estimates are explicitly unverified and cannot enter the numeric verification ledger without an actual SQL result. Offline mode stores the image but explicitly skips interpretation.

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
    vision.py                  Validated uploads and cloud/local chart interpretation
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
  retail_sales.xlsx            Same full dataset in Excel format
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
| `GET /api/health` | Health, default model, available model choices, AI configuration state |
| `POST /api/datasets` | Multipart `file`; returns dataset ID, profile and preview |
| `GET /api/demo/{name}` | Load `retail_sales`, `sensor_data`, or `student_performance` |
| `POST /api/images` | Multipart `file`; returns image ID; interpretation happens during investigation |
| `POST /api/investigations` | JSON `dataset_id`, `question`, optional `image_id`, optional `model` (ID from `/api/health`), `mode` (`agent` / `offline`); returns 202 and state |
| `GET /api/investigations/{id}` | Poll status, plan, timeline, evidence, findings, charts, report and errors |
| `POST /api/investigations/{id}/cancel` | Stop queued/running work, retain completed evidence, and return the final cancellation/partial state; safe to repeat |
| `GET /api/investigations/{id}/report` | Download a PDF report with static charts, verification ledger and evidence appendix |

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
npm test
npm run build
```

Tests cover CSV/Excel ingestion, malformed files, inferred types, missing values, SQL attack rejection, aggregates, row bounds, percentage changes, chart values, recomputation status, evidence references, report export, tool/model failures, adaptive follow-up selection with a mocked model, and full offline API investigations across retail, sensors, and students. The controlled-model test validates orchestration; it is not a live Gemini test. See `VALIDATION.md` for the actual execution results from this build.

## Reliability, security and limitations

- Local, single-process hackathon prototype, not a public multi-tenant service. No authentication. Bind to loopback. Session IDs are random but are not an authentication mechanism.
- In-memory storage, no uploaded file paths. Raw filenames are reduced to a display basename. Inactive sessions expire after two hours; active jobs pin their dataset and image references, and shutdown cancels queued/running work. Limits: 12 datasets, 20 images, 40 investigations, 15 MB data uploads, 5 MB images, 150,000 rows, 100 columns. Request bodies are bounded before multipart parsing/spooling, and at most two uploads are processed concurrently. XLSX expanded content is limited to 60 MB. Workbook parsing uses the first worksheet. Duplicate or blank headers, ragged CSV records, and infinite numeric inputs are rejected explicitly.
- SQL parsing uses `sqlglot` plus an explicit function and table allowlist, one SELECT referencing the uploaded dataset, no recursion or dataset-shadowing CTEs, at most eight table references, and no external table functions. Each execution uses an isolated DuckDB connection, 256 MB engine memory, two threads, a four-second watchdog covering setup and execution, no extension auto-install/load, external access disabled, an empty spill directory and locked configuration. These limits are defense in depth, not an OS sandbox for hostile public use. Query interruption is tested against real expensive computation.
- Data and image text are untrusted and explicitly separated from system instructions. No arbitrary Python, shell commands, executable JavaScript chart specs, or model-generated HTML is executed. React escapes text.
- Only actual numeric SQL cells can get a verified status. Rerunning a query verifies consistency, not correctness of metric definitions, data truth, causality, or every word of a claim. Model narrative can still be wrong; inspect sources.
- Date inference recognizes ISO date strings. Ambiguous locale formats stay categorical. Missing values are not silently imputed. Correlation is descriptive and includes assumptions. IQR flags need human interpretation.
- No live Gemini/vision validation is possible without a configured key. Invalid keys, quota limits, model changes and network issues are surfaced with bounded failures. No silent switch from AI mode to offline mode.
- Plotly is lazy-loaded because its full interactive distribution is large. Vite can warn about its chunk size; this is expected.
- No durable history, multiple-table joins, auth, background scheduler, voice input, database connectors, or production hosting is implemented.

## Build and deployment

`npm run build` produces `frontend/dist`. For a local production-preview check use `npm run preview -- --port 5173`; Vite inherits the development `/api` proxy. For deployment, run one Uvicorn worker (sessions are process-local) behind a reverse proxy forwarding `/api`, serve the static frontend, set `GEMINI_API_KEY` only on the backend, and restrict origins. TLS, authentication, rate limiting, process isolation, durable sessions, and privacy controls are required before public hosting. This implementation is delivered locally and is not published to Sites hosting because its requested Python runtime does not run in a static site or Cloudflare Worker.

## Track fit and future work

This is an applied agent with a bounded **plan → execute → observe → re-plan → verify → report** cycle. Its differentiator is observation-dependent tool selection rather than a fixed chatbot response or dashboard query sequence. Structured chart understanding supplies additional context while exact analytical values come from computation. The offline mode is deliberately separate and is not evidence of agentic capability.

Future work: persistent investigation history, multiple datasets and joins, additional data sources, PDF/voice inputs, stronger statistical tests with validated assumptions, human-reviewed metric definitions, saved investigations, scheduled analyses, and production access control.
