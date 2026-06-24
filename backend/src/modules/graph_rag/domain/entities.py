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


@dataclass
class GapFlaggedNode:
    paper_id: str
    reason: str  # "isolated_cluster" | "has_unfilled_limitation" | "has_contradiction"


@dataclass
class GapFlaggedEdge:
    finding1_id: str
    finding2_id: str
    paper1_id: str
    paper2_id: str
    reason: str  # "contradicts"


@dataclass
class GapContext:
    flagged_nodes: list[GapFlaggedNode] = field(default_factory=list)
    flagged_edges: list[GapFlaggedEdge] = field(default_factory=list)


@dataclass
class GraphContext:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)


@dataclass
class GapPaperRef:
    paper_id: str
    title: str


@dataclass
class GapDetailItem:
    id: str
    type: str  # "contradiction" | "unfilled_limitation" | "isolated_cluster"
    reason: str  # alias của type
    title: str
    description: str
    papers: list[GapPaperRef] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
