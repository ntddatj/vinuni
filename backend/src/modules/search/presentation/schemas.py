from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class PaperResultSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: str
    authors: list[str]
    year: int | None
    abstract: str
    doi: str | None
    arxiv_id: str | None
    url: str
    pdf_url: str | None
    source: str  # "arxiv" | "semantic_scholar"


class SearchResponseSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    results: list[PaperResultSchema]
    warnings: list[str]
    is_broad_query: bool       # → isBroadQuery
    suggestions: list[str]     # → suggestions
