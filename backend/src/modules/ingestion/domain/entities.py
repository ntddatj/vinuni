from dataclasses import dataclass


@dataclass
class UploadedFile:
    id: str
    project_id: str
    user_id: str
    original_filename: str
    file_path: str
    mime_type: str
    file_size: int


@dataclass
class ExtractedMetadata:
    title: str
    authors: list[str]
    abstract: str
    year: int | None


@dataclass
class Paper:
    id: str
    project_id: str
    user_id: str
    title: str
    authors: list[str]
    abstract: str | None
    year: int | None
    source: str
    file_path: str | None
    status: str
