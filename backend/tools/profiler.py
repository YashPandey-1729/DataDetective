import json
import pandas as pd
import numpy as np
import math
from datetime import date, datetime, time, timedelta
from decimal import Decimal


def records(df: pd.DataFrame):
    # Pandas' JSON encoder rounds 1e-12 to zero at its default precision.
    # Preserve the original scalar values until the HTTP JSON encoder handles them.
    return [{str(key): json_value(value) for key,value in row.items()} for row in df.to_dict(orient='records')]


def json_value(value):
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value,np.generic): return json_value(value.item())
    if isinstance(value,(list,tuple,np.ndarray)): return [json_value(v) for v in value]
    if isinstance(value,dict): return {str(k):json_value(v) for k,v in value.items()}
    if isinstance(value,Decimal): return json_value(float(value))
    if isinstance(value,float): return value if math.isfinite(value) else None
    if isinstance(value,pd.Timestamp): return value.isoformat(timespec='milliseconds')
    if isinstance(value,(datetime,date,time)): return value.isoformat()
    if isinstance(value,(timedelta,pd.Timedelta)): return str(value)
    if isinstance(value,(str,int,bool)): return value
    raise ValueError(f'Unsupported result value type: {type(value).__name__}. Cast it to a scalar SQL type.')


def profile_dataset(df: pd.DataFrame) -> dict:
    columns = []
    for name in df.columns:
        col = df[name]
        kind = 'date' if pd.api.types.is_datetime64_any_dtype(col) else 'numeric' if pd.api.types.is_numeric_dtype(col) else 'categorical'
        info = {'name': name, 'dtype': str(col.dtype), 'kind': kind, 'missing': int(col.isna().sum()), 'unique': int(col.nunique())}
        if kind == 'numeric':
            finite = col.replace([np.inf, -np.inf], np.nan)
            info['summary'] = {str(k):json_value(v) for k,v in finite.describe().to_dict().items()}
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
