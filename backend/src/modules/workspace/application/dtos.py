from dataclasses import dataclass


@dataclass
class CreateProjectDTO:
    user_id: str
    name: str
    description: str | None = None


@dataclass
class UpdateProjectDTO:
    project_id: str
    user_id: str
    name: str | None = None
    description: str | None = None
