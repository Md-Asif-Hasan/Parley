import { Mic, Square, Download, RefreshCw, Sparkles, AlertCircle, Settings as SettingsIcon } from 'lucide-react';
import { MeetingStatus } from '../types/meeting';
import { AudioVisualizer } from './AudioVisualizer';

interface HeaderProps {
  status: MeetingStatus;
  statusMessage?: string;
  volume: number;
  isLiveRecording: boolean;
  isConnected: boolean;
  onStartLive: () => void;
  onStopLive: () => void;
  onStartSimulation: () => void;
  onReset: () => void;
  onExport: () => void;
  onOpenSettings?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  status,
  statusMessage,
  volume,
  isLiveRecording,
  isConnected,
  onStartLive,
  onStopLive,
  onStartSimulation,
  onReset,
  onExport,
  onOpenSettings,
}) => {
  const getStatusBadge = () => {
    switch (status) {
      case 'recording':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-red-400 bg-red-950/60 border border-red-800/60 rounded-full animate-pulse">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
            Live Recording
          </span>
        );
      case 'processing':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-amber-300 bg-amber-950/60 border border-amber-800/60 rounded-full">
            <RefreshCw className="w-3 h-3 animate-spin text-amber-400" />
            {statusMessage || 'Analyzing...'}
          </span>
        );
      case 'stopped':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-slate-300 bg-slate-800/80 border border-slate-700 rounded-full">
            {statusMessage || 'Meeting Ended'}
          </span>
        );
      case 'error':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-rose-300 bg-rose-950/60 border border-rose-800 rounded-full">
            <AlertCircle className="w-3 h-3" />
            {statusMessage || 'Error'}
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-slate-400 bg-slate-900 border border-slate-800 rounded-full">
            <span className="w-2 h-2 rounded-full bg-slate-500" />
            {statusMessage || 'Idle'}
          </span>
        );
    }
  };

  return (
    <header className="flex flex-col md:flex-row items-center justify-between gap-4 px-6 py-4 bg-slate-900/90 border-b border-slate-800 backdrop-blur-md sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-10 h-10 rounded-xl overflow-hidden shadow-md shadow-sky-900/40 border border-slate-700/60 bg-slate-800">
          <img src="/logo.jpg" alt="Parley Logo" className="w-full h-full object-cover" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-white">Parley</h1>
            <span className="text-[10px] uppercase font-semibold tracking-wider px-1.5 py-0.5 rounded bg-sky-900/60 text-sky-300 border border-sky-700/50">
              MVP
            </span>
          </div>
          <p className="text-xs text-slate-400">Real-time meeting listener &amp; opinion analyzer</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          {getStatusBadge()}
          <AudioVisualizer volume={volume} isRecording={isLiveRecording} />
          {!isConnected && (
            <span className="text-xs text-rose-400 bg-rose-950/40 px-2 py-0.5 rounded border border-rose-900">
              Disconnected
            </span>
          )}
        </div>

        <div className="h-6 w-px bg-slate-800 hidden sm:block" />

        <div className="flex items-center gap-2">
          {status === 'recording' ? (
            <button
              onClick={onStopLive}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-700 active:scale-95 transition rounded-lg shadow-sm shadow-red-900/30"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              Stop Recording
            </button>
          ) : (
            <button
              onClick={onStartLive}
              disabled={!isConnected}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-white bg-sky-600 hover:bg-sky-500 disabled:opacity-50 disabled:pointer-events-none active:scale-95 transition rounded-lg shadow-sm shadow-sky-900/30"
            >
              <Mic className="w-3.5 h-3.5" />
              Start Live Mic
            </button>
          )}

          <button
            onClick={onStartSimulation}
            disabled={status === 'recording' || !isConnected}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-indigo-200 bg-indigo-950/60 hover:bg-indigo-900/80 border border-indigo-700/50 disabled:opacity-40 disabled:pointer-events-none transition rounded-lg"
            title="Simulate a real-time conversation scenario without microphone"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            Run Simulation
          </button>

          <button
            onClick={onExport}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 active:scale-95 transition rounded-lg border border-slate-700"
            title="Download meeting transcript and analysis as JSON"
          >
            <Download className="w-3.5 h-3.5" />
            Export JSON
          </button>

          <button
            onClick={onReset}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition rounded-lg"
            title="Reset meeting state"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>

          {onOpenSettings && (
            <button
              onClick={onOpenSettings}
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition rounded-lg"
              title="API Keys & Settings"
            >
              <SettingsIcon className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
