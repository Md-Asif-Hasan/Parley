import pytest
from unittest.mock import patch, MagicMock
from app.agent import MeetingAgent
from app.models import AnalysisResult, SpeakerSummary, Conflict, Decision

@pytest.mark.asyncio
async def test_agent_update_analysis_fallback_on_no_transcript():
    agent = MeetingAgent()
    res = await agent.update_analysis("")
    assert isinstance(res, AnalysisResult)
    assert len(res.speaker_summaries) == 0

@pytest.mark.asyncio
async def test_agent_update_analysis_mocked():
    agent = MeetingAgent()
    mock_json = '{"speaker_summaries": [{"speaker_id": "speaker_0", "summary": "Wants Friday release"}], "conflicts": [{"type": "schedule", "description": "QA not ready on Friday", "utterance_ids": ["u2", "u3"]}], "decisions": [{"description": "Deploy Tuesday", "utterance_ids": ["u8"]}]}'

    with patch.object(agent, "_sync_post", return_value=mock_json):
        res = await agent.update_analysis("[u1] speaker_0: launch Friday")
        assert len(res.speaker_summaries) == 1
        assert res.speaker_summaries[0].speaker_id == "speaker_0"
        assert len(res.conflicts) == 1
        assert res.conflicts[0].type == "schedule"
        assert "u2" in res.conflicts[0].utterance_ids
        assert len(res.decisions) == 1

@pytest.mark.asyncio
async def test_agent_answer_question_mocked():
    agent = MeetingAgent()
    mock_answer = "Bob from QA stated that regression testing won't be ready until Monday [u3]."

    with patch.object(agent, "_sync_post", return_value=mock_answer):
        answer = await agent.answer_question(
            "Why can't we launch on Friday?",
            "[u3] Bob: I don't think Friday works. QA won't finish.",
            AnalysisResult()
        )
        assert "Bob" in answer or "QA" in answer
