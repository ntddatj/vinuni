"""Pydantic response schemas cho graph_rag API."""
from pydantic import BaseModel


class NodeResponse(BaseModel):
    id: str
    label: str
    title: str
    authors: list[str] = []
    year: int | None = None
    abstract: str | None = None
    state: str | None = None
    project_id: str | None = None


class EdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    type: str


class GraphResponse(BaseModel):
    nodes: list[NodeResponse]
    edges: list[EdgeResponse]
    has_more: bool


class SyncStatusResponse(BaseModel):
    syncing: bool


class GapFlaggedNodeResponse(BaseModel):
    paper_id: str
    reason: str  # "isolated_cluster" | "has_unfilled_limitation" | "has_contradiction"


class GapFlaggedEdgeResponse(BaseModel):
    finding1_id: str
    finding2_id: str
    paper1_id: str
    paper2_id: str
    reason: str  # "contradicts"


class GapResponse(BaseModel):
    flagged_nodes: list[GapFlaggedNodeResponse]
    flagged_edges: list[GapFlaggedEdgeResponse]


class GapPaperRef(BaseModel):
    paper_id: str
    title: str


class GapDetailItem(BaseModel):
    id: str
    type: str
    reason: str
    title: str
    description: str
    papers: list[GapPaperRef] = []
    evidence: dict = {}


class GapDetailResponse(BaseModel):
    items: list[GapDetailItem]
