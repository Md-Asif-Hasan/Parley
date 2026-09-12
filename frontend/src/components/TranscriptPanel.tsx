import React, { useState, useRef, useEffect } from 'react';
import { Utterance } from '../types/meeting';
import { getSpeakerColor } from '../utils/colors';
import { Edit2, Check, X, MessageSquare, Clock, Volume2 } from 'lucide-react';

interface TranscriptPanelProps {
  transcript: Utterance[];
  speakers: Record<string, string>;
  partialText: string;
  highlightedIds: string[];
  onRenameSpeaker: (speakerId: string, newName: string) => void;
}

export const TranscriptPanel: React.FC<TranscriptPanelProps> = ({
  transcript,
  speakers,
  partialText,
  highlightedIds,
  onRenameSpeaker,
}) => {
  const [editingSpeakerId, setEditingSpeakerId] = useState<string | null>(null);
  const [editNameValue, setEditNameValue] = useState<string>('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new transcript entries if user is near bottom
  useEffect(() => {
    if (bottomRef.current && highlightedIds.length === 0) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcript.length, partialText]);

  // Scroll to highlighted element when selected
  useEffect(() => {
    if (highlightedIds.length > 0) {
      const firstId = highlightedIds[0];
      const el = document.getElementById(`utterance-${firstId}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [highlightedIds]);

  const handleStartEdit = (speakerId: string, currentName: string) => {
    setEditingSpeakerId(speakerId);
    setEditNameValue(currentName);
  };

  const handleSaveEdit = (speakerId: string) => {
    if (editNameValue.trim()) {
      onRenameSpeaker(speakerId, editNameValue.trim());
    }
    setEditingSpeakerId(null);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900/80 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-semibold text-slate-200">Live Transcript</h2>
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
            {transcript.length} utterances
          </span>
        </div>
        {highlightedIds.length > 0 && (
          <span className="text-xs text-amber-400 bg-amber-950/60 border border-amber-800/50 px-2 py-0.5 rounded">
            Filtered by reference: {highlightedIds.join(', ')}
          </span>
        )}
      </div>

      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {transcript.length === 0 && !partialText && (
          <div className="flex flex-col items-center justify-center h-48 text-slate-500 text-center">
            <MessageSquare className="w-8 h-8 mb-2 stroke-[1.5] opacity-50" />
            <p className="text-sm font-medium">No speech recorded yet.</p>
            <p className="text-xs text-slate-600 mt-1 max-w-xs">
              Click &quot;Start Live Mic&quot; or &quot;Run Simulation&quot; to begin capturing discussion.
            </p>
          </div>
        )}

        {transcript.map((u) => {
          const speakerId = u.speaker_id;
          const displayName = speakerId ? speakers[speakerId] || speakerId : 'Unknown Speaker';
          const colors = getSpeakerColor(speakerId);
          const isHighlighted = highlightedIds.includes(u.id);

          return (
            <div
              id={`utterance-${u.id}`}
              key={u.id}
              className={`group relative p-3 rounded-lg border transition-all duration-300 ${
                isHighlighted
                  ? 'bg-amber-950/30 border-amber-500 ring-2 ring-amber-500/40 shadow-lg'
                  : `${colors.bg} ${colors.border}`
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded">
                    {u.id}
                  </span>

                  {speakerId && editingSpeakerId === speakerId ? (
                    <div className="flex items-center gap-1">
                      <input
                        type="text"
                        value={editNameValue}
                        onChange={(e) => setEditNameValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveEdit(speakerId);
                          if (e.key === 'Escape') setEditingSpeakerId(null);
                        }}
                        autoFocus
                        className="text-xs px-2 py-0.5 bg-slate-800 border border-sky-500 rounded text-slate-100 focus:outline-none"
                      />
                      <button
                        onClick={() => handleSaveEdit(speakerId)}
                        className="p-1 text-emerald-400 hover:bg-slate-800 rounded"
                        title="Save name"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => setEditingSpeakerId(null)}
                        className="p-1 text-slate-400 hover:bg-slate-800 rounded"
                        title="Cancel"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${colors.badge}`}>
                        {displayName}
                      </span>
                      {speakerId && (
                        <button
                          onClick={() => handleStartEdit(speakerId, displayName)}
                          className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-sky-300 transition"
                          title="Rename speaker"
                        >
                          <Edit2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-1 text-[11px] text-slate-400 font-mono">
                  <Clock className="w-3 h-3 text-slate-500" />
                  <span>{formatTime(u.start)} - {formatTime(u.end)}</span>
                </div>
              </div>

              <p className="text-sm text-slate-100 leading-relaxed pl-1">{u.text}</p>
            </div>
          );
        })}

        {/* Live Interim / Draft Caption */}
        {partialText && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-sky-950/20 border border-sky-600/30 text-sky-200 animate-pulse">
            <Volume2 className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="text-[10px] uppercase font-bold text-sky-400 tracking-wider">
                Live Drafting...
              </span>
              <p className="text-sm italic text-sky-100">{partialText}</p>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
};
