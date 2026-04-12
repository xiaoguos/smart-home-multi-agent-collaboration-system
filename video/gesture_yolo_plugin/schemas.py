from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


LABEL_PATTERN = re.compile(r"^[a-z0-9_-]{1,64}$")


class RecognizeRequest(BaseModel):
    image_b64: str = Field(..., min_length=16, description="Base64 image string or data URI.")
    top_k: int = Field(default=3, ge=1, le=10)


class LearnRequest(BaseModel):
    label: str = Field(..., description="Custom gesture label, e.g. thumbs_up.")
    image_b64: str = Field(..., min_length=16, description="Base64 image string or data URI.")
    source: str = Field(default="api", max_length=64)

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not LABEL_PATTERN.fullmatch(normalized):
            raise ValueError("label must match ^[a-z0-9_-]{1,64}$")
        return normalized


class Candidate(BaseModel):
    label: str
    score: float
    source: str


class RecognizeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    score: float
    source: str
    model_label: str
    model_score: float
    candidates: list[Candidate]


class LearnResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    sample_count: int
    model_hint_label: str
    model_hint_score: float


class LabelEntry(BaseModel):
    label: str
    sample_count: int


class LabelsResponse(BaseModel):
    labels: list[LabelEntry]


class HealthResponse(BaseModel):
    status: str
    model_path: str
    learning_enabled: bool
