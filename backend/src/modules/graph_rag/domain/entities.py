"""Domain entities cho graph_rag read model."""
from dataclasses import dataclass, field


@dataclass
class GraphNode:
    id: str
    label: str  # "paper" | "author"
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    abstract: str | None = None
    state: str | None = None  # "full_text" | "metadata_only"
    project_id: str | None = None


@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    type: str  # "AUTHORED_BY" | "CITES" | ...


@dataclass
class GraphData:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    has_more: bool = False
