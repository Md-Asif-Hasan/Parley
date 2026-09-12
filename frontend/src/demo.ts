import type { MeetingEvent, Utterance } from './state';

const lines: Utterance[] = [
  { id: 'u1', speaker_id: 'speaker_0', start: 0, end: 5, text: 'What if our meeting notes were a shared canvas? Every idea becomes a card, colored by who said it.' },
  { id: 'u2', speaker_id: 'speaker_1', start: 5, end: 10, text: 'Yes, and when someone suggests an idea, we could find similar open-source projects to build on.' },
  { id: 'u3', speaker_id: 'speaker_2', start: 10, end: 15, text: 'Please write this down: one shared microphone, and we need to know whose idea is whose.' },
  { id: 'u4', speaker_id: 'speaker_0', start: 15, end: 20, text: 'The venue Wi-Fi can drop out. That could interrupt the live demo, so we should test it there first.' },
  { id: 'u5', speaker_id: 'speaker_1', start: 20, end: 25, text: 'Let’s keep the first version focused: transcript, a running summary, references, and highlights.' },
  { id: 'u6', speaker_id: 'speaker_2', start: 25, end: 30, text: 'Agreed on those four sections for the prototype. We can explore the other ideas afterward.' },
];

// Only speech is simulated. No analysis, highlights, or search results live here.
export function replayConversation(send: (event: MeetingEvent | { type: 'meeting.stop' }) => void): () => void {
  const timers: ReturnType<typeof setTimeout>[] = [];
  lines.forEach((u, i) => {
    timers.push(setTimeout(() => send({ type: 'transcript.partial', data: {
      speaker_id: u.speaker_id, text: u.text.slice(0, Math.floor(u.text.length * .6)) + '…',
    } }), i * 5000 + 500));
    timers.push(setTimeout(() => send({ type: 'transcript.final', data: { utterances: [u] } }), (i + 1) * 5000));
  });
  timers.push(setTimeout(() => send({ type: 'meeting.stop' }), 33000));
  return () => timers.forEach(clearTimeout);
}
