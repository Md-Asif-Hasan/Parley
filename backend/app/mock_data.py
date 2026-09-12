from typing import List, Dict, Any
from .models import Utterance, AnalysisResult, SpeakerSummary, Conflict, Decision

# Sample 1: Product launch date discussion with scheduling conflict and agreed decision
MOCK_TRANSCRIPT_SAMPLE: List[Utterance] = [
    Utterance(
        id="u1",
        speaker_id="speaker_0",
        start=0.5,
        end=4.2,
        text="Hey everyone, thanks for joining. We need to decide our target launch date for Version 2.0."
    ),
    Utterance(
        id="u2",
        speaker_id="speaker_0",
        start=4.8,
        end=8.5,
        text="I strongly propose we aim for this Friday afternoon to get ahead of the weekend."
    ),
    Utterance(
        id="u3",
        speaker_id="speaker_1",
        start=9.0,
        end=14.1,
        text="I don't think Friday works. The QA team won't finish regression testing until Monday morning."
    ),
    Utterance(
        id="u4",
        speaker_id="speaker_2",
        start=14.8,
        end=19.3,
        text="I agree with QA. If we deploy Friday and have bugs, no on-call engineers are available on Saturday."
    ),
    Utterance(
        id="u5",
        speaker_id="speaker_0",
        start=20.0,
        end=24.5,
        text="That's a fair point regarding QA and support. How about we launch next Tuesday at 10 AM instead?"
    ),
    Utterance(
        id="u6",
        speaker_id="speaker_1",
        start=25.0,
        end=28.2,
        text="Tuesday at 10 AM works great for QA. We'll have sign-off by Monday afternoon."
    ),
    Utterance(
        id="u7",
        speaker_id="speaker_2",
        start=28.8,
        end=31.5,
        text="Tuesday 10 AM works for DevOps too. Let's lock that in."
    ),
    Utterance(
        id="u8",
        speaker_id="speaker_0",
        start=32.0,
        end=34.0,
        text="Great, it's decided: Tuesday at 10 AM is our official launch time."
    )
]

MOCK_SPEAKERS_SAMPLE: Dict[str, str] = {
    "speaker_0": "Alice (Product)",
    "speaker_1": "Bob (QA Lead)",
    "speaker_2": "Charlie (DevOps)"
}

MOCK_ANALYSIS_SAMPLE: AnalysisResult = AnalysisResult(
    speaker_summaries=[
        SpeakerSummary(
            speaker_id="speaker_0",
            summary="Initially proposed a Friday afternoon launch, but adjusted to Tuesday 10 AM after considering QA and support availability."
        ),
        SpeakerSummary(
            speaker_id="speaker_1",
            summary="Advocated against Friday launch because regression testing requires until Monday morning; approved Tuesday 10 AM."
        ),
        SpeakerSummary(
            speaker_id="speaker_2",
            summary="Pointed out lack of on-call weekend engineering support for a Friday deploy; confirmed DevOps readiness for Tuesday 10 AM."
        )
    ],
    conflicts=[
        Conflict(
            type="schedule",
            description="Alice's proposal to launch Friday conflicts with Bob's QA regression schedule finishing Monday and Charlie's lack of weekend on-call coverage.",
            utterance_ids=["u2", "u3", "u4"]
        )
    ],
    decisions=[
        Decision(
            description="Official Version 2.0 launch time is set for next Tuesday at 10 AM.",
            utterance_ids=["u5", "u6", "u7", "u8"]
        )
    ]
)
