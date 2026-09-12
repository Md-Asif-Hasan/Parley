export type Utterance = { id: string; speaker_id: string | null; start: number; end: number; text: string };
export type Evidence = { description: string; utterance_ids: string[] };
export type Highlight = Evidence & { speaker_id: string | null; source: 'explicit_request' | 'agent_detected'; reason: string };
export type Analysis = {
  meeting_summary: string;
  speaker_summaries: { speaker_id: string; summary: string; utterance_ids: string[] }[];
  decisions: Evidence[]; conflicts: (Evidence & { type: string })[]; highlights: Highlight[];
  search_request?: unknown; based_on_transcript_version: number;
};
export type Search = {
  id: string; purpose: 'idea_reference' | 'fact_check'; query: string; reason: string;
  utterance_ids: string[]; based_on_transcript_version: number;
  status: 'searching' | 'completed' | 'error'; error: string | null;
  result: { text: string; citations: unknown[]; sources: { title: string; url: string; excerpt: string; published_date?: string | null }[] } | null;
};
export type MeetingEvent =
  | { type: 'meeting.export'; data: { analysis_is_current: boolean; analysis_error: string | null } }
  | { type: 'transcript.final'; data: { utterances: Utterance[] } }
  | { type: 'transcript.partial'; data: { text: string; speaker_id: string | null } }
  | { type: 'analysis.updated'; data: Analysis }
  | { type: 'search.updated'; data: Search }
  | { type: 'status'; data: { state: State['status'] } }
  | { type: 'error'; data: { scope: string; message: string } };
export type State = { transcript: Utterance[]; partial: { text: string; speaker_id: string | null } | null; analysis: Analysis; searches: Search[]; status: 'idle' | 'connecting' | 'recording' | 'processing' | 'stopped' | 'error'; error: string | null };
export const initialState: State = { transcript: [], partial: null, analysis: { meeting_summary: '', speaker_summaries: [], decisions: [], conflicts: [], highlights: [], based_on_transcript_version: 0 }, searches: [], status: 'idle', error: null };
export function reduceEvent(state: State, event: MeetingEvent): State {
  switch (event.type) {
    case 'meeting.export': return { ...state, error: event.data.analysis_error || state.error };
    case 'transcript.final': {
      const entries = new Map(state.transcript.map(u => [u.id, u]));
      event.data.utterances.forEach(u => { if (!entries.has(u.id)) entries.set(u.id, u); });
      return { ...state, partial: null, transcript: [...entries.values()].sort((a, b) => a.start - b.start || a.end - b.end || a.id.localeCompare(b.id)) };
    }
    case 'transcript.partial': return { ...state, partial: event.data.text ? event.data : null };
    case 'analysis.updated': return event.data.based_on_transcript_version < state.analysis.based_on_transcript_version ? state : { ...state, analysis: event.data, error: null };
    case 'search.updated': return { ...state, searches: [...state.searches.filter(s => s.id !== event.data.id), event.data] };
    case 'status': return { ...state, status: event.data.state, partial: ['processing', 'stopped', 'error'].includes(event.data.state) ? null : state.partial };
    case 'error': return { ...state, error: `${event.data.scope}: ${event.data.message}` };
  }
}
