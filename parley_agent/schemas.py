"""Shared contracts. Speaker display names and colors belong to middleware/UI."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Utterance(Schema):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, frozen=True)
    id: str = Field(min_length=1)
    speaker_id: str | None
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def valid_span(self) -> "Utterance":
        if self.end < self.start or not self.text.strip():
            raise ValueError("Utterance needs nonblank text and end >= start")
        return self


class SpeakerSummary(Schema):
    speaker_id: str
    summary: str
    utterance_ids: list[str] = Field(min_length=1)


class Decision(Schema):
    description: str
    utterance_ids: list[str] = Field(min_length=1)


class Conflict(Decision):
    type: Literal["schedule", "proposal"]


class SearchRequest(Schema):
    purpose: Literal["fact_check", "idea_reference"] = "fact_check"
    query: str = Field(min_length=1)
    reason: str
    utterance_ids: list[str] = Field(min_length=1)


class Highlight(Schema):
    speaker_id: str | None
    description: str = Field(min_length=1)
    source: Literal["explicit_request", "agent_detected"]
    reason: str = Field(min_length=1)
    utterance_ids: list[str] = Field(min_length=1)


class Analysis(Schema):
    meeting_summary: str
    speaker_summaries: list[SpeakerSummary]
    conflicts: list[Conflict]
    decisions: list[Decision]
    highlights: list[Highlight] = Field(default_factory=list)
    search_request: SearchRequest | None

    @classmethod
    def empty(cls) -> "Analysis":
        return cls(meeting_summary="", speaker_summaries=[], conflicts=[],
                   decisions=[], search_request=None)


class Answer(Schema):
    text: str
    utterance_ids: list[str]
    search_ids: list[str]


class Citation(Schema):
    title: str
    url: str
    start_index: int
    end_index: int


class SearchResult(Schema):
    text: str
    citations: list[Citation]
    sources: list["SearchSource"] = Field(default_factory=list)


class SearchSource(Schema):
    title: str
    url: str
    excerpt: str
    published_date: str | None = None


class SearchRecord(Schema):
    id: str
    purpose: Literal["fact_check", "idea_reference"] = "fact_check"
    query: str
    reason: str
    utterance_ids: list[str]
    based_on_transcript_version: int
    status: Literal["searching", "completed", "error"]
    result: SearchResult | None = None
    error: str | None = None
