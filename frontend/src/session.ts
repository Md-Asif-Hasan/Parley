import { replayConversation } from './demo';
import type { MeetingEvent } from './state';

export function startSession(emit: (event: MeetingEvent) => void) {
  const socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/meeting`);
  let cancelReplay: (() => void) | undefined;
  let disposed = false;
  let stopping = false;
  let finished = false;
  let failed = false;
  emit({ type: 'status', data: { state: 'connecting' } });

  function failure(message: string) {
    if (failed || disposed) return;
    failed = true;
    cancelReplay?.();
    emit({ type: 'error', data: { scope: 'connection', message } });
    emit({ type: 'status', data: { state: 'error' } });
  }

  function stop() {
    if (stopping || finished || failed) return;
    stopping = true;
    cancelReplay?.();
    emit({ type: 'status', data: { state: 'processing' } });
    socket.send(JSON.stringify({ type: 'meeting.stop' }));
  }

  socket.onmessage = ({ data }) => {
    if (disposed) return;
    try {
      const event = JSON.parse(data) as MeetingEvent;
      if (event.type === 'meeting.export') finished = true;
      if (event.type === 'status' && event.data.state === 'error') {
        failed = true;
        cancelReplay?.();
      }
      emit(event);
      if (event.type === 'status' && event.data.state === 'recording' && !cancelReplay) {
        cancelReplay = replayConversation(input => {
          if (input.type === 'meeting.stop') stop();
          else if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(input));
          else failure('Backend disconnected. No substitute results are available.');
        });
      }
    } catch {
      failure('Could not read the backend event.');
      socket.close();
    }
  };
  socket.onerror = () => failure('Cannot connect to the Agent Loop backend on port 8000.');
  socket.onclose = () => {
    cancelReplay?.();
    if (!finished) failure('Connection closed before the meeting export arrived.');
  };
  return {
    stop,
    dispose() { disposed = true; cancelReplay?.(); socket.close(); },
  };
}
