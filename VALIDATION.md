# Validation record

## PDF report export — 2026-10-31

- Replaced the Markdown download with a PDF response and Export PDF control. Reports use validated findings, exact measurements and source labels, static retained-data charts, the verification ledger, limitations, execution notices and a bounded evidence appendix. Export requires no model call. The demo preflight now saves PDF; historical Markdown samples remain unchanged.
- Added pinned ReportLab and pypdf dependencies and installed them in the local environment. Exports run in a worker thread with bounded admission; text is escaped, fonts are embedded, long tables paginate with repeated headers and shortened evidence previews are disclosed. Tests cover all five chart types, Unicode/currency, literal markup, tiny values, long content, download MIME/filename, capacity, missing/not-ready sessions and cancelled-report export.
- Full backend suite: **317 passed** with third-party Starlette/Matplotlib deprecation warnings; **22 frontend tests passed**; TypeScript and production build passed with the existing Plotly chunk warning. Dependency consistency passed. Final pagination refinements passed the **five PDF-specific tests** again.
- Generated a synthetic retail offline report and visually inspected all rendered pages for layout, chart legibility, section breaks and footer numbering. No live AI calls or user datasets were used.

## User-controlled investigation cancellation — 2026-10-31

- Added an idempotent cancellation API and a Stop investigation button for queued/running work. Cancellation stops future steps, retains completed evidence and generates a computed partial report when analytical results exist, with no additional model request. Pre-analysis cancellation has no fabricated report. Already-finished outcomes remain intact.
- Job cleanup handles cancellation before the coroutine starts, releases capacity and preserves existing shutdown behavior. Interrupted timeline events stop showing as running. Frontend progress updates cannot revive a cancelled run or restore an investigation after reset/replacement.
- Full backend suite: **312 passed**, one existing Starlette TestClient deprecation warning, **14.86 seconds**. Frontend suite: **22 passed**. TypeScript and production build passed with the existing Plotly chunk-size warning. Coverage includes running and pre-start cancellation, real computed measurements and Markdown export, repeated cancellation, finished-job races, registry cleanup, controlled API errors and stale polling responses. No live AI calls or model downloads were used.
- Cancellation cannot undo an already-submitted provider request or forcibly terminate a calculation already executing in a worker thread; existing tool limits still apply.

## Partial-result recovery guidance — 2026-10-31

- Replaced the generic resource-limit banner with the actual stop reason and a suggested next step for repeated actions, step exhaustion, tool failures, model unavailability, and interruption. Partial results remain explicitly incomplete; missing or unknown reasons receive generic guidance. Active, successful and failed investigations do not receive this partial-result notice.
- Frontend regression suite: **18 passed**. TypeScript and Vite production build passed; the existing lazy Plotly chunk-size warning remains. No new packages, model downloads or live AI calls were needed. Backend behavior is unchanged.

## Repeated analytical action guard — 2026-10-31

- Identical successful SQL/statistics requests reuse their existing evidence instead of executing again. Skips are visible in the timeline and sent back to the planner with the evidence ID. Failed actions remain retryable; SQL text is matched exactly so differences inside string literals remain meaningful.
- Two duplicate requests stop exploration with `partial / repeated_action_limit`, preserving evidence and report generation. The existing model-call budget remains unchanged; no additional AI calls are introduced.
- Full backend regression suite: **304 passed**, one existing Starlette TestClient deprecation warning, **35.30 seconds**. Six new cases cover cloud/local planner recovery, early stopping, retries after failure, exact SQL literals, parameter key ordering, and retained SQL verification. Planner responses are controlled; no live AI quality claim is made.

## No-download completion pass — 2026-10-31

- Stopped the in-progress Gemma pull and the Ollama service at the user's request. No subsequent package or model downloads were started. The portable runtime is present, but the model download remains partial and is not reported as installed. Partial files are preserved in the ignored runtime directory.
- Corrected the shared DataFrame serialization path: Pandas' default JSON precision converted a genuine `1e-12` to zero and shortened ordinary floats. Dataset previews, SQL/group result rows and profile summaries now preserve native scalar precision through JSON encoding, including nullable, nested and temporal values. Regression tests cover SQL, profiler and actual multipart HTTP responses.
- Added a statistics workbench using the existing catalog and calculation endpoints. It exposes all installed operations/functions, shows required columns and parameter schemas, validates request options, displays computed scalar/table results and exports JSON. Literal calculations and simulations carry separate provenance labels and do not become AI report evidence.
- Added `scripts/run_app.ps1`, a no-download two-server launcher with prerequisite checks, hidden child processes, startup readiness checks, local logs and cleanup on Ctrl+C. `-Check` passed, and the actual launcher started both servers successfully.
- Backend suite: **298 passed**, one existing Starlette deprecation warning, **32.99 seconds**. Frontend request/form/provenance regression suite: **12 passed**. Production build passed; the existing lazy Plotly size warning remains.
- Browser checks passed for retail summary and Excel SUM. Revenue summary showed the actual total **2,434,538.31** and Excel SUM of Quantity showed **13,177**. No browser console errors were observed. No live AI call was made in this pass.
- The full CSV offline HTTP preflight still completed with four SQL results, two charts, a recomputed numeric cell and Markdown export against the independent expected results.

## Excel statistical coverage expansion — 2026-10-31

- Expanded the original six-operation dispatcher to **29 operations**, with **116 named worksheet functions** and **36 legacy-name aliases**. An explicit coverage fixture includes all **111 entries** from Microsoft's statistical-function reference; the additional functions are SUM, SUMSQ, PRODUCT, SUMIF and SUMIFS. The nineteen ToolPak analyses are covered through named operations and ANOVA/t-test variants. This is an uploaded-data statistical API, not a workbook formula interpreter or a claim of bit-identical Excel behavior. See [STATISTICAL_TOOLS.md](STATISTICAL_TOOLS.md) for coverage, arguments and compatibility differences.
- Added descriptive moments and quantiles, covariance/correlation matrices, confidence intervals, paired/pooled/Welch/one-sample tests, known-variance z tests, variance F tests, chi-square tests, balanced one/two-factor ANOVA, multiple linear/log-linear regression, normality diagnostics, probability distributions and inverses, conditional aggregation, moving averages, exponential smoothing, additive ETS forecasting, FFT/inverse FFT, reproducible sampling and seven random-generation families. Calculations use NumPy/SciPy/statsmodels; statsmodels and patsy are pinned in the dependency lock.
- Added agent `statistics_catalog` discovery with strict execution-time parameter validation and operation-specific local decoding schemas. Planner context retains completed action inputs and the complete operation menu. New API endpoints: `GET /api/statistics/catalog` and `POST /api/datasets/{id}/statistics`, usable without a model key. Invalid requests return controlled errors, the calculator has a concurrency bound, and existing HTTP body/session bounds remain enforced.
- Statistical tables and coefficient rows now appear in computed report fallbacks. Reports reject simulations and literal-only calculations as dataset findings. Matrix heatmaps display computed correlation/covariance cells directly, including two-variable matrices and columns whose names collide with row-label fields. The SQL allowlist now also accepts a narrow set of pure arithmetic functions including SQRT, POWER, LN and EXP; file/network/table and execution-resource restrictions remain enforced.
- Final backend suite: **295 passed**, one existing third-party Starlette deprecation warning, **14.98 seconds**. This includes **150 additional tests/cases**, numerical fixtures for every named function, hand-calculated inference/ANOVA examples, regression and rank-deficiency checks, percentile boundaries, matrix charts, complete-case behavior, FFT/smoothing/forecasting, seeded simulation, catalog/schema/API integration, provenance, row bounds, undefined/overflow cases, wildcard escaping and rejection of high-cardinality contingency tables before allocation. The reference coverage test checks names; the numerical fixtures check representative cases, not every possible Excel edge case.
- Frontend regression tests: **8 passed**. Python syntax check passed; `pip check` reported no broken requirements; `git diff --check` passed. No frontend changes were required for this expansion, and no fresh browser or production-bundle validation is claimed for it.
- **Live Gemini advanced workflow passed** on a small synthetic paired dataset: catalog discovery, paired t-test, mean confidence interval and a model-generated evidence-backed report; `completed / sufficient_evidence`, **9.90 seconds**, no errors. The displayed p-value was **0.0005084511309471966**, with interval bounds **12.373641654059922** and **18.876358345940076**. Earlier trials exposed unrelated chart attempts and a missing SQL SQRT permission; the final guidance and arithmetic support corrected those integration gaps.
- **Live local Gemma descriptive regression passed** with the previously validated six-statistics question on **8,000 synthetic rows**: summary, mode, model-generated report, `completed / sufficient_evidence`, **8.55 seconds**, no errors. All six displayed values matched independent calculations. Google client construction was prohibited and its key removed for this run.
- **Local Gemma advanced planning remains unreliable.** It discovered and executed the real paired t-test correctly, but subsequent repeated calls and same-column pair attempts exhausted the tool-failure limit and omitted the confidence interval. The final advanced trial was partial in **14.87 seconds**. No successful complete local advanced-statistics investigation is claimed. The calculation API works independently of this model behavior, and Gemini completed the tested advanced workflow.
- ETS uses additive Holt-Winters fitting, a spectral automatic-seasonality heuristic and centered fixed-seed bootstrap intervals. These can differ from Excel. Statistical assumptions, null/undefined values, input ordering, complete-case rules, output bounds and worksheet coercion/signature differences are documented. Independent numerical recomputation remains available for SQL cells; advanced statistics are labeled computed rather than independently verified.
- The development FastAPI server must be restarted to load the new catalog and routes. Local Ollama was started with the existing cloud-disabled helper for validation and left available. No existing frontend/backend server was stopped or restarted, and the user's actual train.csv was not analyzed.

## Sum and mode completion — 2026-10-31

- Confirmed the screenshot's capability gap: `summary` originally returned mean, median, sample standard deviation and min/max but omitted sum and mode. There was no standalone mode operation, and the SQL function allowlist omitted `MODE`. Repeating a successful summary could not provide the missing calculations and exhausted the model's step budget.
- Added sum to numeric summaries with finite-value handling and integer accumulation that avoids int64 wraparound. Added a validated `mode` operation for numeric/categorical values, including frequencies, all ties, an explicit lack of a unique mode, and bounded/truncation-disclosed results. Modal values are not rounded before frequency counting. Standard deviation remains the sample statistic and is now labeled explicitly.
- Added only the `MODE` aggregate to the SQL function allowlist; existing single-dataset, read-only, external-access, function and resource restrictions remain enforced. Verified deterministic tie handling with `MODE(value ORDER BY value)`. Updated prompts to request one summary plus one mode call rather than repeating summaries, and preserved tied modal values in computed fallback reports through actual row references.
- Final backend suite: **145 passed**, one existing Starlette deprecation warning, **15.05 seconds**. New tests cover the requested summary fields, unique/tied/all-unique modes, categorical/mixed values, tiny numeric values, missing/nonfinite values, truncation, integer sum overflow, SQL mode, and report evidence for ties.
- **Live local Gemma check passed** on **8,000 synthetic rows** using the same six-statistics request: one summary call, one mode call, then `completed / sufficient_evidence` in **21.15 seconds**, with no errors or repeated statistics calls. A **model-generated report** displayed all six requested metrics, individually checked against independent calculations: sum **224,000**, mode **20**, mean **28**, sample standard deviation **14.697857101476458**, minimum **10**, maximum **50**. The Google key was removed and Google client construction was prohibited. These are synthetic test values; the user's actual `train.csv` was not available or analyzed.
- Restart the development FastAPI server to load these changes, re-upload the dataset, and start a new investigation. Existing timeline errors are historical.

## Gemma tool-argument repair and real SQL verification — 2026-10-31

- Reproduced the reported `Unsupported statistical operation` failure: the shared action schema allowed `calculate_statistics` with a missing/null `operation`, and the tool received `None`. This was an integration gap. No unsupported-operation alias or guessed default operation was added.
- Local constrained decoding now uses tool-specific argument variants. Statistics requires a supported operation plus the fields required for that operation; SQL requires a nonempty query. Server-side validation runs before dispatch for all providers and returns specific correction feedback for incomplete calls. Gemini's transmitted schema remains unchanged.
- Restricted local chart evidence IDs to successful SQL/statistics results containing rows, and verification IDs to numeric SQL results. This addresses a live repeat that attempted to chart a scalar correlation record. Local planner row samples are capped at five, with omitted counts, to leave room for the stricter schema. Full retained results are unchanged.
- Final backend suite: **132 passed**, one existing Starlette deprecation warning, **14.52 seconds**. New regressions cover missing/null operations, operation-specific fields, empty SQL, zero-valued verification arguments, failure feedback, wide-result prompt bounds, and eligible chart/verification IDs.
- **Live final anomaly case passed** on synthetic taxi columns `trip_distance` and `total_amount`: `completed / sufficient_evidence` in **13.08 seconds**, with no tool errors. Gemma requested valid summaries, IQR outlier operations, and a correlation. Each column had exactly one IQR candidate, matching independent expectations. The final report was model generated. No claim is made about the user's actual taxi file, which was not inspected.
- **Live final SQL case passed** in **13.58 seconds**: two model-selected real DuckDB queries (count/average/min/max, then largest fares), one bar chart, one recomputed cell, and `completed / sufficient_evidence`. Independent checks matched count **10**, average distance **14.5**, average amount **71.6**, and maximum amount **500**. The report used the explicitly labeled computed fallback after the model omitted valid numeric measurements.
- Both live checks ran against the actual local `gemma4:e4b` service with the Google key removed and Google client construction explicitly prohibited. A prior live SQL check also completed with matching results. Complex-query and report-quality limitations remain; this fix does not guarantee arbitrary model-written SQL is correct.
- The running development backend must be restarted to load this code. Re-upload the dataset after restart and start a new investigation; old timeline errors remain historical records.

## Local Gemma replacement — 2026-10-31

- Removed hosted Gemma from the model registry and cloud default overrides, and removed its Google native-call adapter. Cloud Gemini and deterministic Offline analytics remain available. Local model IDs are namespaced as `ollama:gemma4:e4b`.
- Added local Ollama JSON Schema requests, image bytes through base64, bounded requests, strict output validation, client cleanup, provider-specific readiness, and actionable missing-model errors. The transport accepts only loopback URLs and local Gemma tags, disables redirects/environment proxies, and never falls back to Google.
- Downloaded the official portable Ollama **0.40.13** release into ignored `runtime/ollama`, verified its published SHA256, and pulled **gemma4:e4b** into ignored `runtime/models`. The local service listens on `127.0.0.1:11434`, with cloud disabled and one parallel inference slot through process-local environment settings. No system installation or global environment changes were made. Logs confirmed all **43/43** main model layers offloaded to the RTX 4060 Laptop GPU (8 GB).
- Final backend regression suite: **116 passed**, one existing Starlette deprecation warning, **14.44 seconds**. Mocked local end-to-end cases explicitly prohibit constructing a Google client and run without a Google key; they cover vision, two observation-dependent SQL queries, charts, verification, model reports, and export. Unit tests cover unavailable models, removed hosted choices, nonlocal/cloud rejection, malformed or truncated output, HTTP errors, timeout, and prompt bounds.
- Frontend: **8 tests passed**, TypeScript passed, in-memory production build passed (**1,602 modules**, **17.79 seconds**). Browser verified local selection with no configured Google key, setup guidance before model download, readiness after Reconnect, enabled Start, correct privacy text, and no browser console errors. Only cloud Gemini and local Gemma appeared in the selector.
- **Live local regional investigation completed twice**, in **13.04** and **13.03 seconds** after model warmup: actual CSV/PNG HTTP uploads, image interpretation identifying highlighted West, two model-selected real SQL queries (region totals, then West product totals), one model-selected chart and one recomputed total. Region totals were North **100**, East **70**, West **30**; West product totals were B **20**, A **10**. All requests used local Ollama; the isolated backend had its Google key disabled. Both reached `completed / sufficient_evidence`. The repeat explicitly checked the expected totals and West drill-down. Reusable inputs are `demo/gemma_regions.csv` and `demo/gemma_regions.png`.
- **Live reporting limitation:** that completed example returned a computed evidence-summary report because the model draft supplied no usable numeric measurements. This fallback is explicitly labeled and keeps the actual evidence and verified cell. A fully model-written local report was not demonstrated successfully.
- **Live complex retail limitation:** three local image-plus-retail attempts returned partial results. Image interpretation worked, but generated monthly SQL used invalid syntax or doubled date-format percent signs and returned empty results. Generic DuckDB syntax guidance did not resolve this reliably. No successful local full retail demo or independent retail ground-truth match is claimed. The validated cloud Gemini demo remains the default.
- Fixed an observed malformed-SQL handling gap: unterminated quoted strings now produce a controlled validation error, rather than a generic tool failure. Existing SQL restrictions remain enforced.
- Added `scripts/start_local_gemma.ps1` for repeatable local startup/pull and updated configuration, setup and demo instructions. Temporary validation servers use isolated ports 8001/5174; the existing development backend must be restarted to load this code.

## Hosted Gemma option — historical, replaced by local support

- Added a per-investigation model selector: **Gemini 3.5 Flash-Lite** (existing default) and **Gemma 4 · 26B A4B (experimental)**. Both use the existing backend Google API key; the local default and credentials were not changed.
- `/api/health` exposes model choices. Requests may select a model explicitly; unknown choices are rejected before creating a job. The resolved model is fixed in investigation state, used for every model request, and included in reports and Markdown exports. Offline investigations have no AI model.
- Gemma uses native function calls for analytical actions and structured vision/report results, converted through the same strict Pydantic validation and guarded analytical tools. Failed tool inputs are returned to the planner so it can correct its actual previous SQL.
- Final backend suite: **98 passed**, one existing Starlette deprecation warning, **19.53 seconds**. Tests cover model selection/default snapshots, unknown-model rejection, both model routes through the installed SDK and API, native-call validation, report/image routing, and exports. Provider responses in these regression tests are mocked.
- Frontend: **8 tests passed**, TypeScript check passed, production bundle passed (1,602 modules; generated in memory). Browser verified the Gemma selection, persistence after Reconnect, offline hiding/restoring of the picker, and sample loading. No browser console errors were recorded. The selector screenshot was saved outside the repository as a chat artifact.
- **Live Gemma validation remains partial.** The initial JSON action path produced unreliable SQL, so Gemma was adapted to native calls. A later retail run executed two real SQL queries, generated a chart, recomputed one numeric cell, and returned a model-written report, but stopped at the tool-failure limit. January/February totals and percentage matched the demo ground truth; the signed difference did not. Its image request timed out. Other runs produced SQL errors or provider failures, including a failed basic regional example. No complete, reliable live Gemma demo is claimed.
- The 31B variant returned provider errors during compatibility checks and was not added to the menu. The selectable 26B variant is explicitly experimental; Gemini remains the validated default for the full retail demo.
- Browser/API checks used isolated ports 5174/8001 because the existing development servers were already running. The existing backend had not loaded the new model list; restart it to expose the option in the usual workspace.

## Gemini integration fix — 2026-10-31

- Backend regression suite: **84 passed**, one existing third-party Starlette deprecation warning, 13.43 seconds on the final run. Bytecode and pytest file caches were disabled. Async tests ran outside the restricted sandbox.
- Planner, report, and vision requests use `response_json_schema`, preserving strict object constraints. Transmitted schemas omit array-length caps to avoid Gemini's nested-schema state limit; Pydantic still rejects unexpected fields and oversized reports locally.
- Tests cover actual SDK request serialization, report/vision/action validation, bounded provider-directed quota retries, cancellation during backoff, report timeline completion after a retry, and ordinary SQL `AND`/`OR` filters without relaxing the analytical function/table restrictions.
- **Live HTTP workflow passed** using the local `.env` configuration with `gemini-3.5-flash-lite`: real synthetic CSV and PNG multipart uploads, actual Gemini image interpretation, four model-selected SQL queries, a chart, one recomputed cell, and a **model-generated** report. Status was `completed` / `sufficient_evidence`, with no execution errors, in **17.08 seconds**. Markdown report download returned HTTP 200. The temporary server was stopped afterward.
- Independent ground-truth checks passed for January **633,633.45**, February **528,492.33**, difference **−105,141.12**, and percentage change **−16.5933664013%**. The model selected West for a category drill-down after observing the regional result; the returned West and Electronics differences matched the expected dataset values.
- Model availability was checked rather than assumed: `gemini-flash-latest` returned provider deadline errors; `gemini-2.5-flash` executed live analytics but reached its free-tier daily quota; `gemini-2.5-flash-lite` returned a retirement error recommending `gemini-3.5-flash-lite`. The replacement model successfully completed the full workflow. Only the model setting was updated in the ignored local `.env`; the API key was preserved.
- The separate small-value numerical serialization issue identified during the read-only audit remains outside this Gemini fix. This validation establishes the retail demo's tested values, not arbitrary floating-point precision.

The records below describe earlier validation runs and their configuration at that time.

## Takeover validation — current checkout

Validated on 2026-10-31, Asia/Calcutta. The prior initial-build record is retained below as history.

| Check | Actual result |
| --- | --- |
| Backend regression suite | **71 passed**, one third-party Starlette deprecation warning, 10.95 seconds |
| Frontend `npm test` | **8 passed** using Node's built-in runner; request failures, cancellation, timeouts, multipart contents, file checks and tiny-number formatting |
| Frontend `npm run build` | TypeScript and Vite passed; 1,601 modules; lazy Plotly chunk size warning remains |
| Python compilation / dependency check | Passed; no broken requirements |
| Full multimodal adaptive SDK/API integration | Real XLSX + PNG uploads, actual analytical execution, chart and verification; mocked SDK transport; both flipped-region cases passed |
| SQL timeout | An actual expensive cross-join aggregation was interrupted by the watchdog; regression passed |
| Shutdown cancellation | Server lifespan cancelled a running job and left a failed/cancelled state, not a stuck job |
| Local CSV + image preflight | Completed through HTTP with four SQL queries, two charts, one recomputed cell, independent expected-result checks and Markdown export |
| Local full XLSX + image preflight | Same complete workflow and expected values as CSV |
| Browser sample workflow | Loaded retail, ran offline analytics, saw charts, measured cells with labels, verification and report; source links opened their SQL details; console had no errors |
| Browser responsive check | Mobile navigation visible; page scroll width and client width both 375 CSS px at a 390 × 844 outer viewport; override reset |
| New screenshots | `demo/takeover-dashboard.jpg`, `demo/takeover-results.jpg` |
| Browser file-picker automation | Attempt failed in the browser tool; do not count it as a successful current upload smoke test. Real multipart upload paths passed API tests and local HTTP preflights |
| Live Gemini model and vision | **Not run** — no key in environment or root `.env`; no live AI success is claimed |

The restricted Windows sandbox hangs during asyncio's local socketpair creation before app code executes. Reviewed local test/server runs outside that restriction completed; the suite uses synthetic data and mocked Gemini transport. No OS security settings were changed. See AUDIT.md for concrete findings and fixes, and demo/DEMO_GUIDE.md for the presentation/preflight workflow.

## Initial implementation record (historical)

Completed locally on 2026-10-31 (user timezone: Asia/Calcutta).

| Check | Actual result |
| --- | --- |
| `python -m pytest backend/tests -q` | **36 passed**, one third-party Starlette deprecation warning, 4.81 seconds on final full run |
| `python -m compileall -q backend demo` | Passed, exit 0 |
| `python -m pip check` | No broken requirements found |
| `npm run build` | Passed TypeScript checking and Vite production build; 1,597 modules, 12.87 seconds on final run |
| `python demo/generate.py` | Generated 5,292 retail, 2,400 sensor, and 900 student rows, Excel sample, chart image and independently computed expected findings |
| FastAPI startup | Uvicorn started on `127.0.0.1:8000`; health request returned 200 |
| Vite startup | Started on `127.0.0.1:5173`; HTTP request returned 200 |
| Browser sample workflow | Loaded retail sample, displayed profile and preview, uploaded the generated PNG through the file picker, started offline analytics, and observed completion |
| Browser results | Two interactive Plotly charts rendered, 10 evidence records, one independently recomputed numeric cell, findings, explicit offline image skip, and report appeared |
| Browser report export | Downloaded Markdown via the export control; a copy is `demo/example_report.md` |
| Responsive browser check | 390 × 844 viewport override tested; actual document client width and scroll width both 375 CSS px (scrollbar included in the outer viewport); charts stacked and dataset table scrolled internally. Viewport restored afterward |
| Screenshot | Actual rendered desktop results saved to `demo/dashboard.jpg` |
| Official Gemini SDK contract | Structured action and multimodal request/response serialization passed using `httpx.MockTransport`; unknown vision column match discarded and disclosed |
| Live Gemini reasoning / vision | **Not executed**: no Gemini API key was configured. Mocked responses test orchestration and SDK compatibility, not live model quality or API access |

The API end-to-end test uses a real multipart CSV upload, a real image upload, background investigation state transitions, DuckDB queries, charts, exact-cell verification, and report download. Cross-domain offline tests also run sensor and student investigations. The adaptive model test makes its second query depend on the first query's observed lowest region; no live-model result is implied.

SQL tests reject writes, multiple statements, external readers, glob/range table functions, system tables, extensions, attachments, environment access, and recursive queries. Analytical tests check real totals against independently generated ground truth, row bounds, percentage calculations, malformed inputs, and verification failure behavior.

Vite warns about the large lazy-loaded Plotly distribution (~4.85 MB raw / ~1.47 MB gzip). The initial app bundle is ~262 KB raw / ~80 KB gzip. The backend test warning concerns Starlette's upcoming TestClient transport change; the tests pass with the installed, dependency-consistent versions.

During setup, Windows Application Control rejected compiled modules from initially selected pandas 3.1.0 and Pydantic 2.14.2 wheels. Stable published dependency versions were selected and successfully imported, without changing OS protections. Exact installed versions are recorded in `backend/requirements-lock.txt`, and direct compiled dependency pins are in `backend/requirements.txt`.

The implementation is local-only. Temporary test servers are stopped after validation; start them with the README commands. No API key or `.env` was created, no remote site was published, and no live AI success is claimed.
