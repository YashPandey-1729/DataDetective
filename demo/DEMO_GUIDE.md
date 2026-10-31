# Hackathon demo checklist

Start FastAPI and Vite using the root README commands. On another terminal run:

```powershell
.\.venv\Scripts\python demo\check_demo.py --mode offline
```

This sends real synthetic CSV and PNG multipart uploads, runs real SQL, polls the investigation, verifies the totals against an independent expected-results file, and saves an actual Markdown report. Add `--format xlsx` to run the same workflow with the full Excel workbook. Expected answers are never included in the investigation request. It also checks that offline mode does not fabricate image interpretation.

For the agent presentation, configure `.env`, restart FastAPI, then run:

```powershell
.\.venv\Scripts\python demo\check_demo.py --mode agent
```

That command makes real Gemini calls and may consume API quota. It checks image interpretation, multiple real queries, charts, recomputation, and report export. Run it before presenting; a configured key alone does not prove model access or sufficient quota. No live Gemini success is claimed until this passes with your key.

## Two-minute presentation

1. **Connect:** Load the retail sample or upload the full `retail_sales.csv`. Show row count, detected schema, and data completeness.
2. **Add context:** Attach `revenue_decline.png`. Select **Gemini autonomous agent** and ask why February revenue declined, requesting region and category/product drill-downs.
3. **Show adaptation:** Point to the model-selected regional comparison and its next decision based on the actual observation. Expand the SQL evidence. Explain the tool sequence is selected by the model; chart/verification system finalization, if used, is explicitly labeled.
4. **Show evidence:** Review the interactive charts, measured cells and source labels, and recomputation ledger. Distinguish descriptive contributions from causal explanations.
5. **Deliver:** Show limitations and export Markdown. A `partial` result signals a resource limit or failure; do not present it as a complete investigation.

Model latency varies; finish a preflight investigation before the live two-minute pitch so a real report is available if a later call is slow. Do not present a mocked test as a live agent. If credentials or network fail, explicitly announce **Offline analytics** and use the working deterministic SQL demo.

## Independent synthetic ground truth

January: **633,633.45**. February: **528,492.33**. Difference: **−105,141.12**, or **−16.5934%**. West contributes **−95,796.06**; within West, Electronics contributes **−93,225.75**. All values are synthetic currency units; each synthetic month covers days **1–28**, not full calendar months. These are expected validation answers, not hardcoded app findings or proof of causation.

The full `retail_sales.xlsx` and `retail_sales.csv` contain the same data and support the complete scenario. The short `retail_preview.xlsx` contains only the start of January; use it to demonstrate ingestion, not a February investigation.
