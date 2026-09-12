from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

class Utterance(BaseModel):
    id: str = Field(..., description="Unique utterance ID, e.g. u1, u2")
    speaker_id: Optional[str] = Field(None, description="Speaker identifier, e.g. speaker_0 or null")
    start: float = Field(..., description="Start timestamp in seconds from start of recording")
    end: float = Field(..., description="End timestamp in seconds from start of recording")
    text: str = Field(..., description="Finalized text content")

class SpeakerSummary(BaseModel):
    speaker_id: str = Field(..., description="Speaker ID associated with this summary")
    summary: str = Field(..., description="Grounded summary of the participant's views/arguments")

class Conflict(BaseModel):
    type: Literal["schedule", "proposal", "other"] = Field("proposal", description="Type of potential conflict")
    description: str = Field(..., description="Explanation of the incompatible constraints or proposals")
    utterance_ids: List[str] = Field(default_factory=list, description="IDs of source utterances establishing the conflict")

class Decision(BaseModel):
    description: str = Field(..., description="Description of an agreed upon decision")
    utterance_ids: List[str] = Field(default_factory=list, description="IDs of source utterances showing agreement")

class AnalysisResult(BaseModel):
    speaker_summaries: List[SpeakerSummary] = Field(default_factory=list)
    conflicts: List[Conflict] = Field(default_factory=list)
    decisions: List[Decision] = Field(default_factory=list)

class AgentMessage(BaseModel):
    request_id: str
    question: str
    answer: str
    timestamp: float

class MeetingState(BaseModel):
    transcript: List[Utterance] = Field(default_factory=list)
    speakers: Dict[str, str] = Field(default_factory=dict, description="speaker_id -> display_name")
    analysis: AnalysisResult = Field(default_factory=AnalysisResult)
    messages: List[AgentMessage] = Field(default_factory=list)
    status: Literal["idle", "recording", "processing", "stopped", "error"] = "idle"
    status_message: Optional[str] = None

class WSEvent(BaseModel):
    type: str
    data: Dict[str, Any] = Field(default_factory=dict)
