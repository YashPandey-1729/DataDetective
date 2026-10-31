"""Single registry for statistical execution, discovery and argument schemas."""
from dataclasses import dataclass
from typing import Any,Literal
from pydantic import BaseModel,ConfigDict,Field,create_model


class Parameters(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)


def model(name,**fields): return create_model(name,__base__=Parameters,**fields)

Confidence=model('ConfidenceParameters',confidence=(float,Field(default=.95,gt=0,lt=1)),
    method=(Literal['t','normal'],'t'),sigma=(float|None,Field(default=None,gt=0)))
Quantiles=model('QuantileParameters',probabilities=(list[float],Field(default=[.25,.5,.75],min_length=1,max_length=100)),
    method=(Literal['inclusive','exclusive'],'inclusive'))
Rank=model('RankParameters',descending=(bool,True),ties=(Literal['min','average'],'min'))
Histogram=model('HistogramParameters',bins=(list[float]|None,Field(default=None,max_length=199)),bin_count=(int,Field(default=10,ge=1,le=100)))
Matrix=model('MatrixParameters',columns=(list[str],Field(min_length=2,max_length=30)),population=(bool,True),
    method=(Literal['pearson','spearman','kendall'],'pearson'))
Covariance=model('CovarianceParameters',population=(bool,True))
TTest=model('TTestParameters',method=(Literal['paired','equal_variance','welch'],'welch'),
    alternative=(Literal['two-sided','less','greater'],'two-sided'),difference=(float,0),alpha=(float,Field(default=.05,gt=0,lt=1)))
OneSample=model('OneSampleParameters',mean=(float,...),method=(Literal['t','z'],'t'),sigma=(float|None,Field(default=None,gt=0)),
    alternative=(Literal['two-sided','less','greater'],'two-sided'),alpha=(float,Field(default=.05,gt=0,lt=1)))
ZTest=model('ZTestParameters',variance1=(float,Field(gt=0)),variance2=(float,Field(gt=0)),difference=(float,0),
    alternative=(Literal['two-sided','less','greater'],'two-sided'),alpha=(float,Field(default=.05,gt=0,lt=1)))
FTest=model('FTestParameters',alternative=(Literal['two-sided','less','greater'],'two-sided'),alpha=(float,Field(default=.05,gt=0,lt=1)))
ChiSquare=model('ChiSquareParameters',method=(Literal['independence','goodness_of_fit'],'independence'),
    alpha=(float,Field(default=.05,gt=0,lt=1)))
Anova=model('AnovaParameters',alpha=(float,Field(default=.05,gt=0,lt=1)))
AnovaTwo=model('AnovaTwoParameters',factor2=(str,...),replication=(bool,True),alpha=(float,Field(default=.05,gt=0,lt=1)))
Regression=model('RegressionParameters',predictors=(list[str],Field(min_length=1,max_length=30)),intercept=(bool,True),
    confidence=(float,Field(default=.95,gt=0,lt=1)),exponential=(bool,False),predict_at=(list[list[float]]|None,Field(default=None,max_length=200)))
MovingAverage=model('MovingAverageParameters',window=(int,Field(default=3,ge=1,le=1000)),order_by=(str|None,None))
Smoothing=model('SmoothingParameters',alpha=(float,Field(default=.3,gt=0,le=1)),order_by=(str|None,None))
Sampling=model('SamplingParameters',method=(Literal['random','periodic'],'random'),size=(int,Field(default=20,ge=1,le=200)),
    period=(int,Field(default=2,ge=1,le=150000)),replace=(bool,False),seed=(int,Field(default=0,ge=0,le=2**32-1)),
    columns=(list[str]|None,Field(default=None,max_length=30)))
Random=model('RandomParameters',distribution=(Literal['normal','uniform','bernoulli','binomial','poisson','discrete','patterned'],'normal'),
    size=(int,Field(default=20,ge=1,le=200)),seed=(int,Field(default=0,ge=0,le=2**32-1)),mean=(float,0),std=(float,Field(default=1,gt=0)),
    low=(float,0),high=(float,1),probability=(float,Field(default=.5,ge=0,le=1)),trials=(int,Field(default=10,ge=0,le=1000000)),
    rate=(float,Field(default=1,gt=0)),values=(list[float]|None,Field(default=None,max_length=200)),
    probabilities=(list[float]|None,Field(default=None,max_length=200)),step=(float,1),repeats=(int,Field(default=1,ge=1,le=200)))
Fourier=model('FourierParameters',inverse=(bool,False),imaginary_column=(str|None,None),order_by=(str|None,None))
Forecast=model('ForecastParameters',steps=(int,Field(default=10,ge=1,le=200)),order_by=(str|None,None),
    seasonality=(int,Field(default=0,ge=0,le=365)),confidence=(float,Field(default=.95,gt=0,lt=1)))
Normality=model('NormalityParameters',method=(Literal['shapiro','jarque_bera'],'shapiro'),alpha=(float,Field(default=.05,gt=0,lt=1)))


@dataclass(frozen=True)
class Operation:
    name:str
    category:str
    description:str
    required:tuple[str,...]
    parameters:type[BaseModel]|None=None
    assumptions:str=''


OPERATIONS={item.name:item for item in [
    Operation('summary','descriptive','Count, sum, mean, median, sample/population variance and standard deviation, skewness, kurtosis and standard error.',('column',)),
    Operation('mode','descriptive','Exact modal values, all ties and frequencies.',('column',)),
    Operation('outliers','descriptive','IQR outlier candidates, not confirmed data errors.',('column',)),
    Operation('correlation','relationships','Pearson r and p-value for complete paired observations.',('column','other_column')),
    Operation('group_comparison','descriptive','Descriptive summaries by group.',('column','group_by')),
    Operation('percentage_change','descriptive','Percentage change from supplied before/after values.',('before','after')),
    Operation('quantiles','descriptive','Percentiles/quartiles with Excel inclusive or exclusive interpolation.',('column',),Quantiles),
    Operation('rank','descriptive','Rank and percentile rank, with explicit tie handling.',('column',),Rank),
    Operation('histogram','descriptive','Frequency and cumulative-frequency bins, upper bounds inclusive with overflow bin.',('column',),Histogram),
    Operation('confidence_interval','inference','Mean confidence interval using t or known-sigma normal distribution.',('column',),Confidence,'Independent observations; t interval assumes normal mean sampling distribution.'),
    Operation('covariance','relationships','Sample or population covariance of paired columns.',('column','other_column'),Covariance),
    Operation('correlation_matrix','relationships','Pearson/Spearman/Kendall matrix with complete-case observations.',(),Matrix),
    Operation('covariance_matrix','relationships','Sample or population covariance matrix using complete cases.',(),Matrix),
    Operation('t_test','inference','Paired, pooled equal-variance or Welch two-sample t test.',('column','other_column'),TTest,'Pairing must be meaningful; independent groups for unpaired tests; normality assumptions apply.'),
    Operation('one_sample_test','inference','One-sample t test or z test with known sigma.',('column',),OneSample),
    Operation('z_test','inference','Two-sample z test with known population variances.',('column','other_column'),ZTest,'Variances must be known population quantities, not guessed from small samples.'),
    Operation('f_test','inference','Two-sample variance-ratio F test.',('column','other_column'),FTest,'Independent normal populations; the test is sensitive to nonnormality.'),
    Operation('chi_square_test','inference','Categorical independence or observed/expected goodness-of-fit test.',('column','other_column'),ChiSquare,'Count data and independent observations; sparse expected cells are disclosed.'),
    Operation('anova_one_way','anova','One-factor ANOVA from numeric values and group labels.',('column','group_by'),Anova,'Independent normal errors with equal group variances.'),
    Operation('anova_two_way','anova','Balanced two-factor ANOVA with or without replication.',('column','group_by'),AnovaTwo,'Balanced complete cells; without replication, interaction cannot be separated from residual error.'),
    Operation('regression','regression','Multiple linear or log-linear least squares, ANOVA, coefficient inference and residuals.',('column',),Regression,'Independent errors; homoscedasticity and normal errors for classical coefficient tests; association is not causation.'),
    Operation('moving_average','time_series','Trailing moving averages and one-period-ahead forecasts.',('column',),MovingAverage),
    Operation('exponential_smoothing','time_series','Simple exponential smoothing; alpha is the weight on the newest observation.',('column',),Smoothing),
    Operation('forecast','time_series','Additive Holt/ETS forecast with optional seasonality and model-based intervals.',('column',),Forecast,'Regularly ordered observations and stable time-series structure; forecast methods can differ from Excel ETS.'),
    Operation('fourier_analysis','time_series','Forward/inverse FFT; real, imaginary, magnitude and phase output.',('column',),Fourier,'Equally spaced complete observations; row order is meaningful.'),
    Operation('sampling','sampling','Seeded random or periodic samples from the uploaded dataset.',(),Sampling),
    Operation('random_generation','sampling','Seeded normal, uniform, Bernoulli, binomial, Poisson, discrete or patterned simulation.',(),Random,'Simulation uses supplied distribution parameters; it is not observed dataset evidence.'),
    Operation('normality_test','inference','Shapiro-Wilk or Jarque-Bera normality diagnostic.',('column',),Normality),
    Operation('excel','excel','Named Excel statistical worksheet functions; discover a function name for its exact parameters.',()),
]}


def get_operation(name):
    if name not in OPERATIONS:
        raise ValueError('Unknown statistical operation. Use statistics_catalog to discover an operation or Excel function.')
    return OPERATIONS[name]


def validate_parameters(operation,parameters):
    spec=get_operation(operation)
    if operation=='excel':
        from backend.tools.statistical_excel import validate_excel_parameters
        return validate_excel_parameters(parameters or {})
    if spec.parameters is None:
        if parameters: raise ValueError(f'{operation} does not accept extra parameters.')
        return {}
    try: return spec.parameters.model_validate(parameters or {}).model_dump()
    except ValueError as exc: raise ValueError(f'Invalid parameters for {operation}: '+str(exc)[:600]) from None


def describe_statistics(name='all',category=None):
    from backend.tools.statistical_excel import FUNCTIONS,ALIASES,describe_function
    key=name.strip().upper()
    friendly={'descriptive statistics':'summary','t-test':'t_test','anova single factor':'anova_one_way',
        'paired t-test':'t_test','paired t test':'t_test','welch t-test':'t_test','confidence interval':'confidence_interval',
        'anova with replication':'anova_two_way','rank and percentile':'rank','fourier analysis':'fourier_analysis',
        'random number generation':'random_generation','exponential smoothing':'exponential_smoothing','moving average':'moving_average'}
    name=friendly.get(name.strip().casefold(),name)
    if (key in FUNCTIONS or key in ALIASES and name.strip()==key) and name.strip() not in OPERATIONS: return describe_function(key)
    if name.strip().lower() in OPERATIONS:
        spec=OPERATIONS[name.strip().lower()]
        return {'kind':'operation','operation':spec.name,'category':spec.category,'description':spec.description,
                'required_arguments':list(spec.required),'parameters_schema':spec.parameters.model_json_schema() if spec.parameters else {},
                **({'suggested_parameters':{'method':'paired'}} if key in {'PAIRED T-TEST','PAIRED T TEST'} else {}),
                'assumptions':spec.assumptions}
    needle=name.strip().casefold()
    candidates=[{'name':spec.name,'category':spec.category,'description':spec.description} for spec in OPERATIONS.values()
        if (not category or spec.category==category) and (needle in {'','all'} or needle in (spec.name+' '+spec.description).casefold())]
    functions=[{'name':key,'category':'excel','description':spec.description} for key,spec in FUNCTIONS.items()
        if (not category or category=='excel') and (needle in {'','all'} or needle in (key+' '+spec.description).casefold())]
    return {'kind':'catalog','operation_count':len(OPERATIONS),'excel_function_count':len(FUNCTIONS),
            'categories':sorted({spec.category for spec in OPERATIONS.values()}),
            'operations':candidates[:40],'excel_functions':functions[:200],
            'note':'Call statistics_catalog with an exact operation/function name to obtain validated parameters before executing it.'}
