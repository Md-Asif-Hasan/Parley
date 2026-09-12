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

export interface ActionPlan {
  action_type: 'social_post' | 'chat_message' | 'email' | 'calendar' | 'os_command';
  platform: string;
  description: string;
  params: Record<string, any>;
  requires_confirmation: boolean;
}

export interface AutopilotStatus {
  isActive: boolean;
  status: 'idle' | 'planning' | 'running' | 'completed' | 'failed' | 'cancelled';
  step?: string;
  message?: string;
  plan?: ActionPlan | null;
}

export interface AgentMessage {
  request_id: string;
  question: string;
  answer: string;
  timestamp: number;
  image?: string;
  action_plan?: ActionPlan | null;
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
