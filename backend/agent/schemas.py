from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


def gemini_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Keep strict JSON types, but enforce array caps locally to avoid Gemini state explosion."""
    schema = model.model_json_schema()
    def simplify(value):
        if isinstance(value, dict):
            if value.get('type') == 'array':
                value.pop('maxItems', None)
            for child in value.values():
                simplify(child)
        elif isinstance(value, list):
            for child in value:
                simplify(child)
    simplify(schema)
    return schema


class InvestigationRequest(StrictModel):
    dataset_id: str
    question: str = Field(min_length=5, max_length=2000, pattern=r'\S.{3,}\S|\S{5,}')
    image_id: str | None = None
    mode: Literal['agent', 'offline'] = 'agent'
    model: str | None = Field(default=None, min_length=1, max_length=120)


class ToolArgs(StrictModel):
    sql: str | None = None
    operation: str | None = Field(default=None,max_length=80)
    column: str | None = None
    other_column: str | None = None
    group_by: str | None = None
    before: float | None = None
    after: float | None = None
    evidence_id: str | None = None
    chart_type: Literal['line', 'bar', 'scatter', 'histogram', 'heatmap'] | None = None
    x: str | None = None
    y: str | None = None
    title: str | None = None
    row: int | None = Field(default=None, ge=0, le=199)
    field: str | None = None
    expected: float | None = None
    claim: str | None = None
    parameters: dict[str,Any] | None = Field(default=None,max_length=30)
    name: str | None = Field(default=None,max_length=120)
    category: str | None = Field(default=None,max_length=50)


class AgentAction(StrictModel):
    tool: Literal['profile_dataset', 'execute_sql', 'calculate_statistics', 'statistics_catalog', 'inspect_image', 'generate_chart', 'verify_finding', 'finish']
    explanation: str = Field(max_length=1200)
    plan: list[str] = Field(default_factory=list, max_length=8)
    args: ToolArgs = Field(default_factory=ToolArgs)


class StatisticsRequest(StrictModel):
    operation:str=Field(min_length=1,max_length=80)
    column:str|None=None
    other_column:str|None=None
    group_by:str|None=None
    before:float|None=None
    after:float|None=None
    parameters:dict[str,Any]|None=Field(default=None,max_length=30)


class Measurement(StrictModel):
    evidence_id: str
    row: int | None = Field(default=None, ge=0, le=199)
    field: str
    value: float


class ReportFinding(StrictModel):
    claim: str = Field(max_length=1600)
    evidence_ids: list[str] = Field(max_length=12)
    kind: Literal['observation', 'hypothesis', 'inconclusive']
    measurements: list[Measurement] = Field(default_factory=list, max_length=12)


class AgentReport(StrictModel):
    summary: str = Field(max_length=4000)
    findings: list[ReportFinding] = Field(max_length=20)
    limitations: list[str] = Field(max_length=15)
    next_steps: list[str] = Field(max_length=10)


class ImageContext(StrictModel):
    chart_type: str
    axes: list[str]
    metrics: list[str]
    categories: list[str]
    time_periods: list[str]
    highlighted_regions: list[str]
    visible_patterns: list[str]
    matching_columns: list[str]
    ambiguities: list[str]


class DatasetResponse(BaseModel):
    id: str
    name: str
    profile: dict[str, Any]


class InvestigationResponse(BaseModel):
    id: str
    dataset_id: str
    question: str
    mode: str
    model: str | None = None
    status: str
    plan: list[str]
    events: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    charts: list[dict[str, Any]]
    report: dict[str, Any] | None
    errors: list[str]
    image_context: dict[str, Any] | None
    stop_reason: str | None = None
