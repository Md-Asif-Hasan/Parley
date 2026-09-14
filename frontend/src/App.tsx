import React, { useCallback, useState, useEffect } from 'react';
import { useMeetingSocket } from './hooks/useMeetingSocket';
import { useAudioRecorder } from './hooks/useAudioRecorder';
import { Header } from './components/Header';
import { TranscriptPanel } from './components/TranscriptPanel';
import { SpeakerSummaries } from './components/SpeakerSummaries';
import { ConflictsPanel } from './components/ConflictsPanel';
import { DecisionsPanel } from './components/DecisionsPanel';
import { AskAIPanel } from './components/AskAIPanel';
import { AutopilotDrawer } from './components/AutopilotDrawer';
import { SettingsModal } from './components/SettingsModal';
import { AlertCircle, X, Sparkles, MessageSquare, Keyboard } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'analysis' | 'ask'>('analysis');
  const [showShortcutsHelp, setShowShortcutsHelp] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [activeImageBase64, setActiveImageBase64] = useState<string | null>(null);

  const {
    meetingState,
    partialTranscript,
    isConnected,
    highlightedUtteranceIds,
    isAskingAI,
    autopilotStatus,
    toastError,
    setToastError,
    startMeeting,
    stopMeeting,
    resetMeeting,
    renameSpeaker,
    askAgent,
    askMultimodal,
    executeAutopilot,
    cancelAutopilot,
    sendAudioChunk,
    startSimulation,
    highlightUtterances,
    clearHighlights,
  } = useMeetingSocket();

  const handleAudioChunk = useCallback(
    (chunk: Blob) => {
      sendAudioChunk(chunk);
    },
    [sendAudioChunk]
  );

  const {
    isRecording: isLiveRecording,
    volumeLevel,
    recordingError,
    startRecording,
    stopRecording,
  } = useAudioRecorder(handleAudioChunk);

  const handleStartLive = useCallback(async () => {
    clearHighlights();
    startMeeting(16000);
    await startRecording();
  }, [clearHighlights, startMeeting, startRecording]);

  const handleStopLive = useCallback(() => {
    stopRecording();
    stopMeeting();
  }, [stopRecording, stopMeeting]);

  const handleStartSimulation = useCallback(() => {
    stopRecording();
    clearHighlights();
    startSimulation();
  }, [stopRecording, clearHighlights, startSimulation]);

  const handleReset = useCallback(() => {
    stopRecording();
    resetMeeting();
  }, [stopRecording, resetMeeting]);

  const handleExport = useCallback(() => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(meetingState, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `parley_meeting_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  }, [meetingState]);

  // Global Desktop & Web Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeEl = document.activeElement;
      const isTyping = activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA');

      // Space to toggle recording (when not typing)
      if (e.code === 'Space' && !isTyping) {
        e.preventDefault();
        if (meetingState.status === 'recording') {
          handleStopLive();
        } else if (isConnected) {
          handleStartLive();
        }
      }

      // Ctrl/Cmd + E -> Export JSON
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'e') {
        e.preventDefault();
        handleExport();
      }

      // Ctrl/Cmd + K -> Focus Ask AI tab
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setActiveTab('ask');
        setTimeout(() => {
          const input = document.querySelector('form input[type="text"]') as HTMLInputElement;
          if (input) input.focus();
        }, 100);
      }

      // Ctrl/Cmd + S -> Toggle Simulation
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 's') {
        e.preventDefault();
        handleStartSimulation();
      }

      // ? key -> Toggle shortcut cheatsheet
      if (e.key === '?' && !isTyping) {
        setShowShortcutsHelp((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [meetingState.status, isConnected, handleStartLive, handleStopLive, handleExport, handleStartSimulation]);

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans select-none">
      <Header
        status={meetingState.status}
        statusMessage={meetingState.status_message}
        volume={volumeLevel}
        isLiveRecording={isLiveRecording}
        isConnected={isConnected}
        onStartLive={handleStartLive}
        onStopLive={handleStopLive}
        onStartSimulation={handleStartSimulation}
        onReset={handleReset}
        onExport={handleExport}
        onOpenSettings={() => setShowSettings(true)}
      />

      {/* Error Toasts / Warnings */}
      {(toastError || recordingError) && (
        <div className="mx-6 mt-3 px-4 py-2.5 bg-rose-950/80 border border-rose-700/60 rounded-lg flex items-center justify-between text-xs text-rose-200">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{toastError || recordingError}</span>
          </div>
          <div className="flex items-center gap-2">
            {(toastError?.includes('KEY') || toastError?.includes('key')) && (
              <button
                onClick={() => setShowSettings(true)}
                className="px-2 py-0.5 text-[11px] font-medium bg-rose-900/80 hover:bg-rose-800 text-rose-100 rounded border border-rose-600 transition"
              >
                Configure Keys ⚙️
              </button>
            )}
            <button
              onClick={() => setToastError(null)}
              className="p-1 hover:bg-rose-900/60 rounded text-rose-300"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Shortcuts Helper Modal */}
      {showShortcutsHelp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Keyboard className="w-5 h-5 text-sky-400" />
                <h3 className="text-sm font-bold text-white">Desktop Keyboard Shortcuts</h3>
              </div>
              <button onClick={() => setShowShortcutsHelp(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-2 text-xs text-slate-300">
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span>Toggle Live Recording</span>
                <kbd className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-[10px]">Space</kbd>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span>Focus Ask AI Tab &amp; Input</span>
                <kbd className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-[10px]">Ctrl / Cmd + K</kbd>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span>Export Meeting JSON</span>
                <kbd className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-[10px]">Ctrl / Cmd + E</kbd>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span>Run Mock Simulation</span>
                <kbd className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-[10px]">Ctrl + Shift + S</kbd>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Layout */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 p-4 lg:p-6 overflow-hidden min-h-0">
        {/* Left Column: Live Transcript (7 cols) */}
        <section className="lg:col-span-7 h-full min-h-0 flex flex-col">
          <TranscriptPanel
            transcript={meetingState.transcript}
            speakers={meetingState.speakers}
            partialText={partialTranscript}
            highlightedIds={highlightedUtteranceIds}
            onRenameSpeaker={renameSpeaker}
          />
        </section>

        {/* Right Column: Dynamic Analysis & Ask AI (5 cols) */}
        <section className="lg:col-span-5 h-full min-h-0 flex flex-col gap-4">
          {/* Tab Navigation */}
          <div className="flex items-center gap-1 bg-slate-900/60 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('analysis')}
              className={`flex-1 flex items-center justify-center gap-2 py-1.5 px-3 rounded-lg text-xs font-medium transition ${
                activeTab === 'analysis'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Live Insights &amp; Analysis
            </button>
            <button
              onClick={() => setActiveTab('ask')}
              className={`flex-1 flex items-center justify-center gap-2 py-1.5 px-3 rounded-lg text-xs font-medium transition ${
                activeTab === 'ask'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              Ask Parley AI ({meetingState.messages.length})
            </button>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto space-y-4">
            {activeTab === 'analysis' ? (
              <>
                <SpeakerSummaries
                  summaries={meetingState.analysis.speaker_summaries}
                  speakers={meetingState.speakers}
                />
                <ConflictsPanel
                  conflicts={meetingState.analysis.conflicts}
                  highlightedIds={highlightedUtteranceIds}
                  onHighlightUtterances={highlightUtterances}
                  onClearHighlight={clearHighlights}
                />
                <DecisionsPanel
                  decisions={meetingState.analysis.decisions}
                  highlightedIds={highlightedUtteranceIds}
                  onHighlightUtterances={highlightUtterances}
                  onClearHighlight={clearHighlights}
                />
              </>
            ) : (
              <div className="h-full">
                <AskAIPanel
                  messages={meetingState.messages}
                  isAsking={isAskingAI}
                  onAsk={askAgent}
                  onAskMultimodal={(q, img) => {
                    setActiveImageBase64(img || null);
                    askMultimodal(q, img);
                  }}
                  onExecutePlan={(plan, img) => executeAutopilot(plan, img || activeImageBase64 || undefined)}
                />
              </div>
            )}
          </div>
        </section>
      </main>

      {/* Floating Autopilot Status & Control Drawer */}
      <AutopilotDrawer
        autopilotStatus={autopilotStatus}
        selectedImageBase64={activeImageBase64}
        onExecute={(plan, img) => executeAutopilot(plan, img)}
        onCancel={cancelAutopilot}
      />

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
      />
    </div>
  );
};
