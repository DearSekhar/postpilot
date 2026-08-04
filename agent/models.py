from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


KNOWN_ICONS = {
    "user", "database", "cloud", "camera", "shield", "check", "alert",
    "server", "mail", "chart", "factory", "hospital", "gear", "lock",
    "search", "package",
}


class DiagramStep(BaseModel):
    title: str = Field(..., max_length=30)
    subtitle: Optional[str] = Field(default=None, max_length=40)
    icon: Optional[str] = Field(default=None)

    @field_validator("title", mode="before")
    @classmethod
    def truncate_title(cls, v: str) -> str:
        return _truncate(v, 30) if isinstance(v, str) else v

    @field_validator("subtitle", mode="before")
    @classmethod
    def truncate_subtitle(cls, v):
        return _truncate(v, 40) if isinstance(v, str) else v

    @field_validator("icon", mode="before")
    @classmethod
    def validate_icon(cls, v):
        # Unknown/hallucinated icon names degrade to "no icon" rather than
        # failing the whole draft — icons are a visual nicety, not worth a retry.
        if not isinstance(v, str):
            return None
        v = v.strip().lower()
        return v if v in KNOWN_ICONS else None

class DiagramSpec(BaseModel):
    style: Literal["architecture", "concept", "hierarchy"]
    steps: List[DiagramStep]

    @field_validator("steps")
    @classmethod
    def limit_steps(cls, v: List[DiagramStep]) -> List[DiagramStep]:
        if not (2 <= len(v) <= 4):
            raise ValueError("Diagrams should have between 2 and 4 steps to stay simple")
        return v


class BusinessProblem(BaseModel):
    is_new: bool = False
    problem: str
    why_hard: str
    solution_pattern: str


class PostDraft(BaseModel):
    topic: str
    category: str
    industry: Optional[str] = None
    business_problem: Optional[BusinessProblem] = None
    body_text: str
    hashtags: List[str] = Field(default_factory=list, max_length=5)
    diagram: DiagramSpec

    @property
    def word_count(self) -> int:
        return len(self.body_text.split())
