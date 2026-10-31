"""Named Excel statistical functions over dataset ranges and validated parameters.

This is a statistical API, not a formula evaluator: no executable expressions,
workbook links, macros, filesystem references or arbitrary function imports.
"""
import math
import re
import fnmatch
from dataclasses import dataclass
from typing import Any,Annotated,Literal
import numpy as np
import pandas as pd
from pydantic import Field,create_model
from scipy import stats,special
from backend.tools.statistical_catalog import Parameters
from backend.tools.statistical_common import (bounded_rows,clean_result,finite_scalar,integer,
    probability,excel_quantile)


class ColumnReference(Parameters):
    column:str=Field(min_length=1,max_length=120)

class ColumnsReference(Parameters):
    columns:list[str]=Field(min_length=1,max_length=30)

class EvidenceReference(Parameters):
    evidence_id:str
    row:int|None=Field(default=None,ge=0,le=199)
    field:str

Scalar=float|EvidenceReference
Data=ColumnReference|Annotated[list[float|str|bool|None],Field(max_length=2000)]
Matrix=ColumnsReference|Annotated[list[list[float]],Field(max_length=2000)]

class Criterion(Parameters):
    range:Data
    criterion:float|str|bool


@dataclass(frozen=True)
class Function:
    name:str
    parameters:type[Parameters]
    description:str


FUNCTIONS={}
ALIASES={}


def register(names,description,**fields):
    for name in names.split():
        parameters=create_model('Excel_'+name.replace('.','_'),__base__=Parameters,**fields)
        FUNCTIONS[name]=Function(name,parameters,description)


register('AVEDEV AVERAGE AVERAGEA COUNT COUNTA COUNTBLANK DEVSQ GEOMEAN HARMEAN KURT MAX MAXA MEDIAN MIN MINA MODE.MULT MODE.SNGL SKEW SKEW.P STDEV.P STDEV.S STDEVA STDEVPA VAR.P VAR.S VARA VARPA SUM SUMSQ PRODUCT',
    'Aggregate a dataset column or supplied values; sample/population and text/logical handling follow the named function.',values=(Data,...))
register('LARGE SMALL','Return the kth ordered numeric value.',values=(Data,...),k=(int,Field(ge=1)))
register('TRIMMEAN','Mean after symmetrically excluding an even count of extreme observations.',values=(Data,...),percent=(float,Field(ge=0,lt=1)))
register('PERCENTILE.INC PERCENTILE.EXC','Inclusive or exclusive interpolated percentile.',values=(Data,...),k=(Scalar,...))
register('QUARTILE.INC QUARTILE.EXC','Inclusive or exclusive quartile.',values=(Data,...),quart=(int,...))
register('PERCENTRANK.INC PERCENTRANK.EXC','Interpolated percentile rank; first rank for exact ties, decimal truncation by significance.',values=(Data,...),x=(Scalar,...),significance=(int,Field(default=3,ge=1,le=15)))
register('RANK.EQ RANK.AVG','Ordinal rank, using lowest or average tied rank.',values=(Data,...),number=(Scalar,...),order=(int,0))
register('FREQUENCY','Upper-inclusive bin frequencies plus the final overflow bin.',values=(Data,...),bins=(Data,...))
register('COUNTIF','Conditional count with comparison/wildcard criteria.',range=(Data,...),criterion=(float|str|bool,...))
register('AVERAGEIF SUMIF','Conditional aggregation with comparison/wildcard criteria.',range=(Data,...),criterion=(float|str|bool,...),result_range=(Data|None,None))
register('COUNTIFS','Multiple AND criteria over aligned ranges.',criteria=(list[Criterion],Field(min_length=1,max_length=20)))
register('AVERAGEIFS MAXIFS MINIFS SUMIFS','Multiple AND criteria over aligned ranges.',criteria=(list[Criterion],Field(min_length=1,max_length=20)),values=(Data,...))
register('CORREL PEARSON COVARIANCE.P COVARIANCE.S RSQ','Paired relationship statistic; incomplete pairs are excluded.',array1=(Data,...),array2=(Data,...))
register('INTERCEPT SLOPE STEYX','Simple least-squares regression statistic.',known_y=(Data,...),known_x=(Data,...))
register('LINEST LOGEST','Linear or log-linear multiple least-squares fit, with coefficient inference and model statistics.',known_y=(Data,...),known_x=(Data|Matrix|None,None),const=(bool,True),stats=(bool,True))
register('TREND GROWTH','Linear or exponential least-squares predictions.',known_y=(Data,...),known_x=(Data|Matrix|None,None),new_x=(Data|Matrix|None,None),const=(bool,True))
register('FORECAST FORECAST.LINEAR','Simple linear-regression forecast at x.',x=(Scalar,...),known_y=(Data,...),known_x=(Data,...))
register('STANDARDIZE','Standard normal score (x-mean)/standard deviation.',x=(Scalar,...),mean=(Scalar,...),standard_dev=(Scalar,...))
register('CONFIDENCE.NORM CONFIDENCE.T','Confidence-interval margin for a population mean.',alpha=(float,Field(gt=0,lt=1)),standard_dev=(float,Field(gt=0)),size=(int,Field(ge=1)))
register('FISHER FISHERINV GAMMA GAMMALN GAMMALN.PRECISE GAUSS PHI','Named mathematical/statistical transformation.',x=(Scalar,...))
register('PERMUT PERMUTATIONA','Number of ordered selections without/with repetition.',number=(int,Field(ge=0,le=1000000)),number_chosen=(int,Field(ge=0,le=1000000)))
register('PROB','Probability mass within an inclusive range.',values=(Data,...),probabilities=(Data,...),lower_limit=(Scalar,...),upper_limit=(Scalar|None,None))
register('T.TEST','Paired, pooled or Welch test p-value; type 1/2/3 and tails 1/2.',array1=(Data,...),array2=(Data,...),tails=(Literal[1,2],2),type=(Literal[1,2,3],3))
register('F.TEST','Two-sided variance-ratio test p-value.',array1=(Data,...),array2=(Data,...))
register('Z.TEST','One-tailed mean z-test; uses sample sigma when not provided.',values=(Data,...),x=(Scalar,...),sigma=(float|None,Field(default=None,gt=0)))
register('CHISQ.TEST','Chi-square observed/expected counts test; df follows the supplied vector or matrix shape.',actual=(Data|Matrix,...),expected=(Data|Matrix,...))

# Distribution families use Excel's shape/scale and tail conventions.
register('NORM.DIST','Normal cumulative probability or density.',x=(Scalar,...),mean=(Scalar,...),standard_dev=(Scalar,...),cumulative=(bool,True))
register('NORM.INV','Normal quantile.',probability=(float,Field(gt=0,lt=1)),mean=(Scalar,...),standard_dev=(Scalar,...))
register('NORM.S.DIST','Standard normal cumulative probability or density.',x=(Scalar,...),cumulative=(bool,True))
register('NORM.S.INV','Standard normal quantile.',probability=(float,Field(gt=0,lt=1)))
register('BETA.DIST','Scaled beta cumulative probability or density.',x=(Scalar,...),alpha=(float,Field(gt=0)),beta=(float,Field(gt=0)),cumulative=(bool,True),lower=(float,0),upper=(float,1))
register('BETA.INV','Scaled beta quantile.',probability=(float,Field(ge=0,le=1)),alpha=(float,Field(gt=0)),beta=(float,Field(gt=0)),lower=(float,0),upper=(float,1))
register('BINOM.DIST','Binomial mass or cumulative probability.',number_s=(int,Field(ge=0)),trials=(int,Field(ge=0,le=1000000)),probability_s=(float,Field(ge=0,le=1)),cumulative=(bool,True))
register('BINOM.DIST.RANGE','Inclusive binomial success-count interval probability.',trials=(int,Field(ge=0,le=1000000)),probability_s=(float,Field(ge=0,le=1)),number_s=(int,Field(ge=0)),number_s2=(int|None,Field(default=None,ge=0)))
register('BINOM.INV','Smallest success count whose cumulative probability reaches alpha.',trials=(int,Field(ge=0,le=1000000)),probability_s=(float,Field(ge=0,le=1)),alpha=(float,Field(ge=0,le=1)))
register('CHISQ.DIST CHISQ.DIST.RT','Chi-square density/CDF or right tail.',x=(float,Field(ge=0)),degrees_freedom=(float,Field(gt=0)),cumulative=(bool,True))
register('CHISQ.INV CHISQ.INV.RT','Chi-square left/right-tail inverse.',probability=(float,Field(ge=0,le=1)),degrees_freedom=(float,Field(gt=0)))
register('F.DIST F.DIST.RT','F density/CDF or right tail.',x=(float,Field(ge=0)),degrees_freedom1=(float,Field(gt=0)),degrees_freedom2=(float,Field(gt=0)),cumulative=(bool,True))
register('F.INV F.INV.RT','F left/right-tail inverse.',probability=(float,Field(ge=0,le=1)),degrees_freedom1=(float,Field(gt=0)),degrees_freedom2=(float,Field(gt=0)))
register('T.DIST T.DIST.RT T.DIST.2T','Student t density/CDF or right/two-sided tail.',x=(Scalar,...),degrees_freedom=(float,Field(gt=0)),cumulative=(bool,True))
register('T.INV T.INV.2T','Student t quantile or two-sided critical value.',probability=(float,Field(gt=0,le=1)),degrees_freedom=(float,Field(gt=0)))
register('EXPON.DIST','Exponential CDF/density with rate lambda.',x=(float,Field(ge=0)),rate=(float,Field(gt=0)),cumulative=(bool,True))
register('GAMMA.DIST','Gamma CDF/density with shape alpha and scale beta.',x=(float,Field(ge=0)),alpha=(float,Field(gt=0)),beta=(float,Field(gt=0)),cumulative=(bool,True))
register('GAMMA.INV','Gamma quantile with shape alpha and scale beta.',probability=(float,Field(ge=0,lt=1)),alpha=(float,Field(gt=0)),beta=(float,Field(gt=0)))
register('LOGNORM.DIST','Lognormal CDF/density using the mean/std of log values.',x=(float,Field(gt=0)),mean=(Scalar,...),standard_dev=(Scalar,...),cumulative=(bool,True))
register('LOGNORM.INV','Lognormal quantile using the mean/std of log values.',probability=(float,Field(gt=0,lt=1)),mean=(Scalar,...),standard_dev=(Scalar,...))
register('WEIBULL.DIST','Weibull CDF/density, shape alpha and scale beta.',x=(float,Field(ge=0)),alpha=(float,Field(gt=0)),beta=(float,Field(gt=0)),cumulative=(bool,True))
register('POISSON.DIST','Poisson probability mass or CDF.',x=(int,Field(ge=0,le=1000000)),mean=(float,Field(gt=0)),cumulative=(bool,True))
register('NEGBINOM.DIST','Negative-binomial failures before number_s successes.',number_f=(int,Field(ge=0,le=1000000)),number_s=(int,Field(ge=1,le=1000000)),probability_s=(float,Field(gt=0,le=1)),cumulative=(bool,True))
register('HYPGEOM.DIST','Hypergeometric success probability without replacement.',sample_s=(int,Field(ge=0)),number_sample=(int,Field(ge=0,le=1000000)),population_s=(int,Field(ge=0)),number_pop=(int,Field(ge=1,le=1000000)),cumulative=(bool,True))
register('FORECAST.ETS FORECAST.ETS.CONFINT','Additive ETS forecast or interval radius. Model optimization/automatic seasonality can differ from Excel.',target=(Scalar,...),values=(Data,...),timeline=(Data,...),seasonality=(int,Field(default=1,ge=0,le=365)),confidence=(float,Field(default=.95,gt=0,lt=1)),data_completion=(Literal[0,1],1),aggregation=(Literal['mean','sum','min','max','median','count'],'mean'))
register('FORECAST.ETS.SEASONALITY','Detect season length using the documented spectral heuristic, which can differ from Excel.',values=(Data,...),timeline=(Data,...),data_completion=(Literal[0,1],1),aggregation=(Literal['mean','sum','min','max','median','count'],'mean'))
register('FORECAST.ETS.STAT','ETS alpha/beta/gamma, MASE, SMAPE, MAE, RMSE or timeline step statistic.',values=(Data,...),timeline=(Data,...),statistic_type=(int,Field(ge=1,le=8)),seasonality=(int,Field(default=1,ge=0,le=365)),data_completion=(Literal[0,1],1),aggregation=(Literal['mean','sum','min','max','median','count'],'mean'))

ALIASES.update({'MODE':'MODE.SNGL','STDEV':'STDEV.S','STDEVP':'STDEV.P','VAR':'VAR.S','VARP':'VAR.P',
    'PERCENTILE':'PERCENTILE.INC','PERCENTRANK':'PERCENTRANK.INC','QUARTILE':'QUARTILE.INC','RANK':'RANK.EQ',
    'COVAR':'COVARIANCE.P','CONFIDENCE':'CONFIDENCE.NORM','BETADIST':'BETA.DIST','BETAINV':'BETA.INV',
    'BINOMDIST':'BINOM.DIST','CHIDIST':'CHISQ.DIST.RT','CHIINV':'CHISQ.INV.RT','CHITEST':'CHISQ.TEST',
    'EXPONDIST':'EXPON.DIST','FDIST':'F.DIST.RT','FINV':'F.INV.RT','FTEST':'F.TEST',
    'GAMMADIST':'GAMMA.DIST','GAMMAINV':'GAMMA.INV','HYPGEOMDIST':'HYPGEOM.DIST',
    'LOGINV':'LOGNORM.INV','LOGNORMDIST':'LOGNORM.DIST','NEGBINOMDIST':'NEGBINOM.DIST',
    'NORMDIST':'NORM.DIST','NORMINV':'NORM.INV','NORMSDIST':'NORM.S.DIST','NORMSINV':'NORM.S.INV',
    'POISSON':'POISSON.DIST','TINV':'T.INV.2T','TTEST':'T.TEST','WEIBULL':'WEIBULL.DIST','ZTEST':'Z.TEST'})


def function_schema(name):
    canonical=ALIASES.get(name.upper(),name.upper())
    if canonical not in FUNCTIONS: raise ValueError('Unknown Excel function; use statistics_catalog.')
    schema=FUNCTIONS[canonical].parameters.model_json_schema()
    schema['properties']['function']={'type':'string','const':canonical}
    schema.setdefault('required',[]).insert(0,'function')
    return schema


def describe_function(name):
    canonical=ALIASES.get(name.upper(),name.upper())
    spec=FUNCTIONS[canonical]
    return {'kind':'excel_function','operation':'excel','function':canonical,'description':spec.description,
        'parameters_schema':function_schema(canonical),
        'range_syntax':{'column':'actual_dataset_column'},
        'evidence_syntax':{'evidence_id':'E02','row':None,'field':'mean'},
        'note':'Use named parameters, not formula text. Imported columns use range/array semantics. Excel cell errors and workbook references are not evaluated.'}


def validate_excel_parameters(parameters):
    raw=dict(parameters);name=raw.pop('function','')
    if not isinstance(name,str):raise ValueError('Excel function name must be text.')
    name=ALIASES.get(name.upper(),name.upper())
    if name not in FUNCTIONS: raise ValueError('Supply a supported Excel function name; use statistics_catalog to discover it.')
    try:return {'function':name,**FUNCTIONS[name].parameters.model_validate(raw).model_dump(exclude_none=True)}
    except ValueError as exc:raise ValueError(f'Invalid parameters for {name}: '+str(exc)[:600]) from None


def execute_excel(df,parameters,evidence):
    p=dict(parameters);name=p.pop('function');columns=set();references=[];dataset_reference=False
    def resolve(value):
        nonlocal dataset_reference
        if isinstance(value,dict) and set(value)=={'column'}:
            column=value['column']
            if column not in df:raise ValueError(f'Unknown input column: {column}.')
            columns.add(column);dataset_reference=True;return df[column].to_numpy(dtype=object,na_value=None)
        if isinstance(value,dict) and set(value)=={'columns'}:
            if any(column not in df for column in value['columns']):raise ValueError('Unknown matrix input column.')
            columns.update(value['columns']);dataset_reference=True;return df[value['columns']].to_numpy(dtype=object,na_value=None)
        if isinstance(value,dict) and 'evidence_id' in value:
            source=next((item for item in evidence if item['id']==value['evidence_id'] and item['tool'] in {'execute_sql','calculate_statistics'}),None)
            if not source:raise ValueError('Scalar evidence reference must identify retained analytical evidence.')
            row=value.get('row');result=source['result']
            if row is not None:
                if row>=len(result.get('rows',[])):raise ValueError('Evidence row is unavailable.')
                result=result['rows'][row]
            elif source['tool']=='execute_sql':raise ValueError('SQL evidence inputs require a row index.')
            if value['field'] not in result:raise ValueError('Evidence input field is unavailable.')
            references.append(value['evidence_id'])
            dataset_reference=dataset_reference or source['result'].get('source_type','dataset')=='dataset'
            return result[value['field']]
        if isinstance(value,dict):return {key:resolve(item) for key,item in value.items()}
        if isinstance(value,list):return [resolve(item) for item in value]
        return value
    resolved={key:resolve(value) for key,value in p.items()}
    with np.errstate(all='ignore'):
        result=_execute(name,resolved)
    if isinstance(result,dict):output=result
    elif np.isscalar(result):
        result=finite_scalar(result,'calculated result')
        output={'value':result}
    else:
        array=np.asarray(result,dtype=float)
        if not np.isfinite(array).all():raise ValueError('The function result is undefined or exceeds finite precision.')
        output=bounded_rows([{'index':i,'value':value} for i,value in enumerate(array.ravel())])
    return clean_result({**output,'function':name,'operation':'excel','source_type':'dataset' if dataset_reference else 'parameters',
        'input_columns':sorted(columns),'input_evidence_ids':sorted(set(references)),
        'note':'Statistical result from the named function and validated inputs. Literal parameters are supplied assumptions; workbook formula/cell-error semantics are not emulated.'})


def _missing(value):return value is None or bool(pd.isna(value))


def _numbers(values,include_text=False,minimum=1):
    raw=np.asarray(values,dtype=object).ravel();out=[]
    for value in raw:
        if _missing(value):continue
        if isinstance(value,(bool,np.bool_)):
            if include_text:out.append(float(value))
        elif isinstance(value,(int,float,np.number)):
            if np.isfinite(value):out.append(float(value))
        elif include_text:out.append(0.)
    if len(out)<minimum:raise ValueError(f'This function requires at least {minimum} finite numeric observations.')
    return np.asarray(out,dtype=float)


def _paired(left,right,minimum=2):
    left=np.asarray(left,dtype=object).ravel();right=np.asarray(right,dtype=object).ravel()
    if len(left)!=len(right):raise ValueError('Paired ranges must have equal lengths.')
    pairs=[]
    for a,b in zip(left,right):
        if all(isinstance(value,(int,float,np.number)) and not isinstance(value,(bool,np.bool_)) and np.isfinite(value) for value in (a,b)):
            pairs.append((float(a),float(b)))
    if len(pairs)<minimum:raise ValueError(f'At least {minimum} complete numeric pairs are required.')
    return np.asarray(pairs).T


def _criterion(raw,criterion):
    raw=np.asarray(raw,dtype=object).ravel()
    text=str(criterion);match=re.match(r'^(<=|>=|<>|=|<|>)(.*)$',text)
    op,target=match.groups() if match else ('=',text)
    if target=='':
        blank=np.array([_missing(value) or value=='' for value in raw])
        return ~blank if op=='<>' else blank if op=='=' else np.zeros(len(raw),dtype=bool)
    if isinstance(criterion,bool):return np.array([isinstance(value,(bool,np.bool_)) and value==criterion for value in raw])
    try:number=float(target)
    except ValueError:number=None
    if number is not None and np.isfinite(number):
        numeric=pd.to_numeric(pd.Series(raw),errors='coerce').to_numpy(dtype=float)
        compare={'=':np.equal,'<>':np.not_equal,'<':np.less,'>':np.greater,'<=':np.less_equal,'>=':np.greater_equal}[op]
        return np.isfinite(numeric)&compare(numeric,number)
    pattern='';i=0
    while i<len(target):
        char=target[i]
        escaped=char=='~' and i+1<len(target)
        if escaped:i+=1;char=target[i]
        if char=='[':pattern+='[[]'
        elif char==']':pattern+='[]]'
        elif escaped and char in '*?':pattern+='['+char+']'
        else:pattern+=char
        i+=1
    if op in {'=','<>'}:
        # fnmatch compiles star patterns with atomic groups, avoiding exponential
        # regex backtracking on user-supplied wildcard criteria.
        expression=re.compile(fnmatch.translate(pattern),flags=re.I|re.S)
        mask=np.array([False if _missing(value) else bool(expression.fullmatch(str(value))) for value in raw])
        return ~mask if op=='<>' else mask
    compare={'<':lambda a,b:a<b,'>':lambda a,b:a>b,'<=':lambda a,b:a<=b,'>=':lambda a,b:a>=b}[op]
    return np.array([False if _missing(value) else compare(str(value).casefold(),target.casefold()) for value in raw])


def _execute(name,p):
    if 'values' in p and name in {'AVEDEV','AVERAGE','AVERAGEA','COUNT','COUNTA','COUNTBLANK','DEVSQ','GEOMEAN','HARMEAN','KURT','MAX','MAXA','MEDIAN','MIN','MINA','MODE.MULT','MODE.SNGL','SKEW','SKEW.P','STDEV.P','STDEV.S','STDEVA','STDEVPA','VAR.P','VAR.S','VARA','VARPA','SUM','SUMSQ','PRODUCT','LARGE','SMALL','TRIMMEAN','PERCENTILE.INC','PERCENTILE.EXC','QUARTILE.INC','QUARTILE.EXC','PERCENTRANK.INC','PERCENTRANK.EXC','RANK.EQ','RANK.AVG','FREQUENCY'}:
        raw=np.asarray(p['values'],dtype=object).ravel()
        if name=='COUNTA':return sum(not _missing(value) for value in raw)
        if name=='COUNTBLANK':return sum(_missing(value) or value=='' for value in raw)
        x=_numbers(raw,name in {'AVERAGEA','MAXA','MINA','STDEVA','STDEVPA','VARA','VARPA'},minimum=0)
        if name=='COUNT':return len(x)
        if name=='FREQUENCY':
            bins=_numbers(p['bins'],minimum=0)
            if (np.diff(bins)<0).any():raise ValueError('Frequency bins must be ordered by ascending upper bound.')
            return np.bincount(np.searchsorted(bins,x,side='left'),minlength=len(bins)+1)
        if not len(x):
            if name in {'MIN','MINA','MAX','MAXA','SUM','SUMSQ','PRODUCT'}:return 0
            raise ValueError('The range contains no numeric observations.')
        if name in {'AVERAGE','AVERAGEA'}:return np.mean(x)
        if name=='SUM':return math.fsum(x)
        if name=='SUMSQ':return np.dot(x,x)
        if name=='PRODUCT':return np.prod(x)
        if name=='MEDIAN':return np.median(x)
        if name in {'MIN','MINA'}:return np.min(x)
        if name in {'MAX','MAXA'}:return np.max(x)
        if name=='AVEDEV':return np.mean(np.abs(x-np.mean(x)))
        if name=='DEVSQ':return np.dot(x-x.mean(),x-x.mean())
        if name in {'GEOMEAN','HARMEAN'}:
            if (x<=0).any():raise ValueError('Geometric/harmonic means require strictly positive observations.')
            return stats.gmean(x) if name=='GEOMEAN' else stats.hmean(x)
        if name.startswith(('STDEV','VAR')):
            population=name in {'STDEV.P','STDEVPA','VAR.P','VARPA'}
            if not population and len(x)<2:raise ValueError('Sample variance/std requires at least two observations.')
            variance=np.var(x,ddof=0 if population else 1)
            return np.sqrt(variance) if name.startswith('STDEV') else variance
        if name in {'SKEW','SKEW.P','KURT'}:
            if len(x)<(4 if name=='KURT' else 3) or np.ptp(x)==0:
                raise ValueError('Skewness/kurtosis needs enough varying observations.')
            return stats.kurtosis(x,fisher=True,bias=False) if name=='KURT' else stats.skew(x,bias=name=='SKEW.P')
        if name.startswith('MODE.'):
            values,counts=np.unique(x,return_counts=True)
            if counts.max()<2:raise ValueError('No repeated value: Excel MODE has no modal result.')
            modes=values[counts==counts.max()]
            return modes if name=='MODE.MULT' else modes[0]
        if name in {'LARGE','SMALL'}:
            k=p['k']
            if k>len(x):raise ValueError('k exceeds the numeric sample size.')
            return np.sort(x)[-k if name=='LARGE' else k-1]
        if name=='TRIMMEAN':
            trim=int(len(x)*p['percent']/2);ordered=np.sort(x)
            return np.mean(ordered[trim:len(x)-trim])
        if name.startswith(('PERCENTILE.','QUARTILE.')):
            q=p['k'] if 'k' in p else p['quart']/4
            return excel_quantile(x,q,name.endswith('.EXC'))
        if name.startswith('PERCENTRANK.'):
            target=finite_scalar(p['x']);ordered=np.sort(x);n=len(x)
            if n<2 or target<ordered[0] or target>ordered[-1]:raise ValueError('Percent rank needs two observations and x within the observed range.')
            position=np.searchsorted(ordered,target,side='left')
            rank=float(position) if ordered[position]==target else position-1+(target-ordered[position-1])/(ordered[position]-ordered[position-1])
            result=(rank+1)/(n+1) if name.endswith('.EXC') else rank/(n-1)
            factor=10**p['significance'];return math.floor(result*factor+1e-12)/factor
        if name.startswith('RANK.'):
            target=finite_scalar(p['number']);ties=int(np.sum(x==target))
            if not ties:raise ValueError('Rank number must occur in the reference range.')
            rank=1+np.sum(x<target if p['order'] else x>target)
            return rank+(ties-1)/2 if name=='RANK.AVG' else rank
    if name.endswith('IF') or name.endswith('IFS'):
        criteria=p.get('criteria') or [{'range':p['range'],'criterion':p['criterion']}]
        arrays=[np.asarray(item['range'],dtype=object).ravel() for item in criteria]
        if len({len(array) for array in arrays})!=1:raise ValueError('All conditional ranges must have equal lengths.')
        mask=np.logical_and.reduce([_criterion(array,item['criterion']) for array,item in zip(arrays,criteria)])
        if name.startswith('COUNT'):return int(mask.sum())
        values=p.get('values',p.get('result_range',arrays[0]));values=np.asarray(values,dtype=object).ravel()
        if len(values)!=len(mask):raise ValueError('The result and criteria ranges must align.')
        selected=_numbers(values[mask],minimum=0)
        if name.startswith('SUM'):return math.fsum(selected)
        if not len(selected):
            if name.startswith(('MIN','MAX')):return 0
            raise ValueError('No numeric observations match the criteria.')
        return np.mean(selected) if name.startswith('AVERAGE') else np.max(selected) if name.startswith('MAX') else np.min(selected)
    if name in {'CORREL','PEARSON','COVARIANCE.P','COVARIANCE.S','RSQ','F.TEST','T.TEST'}:
        if name=='T.TEST' and p['type']!=1:
            x=_numbers(p['array1'],minimum=2);y=_numbers(p['array2'],minimum=2)
        elif name=='F.TEST':x=_numbers(p['array1'],minimum=2);y=_numbers(p['array2'],minimum=2)
        else:x,y=_paired(p['array1'],p['array2'])
        if name.startswith('COVARIANCE'):return np.cov(x,y,ddof=1 if name.endswith('.S') else 0)[0,1]
        if name in {'CORREL','PEARSON','RSQ'}:
            if min(np.ptp(x),np.ptp(y))==0:raise ValueError('Correlation requires varying paired observations.')
            r=np.corrcoef(x,y)[0,1];return r*r if name=='RSQ' else r
        if name=='T.TEST':
            result=stats.ttest_rel(x,y) if p['type']==1 else stats.ttest_ind(x,y,equal_var=p['type']==2)
            return float(result.pvalue)/(2 if p['tails']==1 else 1)
        v1=np.var(x,ddof=1);v2=np.var(y,ddof=1)
        if min(v1,v2)<=0:raise ValueError('F.TEST requires positive variances.')
        f=v1/v2;return min(1,2*min(stats.f.cdf(f,len(x)-1,len(y)-1),stats.f.sf(f,len(x)-1,len(y)-1)))
    if name in {'SLOPE','INTERCEPT','STEYX','FORECAST','FORECAST.LINEAR'}:
        y,x=_paired(p['known_y'],p['known_x'],3 if name=='STEYX' else 2)
        if np.ptp(x)==0:raise ValueError('Regression predictor must vary.')
        fit=stats.linregress(x,y)
        if name=='SLOPE':return fit.slope
        if name=='INTERCEPT':return fit.intercept
        if name=='STEYX':return np.sqrt(np.sum((y-fit.intercept-fit.slope*x)**2)/(len(y)-2))
        return fit.intercept+fit.slope*finite_scalar(p['x'])
    if name in {'LINEST','LOGEST','TREND','GROWTH'}:
        from backend.tools.statistical_analysis import regression_fit
        y=np.asarray(p['known_y'],dtype=float).ravel()
        x=np.asarray(p.get('known_x',np.arange(1,len(y)+1)),dtype=float)
        if x.ndim==1:x=x[:,None]
        if len(x)!=len(y):raise ValueError('Regression X and Y ranges must have the same number of observations.')
        exponential=name in {'LOGEST','GROWTH'}
        if exponential and (y<=0).any():raise ValueError('Exponential fits require positive responses.')
        result,fit=regression_fit(np.log(y) if exponential else y,x,p['const'])
        if name in {'TREND','GROWTH'}:
            new=np.asarray(p.get('new_x',x),dtype=float)
            if new.ndim==1:new=new[:,None]
            if new.shape[1]!=x.shape[1] or not np.isfinite(new).all():raise ValueError('New predictor ranges must match the fitted predictor count.')
            predicted=fit.predict(np.column_stack([np.ones(len(new)),new]) if p['const'] else new)
            return np.exp(predicted) if exponential else predicted
        if exponential:
            for row in result['rows']:row['growth_factor']=np.exp(row['coefficient'])
            result['response_scale']='log; coefficient inference is on the log scale'
        return result
    if name=='STANDARDIZE':
        sigma=finite_scalar(p['standard_dev'])
        if sigma<=0:raise ValueError('Standard deviation must be positive.')
        return (finite_scalar(p['x'])-finite_scalar(p['mean']))/sigma
    if name.startswith('CONFIDENCE.'):
        if name.endswith('.T') and p['size']<2:raise ValueError('T confidence needs sample size >=2.')
        critical=stats.t.ppf(1-p['alpha']/2,p['size']-1) if name.endswith('.T') else stats.norm.ppf(1-p['alpha']/2)
        return critical*p['standard_dev']/np.sqrt(p['size'])
    if name in {'FISHER','FISHERINV','GAMMA','GAMMALN','GAMMALN.PRECISE','GAUSS','PHI'}:
        x=finite_scalar(p['x'])
        if name=='FISHER':
            if abs(x)>=1:raise ValueError('Fisher input must lie strictly between minus one and one.')
            return np.arctanh(x)
        if name=='FISHERINV':return np.tanh(x)
        if name=='GAMMA':
            if x<=0 and x==math.floor(x):raise ValueError('Gamma is undefined at nonpositive integers.')
            return special.gamma(x)
        if name.startswith('GAMMALN'):
            if x<=0:raise ValueError('Log-gamma requires a positive argument.')
            return special.gammaln(x)
        return stats.norm.cdf(x)-.5 if name=='GAUSS' else stats.norm.pdf(x)
    if name.startswith('PERMUT'):
        n=p['number'];k=p['number_chosen']
        if name=='PERMUT' and k>n:raise ValueError('Cannot choose more objects than exist without replacement.')
        if name=='PERMUTATIONA':
            if n==0:return 1 if k==0 else 0
            log=k*math.log(n)
        else:log=special.gammaln(n+1)-special.gammaln(n-k+1)
        if log>math.log(np.finfo(float).max):raise ValueError('Permutation result exceeds finite numeric precision.')
        return float(math.perm(n,k)) if name=='PERMUT' else float(n**k)
    if name=='PROB':
        x,probs=_paired(p['values'],p['probabilities'],1)
        if (probs<0).any() or (probs>1).any() or not np.isclose(probs.sum(),1):raise ValueError('Probability masses must be nonnegative and sum to one.')
        low=finite_scalar(p['lower_limit']);high=finite_scalar(p.get('upper_limit',low))
        if high<low:raise ValueError('Upper probability limit must not be below lower limit.')
        return np.sum(probs[(x>=low)&(x<=high)])
    if name=='Z.TEST':
        x=_numbers(p['values'],minimum=2);sigma=p.get('sigma',np.std(x,ddof=1))
        if sigma<=0:raise ValueError('Z.TEST requires positive known or sample sigma.')
        return stats.norm.sf((x.mean()-finite_scalar(p['x']))/(sigma/np.sqrt(len(x))))
    if name=='CHISQ.TEST':
        observed=np.asarray(p['actual'],dtype=float);expected=np.asarray(p['expected'],dtype=float)
        if observed.shape!=expected.shape or observed.size<2 or not np.isfinite(observed).all() or not np.isfinite(expected).all() or (observed<0).any() or (expected<=0).any():
            raise ValueError('Actual/expected count arrays must align, be finite, and have nonnegative/positive entries.')
        if not np.isclose(observed.sum(),expected.sum()):raise ValueError('Actual and expected totals must match.')
        df=(observed.shape[0]-1)*(observed.shape[1]-1) if observed.ndim==2 and min(observed.shape)>1 else observed.size-1
        return stats.chi2.sf(np.sum((observed-expected)**2/expected),df)
    if name.startswith('FORECAST.ETS'):return _forecast_ets(name,p)
    return _distribution(name,p)


def _distribution(name,p):
    discrete=False;inverse='.INV' in name
    if name.startswith('NORM.S.'):distribution=stats.norm
    elif name.startswith('NORM.'):
        sigma=finite_scalar(p['standard_dev'])
        if sigma<=0:raise ValueError('Normal standard deviation must be positive.')
        distribution=stats.norm(loc=finite_scalar(p['mean']),scale=sigma)
    elif name.startswith('BETA.'):
        if p['lower']>=p['upper']:raise ValueError('Beta upper bound must exceed lower bound.')
        if name=='BETA.DIST' and not p['lower']<=finite_scalar(p['x'])<=p['upper']:raise ValueError('Beta x must lie within the supplied lower and upper bounds.')
        distribution=stats.beta(p['alpha'],p['beta'],loc=p['lower'],scale=p['upper']-p['lower'])
    elif name.startswith('BINOM.'):
        distribution=stats.binom(p['trials'],p['probability_s']);discrete=True
        if name=='BINOM.DIST.RANGE':
            lo=p['number_s'];hi=p.get('number_s2',lo)
            if not 0<=lo<=hi<=p['trials']:raise ValueError('Binomial success limits must lie within the trial count.')
            return distribution.cdf(hi)-distribution.cdf(lo-1)
        if name=='BINOM.INV':return 0 if p['alpha']==0 or p['probability_s']==0 else p['trials'] if p['probability_s']==1 else distribution.ppf(p['alpha'])
        if p['number_s']>p['trials']:raise ValueError('Success count cannot exceed trial count.')
    elif name.startswith('CHISQ.'):distribution=stats.chi2(integer(math.trunc(p['degrees_freedom']),minimum=1))
    elif name.startswith('F.'):distribution=stats.f(integer(math.trunc(p['degrees_freedom1']),minimum=1),integer(math.trunc(p['degrees_freedom2']),minimum=1))
    elif name.startswith('T.'):distribution=stats.t(integer(math.trunc(p['degrees_freedom']),minimum=1))
    elif name.startswith('EXPON.'):distribution=stats.expon(scale=1/p['rate'])
    elif name.startswith('GAMMA.'):distribution=stats.gamma(p['alpha'],scale=p['beta'])
    elif name.startswith('LOGNORM.'):
        sigma=finite_scalar(p['standard_dev'])
        if sigma<=0:raise ValueError('Lognormal log standard deviation must be positive.')
        distribution=stats.lognorm(sigma,scale=np.exp(finite_scalar(p['mean'])))
    elif name=='WEIBULL.DIST':distribution=stats.weibull_min(p['alpha'],scale=p['beta'])
    elif name=='POISSON.DIST':distribution=stats.poisson(p['mean']);discrete=True
    elif name=='NEGBINOM.DIST':distribution=stats.nbinom(p['number_s'],p['probability_s']);discrete=True
    elif name=='HYPGEOM.DIST':
        if p['population_s']>p['number_pop'] or p['number_sample']>p['number_pop'] or p['sample_s']>min(p['population_s'],p['number_sample']):
            raise ValueError('Invalid hypergeometric population/sample counts.')
        distribution=stats.hypergeom(p['number_pop'],p['population_s'],p['number_sample']);discrete=True
    else:raise ValueError('Unknown statistical worksheet function.')
    if inverse:
        q=probability(p['probability'])
        return distribution.isf(q/2 if name.endswith('.2T') else q) if name.endswith(('.RT','.2T')) else distribution.ppf(q)
    x=finite_scalar(p['number_f'] if name=='NEGBINOM.DIST' else p.get('x',p.get('number_s',p.get('sample_s'))))
    if name.endswith('.2T'):
        if x<0:raise ValueError('Two-tailed t input must be nonnegative.')
        return 2*distribution.sf(x)
    if name.endswith('.RT'):return distribution.sf(x)
    return distribution.cdf(x) if p.get('cumulative',True) else distribution.pmf(x) if discrete else distribution.pdf(x)


def _forecast_ets(name,p):
    from backend.tools.statistical_analysis import ets_forecast
    values=np.asarray(p['values'],dtype=float).ravel();timeline=np.asarray(p['timeline'],dtype=float).ravel()
    if len(values)!=len(timeline) or not np.isfinite(values).all() or not np.isfinite(timeline).all():raise ValueError('ETS values and numeric timeline must align and be finite.')
    frame=pd.DataFrame({'time':timeline,'value':values}).groupby('time',sort=True)['value'].agg(p.get('aggregation','mean'))
    times=frame.index.to_numpy(dtype=float)
    if len(times)<4:raise ValueError('ETS requires at least four distinct timeline points.')
    step=float(np.min(np.diff(times)))
    positions=(times-times[0])/step
    if not np.allclose(positions,np.round(positions)):raise ValueError('ETS timeline must be regularly spaced or have integer-multiple gaps.')
    if positions[-1]>4999:raise ValueError('ETS expanded timeline exceeds 5000 observations.')
    full=np.arange(int(round(positions[-1]))+1);series=pd.Series(frame.to_numpy(),index=np.round(positions).astype(int)).reindex(full)
    missing=int(series.isna().sum())
    if missing/len(series)>.3:raise ValueError('ETS supports at most thirty percent missing timeline points.')
    series=series.interpolate(limit_direction='both') if p.get('data_completion',1) else series.fillna(0)
    target=finite_scalar(p.get('target',times[-1]+step))
    horizon=(target-times[-1])/step
    if horizon<=0 or not np.isclose(horizon,round(horizon)) or horizon>200:raise ValueError('ETS target must be a future timeline step within two hundred steps.')
    output=ets_forecast(series.to_numpy(),int(round(horizon)),p.get('seasonality',1),p.get('confidence',.95))
    if name=='FORECAST.ETS.SEASONALITY':return output['seasonality']
    if name=='FORECAST.ETS.STAT':
        lag=max(1,output['seasonality']);denom=float(np.mean(np.abs(series.to_numpy()[lag:]-series.to_numpy()[:-lag])))
        choices={1:output['alpha'],2:output['beta'],3:output['gamma'],4:output['mae']/denom if denom else None,
                 5:output['smape'],6:output['mae'],7:output['rmse'],8:step}
        if choices[p['statistic_type']] is None:raise ValueError('The requested ETS statistic is undefined for a constant series.')
        return choices[p['statistic_type']]
    last=output['rows'][-1]
    value=(last['upper']-last['lower'])/2 if name=='FORECAST.ETS.CONFINT' else last['forecast']
    return {'value':value,'seasonality':output['seasonality'],'method':output['method'],'target':target,'timeline_step':step}
