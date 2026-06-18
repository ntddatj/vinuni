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
