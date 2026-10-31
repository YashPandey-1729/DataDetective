import math
import numpy as np
import pandas as pd
from scipy import stats
from backend.tools.profiler import records


def calculate_statistics(df, args, evidence=None):
    op = args.operation
    if op not in {'summary','mode','outliers','correlation','group_comparison','percentage_change'}:
        if not op:raise ValueError('calculate_statistics requires an operation; use statistics_catalog for available operations.')
        from backend.tools.statistical_analysis import calculate_advanced
        return calculate_advanced(df,args,evidence)
    if op == 'percentage_change':
        if args.before is None or args.after is None or not np.isfinite([args.before, args.after]).all() or args.before == 0:
            raise ValueError('Finite before and after values and a nonzero baseline are required.')
        change = (args.after - args.before) / abs(args.before) * 100
        if not np.isfinite(change):
            raise ValueError('Percentage change overflows; choose a meaningful nonzero baseline.')
        return {'before': args.before, 'after': args.after, 'percentage_change': change,
                'note': 'Inputs are supplied values; verify their source separately.'}
    if args.column not in df.columns:
        raise ValueError('Select an existing column.')
    if op == 'mode':
        s = df[args.column]
        if pd.api.types.is_numeric_dtype(s):
            s = s.replace([np.inf, -np.inf], np.nan)
        s = s.dropna()
        if s.empty:
            raise ValueError('No nonmissing finite values for mode.')
        counts = s.value_counts()
        frequency = int(counts.max())
        modes = counts[counts == frequency].index
        try:
            modes = modes.sort_values()
        except TypeError:
            modes = sorted(modes,key=lambda value:(type(value).__name__,str(value)))
        def scalar(value):
            if isinstance(value,np.generic): value=value.item()
            return value.isoformat() if hasattr(value,'isoformat') else value
        rows = [{'mode':scalar(value),'frequency':frequency} for value in modes[:200]]
        note = ('One unique mode.' if len(modes)==1 else 'All observed values occur once; there is no unique mode.'
                if frequency==1 else 'Several values tie for the highest frequency; there is no unique mode.')
        return {'operation':'mode','column':args.column,'count':len(s),'mode':rows[0]['mode'] if len(modes)==1 else None,
                'frequency':frequency,'mode_count':len(modes),'rows':rows,'truncated':len(modes)>200,
                'note':note+' Missing values and numeric infinities are excluded. Rows contain tied modes, capped at two hundred. Values are compared exactly without rounding.'}
    if not pd.api.types.is_numeric_dtype(df[args.column]):
        raise ValueError('Select an existing numeric column.')
    s = df[args.column].replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty:
        raise ValueError('No finite numeric values.')
    if op == 'summary':
        try:
            total = sum(int(value) for value in s) if pd.api.types.is_integer_dtype(s) else math.fsum(float(value) for value in s)
        except OverflowError:
            raise ValueError('Summary overflowed finite precision. Rescale the numeric column before analysis.') from None
        result = {'column': args.column, 'count': len(s), 'sum':total, 'mean': float(s.mean()), 'median': float(s.median()),
                  'std': float(s.std()) if len(s) > 1 else None, 'min': float(s.min()), 'max': float(s.max()),
                  'note':'Finite nonmissing values only. Standard deviation is the sample standard deviation (ddof=1). Use operation mode for modal values and frequencies.'}
        result.update(variance=float(s.var(ddof=1)) if len(s)>1 else None,
            variance_population=float(s.var(ddof=0)),std_population=float(s.std(ddof=0)),
            standard_error=float(s.std(ddof=1)/np.sqrt(len(s))) if len(s)>1 else None,
            range=float(s.max())-float(s.min()),mean_absolute_deviation=float(np.mean(np.abs(s-s.mean()))),
            skewness=float(stats.skew(s,bias=False)) if len(s)>=3 and s.nunique()>1 else None,
            kurtosis=float(stats.kurtosis(s,fisher=True,bias=False)) if len(s)>=4 and s.nunique()>1 else None,
            confidence_margin_95=float(stats.t.ppf(.975,len(s)-1)*s.std(ddof=1)/np.sqrt(len(s))) if len(s)>1 else None,
            geometric_mean=float(stats.gmean(s)) if (s>0).all() else None,
            harmonic_mean=float(stats.hmean(s)) if (s>0).all() else None)
        if any(isinstance(value, float) and not np.isfinite(value) for value in result.values()):
            raise ValueError('Summary overflowed finite precision. Rescale the numeric column before analysis.')
        return result
    if op == 'outliers':
        q1, q3 = s.quantile([.25, .75]); iqr = q3 - q1
        if not np.isfinite([q1 - 1.5 * iqr, q3 + 1.5 * iqr]).all():
            raise ValueError('Outlier thresholds overflowed finite precision. Rescale the numeric column.')
        finite = df[args.column].replace([np.inf, -np.inf], np.nan)
        mask = (finite < q1 - 1.5 * iqr) | (finite > q3 + 1.5 * iqr)
        return {'column': args.column, 'method': '1.5 × IQR; candidates, not confirmed errors', 'count': int(mask.sum()),
                'lower': float(q1 - 1.5 * iqr), 'upper': float(q3 + 1.5 * iqr), 'rows': records(df.loc[mask].head(50))}
    if op == 'correlation':
        if args.other_column not in df.columns or not pd.api.types.is_numeric_dtype(df[args.other_column]):
            raise ValueError('A second numeric column is required.')
        pairs = df[[args.column, args.other_column]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(pairs) < 3 or (pairs.nunique() < 2).any():
            raise ValueError('Correlation requires at least three complete pairs and varying columns.')
        result = stats.pearsonr(pairs.iloc[:, 0], pairs.iloc[:, 1])
        if not np.isfinite([result.statistic, result.pvalue]).all():
            raise ValueError('Correlation is numerically undefined for these values.')
        return {'columns': list(pairs.columns), 'n': len(pairs), 'r': float(result.statistic), 'p_value': float(result.pvalue),
                'assumptions': 'Pearson linear association; p-value assumes independent observations and suitable distribution. Association is not causation.'}
    if op == 'group_comparison':
        if args.group_by not in df.columns:
            raise ValueError('Select an existing group column.')
        clean = df.copy(deep=False).assign(**{args.column: df[args.column].replace([np.inf, -np.inf], np.nan)})
        grouped = clean.groupby(args.group_by, dropna=False)[args.column].agg(['count','sum','mean','median','std'])
        group_column = args.group_by
        if group_column in grouped.columns:
            group_column = args.group_by + '_group'
        grouped.index.name = group_column
        grouped = grouped.reset_index()
        return {'rows': records(grouped.head(200)), 'truncated': len(grouped) > 200, 'group_column': group_column,
                'note': 'Descriptive comparison; no significance test performed. Nonfinite inputs are excluded; undefined or overflowing summaries are null.'}
    raise ValueError('Unsupported statistical operation.')
