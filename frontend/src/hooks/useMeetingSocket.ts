import { useState, useEffect, useRef, useCallback } from 'react';
import { MeetingState, MeetingStatus, Utterance, AnalysisResult, WSEvent } from '../types/meeting';

const INITIAL_STATE: MeetingState = {
  transcript: [],
  speakers: {},
  analysis: {
    speaker_summaries: [],
    conflicts: [],
    decisions: []
  },
  messages: [],
  status: 'idle',
  status_message: undefined
};

export function useMeetingSocket() {
  const [meetingState, setMeetingState] = useState<MeetingState>(INITIAL_STATE);
  const [partialTranscript, setPartialTranscript] = useState<string>('');
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [highlightedUtteranceIds, setHighlightedUtteranceIds] = useState<string[]>([]);
  const [isAskingAI, setIsAskingAI] = useState<boolean>(false);
  const [toastError, setToastError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);

  const connect = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.port === '5173' ? 'localhost:8000' : window.location.host;
    const wsUrl = `${protocol}//${host}/ws/meeting`;

    console.log('[Parley] Connecting to WebSocket:', wsUrl);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[Parley] WebSocket connected.');
      setIsConnected(true);
      setToastError(null);
    };

    ws.onclose = () => {
      console.log('[Parley] WebSocket closed. Retrying in 2s...');
      setIsConnected(false);
      reconnectTimeoutRef.current = setTimeout(connect, 2000);
    };

    ws.onerror = (err) => {
      console.error('[Parley] WebSocket error:', err);
    };

    ws.onmessage = (event) => {
      try {
        const payload: WSEvent = JSON.parse(event.data);
        const { type, data } = payload;

        switch (type) {
          case 'state.init':
            setMeetingState((prev) => ({
              ...prev,
              ...data,
              analysis: data.analysis || prev.analysis,
            }));
            break;

          case 'status':
            setMeetingState((prev) => ({
              ...prev,
              status: data.state as MeetingStatus,
              status_message: data.message,
            }));
            break;

          case 'transcript.partial':
            setPartialTranscript(data.text || '');
            break;

          case 'transcript.final':
            const newUtterances: Utterance[] = data.utterances || [];
            setMeetingState((prev) => {
              // Deduplicate by ID
              const existingIds = new Set(prev.transcript.map((u) => u.id));
              const filtered = newUtterances.filter((u) => !existingIds.has(u.id));
              return {
                ...prev,
                transcript: [...prev.transcript, ...filtered],
              };
            });
            break;

          case 'analysis.updated':
            setMeetingState((prev) => ({
              ...prev,
              analysis: data as AnalysisResult,
            }));
            break;

          case 'speaker.updated':
            setMeetingState((prev) => ({
              ...prev,
              speakers: data.speakers || prev.speakers,
            }));
            break;

          case 'agent.answer':
            setIsAskingAI(false);
            setMeetingState((prev) => ({
              ...prev,
              messages: [
                ...prev.messages,
                {
                  request_id: data.request_id,
                  question: data.question || '',
                  answer: data.text,
                  timestamp: Date.now() / 1000,
                },
              ],
            }));
            break;

          case 'meeting.reset':
            setMeetingState({
              ...INITIAL_STATE,
              ...data,
            });
            setPartialTranscript('');
            setHighlightedUtteranceIds([]);
            break;

          case 'error':
            console.warn('[Parley Error]', data.message);
            setToastError(data.message);
            break;

          default:
            console.log('[Parley Unhandled Event]', type, data);
        }
      } catch (err) {
        console.error('[Parley] Error handling message:', err);
      }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  const sendEvent = useCallback((type: string, data: any = {}) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, data }));
    } else {
      console.warn('[Parley] Cannot send event: WebSocket is not open', type);
    }
  }, []);

  const sendAudioChunk = useCallback((chunk: ArrayBuffer | Blob) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(chunk);
    }
  }, []);

  const startMeeting = useCallback((sampleRate: number = 16000, encoding?: string) => {
    sendEvent('meeting.start', { sample_rate: sampleRate, encoding });
  }, [sendEvent]);

  const stopMeeting = useCallback(() => {
    sendEvent('meeting.stop');
  }, [sendEvent]);

  const resetMeeting = useCallback(() => {
    sendEvent('meeting.reset');
  }, [sendEvent]);

  const renameSpeaker = useCallback((speakerId: string, name: string) => {
    sendEvent('speaker.rename', { speaker_id: speakerId, name });
  }, [sendEvent]);

  const askAgent = useCallback((question: string) => {
    const requestId = `req_${Date.now()}`;
    setIsAskingAI(true);
    sendEvent('agent.ask', { request_id: requestId, question });
  }, [sendEvent]);

  const startSimulation = useCallback(() => {
    sendEvent('simulation.start');
  }, [sendEvent]);

  const highlightUtterances = useCallback((utteranceIds: string[]) => {
    setHighlightedUtteranceIds(utteranceIds);
  }, []);

  const clearHighlights = useCallback(() => {
    setHighlightedUtteranceIds([]);
  }, []);

  return {
    meetingState,
    partialTranscript,
    isConnected,
    highlightedUtteranceIds,
    isAskingAI,
    toastError,
    setToastError,
    startMeeting,
    stopMeeting,
    resetMeeting,
    renameSpeaker,
    askAgent,
    sendAudioChunk,
    startSimulation,
    highlightUtterances,
    clearHighlights,
  };
}
