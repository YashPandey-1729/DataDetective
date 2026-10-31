# DataDetective AI investigation

Why did revenue decline in February? Compare regions, then investigate categories and products in the region contributing most. Verify the numerical change.

Mode: offline

Offline analytics computed the temporal or categorical comparisons and descriptive statistics shown below. Fixed rules chose the metric; the natural-language question did not control this workflow.

## Findings
- [observation] Computed query results; inspect the segment labels and source query. (E02)
  - total = 633633.4500000003 · computed · E02 row 0 · {"period": "2026-01-01T00:00:00.000"}
  - total = 528492.3300000001 · computed · E02 row 1 · {"period": "2026-02-01T00:00:00.000"}
  - total = 617340.5199999998 · computed · E02 row 2 · {"period": "2026-03-01T00:00:00.000"}
- [observation] Computed query results; inspect the segment labels and source query. (E04)
  - previous = 633633.4500000003 · computed · E04 row 0 · {"period": "2026-02-01T00:00:00.000", "previous_period": "2026-01-01T00:00:00.000"}
  - total = 528492.3300000001 · computed · E04 row 0 · {"period": "2026-02-01T00:00:00.000", "previous_period": "2026-01-01T00:00:00.000"}
  - delta = -105141.12000000023 · verified · E04 row 0 · {"period": "2026-02-01T00:00:00.000", "previous_period": "2026-01-01T00:00:00.000"}
  - pct_change = -16.593366401347684 · computed · E04 row 0 · {"period": "2026-02-01T00:00:00.000", "previous_period": "2026-01-01T00:00:00.000"}
- [observation] Computed query results; inspect the segment labels and source query. (E06)
  - current_total = 67210.81999999996 · computed · E06 row 0 · {"segment": "West"}
  - previous_total = 163006.87999999995 · computed · E06 row 0 · {"segment": "West"}
  - delta = -95796.05999999998 · computed · E06 row 0 · {"segment": "West"}
  - current_total = 147612.3 · computed · E06 row 1 · {"segment": "South"}
  - previous_total = 164556.25000000012 · computed · E06 row 1 · {"segment": "South"}
  - delta = -16943.950000000128 · computed · E06 row 1 · {"segment": "South"}
  - current_total = 153419.74000000005 · computed · E06 row 2 · {"segment": "East"}
  - previous_total = 153458.02000000014 · computed · E06 row 2 · {"segment": "East"}
  - delta = -38.28000000008615 · computed · E06 row 2 · {"segment": "East"}
- [observation] Computed query results; inspect the segment labels and source query. (E08)
  - current_total = 30690.649999999994 · computed · E08 row 0 · {"category": "Electronics"}
  - previous_total = 123916.4 · computed · E08 row 0 · {"category": "Electronics"}
  - delta = -93225.75 · computed · E08 row 0 · {"category": "Electronics"}
  - current_total = 24105.919999999995 · computed · E08 row 1 · {"category": "Home"}
  - previous_total = 27388.74000000001 · computed · E08 row 1 · {"category": "Home"}
  - delta = -3282.8200000000143 · computed · E08 row 1 · {"category": "Home"}
  - current_total = 12414.25 · computed · E08 row 2 · {"category": "Lifestyle"}
  - previous_total = 11701.740000000003 · computed · E08 row 2 · {"category": "Lifestyle"}
  - delta = 712.5099999999966 · computed · E08 row 2 · {"category": "Lifestyle"}
- [observation] Computed statistical analysis; inspect the tool evidence for method and assumptions. (E09)
  - count = 5292 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - sum = 2434538.31 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - mean = 460.0412528344671 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - median = 181.95999999999998 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - std = 740.4908809245985 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - min = 20.24 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - max = 3369.6 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - variance = 548326.744732488 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - variance_population = 548223.1304572172 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - std_population = 740.4209143839855 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - standard_error = 10.17910974843524 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - range = 3349.36 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - mean_absolute_deviation = 473.9124110110156 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - skewness = 2.540846145842416 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - kurtosis = 5.550105554055278 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - confidence_margin_95 = 19.95525343077826 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - geometric_mean = 201.17250664743466 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
  - harmonic_mean = 110.62650231923793 · computed · E09 row None · {"column": "Revenue", "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies."}
- [observation] Computed statistical analysis; inspect the tool evidence for method and assumptions. (E10)
  - count = 614 · computed · E10 row None · {"column": "Revenue", "method": "1.5 × IQR; candidates, not confirmed errors"}
  - lower = -370.78999999999996 · computed · E10 row None · {"column": "Revenue", "method": "1.5 × IQR; candidates, not confirmed errors"}
  - upper = 852.3299999999999 · computed · E10 row None · {"column": "Revenue", "method": "1.5 × IQR; candidates, not confirmed errors"}
- [observation] Computed statistical table; row labels identify coefficients, bins or other statistical outputs. (E10)
  - Quantity = 4 · computed · E10 row 0 · {"Transaction ID": "T000001", "Date": "2026-01-01T00:00:00.000", "Region": "West", "Product": "Laptop", "Category": "Electronics"}
  - Unit Price = 772.37 · computed · E10 row 0 · {"Transaction ID": "T000001", "Date": "2026-01-01T00:00:00.000", "Region": "West", "Product": "Laptop", "Category": "Electronics"}
  - Revenue = 3089.48 · computed · E10 row 0 · {"Transaction ID": "T000001", "Date": "2026-01-01T00:00:00.000", "Region": "West", "Product": "Laptop", "Category": "Electronics"}
  - Quantity = 4 · computed · E10 row 1 · {"Transaction ID": "T000002", "Date": "2026-01-01T00:00:00.000", "Region": "West", "Product": "Laptop", "Category": "Electronics"}
  - Unit Price = 804.63 · computed · E10 row 1 · {"Transaction ID": "T000002", "Date": "2026-01-01T00:00:00.000", "Region": "West", "Product": "Laptop", "Category": "Electronics"}
  - Revenue = 3218.52 · computed · E10 row 1 · {"Transaction ID": "T000002", "Date": "2026-01-01T00:00:00.000", "Region": "West", "Product": "Laptop", "Category": "Electronics"}
  - Quantity = 2 · computed · E10 row 2 · {"Transaction ID": "T000014", "Date": "2026-01-01T00:00:00.000", "Region": "East", "Product": "Laptop", "Category": "Electronics"}
  - Unit Price = 723.07 · computed · E10 row 2 · {"Transaction ID": "T000014", "Date": "2026-01-01T00:00:00.000", "Region": "East", "Product": "Laptop", "Category": "Electronics"}
  - Revenue = 1446.14 · computed · E10 row 2 · {"Transaction ID": "T000014", "Date": "2026-01-01T00:00:00.000", "Region": "East", "Product": "Laptop", "Category": "Electronics"}
  - Quantity = 3 · computed · E10 row 3 · {"Transaction ID": "T000025", "Date": "2026-01-01T00:00:00.000", "Region": "North", "Product": "Laptop", "Category": "Electronics"}
  - Unit Price = 735.04 · computed · E10 row 3 · {"Transaction ID": "T000025", "Date": "2026-01-01T00:00:00.000", "Region": "North", "Product": "Laptop", "Category": "Electronics"}
  - Revenue = 2205.12 · computed · E10 row 3 · {"Transaction ID": "T000025", "Date": "2026-01-01T00:00:00.000", "Region": "North", "Product": "Laptop", "Category": "Electronics"}
  - Quantity = 3 · computed · E10 row 4 · {"Transaction ID": "T000028", "Date": "2026-01-01T00:00:00.000", "Region": "North", "Product": "Laptop", "Category": "Electronics"}
  - Unit Price = 815.03 · computed · E10 row 4 · {"Transaction ID": "T000028", "Date": "2026-01-01T00:00:00.000", "Region": "North", "Product": "Laptop", "Category": "Electronics"}
  - Revenue = 2445.09 · computed · E10 row 4 · {"Transaction ID": "T000028", "Date": "2026-01-01T00:00:00.000", "Region": "North", "Product": "Laptop", "Category": "Electronics"}
  - Quantity = 3 · computed · E10 row 5 · {"Transaction ID": "T000040", "Date": "2026-01-01T00:00:00.000", "Region": "South", "Product": "Laptop", "Category": "Electronics"}
  - Unit Price = 815.43 · computed · E10 row 5 · {"Transaction ID": "T000040", "Date": "2026-01-01T00:00:00.000", "Region": "South", "Product": "Laptop", "Category": "Electronics"}
  - Revenue = 2446.29 · computed · E10 row 5 · {"Transaction ID": "T000040", "Date": "2026-01-01T00:00:00.000", "Region": "South", "Product": "Laptop", "Category": "Electronics"}

## Numerical verification ledger
- verified: delta row 0 = -105141.12000000023; source E04. Only the referenced numeric cell in an unambiguously matched result row was independently recomputed; this does not verify causality or other text in the claim.

## Limitations
- Offline analytics demo: deterministic rules, no autonomous LLM or image understanding.
- No causal inference was performed.
- Review period coverage and missing values before making business decisions.
- Contributing segments are descriptive evidence, not proven causes.
- Report numbers come from exact referenced cells. Evidence links do not independently validate narrative interpretation.
- Recomputation checks query consistency, not source-data truth or correctness of metric definitions.
- Sessions expire after two hours of inactivity and disappear on restart.
- The attached chart was not interpreted; no visual context influenced this report.

## Next steps
- Validate surprising segments against source records.
- Investigate additional periods or candidate confounding factors.

## Report checks

## Evidence
### E01 · profile_dataset
```json
{
  "rows": 5292,
  "column_count": 8,
  "missing": 0,
  "duplicates": 0,
  "columns": [
    {
      "name": "Transaction ID",
      "dtype": "object",
      "kind": "categorical",
      "missing": 0,
      "unique": 5292
    },
    {
      "name": "Date",
      "dtype": "datetime64[ns]",
      "kind": "date",
      "missing": 0,
      "unique": 112,
      "coverage": {
        "min": "2026-01-01 00:00:00",
        "max": "2026-04-28 00:00:00",
        "distinct_dates": 112
      },
      "monthly_coverage": [
        {
          "month": "2026-01",
          "first": "2026-01-01T00:00:00.000",
          "last": "2026-01-28T00:00:00.000",
          "records": 1344
        },
        {
          "month": "2026-02",
          "first": "2026-02-01T00:00:00.000",
          "last": "2026-02-28T00:00:00.000",
          "records": 1260
        },
        {
          "month": "2026-03",
          "first": "2026-03-01T00:00:00.000",
          "last": "2026-03-28T00:00:00.000",
          "records": 1344
        },
        {
          "month": "2026-04",
          "first": "2026-04-01T00:00:00.000",
          "last": "2026-04-28T00:00:00.000",
          "records": 1344
        }
      ]
    },
    {
      "name": "Region",
      "dtype": "object",
      "kind": "categorical",
      "missing": 0,
      "unique": 4
    },
    {
      "name": "Product",
      "dtype": "object",
      "kind": "categorical",
      "missing": 0,
      "unique": 6
    },
    {
      "name": "Category",
      "dtype": "object",
      "kind": "categorical",
      "missing": 0,
      "unique": 3
    },
    {
      "name": "Quantity",
      "dtype": "int64",
      "kind": "numeric",
      "missing": 0,
      "unique": 4,
      "summary": {
        "count": 5292.0,
        "mean": 2.489984882842026,
        "std": 1.1128422695914033,
        "min": 1.0,
        "25%": 1.0,
        "50%": 2.0,
        "75%": 3.0,
        "max": 4.0
      }
    },
    {
      "name": "Unit Price",
      "dtype": "float64",
      "kind": "numeric",
      "missing": 0,
      "unique": 3640,
      "summary": {
        "count": 5292.0,
        "mean": 185.21075774754345,
        "std": 261.80498667956203,
        "min": 20.24,
        "25%": 44.8775,
        "50%": 69.5,
        "75%": 138.5125,
        "max": 842.4
      }
    },
    {
      "name": "Revenue",
      "dtype": "float64",
      "kind": "numeric",
      "missing": 0,
      "unique": 4521,
      "summary": {
        "count": 5292.0,
        "mean": 460.0412528344671,
        "std": 740.4908809245985,
        "min": 20.24,
        "25%": 87.88,
        "50%": 181.95999999999998,
        "75%": 393.65999999999997,
        "max": 3369.6
      }
    }
  ],
  "metrics": [
    "Quantity",
    "Unit Price",
    "Revenue"
  ],
  "dimensions": [
    "Transaction ID",
    "Region",
    "Product",
    "Category"
  ],
  "dates": [
    "Date"
  ],
  "preview": [
    {
      "Transaction ID": "T000001",
      "Date": "2026-01-01T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 772.37,
      "Revenue": 3089.48
    },
    {
      "Transaction ID": "T000002",
      "Date": "2026-01-01T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 804.63,
      "Revenue": 3218.52
    },
    {
      "Transaction ID": "T000003",
      "Date": "2026-01-01T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 1,
      "Unit Price": 839.36,
      "Revenue": 839.36
    },
    {
      "Transaction ID": "T000004",
      "Date": "2026-01-01T00:00:00.000",
      "Region": "West",
      "Product": "Headphones",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 99.35,
      "Revenue": 397.4
    },
    {
      "Transaction ID": "T000005",
      "Date": "2026-01-01T00:00:00.000",
      "Region": "West",
      "Product": "Chair",
      "Category": "Home",
      "Quantity": 1,
      "Unit Price": 138.89,
      "Revenue": 138.89
    },
    {
      "Transaction ID": "T000006",
      "Date": "2026-01-01T00:00:00.000",
      "Region": "West",
      "Product": "Chair",
      "Category": "Home",
      "Quantity": 2,
      "Unit Price": 149.56,
      "Revenue": 299.12
    },
    {
      "Transaction ID": "T000007",
      "Date": "2026-01-01T00:00:00.000",
      "Region": "West",
      "Product": "Chair",
      "Category": "Home",
      "Quantity": 3,
      "Unit Price": 147.23,
      "Revenue": 441.69
    },
    {
      "Transaction ID": "T000008",
      "Date": "2026-01-01T00:00:00.000",
      "Region": "West",
      "Product": "Chair",
      "Category": "Home",
      "Quantity": 2,
      "Unit Price": 133.89,
      "Revenue": 267.78
    }
  ]
}
```
### E02 · execute_sql
```json
{
  "sql": "SELECT DATE_TRUNC('MONTH', \"Date\") AS period, SUM(\"Revenue\") AS total FROM dataset GROUP BY 1 ORDER BY 1",
  "columns": [
    "period",
    "total"
  ],
  "rows": [
    {
      "period": "2026-01-01T00:00:00.000",
      "total": 633633.4500000003
    },
    {
      "period": "2026-02-01T00:00:00.000",
      "total": 528492.3300000001
    },
    {
      "period": "2026-03-01T00:00:00.000",
      "total": 617340.5199999998
    },
    {
      "period": "2026-04-01T00:00:00.000",
      "total": 655072.0100000007
    }
  ],
  "row_count": 4,
  "truncated": false
}
```
### E03 · generate_chart
```json
{
  "title": "Revenue over time",
  "data": [
    {
      "type": "scatter",
      "x": [
        "2026-01-01T00:00:00.000",
        "2026-02-01T00:00:00.000",
        "2026-03-01T00:00:00.000",
        "2026-04-01T00:00:00.000"
      ],
      "y": [
        633633.4500000003,
        528492.3300000001,
        617340.5199999998,
        655072.0100000007
      ],
      "marker": {
        "color": "#56d8e4"
      },
      "name": "total",
      "mode": "lines+markers",
      "line": {
        "color": "#56d8e4",
        "width": 3
      }
    }
  ],
  "layout": {
    "xaxis": {
      "title": {
        "text": "period"
      }
    },
    "yaxis": {
      "title": {
        "text": "total"
      }
    }
  },
  "evidence_id": "E02",
  "truncated": false
}
```
### E04 · execute_sql
```json
{
  "sql": "WITH monthly AS (SELECT DATE_TRUNC('MONTH', \"Date\") AS period, SUM(\"Revenue\") AS total FROM dataset WHERE NOT \"Date\" IS NULL GROUP BY 1), compared AS (SELECT period, total, LAG(total) OVER (ORDER BY period) AS previous, LAG(period) OVER (ORDER BY period) AS previous_period FROM monthly) SELECT period, previous_period, previous, total, total - previous AS delta, 100.0 * (total - previous) / NULLIF(ABS(previous), 0) AS pct_change FROM compared WHERE NOT previous IS NULL ORDER BY delta LIMIT 1",
  "columns": [
    "period",
    "previous_period",
    "previous",
    "total",
    "delta",
    "pct_change"
  ],
  "rows": [
    {
      "period": "2026-02-01T00:00:00.000",
      "previous_period": "2026-01-01T00:00:00.000",
      "previous": 633633.4500000003,
      "total": 528492.3300000001,
      "delta": -105141.12000000023,
      "pct_change": -16.593366401347684
    }
  ],
  "row_count": 1,
  "truncated": false
}
```
### E05 · verify_finding
```json
{
  "claim": "Monthly total difference",
  "evidence_id": "E04",
  "sql": "WITH monthly AS (SELECT DATE_TRUNC('MONTH', \"Date\") AS period, SUM(\"Revenue\") AS total FROM dataset WHERE NOT \"Date\" IS NULL GROUP BY 1), compared AS (SELECT period, total, LAG(total) OVER (ORDER BY period) AS previous, LAG(period) OVER (ORDER BY period) AS previous_period FROM monthly) SELECT period, previous_period, previous, total, total - previous AS delta, 100.0 * (total - previous) / NULLIF(ABS(previous), 0) AS pct_change FROM compared WHERE NOT previous IS NULL ORDER BY delta LIMIT 1",
  "row": 0,
  "field": "delta",
  "original": -105141.12000000023,
  "actual": -105141.12000000023,
  "expected": -105141.12000000023,
  "status": "verified",
  "matched_row": 0,
  "identity_fields": [
    "period",
    "previous_period",
    "previous",
    "total",
    "pct_change"
  ],
  "scope": "Only the referenced numeric cell in an unambiguously matched result row was independently recomputed; this does not verify causality or other text in the claim.",
  "note": "Result row matched using the other returned fields."
}
```
### E06 · execute_sql
```json
{
  "sql": "SELECT \"Region\" AS segment, SUM(CASE WHEN DATE_TRUNC('MONTH', \"Date\") = CAST('2026-02-01' AS DATE) THEN \"Revenue\" ELSE 0 END) AS current_total, SUM(CASE WHEN DATE_TRUNC('MONTH', \"Date\") = CAST('2026-01-01' AS DATE) THEN \"Revenue\" ELSE 0 END) AS previous_total, current_total - previous_total AS delta FROM dataset GROUP BY 1 ORDER BY delta",
  "columns": [
    "segment",
    "current_total",
    "previous_total",
    "delta"
  ],
  "rows": [
    {
      "segment": "West",
      "current_total": 67210.81999999996,
      "previous_total": 163006.87999999995,
      "delta": -95796.05999999998
    },
    {
      "segment": "South",
      "current_total": 147612.3,
      "previous_total": 164556.25000000012,
      "delta": -16943.950000000128
    },
    {
      "segment": "East",
      "current_total": 153419.74000000005,
      "previous_total": 153458.02000000014,
      "delta": -38.28000000008615
    },
    {
      "segment": "North",
      "current_total": 160249.47000000003,
      "previous_total": 152612.3,
      "delta": 7637.170000000042
    }
  ],
  "row_count": 4,
  "truncated": false
}
```
### E07 · generate_chart
```json
{
  "title": "Contribution to monthly change",
  "data": [
    {
      "type": "bar",
      "x": [
        "West",
        "South",
        "East",
        "North"
      ],
      "y": [
        -95796.05999999998,
        -16943.950000000128,
        -38.28000000008615,
        7637.170000000042
      ],
      "marker": {
        "color": "#56d8e4"
      },
      "name": "delta"
    }
  ],
  "layout": {
    "xaxis": {
      "title": {
        "text": "segment"
      }
    },
    "yaxis": {
      "title": {
        "text": "delta"
      }
    }
  },
  "evidence_id": "E06",
  "truncated": false
}
```
### E08 · execute_sql
```json
{
  "sql": "SELECT \"Category\" AS category, SUM(CASE WHEN DATE_TRUNC('MONTH', \"Date\") = CAST('2026-02-01' AS DATE) THEN \"Revenue\" ELSE 0 END) AS current_total, SUM(CASE WHEN DATE_TRUNC('MONTH', \"Date\") = CAST('2026-01-01' AS DATE) THEN \"Revenue\" ELSE 0 END) AS previous_total, current_total - previous_total AS delta FROM dataset WHERE CAST(\"Region\" AS TEXT) = 'West' GROUP BY 1 ORDER BY delta",
  "columns": [
    "category",
    "current_total",
    "previous_total",
    "delta"
  ],
  "rows": [
    {
      "category": "Electronics",
      "current_total": 30690.649999999994,
      "previous_total": 123916.4,
      "delta": -93225.75
    },
    {
      "category": "Home",
      "current_total": 24105.919999999995,
      "previous_total": 27388.74000000001,
      "delta": -3282.8200000000143
    },
    {
      "category": "Lifestyle",
      "current_total": 12414.25,
      "previous_total": 11701.740000000003,
      "delta": 712.5099999999966
    }
  ],
  "row_count": 3,
  "truncated": false
}
```
### E09 · calculate_statistics
```json
{
  "column": "Revenue",
  "count": 5292,
  "sum": 2434538.31,
  "mean": 460.0412528344671,
  "median": 181.95999999999998,
  "std": 740.4908809245985,
  "min": 20.24,
  "max": 3369.6,
  "note": "Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies.",
  "variance": 548326.744732488,
  "variance_population": 548223.1304572172,
  "std_population": 740.4209143839855,
  "standard_error": 10.17910974843524,
  "range": 3349.36,
  "mean_absolute_deviation": 473.9124110110156,
  "skewness": 2.540846145842416,
  "kurtosis": 5.550105554055278,
  "confidence_margin_95": 19.95525343077826,
  "geometric_mean": 201.17250664743466,
  "harmonic_mean": 110.62650231923793
}
```
### E10 · calculate_statistics
```json
{
  "column": "Revenue",
  "method": "1.5 × IQR; candidates, not confirmed errors",
  "count": 614,
  "lower": -370.78999999999996,
  "upper": 852.3299999999999,
  "rows": [
    {
      "Transaction ID": "T000001",
      "Date": "2026-01-01T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 772.37,
      "Revenue": 3089.48
    },
    {
      "Transaction ID": "T000002",
      "Date": "2026-01-01T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 804.63,
      "Revenue": 3218.52
    },
    {
      "Transaction ID": "T000014",
      "Date": "2026-01-01T00:00:00.000",
      "Region": "East",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 2,
      "Unit Price": 723.07,
      "Revenue": 1446.14
    },
    {
      "Transaction ID": "T000025",
      "Date": "2026-01-01T00:00:00.000",
      "Region": "North",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 3,
      "Unit Price": 735.04,
      "Revenue": 2205.12
    },
    {
      "Transaction ID": "T000028",
      "Date": "2026-01-01T00:00:00.000",
      "Region": "North",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 3,
      "Unit Price": 815.03,
      "Revenue": 2445.09
    },
    {
      "Transaction ID": "T000040",
      "Date": "2026-01-01T00:00:00.000",
      "Region": "South",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 3,
      "Unit Price": 815.43,
      "Revenue": 2446.29
    },
    {
      "Transaction ID": "T000051",
      "Date": "2026-01-02T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 804.92,
      "Revenue": 3219.68
    },
    {
      "Transaction ID": "T000052",
      "Date": "2026-01-02T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 2,
      "Unit Price": 838.55,
      "Revenue": 1677.1
    },
    {
      "Transaction ID": "T000061",
      "Date": "2026-01-02T00:00:00.000",
      "Region": "East",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 3,
      "Unit Price": 798.7,
      "Revenue": 2396.1
    },
    {
      "Transaction ID": "T000064",
      "Date": "2026-01-02T00:00:00.000",
      "Region": "East",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 2,
      "Unit Price": 735.64,
      "Revenue": 1471.28
    },
    {
      "Transaction ID": "T000076",
      "Date": "2026-01-02T00:00:00.000",
      "Region": "North",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 829.44,
      "Revenue": 3317.76
    },
    {
      "Transaction ID": "T000099",
      "Date": "2026-01-03T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 3,
      "Unit Price": 826.75,
      "Revenue": 2480.25
    },
    {
      "Transaction ID": "T000121",
      "Date": "2026-01-03T00:00:00.000",
      "Region": "North",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 817.04,
      "Revenue": 3268.16
    },
    {
      "Transaction ID": "T000134",
      "Date": "2026-01-03T00:00:00.000",
      "Region": "South",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 2,
      "Unit Price": 736.77,
      "Revenue": 1473.54
    },
    {
      "Transaction ID": "T000146",
      "Date": "2026-01-04T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 724.08,
      "Revenue": 2896.32
    },
    {
      "Transaction ID": "T000147",
      "Date": "2026-01-04T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 729.97,
      "Revenue": 2919.88
    },
    {
      "Transaction ID": "T000159",
      "Date": "2026-01-04T00:00:00.000",
      "Region": "East",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 2,
      "Unit Price": 803.18,
      "Revenue": 1606.36
    },
    {
      "Transaction ID": "T000160",
      "Date": "2026-01-04T00:00:00.000",
      "Region": "East",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 2,
      "Unit Price": 836.02,
      "Revenue": 1672.04
    },
    {
      "Transaction ID": "T000172",
      "Date": "2026-01-04T00:00:00.000",
      "Region": "North",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 791.69,
      "Revenue": 3166.76
    },
    {
      "Transaction ID": "T000181",
      "Date": "2026-01-04T00:00:00.000",
      "Region": "South",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 732.54,
      "Revenue": 2930.16
    },
    {
      "Transaction ID": "T000183",
      "Date": "2026-01-04T00:00:00.000",
      "Region": "South",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 3,
      "Unit Price": 769.84,
      "Revenue": 2309.52
    },
    {
      "Transaction ID": "T000193",
      "Date": "2026-01-05T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 2,
      "Unit Price": 840.73,
      "Revenue": 1681.46
    },
    {
      "Transaction ID": "T000194",
      "Date": "2026-01-05T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 3,
      "Unit Price": 836.31,
      "Revenue": 2508.93
    },
    {
      "Transaction ID": "T000206",
      "Date": "2026-01-05T00:00:00.000",
      "Region": "East",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 3,
      "Unit Price": 798.74,
      "Revenue": 2396.22
    },
    {
      "Transaction ID": "T000229",
      "Date": "2026-01-05T00:00:00.000",
      "Region": "South",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 774.83,
      "Revenue": 3099.32
    },
    {
      "Transaction ID": "T000232",
      "Date": "2026-01-05T00:00:00.000",
      "Region": "South",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 755.21,
      "Revenue": 3020.84
    },
    {
      "Transaction ID": "T000241",
      "Date": "2026-01-06T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 2,
      "Unit Price": 744.76,
      "Revenue": 1489.52
    },
    {
      "Transaction ID": "T000244",
      "Date": "2026-01-06T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 2,
      "Unit Price": 745.75,
      "Revenue": 1491.5
    },
    {
      "Transaction ID": "T000254",
      "Date": "2026-01-06T00:00:00.000",
      "Region": "East",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 2,
      "Unit Price": 822.11,
      "Revenue": 1644.22
    },
    {
      "Transaction ID": "T000255",
      "Date": "2026-01-06T00:00:00.000",
      "Region": "East",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 2,
      "Unit Price": 732.06,
      "Revenue": 1464.12
    },
    {
      "Transaction ID": "T000265",
      "Date": "2026-01-06T00:00:00.000",
      "Region": "North",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 756.41,
      "Revenue": 3025.64
    },
    {
      "Transaction ID": "T000279",
      "Date": "2026-01-06T00:00:00.000",
      "Region": "South",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 2,
      "Unit Price": 778.78,
      "Revenue": 1557.56
    },
    {
      "Transaction ID": "T000289",
      "Date": "2026-01-07T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 790.87,
      "Revenue": 3163.48
    },
    {
      "Transaction ID": "T000290",
      "Date": "2026-01-07T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 760.11,
      "Revenue": 3040.44
    },
    {
      "Transaction ID": "T000303",
      "Date": "2026-01-07T00:00:00.000",
      "Region": "East",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 815.19,
      "Revenue": 3260.76
    },
    {
      "Transaction ID": "T000304",
      "Date": "2026-01-07T00:00:00.000",
      "Region": "East",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 731.84,
      "Revenue": 2927.36
    },
    {
      "Transaction ID": "T000313",
      "Date": "2026-01-07T00:00:00.000",
      "Region": "North",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 768.96,
      "Revenue": 3075.84
    },
    {
      "Transaction ID": "T000314",
      "Date": "2026-01-07T00:00:00.000",
      "Region": "North",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 728.19,
      "Revenue": 2912.76
    },
    {
      "Transaction ID": "T000315",
      "Date": "2026-01-07T00:00:00.000",
      "Region": "North",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 3,
      "Unit Price": 817.7,
      "Revenue": 2453.1
    },
    {
      "Transaction ID": "T000316",
      "Date": "2026-01-07T00:00:00.000",
      "Region": "North",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 820.26,
      "Revenue": 3281.04
    },
    {
      "Transaction ID": "T000325",
      "Date": "2026-01-07T00:00:00.000",
      "Region": "South",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 3,
      "Unit Price": 721.29,
      "Revenue": 2163.87
    },
    {
      "Transaction ID": "T000328",
      "Date": "2026-01-07T00:00:00.000",
      "Region": "South",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 761.03,
      "Revenue": 3044.12
    },
    {
      "Transaction ID": "T000337",
      "Date": "2026-01-08T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 805.07,
      "Revenue": 3220.28
    },
    {
      "Transaction ID": "T000339",
      "Date": "2026-01-08T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 779.62,
      "Revenue": 3118.48
    },
    {
      "Transaction ID": "T000373",
      "Date": "2026-01-08T00:00:00.000",
      "Region": "South",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 3,
      "Unit Price": 778.69,
      "Revenue": 2336.07
    },
    {
      "Transaction ID": "T000374",
      "Date": "2026-01-08T00:00:00.000",
      "Region": "South",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 2,
      "Unit Price": 771.43,
      "Revenue": 1542.86
    },
    {
      "Transaction ID": "T000387",
      "Date": "2026-01-09T00:00:00.000",
      "Region": "West",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 3,
      "Unit Price": 823.61,
      "Revenue": 2470.83
    },
    {
      "Transaction ID": "T000409",
      "Date": "2026-01-09T00:00:00.000",
      "Region": "North",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 4,
      "Unit Price": 784.52,
      "Revenue": 3138.08
    },
    {
      "Transaction ID": "T000410",
      "Date": "2026-01-09T00:00:00.000",
      "Region": "North",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 3,
      "Unit Price": 751.69,
      "Revenue": 2255.07
    },
    {
      "Transaction ID": "T000412",
      "Date": "2026-01-09T00:00:00.000",
      "Region": "North",
      "Product": "Laptop",
      "Category": "Electronics",
      "Quantity": 2,
      "Unit Price": 800.42,
      "Revenue": 1600.84
    }
  ]
}
```