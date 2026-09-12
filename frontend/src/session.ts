import type { MeetingEvent } from './state';

export function startSession(emit: (event: MeetingEvent) => void) {
  let socket: WebSocket | undefined;
  let stream: MediaStream | undefined;
  let recorder: MediaRecorder | undefined;
  let disposed = false;
  let stopping = false;
  let finished = false;
  let failed = false;
  emit({ type: 'status', data: { state: 'connecting' } });

  function releaseMicrophone() {
    if (recorder && recorder.state !== 'inactive') recorder.stop();
    stream?.getTracks().forEach(track => track.stop());
  }
  function failure(message: string) {
    if (failed || disposed) return;
    failed = true;
    releaseMicrophone();
    socket?.close();
    emit({ type: 'error', data: { scope: 'voice input', message } });
    emit({ type: 'status', data: { state: 'error' } });
  }
  function stop() {
    if (stopping || finished || failed || !recorder) return;
    stopping = true;
    emit({ type: 'status', data: { state: 'processing' } });
    // stop() emits the final dataavailable BEFORE onstop. Blob sends preserve order.
    recorder.stop();
  }
  async function connect() {
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
        throw new Error('Microphone recording requires a supported browser on localhost or HTTPS.');
      }
      const mimeType = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4'].find(type => MediaRecorder.isTypeSupported(type));
      if (!mimeType) throw new Error('This browser has no supported microphone recording format.');
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (disposed) { releaseMicrophone(); return; }
      stream.getAudioTracks().forEach(track => track.onended = () => {
        if (!stopping) failure('Microphone disconnected or permission was revoked.');
      });
      socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/meeting`);
      socket.onmessage = ({ data }) => {
        if (disposed) return;
        try {
          const event = JSON.parse(data) as MeetingEvent;
          if (event.type === 'meeting.export') finished = true;
          if (event.type === 'status' && event.data.state === 'processing' && !stopping) {
            stopping = true;
            releaseMicrophone();
          }
          if (event.type === 'status' && event.data.state === 'error') {
            failed = true;
            releaseMicrophone();
          }
          if (event.type === 'status' && event.data.state === 'recording' && !recorder) {
            recorder = new MediaRecorder(stream!, { mimeType });
            recorder.ondataavailable = ({ data: audio }) => {
              if (!audio.size || disposed || failed) return;
              if (socket?.readyState !== WebSocket.OPEN) { failure('Audio connection closed unexpectedly.'); return; }
              socket.send(audio);
            };
            recorder.onstop = () => {
              stream?.getTracks().forEach(track => track.stop());
              if (!disposed && !failed && stopping && socket?.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ type: 'meeting.stop' }));
              }
            };
            recorder.onerror = () => failure('The browser could not record microphone audio.');
            recorder.start(250);
          }
          emit(event);
        } catch (error) {
          failure(error instanceof Error ? error.message : 'Could not process the voice session.');
        }
      };
      socket.onerror = () => failure('Cannot connect to the voice backend on port 8000.');
      socket.onclose = () => {
        if (!finished) failure('Connection closed before the meeting export arrived.');
        releaseMicrophone();
      };
    } catch (error) {
      failure(error instanceof Error ? error.message : 'Unable to access the microphone.');
    }
  }
  void connect();
  return { stop, dispose() { disposed = true; releaseMicrophone(); socket?.close(); } };
}
