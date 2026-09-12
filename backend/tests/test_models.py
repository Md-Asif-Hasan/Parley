import pytest
from app.models import Utterance, SpeakerSummary, Conflict, Decision, AnalysisResult, MeetingState
from app.state import MeetingStateManager

def test_utterance_serialization():
    u = Utterance(
        id="u1",
        speaker_id="speaker_0",
        start=1.2,
        end=4.5,
        text="Let's release on Friday."
    )
    data = u.model_dump()
    assert data["id"] == "u1"
    assert data["speaker_id"] == "speaker_0"
    assert data["start"] == 1.2
    assert data["end"] == 4.5
    assert data["text"] == "Let's release on Friday."

def test_analysis_result_schema():
    analysis = AnalysisResult(
        speaker_summaries=[
            SpeakerSummary(speaker_id="speaker_0", summary="Wants Friday launch")
        ],
        conflicts=[
            Conflict(type="schedule", description="Friday conflicts with QA", utterance_ids=["u1", "u2"])
        ],
        decisions=[
            Decision(description="Launch on Tuesday", utterance_ids=["u3", "u4"])
        ]
    )
    assert len(analysis.speaker_summaries) == 1
    assert analysis.conflicts[0].type == "schedule"
    assert "u1" in analysis.conflicts[0].utterance_ids
    assert len(analysis.decisions) == 1

def test_state_manager_lifecycle():
    manager = MeetingStateManager()
    assert manager.state.status == "idle"

    u1 = Utterance(id=manager.next_utterance_id(), speaker_id="speaker_0", start=0.0, end=2.0, text="Hello team")
    u2 = Utterance(id=manager.next_utterance_id(), speaker_id="speaker_1", start=2.5, end=5.0, text="Hi Alice")
    manager.add_utterances([u1, u2])

    assert len(manager.state.transcript) == 2
    assert "speaker_0" in manager.state.speakers
    assert manager.state.speakers["speaker_0"] == "Speaker 0"

    manager.rename_speaker("speaker_0", "Alice")
    assert manager.state.speakers["speaker_0"] == "Alice"

    prompt_text = manager.get_transcript_for_prompt()
    assert "[u1]" in prompt_text
    assert "Alice" in prompt_text
