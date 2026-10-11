from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class FlowStep(BaseModel):
    step_number: int
    file_path: str
    symbol_or_endpoint: Optional[str] = None
    description: str


class FlowExplanation(BaseModel):
    flow_name: str
    overview: str
    steps: List[FlowStep]
    caveats: Optional[str] = None


class ImpactedItem(BaseModel):
    file_path: str
    symbol: Optional[str] = None
    risk_level: str = Field(description="high, medium, or low")
    rationale: str


class ImpactAnalysis(BaseModel):
    target: str
    suggested_change_order: List[str]
    impacted_items: List[ImpactedItem]
    static_analysis_caveat: str = "Static edge detection may miss dynamic reflections or untyped runtime dispatches."


class ComponentOverview(BaseModel):
    name: str
    responsibilities: str
    key_files: List[str]


class ArchitectureOverview(BaseModel):
    system_overview: str
    entry_points: List[str]
    components: List[ComponentOverview]
    data_stores: List[str]
    external_dependencies: List[str]


class ReadingGuideItem(BaseModel):
    order: int
    file_path: str
    why_read: str


class OnboardingGuide(BaseModel):
    summary: str
    where_to_start: List[ReadingGuideItem]
    key_concepts: List[str]
    development_workflow_notes: str


class RefactorUnit(BaseModel):
    name: str
    lines: str
    purpose: str
    dead_code_flags: Optional[str] = None
    hidden_dependencies: List[str] = []


class LegacyCodeBreakdown(BaseModel):
    file_path: str
    total_lines: int
    summary: str
    units: List[RefactorUnit]
    suggested_refactor_split: List[str]


class RepoComparisonAspect(BaseModel):
    topic: str
    repo_a_approach: str
    repo_b_approach: str
    tradeoffs: str


class RepoComparison(BaseModel):
    repo_a: str
    repo_b: str
    summary: str
    aspects: List[RepoComparisonAspect]
