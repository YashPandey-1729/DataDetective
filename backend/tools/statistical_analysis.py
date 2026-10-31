"""Dataset-based equivalents of Excel Analysis ToolPak analysis families."""
import math
import warnings
import numpy as np
import pandas as pd
from scipy import stats
from backend.tools.statistical_common import (numeric_column,numeric_frame,paired_columns,ordered_series,
    bounded_rows,clean_result,safe_call,excel_quantile)
from backend.tools.statistical_catalog import get_operation,validate_parameters


def test_result(statistic,p_value,alpha,**extra):
    if not np.isfinite(statistic) or not np.isfinite(p_value):
        raise ValueError('The test is undefined for these data (often zero variance or insufficient observations).')
    return {'statistic':float(statistic),'p_value':float(p_value),'alpha':alpha,
            'reject_null':bool(p_value<alpha),**extra}


def tail_probability(statistic,distribution,alternative):
    return float(distribution.cdf(statistic) if alternative=='less' else distribution.sf(statistic)
                 if alternative=='greater' else min(1,2*distribution.sf(abs(statistic))))


def regression_fit(y,x,intercept=True,confidence=.95,names=None):
    from statsmodels.regression.linear_model import OLS
    y=np.asarray(y,dtype=float);x=np.asarray(x,dtype=float)
    if x.ndim==1:x=x[:,None]
    design=np.column_stack([np.ones(len(x)),x]) if intercept else x
    if len(y)<=design.shape[1] or x.shape[1]>30 or len(y)>150000:
        raise ValueError('Regression needs more complete observations than coefficients and at most thirty predictors.')
    if not np.isfinite(design).all() or not np.isfinite(y).all() or np.linalg.matrix_rank(design)!=design.shape[1]:
        raise ValueError('Regression requires finite data and a full-rank predictor matrix; remove collinear predictors.')
    fit=OLS(y,design).fit()
    labels=(['intercept'] if intercept else [])+(names or [f'x{i+1}' for i in range(x.shape[1])])
    intervals=fit.conf_int(alpha=1-confidence)
    coefficients=[{'term':name,'coefficient':float(fit.params[i]),'standard_error':float(fit.bse[i]),
        't_statistic':float(fit.tvalues[i]),'p_value':float(fit.pvalues[i]),
        'lower':float(intervals[i,0]),'upper':float(intervals[i,1])} for i,name in enumerate(labels)]
    result={'n':len(y),'r_squared':float(fit.rsquared),'adjusted_r_squared':float(fit.rsquared_adj),
        'standard_error':float(np.sqrt(fit.mse_resid)),'f_statistic':float(fit.fvalue) if fit.df_model else None,
        'f_p_value':float(fit.f_pvalue) if fit.df_model else None,'df_residual':int(fit.df_resid),
        'sse':float(fit.ssr),'ss_regression':float(fit.ess),'ss_total':float(fit.centered_tss if intercept else fit.uncentered_tss),
        'confidence':confidence,'coefficients':coefficients,**bounded_rows(coefficients)}
    return clean_result(result),fit


def ets_forecast(values,steps=10,seasonality=0,confidence=.95):
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    values=np.asarray(values,dtype=float)
    if not 4<=len(values)<=5000 or not np.isfinite(values).all():
        raise ValueError('ETS forecasting requires four to five thousand finite regularly spaced observations.')
    period=seasonality
    if period==1:
        # Explicit heuristic; Excel's proprietary automatic-seasonality selection can differ.
        centered=values-np.polyval(np.polyfit(np.arange(len(values)),values,1),np.arange(len(values)))
        spectrum=np.abs(np.fft.rfft(centered))**2
        index=int(np.argmax(spectrum[1:]))+1 if len(spectrum)>1 else 0
        candidate=int(round(len(values)/index)) if index else 0
        period=candidate if 2<=candidate<=min(365,len(values)//2) and spectrum[index]>1e-10 else 0
    if period and len(values)<2*period: raise ValueError('Seasonal ETS requires at least two complete seasons.')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        fit=ExponentialSmoothing(values,trend='add',seasonal='add' if period else None,
            seasonal_periods=period or None,initialization_method='estimated').fit(optimized=True,minimize_kwargs={'options':{'maxiter':300}})
    forecast=np.asarray(fit.forecast(steps),dtype=float)
    if not np.isfinite(forecast).all(): raise ValueError('ETS fit produced nonfinite forecasts; rescale or review the series.')
    residual=values-fit.fittedvalues
    scale=float(np.sqrt(np.mean(residual**2)))
    # Simulated additive innovation intervals use a fixed seed and report their method.
    innovations=np.random.default_rng(0).choice(residual-residual.mean(),size=(steps,500))
    simulations=np.asarray(fit.simulate(steps,repetitions=500,error='add',random_errors=innovations,random_state=0))
    lower,upper=np.quantile(simulations,[(1-confidence)/2,(1+confidence)/2],axis=1)
    rows=[{'step':i+1,'forecast':forecast[i],'lower':lower[i],'upper':upper[i]} for i in range(steps)]
    nonzero=values!=0;denom=np.abs(values)+np.abs(fit.fittedvalues)
    result={'seasonality':period,'rmse':scale,'mae':float(np.mean(np.abs(residual))),
        'mape':float(np.mean(np.abs(residual[nonzero]/values[nonzero]))*100) if nonzero.any() else None,
        'smape':float(np.mean(np.divide(200*np.abs(residual),denom,out=np.zeros_like(residual),where=denom!=0))),
        'alpha':float(fit.params['smoothing_level']),'beta':float(fit.params['smoothing_trend']),
        'gamma':float(fit.params['smoothing_seasonal']) if period else 0.,
        'confidence':confidence,'method':'Additive Holt-Winters ETS; fixed-seed bootstrap innovation intervals. Excel optimization, automatic seasonality and intervals can differ.',
        **bounded_rows(rows)}
    return clean_result(result)


def calculate_advanced(df,args,evidence=None):
    operation=args.operation;spec=get_operation(operation)
    p=validate_parameters(operation,getattr(args,'parameters',None))
    if operation=='excel':
        from backend.tools.statistical_excel import execute_excel
        return execute_excel(df,p,evidence or [])
    for key in spec.required:
        if getattr(args,key,None) is None: raise ValueError(f'{operation} requires {key}.')
    with np.errstate(all='ignore'):
        result=_calculate(df,args,p)
    if any(isinstance(value,(float,np.floating)) and not np.isfinite(value) for value in result.values()):
        raise ValueError('Statistical calculation overflowed finite precision or is undefined. Rescale or review the input data.')
    result=clean_result(result)
    result.update(operation=operation,source_type='simulation' if operation=='random_generation' else 'dataset')
    for key in ('column','other_column','group_by'):
        value=getattr(args,key,None)
        if value is not None:result[key]=value
    if operation in {'moving_average','exponential_smoothing','forecast','fourier_analysis'}:
        result['ordering']=p.get('order_by') or 'Original dataset row order; equally spaced observations assumed.'
    result['undefined_values']='Null numeric cells indicate undefined statistics or insufficient observations, not zero.'
    if spec.assumptions: result['assumptions']=spec.assumptions
    if 'rows' in result and len(result['rows'])>200: result.update(bounded_rows(result['rows']))
    return result


def _calculate(df,a,p):
    op=a.operation
    if op=='quantiles':
        x=numeric_column(df,a.column)
        rows=[{'probability':q,'value':excel_quantile(x,q,p['method']=='exclusive')} for q in p['probabilities']]
        return {'column':a.column,'n':len(x),'method':p['method'],**bounded_rows(rows)}
    if op=='rank':
        x=numeric_column(df,a.column)
        series=pd.Series(x)
        ranks=series.rank(method=p['ties'],ascending=not p['descending'])
        percent=series.rank(method='min',ascending=True).sub(1).div(max(1,len(x)-1))
        return {'column':a.column,'n':len(x),'note':'Ranks use finite observations in their original order; percentile ranks use the lowest tied rank.',
                **bounded_rows([{'observation':i,'value':value,'rank':ranks.iloc[i],'percentile_rank':percent.iloc[i]} for i,value in enumerate(x)])}
    if op=='histogram':
        x=numeric_column(df,a.column)
        bins=np.asarray(p['bins'] if p['bins'] is not None else np.linspace(x.min(),x.max(),p['bin_count']+1)[1:],dtype=float)
        if not len(bins) or not np.isfinite(bins).all() or (np.diff(bins)<=0).any():
            if x.min()==x.max() and p['bins'] is None: bins=np.array([x[0]])
            else: raise ValueError('Histogram upper bounds must be finite and strictly increasing.')
        counts=np.bincount(np.searchsorted(bins,x,side='left'),minlength=len(bins)+1)
        cumulative=0;rows=[]
        for i,count in enumerate(counts):
            cumulative+=int(count)
            rows.append({'bin':f'≤ {bins[i]:g}' if i<len(bins) else f'> {bins[-1]:g}',
                'upper':float(bins[i]) if i<len(bins) else None,'count':int(count),'cumulative_count':cumulative,
                'cumulative_percent':100*cumulative/len(x)})
        return {'column':a.column,'n':len(x),'bin_semantics':'Upper bounds inclusive; final row is overflow.',**bounded_rows(rows)}
    if op=='confidence_interval':
        x=numeric_column(df,a.column,2);n=len(x);mean=float(np.mean(x))
        if p['method']=='normal':
            if p['sigma'] is None: raise ValueError('Normal confidence intervals require known population sigma; otherwise select t.')
            se=p['sigma']/np.sqrt(n);critical=stats.norm.ppf((1+p['confidence'])/2)
        else: se=np.std(x,ddof=1)/np.sqrt(n);critical=stats.t.ppf((1+p['confidence'])/2,n-1)
        margin=se*critical
        return {'column':a.column,'n':n,'mean':mean,'standard_error':se,'margin':margin,'lower':mean-margin,'upper':mean+margin,**p}
    if op in {'correlation_matrix','covariance_matrix'}:
        frame=numeric_frame(df,p['columns'],3 if op=='correlation_matrix' else 2)
        if op=='correlation_matrix': matrix=frame.corr(method=p['method'])
        else: matrix=frame.cov(ddof=0 if p['population'] else 1)
        label='variable'
        while label in p['columns']:label='_'+label
        return {'n':len(frame),'columns':p['columns'],'matrix_label':label,'matrix_kind':'correlation' if op=='correlation_matrix' else 'covariance','missing_policy':'Complete cases across selected columns.',
                **bounded_rows([{label:name,**matrix.loc[name].to_dict()} for name in matrix.index])}
    if op=='covariance':
        x,y=paired_columns(df,a.column,a.other_column)
        return {'columns':[a.column,a.other_column],'n':len(x),'covariance':np.cov(x,y,ddof=0 if p['population'] else 1)[0,1],**p}
    if op=='t_test':
        if p['method']=='paired':
            x,y=paired_columns(df,a.column,a.other_column)
            test=stats.ttest_1samp(x-y,p['difference'],alternative=p['alternative'])
        else:
            x=numeric_column(df,a.column,2);y=numeric_column(df,a.other_column,2)
            test=stats.ttest_ind(x-p['difference'],y,equal_var=p['method']=='equal_variance',alternative=p['alternative'])
        return test_result(test.statistic,test.pvalue,p['alpha'],df=float(test.df),n1=len(x),n2=len(y),mean1=float(np.mean(x)),mean2=float(np.mean(y)),**{k:v for k,v in p.items() if k!='alpha'})
    if op=='one_sample_test':
        x=numeric_column(df,a.column,2)
        if p['method']=='t':
            test=stats.ttest_1samp(x,p['mean'],alternative=p['alternative']);statistic=test.statistic;pv=test.pvalue
        else:
            if p['sigma'] is None: raise ValueError('One-sample z test requires known sigma.')
            statistic=(np.mean(x)-p['mean'])/(p['sigma']/np.sqrt(len(x)));pv=tail_probability(statistic,stats.norm,p['alternative'])
        return test_result(statistic,pv,p['alpha'],n=len(x),sample_mean=np.mean(x),null_mean=p['mean'],method=p['method'],alternative=p['alternative'])
    if op=='z_test':
        x=numeric_column(df,a.column,2);y=numeric_column(df,a.other_column,2)
        statistic=(np.mean(x)-np.mean(y)-p['difference'])/np.sqrt(p['variance1']/len(x)+p['variance2']/len(y))
        return test_result(statistic,tail_probability(statistic,stats.norm,p['alternative']),p['alpha'],n1=len(x),n2=len(y),**{k:v for k,v in p.items() if k!='alpha'})
    if op=='f_test':
        x=numeric_column(df,a.column,2);y=numeric_column(df,a.other_column,2)
        v1=np.var(x,ddof=1);v2=np.var(y,ddof=1)
        if min(v1,v2)<=0: raise ValueError('Variance tests require positive sample variances.')
        f=v1/v2;distribution=stats.f(len(x)-1,len(y)-1)
        pv=distribution.cdf(f) if p['alternative']=='less' else distribution.sf(f) if p['alternative']=='greater' else min(1,2*min(distribution.cdf(f),distribution.sf(f)))
        return test_result(f,pv,p['alpha'],variance1=v1,variance2=v2,df1=len(x)-1,df2=len(y)-1)
    if op=='chi_square_test':
        if p['method']=='independence':
            if a.column not in df or a.other_column not in df: raise ValueError('Select two existing categorical columns.')
            if a.column==a.other_column or any(not 2<=df[name].nunique()<=100 for name in (a.column,a.other_column)):
                raise ValueError('Choose distinct categorical columns with two to one hundred levels each.')
            table=pd.crosstab(df[a.column],df[a.other_column])
            if min(table.shape)<2 or max(table.shape)>100: raise ValueError('Independence needs at least two and at most one hundred levels per variable.')
            statistic,pv,dof,expected=stats.chi2_contingency(table.to_numpy(),correction=False)
            rows=[{'row_group':str(row),'column_group':str(col),'observed':int(table.iloc[i,j]),'expected':float(expected[i,j])}
                for i,row in enumerate(table.index) for j,col in enumerate(table.columns)]
        else:
            observed,expected=paired_columns(df,a.column,a.other_column)
            if (observed<0).any() or (expected<=0).any() or not np.isclose(observed.sum(),expected.sum()):
                raise ValueError('Observed counts must be nonnegative, expected counts positive, and totals equal.')
            statistic,pv=stats.chisquare(observed,expected);dof=len(observed)-1
            rows=[{'category':i,'observed':v,'expected':expected[i]} for i,v in enumerate(observed)]
        return {**test_result(statistic,pv,p['alpha'],df=int(dof)),
            'warning':'Some expected counts are below five; asymptotic p-values may be unreliable.' if np.any(expected<5) else None,**bounded_rows(rows)}
    if op=='anova_one_way':
        if a.column==a.group_by:raise ValueError('Choose distinct response and group columns.')
        if a.group_by not in df: raise ValueError('Choose an existing group column.')
        numeric_column(df,a.column,2)
        clean=df[[a.column,a.group_by]].replace([np.inf,-np.inf],np.nan).dropna()
        groups=[group[a.column].to_numpy(dtype=float) for _,group in clean.groupby(a.group_by,observed=True)]
        if not 2<=len(groups)<=100 or any(len(group)<2 for group in groups): raise ValueError('One-way ANOVA requires two to one hundred groups, each with at least two observations.')
        n=sum(map(len,groups));grand=np.mean(np.concatenate(groups));between=sum(len(g)*(g.mean()-grand)**2 for g in groups)
        within=sum(np.sum((g-g.mean())**2) for g in groups);df1=len(groups)-1;df2=n-len(groups)
        if within<=0: raise ValueError('ANOVA residual variance must be positive.')
        f=(between/df1)/(within/df2)
        return {**test_result(f,stats.f.sf(f,df1,df2),p['alpha'],df_between=df1,df_within=df2),**bounded_rows([
            {'source':'between','ss':between,'df':df1,'ms':between/df1},
            {'source':'within','ss':within,'df':df2,'ms':within/df2},{'source':'total','ss':between+within,'df':n-1,'ms':None}])}
    if op=='anova_two_way': return two_way_anova(df,a.column,a.group_by,p['factor2'],p['replication'],p['alpha'])
    if op=='regression':
        frame=numeric_frame(df,[a.column,*p['predictors']],3)
        y=frame[a.column].to_numpy();x=frame[p['predictors']].to_numpy()
        if p['exponential']:
            if (y<=0).any(): raise ValueError('Exponential regression requires positive response values.')
            y=np.log(y)
        result,fit=regression_fit(y,x,p['intercept'],p['confidence'],p['predictors'])
        result['response_scale']='log' if p['exponential'] else 'original'
        result['residuals']=clean_result([{'observation':i,'actual':v,'fitted':fit.fittedvalues[i],'residual':fit.resid[i]} for i,v in enumerate(y[:200])])
        if p['predict_at'] is not None:
            new=np.asarray(p['predict_at'],dtype=float)
            if new.ndim!=2 or new.shape[1]!=x.shape[1] or not np.isfinite(new).all():raise ValueError('Prediction rows must match the predictor count and contain finite numbers.')
            pred=fit.predict(np.column_stack([np.ones(len(new)),new]) if p['intercept'] else new)
            result['predictions']=clean_result([{'observation':i,'prediction':np.exp(v) if p['exponential'] else v} for i,v in enumerate(pred)])
        return result
    if op in {'moving_average','exponential_smoothing','forecast','fourier_analysis'}:
        x,labels=ordered_series(df,a.column,p.get('order_by'),minimum=4 if op=='forecast' else 2,regular=op in {'forecast','fourier_analysis'})
        if op=='moving_average':
            if p['window']>len(x): raise ValueError('Moving-average window exceeds series length.')
            rolling=pd.Series(x).rolling(p['window']).mean()
            rows=[{'period':labels[i],'actual':v,'moving_average':rolling.iloc[i],
                'one_step_forecast':rolling.iloc[i-1] if i else None} for i,v in enumerate(x)]
            return {'column':a.column,'window':p['window'],'next_forecast':rolling.iloc[-1],**bounded_rows(rows)}
        if op=='exponential_smoothing':
            level=float(x[0]);rows=[]
            for i,value in enumerate(x):
                rows.append({'period':labels[i],'actual':value,'forecast':level if i else None})
                level=p['alpha']*value+(1-p['alpha'])*level
            return {'column':a.column,'alpha':p['alpha'],'excel_damping_factor':1-p['alpha'],'next_forecast':level,**bounded_rows(rows)}
        if op=='forecast':return ets_forecast(x,p['steps'],p['seasonality'],p['confidence'])
        if len(x)>65536: raise ValueError('Fourier analysis is limited to 65,536 observations.')
        if p['imaginary_column']:
            imaginary,_=ordered_series(df,p['imaginary_column'],p['order_by'],2,regular=True)
            x=x+1j*imaginary
        transform=np.fft.ifft(x) if p['inverse'] else np.fft.fft(x)
        if not np.isfinite(transform).all():raise ValueError('Fourier transform overflowed finite precision. Rescale the series.')
        return {'n':len(x),'inverse':p['inverse'],**bounded_rows([{'index':i,'real':v.real,'imaginary':v.imag,'magnitude':abs(v),'phase':np.angle(v)} for i,v in enumerate(transform)])}
    if op=='sampling':
        columns=p['columns'] or list(df.columns)
        if any(name not in df for name in columns): raise ValueError('Unknown sampling column.')
        if p['method']=='periodic':sample=df.iloc[p['period']-1::p['period']][columns].head(p['size'])
        else:
            if not p['replace'] and p['size']>len(df): raise ValueError('Sample size exceeds population without replacement.')
            sample=df[columns].sample(n=p['size'],replace=p['replace'],random_state=p['seed'])
        return {'population':len(df),'sample_size':len(sample),'method':p['method'],'seed':p['seed'],**bounded_rows(sample.to_dict(orient='records'))}
    if op=='random_generation':
        rng=np.random.default_rng(p['seed']);size=p['size'];kind=p['distribution']
        if kind=='normal':values=rng.normal(p['mean'],p['std'],size)
        elif kind=='uniform':
            if p['low']>=p['high']:raise ValueError('Uniform lower bound must be below upper bound.')
            values=rng.uniform(p['low'],p['high'],size)
        elif kind=='bernoulli':values=rng.binomial(1,p['probability'],size)
        elif kind=='binomial':values=rng.binomial(p['trials'],p['probability'],size)
        elif kind=='poisson':values=rng.poisson(p['rate'],size)
        elif kind=='discrete':
            if not p['values'] or not p['probabilities'] or len(p['values'])!=len(p['probabilities']) or min(p['probabilities'])<0 or not np.isclose(sum(p['probabilities']),1):
                raise ValueError('Discrete values/probabilities must match, be nonnegative and sum to one.')
            values=rng.choice(p['values'],size=size,p=p['probabilities'])
        else:values=p['low']+p['step']*(np.arange(size)//p['repeats'])
        return {'distribution':kind,'seed':p['seed'],'note':'Generated simulation, not observed uploaded data.',**bounded_rows([{'index':i,'value':v} for i,v in enumerate(values)])}
    if op=='normality_test':
        x=numeric_column(df,a.column,3)
        if np.ptp(x)==0:raise ValueError('Normality diagnostics require varying observations.')
        if p['method']=='shapiro' and len(x)>5000:raise ValueError('Shapiro-Wilk is limited to 5000 observations; choose jarque_bera for larger samples.')
        test=stats.shapiro(x) if p['method']=='shapiro' else stats.jarque_bera(x)
        return test_result(test.statistic,test.pvalue,p['alpha'],n=len(x),method=p['method'],
            note='Failure to reject normality does not prove normality; review plots, independence and sample size.')
    raise ValueError('Statistical operation is not implemented.')


def two_way_anova(df,column,factor1,factor2,replication=True,alpha=.05):
    if len({column,factor1,factor2})!=3 or any(name not in df for name in [column,factor1,factor2]):
        raise ValueError('Choose a numeric response and two distinct factor columns.')
    numeric_column(df,column,4)
    frame=df[[column,factor1,factor2]].replace([np.inf,-np.inf],np.nan).dropna()
    a=frame[factor1].unique();b=frame[factor2].unique()
    if min(len(a),len(b))<2 or len(a)*len(b)>1000:raise ValueError('Two-way ANOVA needs at least two levels per factor and at most 1000 cells.')
    cells=[[frame.loc[(frame[factor1]==left)&(frame[factor2]==right),column].to_numpy(dtype=float) for right in b] for left in a]
    counts={len(cell) for row in cells for cell in row}
    if len(counts)!=1 or min(counts)<(2 if replication else 1) or (not replication and counts!={1}):
        raise ValueError('Excel-style two-factor ANOVA requires complete balanced cells: equal replication >=2, or exactly one observation without replication.')
    n=next(iter(counts));cube=np.asarray(cells);grand=cube.mean();am=cube.mean(axis=(1,2));bm=cube.mean(axis=(0,2));cm=cube.mean(axis=2)
    ssa=len(b)*n*np.sum((am-grand)**2);ssb=len(a)*n*np.sum((bm-grand)**2)
    ssi=n*np.sum((cm-am[:,None]-bm[None,:]+grand)**2);sse=np.sum((cube-cm[:,:,None])**2)
    dfa=len(a)-1;dfb=len(b)-1;dfi=dfa*dfb;dfe=len(a)*len(b)*(n-1) if replication else dfi
    error=sse if replication else ssi
    if error<=0 or dfe<=0:raise ValueError('ANOVA needs positive residual variance.')
    mse=error/dfe
    rows=[{'source':factor1,'ss':ssa,'df':dfa,'ms':ssa/dfa,'f_statistic':ssa/dfa/mse,'p_value':stats.f.sf(ssa/dfa/mse,dfa,dfe)},
          {'source':factor2,'ss':ssb,'df':dfb,'ms':ssb/dfb,'f_statistic':ssb/dfb/mse,'p_value':stats.f.sf(ssb/dfb/mse,dfb,dfe)}]
    if replication:rows.append({'source':'interaction','ss':ssi,'df':dfi,'ms':ssi/dfi,'f_statistic':ssi/dfi/mse,'p_value':stats.f.sf(ssi/dfi/mse,dfi,dfe)})
    rows.extend([{'source':'error','ss':error,'df':dfe,'ms':mse},{'source':'total','ss':np.sum((cube-grand)**2),'df':cube.size-1,'ms':None}])
    return {'replication':replication,'replicates_per_cell':n,'alpha':alpha,'balanced':True,**bounded_rows(rows)}
