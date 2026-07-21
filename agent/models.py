from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class DiagramStep(BaseModel):
    title: str = Field(..., max_length=30)
    subtitle: Optional[str] = Field(default=None, max_length=40)


class DiagramSpec(BaseModel):
    style: Literal["architecture", "concept"]
    steps: List[DiagramStep]

    @field_validator("steps")
    @classmethod
    def limit_steps(cls, v: List[DiagramStep]) -> List[DiagramStep]:
        if not (2 <= len(v) <= 4):
            raise ValueError("Diagrams should have between 2 and 4 steps to stay simple")
        return v


class PostDraft(BaseModel):
    topic: str
    body_text: str
    hashtags: List[str] = Field(default_factory=list, max_length=5)
    diagram: DiagramSpec

    @property
    def word_count(self) -> int:
        return len(self.body_text.split())
