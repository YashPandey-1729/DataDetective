import json
import pandas as pd
import numpy as np


def records(df: pd.DataFrame):
    return json.loads(df.to_json(orient='records', date_format='iso'))


def profile_dataset(df: pd.DataFrame) -> dict:
    columns = []
    for name in df.columns:
        col = df[name]
        kind = 'date' if pd.api.types.is_datetime64_any_dtype(col) else 'numeric' if pd.api.types.is_numeric_dtype(col) else 'categorical'
        info = {'name': name, 'dtype': str(col.dtype), 'kind': kind, 'missing': int(col.isna().sum()), 'unique': int(col.nunique())}
        if kind == 'numeric':
            finite = col.replace([np.inf, -np.inf], np.nan)
            info['summary'] = json.loads(finite.describe().to_json())
        if kind == 'date':
            valid = col.dropna()
            info['coverage'] = {'min': str(valid.min()) if len(valid) else None, 'max': str(valid.max()) if len(valid) else None, 'distinct_dates': int(valid.dt.date.nunique())}
            coverage = pd.DataFrame({'date': valid}).assign(month=valid.dt.strftime('%Y-%m'))
            info['monthly_coverage'] = records(coverage.groupby('month').agg(first=('date','min'),last=('date','max'),records=('date','size')).reset_index().head(24))
        columns.append(info)
    return {'rows': len(df), 'column_count': len(columns), 'missing': int(df.isna().sum().sum()),
            'duplicates': int(df.duplicated().sum()), 'columns': columns,
            'metrics': [c['name'] for c in columns if c['kind'] == 'numeric'],
            'dimensions': [c['name'] for c in columns if c['kind'] == 'categorical'],
            'dates': [c['name'] for c in columns if c['kind'] == 'date'], 'preview': records(df.head(8))}
