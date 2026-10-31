# DataDetective takeover audit

Reviewed and improved in the existing checkout on 2026-10-31. The React/Vite frontend, FastAPI backend, official Gemini SDK, DuckDB tool layer, in-memory sessions, and synthetic dataset generator were retained.

## Existing functionality confirmed

- CSV/Excel profiling, chart image uploads, tool-dispatch agent loop, deterministic offline workflow, live polling timeline, Plotly charts, Markdown reports, demo data and tests already existed.
- The AI path was observation-dependent: each selected action executed an actual Python tool and returned the result to the next model request. The offline sales sequence was separate, not masquerading as an LLM agent.
- Existing source references and numeric recomputation were useful, but references alone did not establish whether the report's numbers matched them.

## Findings and corrections

| Issue | Correction |
| --- | --- |
| Invented numbers could cite an unrelated but real evidence ID | Typed report measurements resolve to exact SQL/statistics cells, carry source labels, and reject mismatches; model numerical prose is withheld rather than treated as verified |
| Model could finish after one analysis without charts/verification | Finish requirements enforce distinct analytical actions and appropriate artifacts; bounded early stops return `partial`; transparent system finalization can chart/recompute retained results without choosing analytical queries |
| Supplied percentage inputs could appear dataset-backed | Such results remain labeled supplied inputs and cannot satisfy dataset-analysis or numerical-report provenance checks |
| Context could contain megabytes of uploaded text | Planner context caps text, lists and overall payload, discloses omissions, and avoids repeating raw previews |
| Upload size checked after multipart spool | Raw request limits and concurrent-upload limits now run before multipart parsing; storage limits are rechecked after async loading |
| Duplicate/blank/case-colliding headers silently renamed by Pandas | Validate original CSV/Excel headers before loading; reject ragged CSV records instead of silent reindexing |
| Infinite inputs, overflow and undefined correlations | Reject infinite uploads; validate finite computations; keep undefined heatmap correlations null; validate chart inputs and row bounds |
| Numeric verification depended on query row order | Match result rows using their other fields; ambiguous matches stay inconclusive; tighter tolerance prevents tiny values being verified as zero |
| Small frontend values rounded to a misleading zero | Scientific formatting preserves small nonzero measurements |
| SQL resources and provenance | Watchdog covers setup and execution, spill disabled, query must reference the dataset, and CTEs cannot shadow it; external functions and writes remain blocked |
| Missing calendar months broke overall/segment reconciliation | Both comparisons use the same adjacent observed periods; no implied zero for absent months |
| Numeric-only data had no offline chart | Add a clearly labeled histogram from the retained first metric values |
| Active-job inputs could expire, shutdown left stale states | Pin active dataset/image references, retain an image object while queued, refresh investigation access and cancel jobs during server shutdown |
| Expired sessions or failed requests locked the UI | Typed API errors, abort/timeouts, recovery notices, and a reset path; reconnect clears stale connection state |
| Images persisted across dataset changes and leaked object URLs | Explicit image lifecycle cleanup and local extension/size checks |
| Evidence links only scrolled to collapsed sections | Links open the source details and focus their summary |
| Weak small-screen navigation and vision display | Mobile section navigation, structured vision cards, report notices and a chart error boundary preserve the existing design |
| Vision failure not sufficiently disclosed | Image trust rules are system instructions, schema matches checked, and reports explicitly state when no image context was available |

## Proof and limitations

`backend/tests/test_takeover.py` uploads real XLSX and PNG data through FastAPI and uses the installed Gemini SDK with a mocked HTTP transport. It runs actual DuckDB queries. The second query is chosen from the previous result; flipping the lowest-revenue region flips the follow-up. It also checks image context and the natural-language question reach the planner, chart creation, verification, and report export. This proves integration and orchestration under controlled model responses; it does not prove live Gemini reasoning quality.

The actual local offline preflight uploads the full retail CSV or XLSX and chart, performs four queries, checks the overall and regional/category contributions against independent Pandas answers, renders two chart specifications and exports a report. Expected answers are never sent to the agent.

No Gemini key is available. Live model/vision quality and the agent's choices on unseen data remain unverified. Numeric-free model interpretation, metric definitions in SQL, source-data truth, causal inference, and spelled-out numerical prose still require human review. Exact-cell validation and recomputation do not establish these semantics.

The service remains a loopback-only, single-process hackathon prototype with in-memory sessions. It has no authentication, durable multi-worker storage, OS-level SQL sandbox, production rate limiting, or public deployment. These remain architectural limits rather than claimed completed features. The large Plotly lazy chunk and a third-party Starlette TestClient deprecation warning are documented in VALIDATION.md.

For presentation use `demo/DEMO_GUIDE.md` and the reproducible `demo/check_demo.py` preflight. See VALIDATION.md for actual test results and browser coverage limits.
