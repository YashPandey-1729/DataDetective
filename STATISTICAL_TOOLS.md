# Statistical analysis tools

The backend exposes **29 statistical operations** through `calculate_statistics`, including an `excel` dispatcher with **116 named functions**. This covers the **111 functions** in [Microsoft's statistical reference](https://support.microsoft.com/en-us/excel/statistical-functions-reference), plus `SUM`, `SUMSQ`, `PRODUCT`, `SUMIF` and `SUMIFS`. The [Analysis ToolPak families](https://support.microsoft.com/en-us/excel/use-the-analysis-toolpak-to-perform-complex-data-analysis) are mapped below. This is a statistical API over uploaded data, not an Excel workbook formula engine.

## How to use it

Ask a statistical question in the existing investigation screen. Gemini and local Gemma have access to `statistics_catalog`, which discovers operations, named functions, required inputs, parameter schemas and assumptions. The local decoder makes discovered operations available through tool-specific schemas; the backend validates every call independently.

Examples:

- “Find the sum, all modes, mean, sample standard deviation, minimum and maximum of total_amount.”
- “Calculate the 25th, 50th and 75th percentiles of trip_distance.”
- “Use a paired t-test to compare before and after, then calculate a mean confidence interval for before.”
- “Regress Revenue on Price and Marketing. Report coefficients and uncertainty.”
- “Compute a correlation matrix for temperature, pressure and vibration.”

Model planning quality is separate from calculation correctness. A live Gemini paired-test/interval investigation completed without errors. Local Gemma executed advanced tests but also repeated calls and missed requested analyses in live trials. Use the direct API for a specific calculation when autonomous selection is unreliable; it requires no model or API key.

### Direct API

1. Upload a CSV/XLS/XLSX through `POST /api/datasets` or the UI and retain its dataset ID.
2. Inspect `GET /api/statistics/catalog?name=all`, or request an exact operation/function, such as `?name=t_test` or `?name=NORM.DIST`. `category` optionally filters searches. Lowercase operation names select analyses; uppercase legacy aliases such as `RANK` select named functions.
3. Send `POST /api/datasets/{dataset_id}/statistics` with the body below. OpenAPI documentation is at `/docs` on the backend.

Paired test:

```json
{
  "operation": "t_test",
  "column": "before",
  "other_column": "after",
  "parameters": {"method": "paired", "alternative": "two-sided", "alpha": 0.05}
}
```

Exclusive worksheet percentile:

```json
{
  "operation": "excel",
  "parameters": {"function": "PERCENTILE.EXC", "values": {"column": "amount"}, "k": 0.25}
}
```

Multiple regression:

```json
{
  "operation": "regression",
  "column": "Revenue",
  "parameters": {"predictors": ["Price", "Marketing"], "confidence": 0.95}
}
```

Named functions use named arguments, not formula text. A range reference is `{"column":"actual_column"}`; a predictor matrix is `{"columns":["x1","x2"]}`. Small literal arrays and scalar distribution parameters are also accepted. Discover the function for its exact API names: for example, `EXPON.DIST` uses `rate` for Excel's lambda, and percentile functions use `k`.

Within an investigation, reference-capable scalar inputs can use retained analytical evidence: `{"evidence_id":"E03","row":null,"field":"std"}`. Consult the function's schema for fields that accept this reference form. SQL cell references require a numeric row index. This avoids copying or inventing computed inputs. Standalone API calls do not retain an investigation evidence ledger, so use column references or explicit values there.

## Operations and ToolPak coverage

| Operation | Inputs and supported analyses |
| --- | --- |
| `summary` | Numeric `column`: count, sum, mean, median, min/max, range, sample/population variance and standard deviation, standard error, mean absolute deviation, skewness, excess kurtosis, confidence margin, geometric/harmonic mean when defined. ToolPak descriptive statistics. |
| `mode` | `column`: all exact modal ties and frequencies, including categorical data. Unlike worksheet MODE, singleton values are retained with “no unique mode” disclosure. |
| `outliers` | Numeric `column`: IQR candidates, not confirmed data errors. |
| `correlation` | `column`, `other_column`: Pearson coefficient and p-value. |
| `group_comparison` | `column`, `group_by`: descriptive grouped summaries. |
| `percentage_change` | Supplied `before`, `after`; not treated as observed dataset evidence. |
| `quantiles` | `column`; `probabilities`, inclusive/exclusive interpolation. |
| `rank` | `column`; direction and lowest/average tie ranks. ToolPak rank and percentile. |
| `histogram` | `column`; explicit upper-inclusive `bins` or automatic equal-width bins, cumulative counts and overflow. ToolPak histogram. |
| `confidence_interval` | `column`; t interval or normal interval with known `sigma`. Returns mean, standard error, margin and bounds. |
| `covariance` | `column`, `other_column`; sample/population choice. |
| `correlation_matrix` | `parameters.columns`; Pearson, Spearman or Kendall. ToolPak correlation, with additional methods. |
| `covariance_matrix` | `parameters.columns`; sample/population choice. ToolPak covariance. |
| `t_test` | `column`, `other_column`; `method` paired/equal_variance/welch, direction, hypothesized difference, alpha. Covers the three ToolPak t-tests. |
| `one_sample_test` | `column`; null `mean`, t or known-sigma z test, direction. |
| `z_test` | Two columns; known population `variance1`, `variance2`, difference and direction. ToolPak two-sample z test. |
| `f_test` | Two columns; directional or two-sided variance-ratio test. ToolPak F-test. |
| `chi_square_test` | Two categorical columns for independence; or observed/expected count columns with `method:goodness_of_fit`. No Yates correction. Sparse expected counts are disclosed. |
| `anova_one_way` | Numeric `column`, `group_by`. ToolPak single-factor ANOVA. |
| `anova_two_way` | Numeric `column`, `group_by`, `parameters.factor2`, `replication`. Balanced complete cells with equal replicates, or one observation per cell without replication. Covers both ToolPak two-factor analyses. |
| `regression` | Response `column`, `parameters.predictors`; intercept, linear/log-linear fit, confidence, optional prediction rows. Coefficients, inference, residuals, fit statistics and sums of squares. ToolPak regression. |
| `moving_average` | `column`; window, optional ordering column. Trailing average and one-step forecast. ToolPak moving average. |
| `exponential_smoothing` | `column`; newest-observation weight `alpha`, optional ordering column. Excel damping factor is `1-alpha`. ToolPak exponential smoothing. |
| `forecast` | `column`; steps, ordering column, additive ETS seasonality and confidence. |
| `fourier_analysis` | Real `column`, optional imaginary column, forward/inverse FFT. ToolPak Fourier analysis. |
| `sampling` | Seeded random with/without replacement or periodic sampling. ToolPak sampling. |
| `random_generation` | Seeded normal, uniform, Bernoulli, binomial, Poisson, discrete or patterned output. ToolPak random number generation. Explicitly simulated data. |
| `normality_test` | `column`; Shapiro-Wilk or Jarque-Bera diagnostic. |
| `excel` | `parameters.function` and its validated named inputs; complete function list below. |

Together these cover the nineteen ToolPak menu analyses, counting ANOVA and t-test variants separately. Parameter defaults and complete JSON schemas are available from the catalog; names in the table are not a substitute for the schema.

## Named worksheet functions

| Family | Functions |
| --- | --- |
| Aggregation and moments | AVEDEV, AVERAGE, AVERAGEA, COUNT, COUNTA, COUNTBLANK, DEVSQ, GEOMEAN, HARMEAN, KURT, MAX, MAXA, MEDIAN, MIN, MINA, MODE.MULT, MODE.SNGL, SKEW, SKEW.P, STDEV.P, STDEV.S, STDEVA, STDEVPA, VAR.P, VAR.S, VARA, VARPA, SUM, SUMSQ, PRODUCT |
| Conditional aggregation | AVERAGEIF, AVERAGEIFS, COUNTIF, COUNTIFS, MAXIFS, MINIFS, SUMIF, SUMIFS |
| Ordering and frequency | LARGE, SMALL, TRIMMEAN, PERCENTILE.INC, PERCENTILE.EXC, QUARTILE.INC, QUARTILE.EXC, PERCENTRANK.INC, PERCENTRANK.EXC, RANK.EQ, RANK.AVG, FREQUENCY |
| Relationships and regression | CORREL, PEARSON, COVARIANCE.P, COVARIANCE.S, RSQ, INTERCEPT, SLOPE, STEYX, LINEST, LOGEST, TREND, GROWTH, FORECAST, FORECAST.LINEAR |
| Testing and transformations | STANDARDIZE, CONFIDENCE.NORM, CONFIDENCE.T, T.TEST, F.TEST, Z.TEST, CHISQ.TEST, FISHER, FISHERINV, GAMMA, GAMMALN, GAMMALN.PRECISE, GAUSS, PHI, PERMUT, PERMUTATIONA, PROB |
| Normal and beta distributions | NORM.DIST, NORM.INV, NORM.S.DIST, NORM.S.INV, BETA.DIST, BETA.INV |
| Discrete distributions | BINOM.DIST, BINOM.DIST.RANGE, BINOM.INV, POISSON.DIST, NEGBINOM.DIST, HYPGEOM.DIST |
| Test distributions | CHISQ.DIST, CHISQ.DIST.RT, CHISQ.INV, CHISQ.INV.RT, F.DIST, F.DIST.RT, F.INV, F.INV.RT, T.DIST, T.DIST.RT, T.DIST.2T, T.INV, T.INV.2T |
| Other distributions | EXPON.DIST, GAMMA.DIST, GAMMA.INV, LOGNORM.DIST, LOGNORM.INV, WEIBULL.DIST |
| ETS | FORECAST.ETS, FORECAST.ETS.CONFINT, FORECAST.ETS.SEASONALITY, FORECAST.ETS.STAT |

Legacy aliases such as MODE, STDEV, STDEVP, VAR, VARP, PERCENTILE, QUARTILE, RANK, COVAR, NORMDIST and TTEST resolve to modern names. They use the modern API's named arguments; legacy positional signatures are not implemented. `statistics_catalog` returns the canonical function and exact schema.

## Statistical and compatibility rules

- Calculations use NumPy, SciPy and statsmodels on the backend; the model does not calculate numerical answers itself. SQL also permits safe arithmetic such as SQRT/POWER/LN/EXP while retaining its table, external-access, memory and time restrictions.
- Numeric ranges exclude missing/nonfinite values; paired calculations drop incomplete pairs together. Independent tests use each group's available values. Matrices and dataset regressions use complete cases across selected columns. Time-series calculations reject missing measurements to preserve time positions. Ordering columns must be distinct and nonmissing. Forecast/FFT ordering must be a regular numeric or date sequence; without an ordering column, equally spaced dataset row order is assumed.
- Standard statistical functions ignore text/logicals in ranges. A variants count text as zero and booleans as zero/one. COUNTA counts empty strings as present; COUNTBLANK counts empty strings and missing values. Conditional criteria support comparisons, case-insensitive wildcards and tilde escapes.
- Sample and population denominators are explicit. Excel exclusive percentiles reject ranks that cannot be interpolated. Worksheet MODE reports an error when nothing repeats, while the dataset mode operation explains the ties. Skewness and kurtosis reject insufficient/constant samples; undefined optional summary/matrix/regression cells are null, never fabricated zero.
- Tests expose p-values, alpha, direction and rejection decisions where relevant. Inference depends on independence, distribution, variance and pairing assumptions; the tool cannot establish those assumptions for the user. Multiple-testing adjustments are not automatic. Correlation and regression do not prove causation.
- Regression rejects collinear predictors. LINEST/LOGEST return named coefficient rows and model statistics rather than Excel's spilled-array orientation; LOGEST also returns growth factors and identifies log-scale inference. The API includes statistics even when the accepted worksheet `stats` flag is false. Prediction arrays use rows as observations. Missing entries in worksheet matrix regression inputs are rejected; dataset `regression` performs complete-case selection.
- ETS uses **additive Holt-Winters optimization and centered, fixed-seed residual bootstrap intervals**. Automatic seasonality uses a spectral heuristic. These methods, confidence intervals and floating-point results can differ from Excel's implementation. The worksheet ETS timeline currently uses numeric serials, handles duplicate timestamps by the selected aggregation, permits up to thirty percent missing steps, and fills gaps by interpolation or zero. The dataset forecast operation also supports regularly spaced date columns. These are explicit statistical equivalents, not a promise of identical Excel forecasts.
- Imported range/array behavior is supported, not a workbook calculation engine. Cell errors, workbook references, Excel's complete scalar coercion rules, localization, direct-argument versus referenced-cell distinctions, and every historical Excel edge case are not emulated. Invalid/undefined calculations return controlled errors rather than Excel error tokens.
- Dataset calculations retain source columns and assumptions. Simulation and literal-only calculations are marked separately and cannot become findings about uploaded data. Reports validate numerical measurements against retained cells. Advanced statistical outputs are labeled computed; independent recomputation currently applies to SQL cells.
- Results retain at most two hundred tabular rows and disclose total/truncation where supported. Dataset operations still calculate on the complete finite input. Literal arrays are limited to two thousand entries; matrices and predictors are bounded. ETS allows at most five thousand points and two hundred forecast steps; FFT allows at most sixty-five thousand five hundred thirty-six points. The HTTP request-size limit also applies.

## Validation

`backend/tests/test_excel_statistics.py` has numerical fixtures for every named function, an explicit Microsoft-reference coverage set, range/provenance checks and undefined-input cases. `backend/tests/test_statistical_library.py` checks hand-calculated inference/ANOVA fixtures, regression, matrix charts, sampling, forecasting, FFT, catalog discovery, direct API behavior and report grounding. See [VALIDATION.md](VALIDATION.md) for actual full-suite and live-model results.
