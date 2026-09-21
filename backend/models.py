from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class Entity(BaseModel):
    id: str
    type: str
    value: str

class Relationship(BaseModel):
    source: str
    target: str
    relationship: str
    evidence_ids: List[str]
    is_suspicious: bool = False

class Signal(BaseModel):
    rule_id: str
    name: str
    weight: int
    description: str
    affected_entities: List[str]

class RiskAssessment(BaseModel):
    score: int
    level: str
    signals: List[Signal]

class TimelineEvent(BaseModel):
    timestamp: str
    event_type: str
    source: str
    evidence_id: str
    description: str

class GraphData(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

class AnalysisResponse(BaseModel):
    summary: Dict[str, Any]
    entities: List[Entity]
    relationships: List[Relationship]
    risk: RiskAssessment
    timeline: List[TimelineEvent]
    graph: GraphData
    sha256: str
    investigative_brief: str