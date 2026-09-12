import time
from typing import Dict, List, Optional, Any
from .models import MeetingState, Utterance, AnalysisResult, AgentMessage

class MeetingStateManager:
    def __init__(self):
        self.state = MeetingState()
        self._utterance_counter = 0

    def reset(self):
        self.state = MeetingState()
        self._utterance_counter = 0

    def next_utterance_id(self) -> str:
        self._utterance_counter += 1
        return f"u{self._utterance_counter}"

    def set_status(self, status: str, message: Optional[str] = None):
        self.state.status = status
        self.state.status_message = message

    def add_utterances(self, utterances: List[Utterance]) -> List[Utterance]:
        for u in utterances:
            if u.speaker_id and u.speaker_id not in self.state.speakers:
                # Default display name
                speaker_num = u.speaker_id.replace("speaker_", "")
                self.state.speakers[u.speaker_id] = f"Speaker {speaker_num}"
            self.state.transcript.append(u)
        return utterances

    def rename_speaker(self, speaker_id: str, name: str):
        self.state.speakers[speaker_id] = name

    def update_analysis(self, analysis: AnalysisResult):
        self.state.analysis = analysis

    def add_message(self, request_id: str, question: str, answer: str):
        self.state.messages.append(
            AgentMessage(
                request_id=request_id,
                question=question,
                answer=answer,
                timestamp=time.time()
            )
        )

    def get_transcript_for_prompt(self) -> str:
        lines = []
        for u in self.state.transcript:
            speaker_name = self.state.speakers.get(u.speaker_id, u.speaker_id or "Unknown")
            speaker_tag = f"[{u.speaker_id}] {speaker_name}" if u.speaker_id else "[Unknown]"
            lines.append(f"[{u.id}] ({u.start:.1f}s - {u.end:.1f}s) {speaker_tag}: {u.text}")
        return "\n".join(lines)

    def get_export_data(self) -> Dict[str, Any]:
        return self.state.model_dump()
