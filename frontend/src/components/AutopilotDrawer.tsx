import React, { useEffect } from 'react';
import { AutopilotStatus, ActionPlan } from '../types/meeting';
import { Play, Square, Loader2, CheckCircle2, AlertTriangle, Sparkles, Globe, Monitor, Share2, MessageSquare, Mail, Calendar } from 'lucide-react';

interface AutopilotDrawerProps {
  autopilotStatus: AutopilotStatus;
  selectedImageBase64?: string | null;
  onExecute: (plan: ActionPlan, imageBase64?: string) => void;
  onCancel: () => void;
}

export const AutopilotDrawer: React.FC<AutopilotDrawerProps> = ({
  autopilotStatus,
  selectedImageBase64,
  onExecute,
  onCancel,
}) => {
  const { isActive, status, step, message, plan } = autopilotStatus;

  // Keyboard shortcut Esc to cancel
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && (isActive || status === 'planning')) {
        onCancel();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isActive, status, onCancel]);

  if (!isActive && status === 'idle' && !plan) {
    return null;
  }

  const getPlatformIcon = (platform?: string) => {
    const p = (platform || '').toLowerCase();
    if (p.includes('twitter') || p.includes('x') || p.includes('social') || p.includes('linkedin')) {
      return <Share2 className="w-5 h-5 text-sky-400" />;
    }
    if (p.includes('whatsapp') || p.includes('telegram') || p.includes('chat') || p.includes('message')) {
      return <MessageSquare className="w-5 h-5 text-emerald-400" />;
    }
    if (p.includes('email') || p.includes('mail') || p.includes('gmail')) {
      return <Mail className="w-5 h-5 text-amber-400" />;
    }
    if (p.includes('calendar') || p.includes('schedule') || p.includes('meeting')) {
      return <Calendar className="w-5 h-5 text-purple-400" />;
    }
    return <Monitor className="w-5 h-5 text-indigo-400" />;
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 max-w-md w-full bg-slate-900/95 border border-indigo-500/40 rounded-2xl shadow-2xl backdrop-blur-xl p-5 text-slate-100 transition-all duration-300 animate-in slide-in-from-bottom-5">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-indigo-950/80 border border-indigo-700/50 flex items-center justify-center">
            {getPlatformIcon(plan?.platform)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                Parley Autopilot
              </h3>
              <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${
                status === 'running' ? 'bg-amber-950/80 text-amber-300 border-amber-800/80 animate-pulse' :
                status === 'completed' ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800/80' :
                status === 'failed' ? 'bg-rose-950/80 text-rose-300 border-rose-800/80' :
                'bg-indigo-950/80 text-indigo-300 border-indigo-800/80'
              }`}>
                {status}
              </span>
              {step && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                  {step}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">{plan?.platform || 'Device Action'}</p>
          </div>
        </div>

        <button
          onClick={onCancel}
          className="text-xs px-2.5 py-1 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
          title="Cancel Autopilot (Esc)"
        >
          Dismiss
        </button>
      </div>

      {/* Body description & status */}
      <div className="py-3 space-y-2">
        <p className="text-xs font-medium text-slate-200">
          {plan?.description || 'Autonomous Action Plan'}
        </p>

        {message && (
          <div className="flex items-start gap-2 bg-slate-950/60 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-300">
            {status === 'running' ? (
              <Loader2 className="w-4 h-4 text-indigo-400 animate-spin shrink-0 mt-0.5" />
            ) : status === 'completed' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            ) : status === 'failed' ? (
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            ) : (
              <Globe className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
            )}
            <span className="leading-relaxed">{message}</span>
          </div>
        )}

        {/* Media Preview if attached */}
        {selectedImageBase64 && (
          <div className="flex items-center gap-2 pt-1">
            <img
              src={`data:image/png;base64,${selectedImageBase64}`}
              alt="Attached preview"
              className="w-12 h-12 object-cover rounded-lg border border-slate-700 shadow-sm"
            />
            <span className="text-[11px] text-slate-400">1 image payload attached</span>
          </div>
        )}
      </div>

      {/* Action footer */}
      <div className="pt-2 flex items-center justify-between gap-3 border-t border-slate-800/80">
        <span className="text-[10px] text-slate-500">
          Press <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-700 rounded text-slate-400 font-mono">Esc</kbd> to emergency stop
        </span>

        <div className="flex items-center gap-2">
          {status === 'running' ? (
            <button
              onClick={onCancel}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg transition active:scale-95 shadow-md shadow-red-950/50"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              Stop Autopilot
            </button>
          ) : (
            plan && (
              <button
                onClick={() => onExecute(plan, selectedImageBase64 || undefined)}
                className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition active:scale-95 shadow-md shadow-indigo-950/50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                Run Autopilot Now
              </button>
            )
          )}
        </div>
      </div>
    </div>
  );
};
