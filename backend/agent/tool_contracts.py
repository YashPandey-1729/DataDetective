"""Tool-specific argument contracts for execution and local constrained decoding."""
from copy import deepcopy
from backend.agent.schemas import AgentAction
from backend.tools.statistical_catalog import get_operation,validate_parameters


TOOLS = {
    'profile_dataset': ((), ()),
    'execute_sql': (('sql',), ('sql',)),
    'calculate_statistics': (('operation','column','other_column','group_by','before','after','parameters'), ('operation',)),
    'statistics_catalog': (('name','category'), ('name',)),
    'inspect_image': ((), ()),
    'generate_chart': (('evidence_id','chart_type','x','y','title'), ('evidence_id','chart_type')),
    'verify_finding': (('evidence_id','row','field','expected','claim'), ('evidence_id','row','field','expected')),
    'finish': ((), ()),
}
STATISTICS = {
    'summary': ('column',), 'mode': ('column',), 'outliers': ('column',),
    'correlation': ('column','other_column'), 'group_comparison': ('column','group_by'),
    'percentage_change': ('before','after'),
}


def validate_tool_arguments(action):
    """Reject incomplete calls before dispatch; never guess an analytical operation."""
    _, required = TOOLS[action.tool]
    args = action.args.model_dump(exclude_none=True)
    missing = [key for key in required if key not in args or isinstance(args[key],str) and not args[key].strip()]
    if missing:
        hint = ' Choose summary, mode, outliers, correlation, group_comparison or percentage_change.' if action.tool=='calculate_statistics' else ''
        raise ValueError(f"{action.tool} requires: {', '.join(missing)}.{hint}")
    if action.tool=='calculate_statistics':
        required = get_operation(action.args.operation).required
        validate_parameters(action.args.operation,action.args.parameters)
    elif action.tool=='generate_chart':
        required = () if action.args.chart_type=='heatmap' else ('x',) if action.args.chart_type=='histogram' else ('x','y')
    else:
        return action
    missing = [key for key in required if key not in args or isinstance(args[key],str) and not args[key].strip()]
    if missing:
        operation = action.args.operation or action.args.chart_type
        raise ValueError(f"{action.tool} ({operation}) requires: {', '.join(missing)}.")
    return action


def local_action_json_schema(constraints=None):
    """Each allowed tool gets its own required args, instead of one nullable bag."""
    original = AgentAction.model_json_schema()
    fields = original['$defs']['ToolArgs']['properties']
    constraints = constraints or {}
    definitions={}

    def arguments(names, required, constants=None, evidence_ids=None):
        properties = {key:deepcopy(fields[key]) for key in names}
        for key, definition in properties.items():
            definition.pop('title',None)
            definition.pop('default',None)
            if key in required and 'anyOf' in definition:
                properties[key] = next(item for item in definition['anyOf'] if item.get('type')!='null')
            if key in required and properties[key].get('type')=='string':
                properties[key]['minLength'] = 1
        for key,value in (constants or {}).items():
            properties[key] = {'type':'string','const':value}
        if evidence_ids is not None and 'evidence_id' in properties:
            properties['evidence_id']['enum'] = list(evidence_ids)
        if 'sql' in properties:
            properties['sql'].update(minLength=1,maxLength=8000)
        return {'type':'object','properties':properties,'required':list(required),'additionalProperties':False}

    variants = []
    for tool,(names,required) in TOOLS.items():
        ids = constraints.get('chart_evidence_ids' if tool=='generate_chart' else 'verification_evidence_ids')
        if tool in {'generate_chart','verify_finding'} and ids==[]:
            continue
        if tool=='calculate_statistics':
            choices=[arguments(('operation',*keys),('operation',*keys),{'operation':op}) for op,keys in STATISTICS.items()]
            for request in constraints.get('statistical_requests',[])[:3]:
                op=request['operation']
                if op in STATISTICS:continue
                spec=get_operation(op)
                if op=='excel':
                    if not request.get('function'):continue
                    from backend.tools.statistical_excel import function_schema
                    schema=deepcopy(function_schema(request['function']))
                else:schema=deepcopy(spec.parameters.model_json_schema()) if spec.parameters else {'type':'object','properties':{},'additionalProperties':False}
                definitions.update(schema.pop('$defs',{}))
                branch=arguments(('operation',*spec.required,'parameters'),('operation',*spec.required,'parameters'),{'operation':op})
                branch['properties']['parameters']=schema
                choices.append(branch)
            args = {'oneOf':choices}
        elif tool=='generate_chart':
            args = {'oneOf':[arguments(('evidence_id','chart_type','title',*axes),('evidence_id','chart_type',*axes),{'chart_type':kind},ids)
                    for kind,axes in [('heatmap',()),('histogram',('x',)),('line',('x','y')),('bar',('x','y')),('scatter',('x','y'))]]}
        else:
            args = arguments(names,required,evidence_ids=ids if tool=='verify_finding' else None)
        variants.append({'type':'object','properties':{
            'tool':{'type':'string','const':tool},
            'explanation':original['properties']['explanation'],
            'plan':original['properties']['plan'],'args':args},
            'required':['tool','explanation','args'],'additionalProperties':False})
    return {'title':'AgentAction','oneOf':variants,**({'$defs':definitions} if definitions else {})}
