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
class ClientSearchResult:
    papers: list[PaperResult]
    total_available: int  # Tổng kết quả có thể có từ API nguồn (để detect broad query)


@dataclass
class SearchResponse:
    results: list[PaperResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    is_broad_query: bool = False
    suggestions: list[str] = field(default_factory=list)
