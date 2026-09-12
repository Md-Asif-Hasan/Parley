export interface Utterance {
  id: string;
  speaker_id: string | null;
  start: number;
  end: number;
  text: string;
}

export interface SpeakerSummary {
  speaker_id: string;
  summary: string;
}

export interface Conflict {
  type: 'schedule' | 'proposal' | 'other';
  description: string;
  utterance_ids: string[];
}

export interface Decision {
  description: string;
  utterance_ids: string[];
}

export interface AnalysisResult {
  speaker_summaries: SpeakerSummary[];
  conflicts: Conflict[];
  decisions: Decision[];
}

export interface AgentMessage {
  request_id: string;
  question: string;
  answer: string;
  timestamp: number;
}

export type MeetingStatus = 'idle' | 'recording' | 'processing' | 'stopped' | 'error';

export interface MeetingState {
  transcript: Utterance[];
  speakers: Record<string, string>;
  analysis: AnalysisResult;
  messages: AgentMessage[];
  status: MeetingStatus;
  status_message?: string;
}

export interface WSEvent<T = any> {
  type: string;
  data: T;
}
