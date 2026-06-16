from dataclasses import dataclass, field


@dataclass
class PaperResult:
    title: str
    authors: list[str]
    year: int | None
    abstract: str
    doi: str | None
    arxiv_id: str | None
    url: str
    pdf_url: str | None
    source: str  # "arxiv" | "semantic_scholar"


@dataclass
class SearchResponse:
    results: list[PaperResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # is_broad_query + suggestions sẽ được thêm vào Story 2.3
