"""Shared validation and finite, bounded statistical result handling."""
import math
import warnings
import numpy as np
import pandas as pd

MAX_RESULT_ROWS=200


def numeric_column(df,name,minimum=1):
    if not name or name not in df.columns or not pd.api.types.is_numeric_dtype(df[name]) or pd.api.types.is_bool_dtype(df[name]):
        raise ValueError(f'Select an existing numeric column: {name!r}.')
    values=df[name].to_numpy(dtype=float,na_value=np.nan)
    values=values[np.isfinite(values)]
    if len(values)<minimum:
        raise ValueError(f'{name} requires at least {minimum} finite observations.')
    return values


def numeric_frame(df,columns,minimum=2,complete=True):
    if not columns or len(columns)>31 or len(set(columns))!=len(columns):
        raise ValueError('Choose distinct numeric columns, at most thirty predictors plus a response.')
    for column in columns: numeric_column(df,column,minimum=1)
    frame=df[columns].astype(float).replace([np.inf,-np.inf],np.nan)
    if complete: frame=frame.dropna()
    if len(frame)<minimum: raise ValueError(f'At least {minimum} complete finite observations are required.')
    return frame


def paired_columns(df,left,right,minimum=2):
    frame=numeric_frame(df,[left,right],minimum)
    return frame.iloc[:,0].to_numpy(),frame.iloc[:,1].to_numpy()


def ordered_series(df,column,order_by=None,minimum=2,regular=False):
    if order_by is not None and order_by not in df.columns: raise ValueError('Unknown ordering column.')
    frame=df.sort_values(order_by,kind='stable') if order_by else df
    values=frame[column].to_numpy(dtype=float,na_value=np.nan) if column in frame and pd.api.types.is_numeric_dtype(frame[column]) and not pd.api.types.is_bool_dtype(frame[column]) else None
    if values is None or len(values)<minimum or not np.isfinite(values).all():
        raise ValueError(f'An ordered numeric series needs at least {minimum} observations and no missing/nonfinite values; fill gaps explicitly first.')
    labels=frame[order_by].tolist() if order_by else list(range(len(frame)))
    if order_by:
        order=frame[order_by]
        if order.isna().any() or order.duplicated().any():raise ValueError('Series ordering requires distinct, nonmissing timeline points; aggregate duplicates first.')
        if regular:
            if pd.api.types.is_datetime64_any_dtype(order):
                times=pd.DatetimeIndex(order)
                equally_spaced=len(times)>=3 and pd.infer_freq(times) is not None
                if not equally_spaced:
                    deltas=np.diff(times.asi8);equally_spaced=bool(len(deltas) and np.all(deltas==deltas[0]))
            elif pd.api.types.is_numeric_dtype(order):
                deltas=np.diff(order.to_numpy(dtype=float));equally_spaced=bool(np.isfinite(deltas).all() and np.allclose(deltas,deltas[0]))
            else:equally_spaced=False
            if not equally_spaced:raise ValueError('Forecast/FFT timeline must be a regularly spaced numeric or date column; fill gaps or aggregate explicitly.')
    return values,labels


def clean_result(value):
    if isinstance(value,np.generic): value=value.item()
    if isinstance(value,np.ndarray): value=value.tolist()
    if isinstance(value,dict): return {str(k):clean_result(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [clean_result(v) for v in value]
    if isinstance(value,float) and not math.isfinite(value): return None
    if hasattr(value,'isoformat'): return value.isoformat()
    return value


def bounded_rows(rows):
    return {'rows':clean_result(rows[:MAX_RESULT_ROWS]),'row_count':min(len(rows),MAX_RESULT_ROWS),
            'total_rows':len(rows),'truncated':len(rows)>MAX_RESULT_ROWS}


def safe_call(function,*args,**kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',RuntimeWarning)
        result=function(*args,**kwargs)
    return result


def probability(value,open_interval=False):
    if not np.isfinite(value) or (not 0<value<1 if open_interval else not 0<=value<=1):
        raise ValueError('Probability must be between zero and one'+(' exclusively.' if open_interval else '.'))
    return float(value)


def finite_scalar(value,name='value'):
    if isinstance(value,(bool,str)) or not np.isscalar(value) or not np.isfinite(value):
        raise ValueError(f'{name} must be a finite number.')
    return float(value)


def integer(value,name='value',minimum=0,maximum=1_000_000):
    value=finite_scalar(value,name)
    if value!=int(value) or not minimum<=value<=maximum:
        raise ValueError(f'{name} must be an integer between {minimum} and {maximum}.')
    return int(value)


def excel_quantile(values,p,exclusive=False):
    values=np.sort(np.asarray(values,dtype=float))
    probability(p,exclusive)
    if not len(values): raise ValueError('At least one numeric observation is required.')
    rank=(len(values)+1)*p if exclusive else 1+(len(values)-1)*p
    if not 1<=rank<=len(values): raise ValueError('Exclusive percentile cannot be interpolated for this sample size and probability.')
    lower=int(math.floor(rank))-1
    upper=min(lower+1,len(values)-1)
    return float(values[lower]+(rank-math.floor(rank))*(values[upper]-values[lower]))
