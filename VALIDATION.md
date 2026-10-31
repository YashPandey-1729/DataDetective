# Validation record

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
