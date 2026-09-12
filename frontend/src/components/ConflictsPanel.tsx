import React from 'react';
import { Conflict } from '../types/meeting';
import { AlertTriangle, Calendar, Lightbulb, Link as LinkIcon } from 'lucide-react';

interface ConflictsPanelProps {
  conflicts: Conflict[];
  highlightedIds: string[];
  onHighlightUtterances: (utteranceIds: string[]) => void;
  onClearHighlight: () => void;
}

export const ConflictsPanel: React.FC<ConflictsPanelProps> = ({
  conflicts,
  highlightedIds,
  onHighlightUtterances,
  onClearHighlight,
}) => {
  return (
    <div className="flex flex-col bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900/80 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          <h2 className="text-sm font-semibold text-slate-200">Potential Conflicts</h2>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full bg-amber-950/60 text-amber-400 border border-amber-800/40 font-mono">
          {conflicts.length} flagged
        </span>
      </div>

      <div className="p-4 space-y-3 max-h-72 overflow-y-auto">
        {conflicts.length === 0 ? (
          <div className="text-center py-6 text-slate-500 text-xs">
            No conflicting proposals or scheduling constraints detected.
          </div>
        ) : (
          conflicts.map((c, idx) => {
            const isSelected =
              c.utterance_ids.length > 0 &&
              c.utterance_ids.every((id) => highlightedIds.includes(id));

            return (
              <div
                key={idx}
                className={`p-3 rounded-lg border transition-all duration-200 ${
                  isSelected
                    ? 'bg-amber-950/40 border-amber-500 ring-1 ring-amber-500/50'
                    : 'bg-slate-900/80 border-amber-900/30 hover:border-amber-700/50'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-1.5">
                    {c.type === 'schedule' ? (
                      <span className="flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-700/40">
                        <Calendar className="w-3 h-3" />
                        Schedule Conflict
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded bg-orange-950/80 text-orange-300 border border-orange-700/40">
                        <Lightbulb className="w-3 h-3" />
                        Proposal Incompatibility
                      </span>
                    )}
                  </div>

                  {c.utterance_ids.length > 0 && (
                    <div className="flex items-center gap-1">
                      <span className="text-[10px] text-slate-400 flex items-center gap-0.5">
                        <LinkIcon className="w-2.5 h-2.5" />
                        Sources:
                      </span>
                      {c.utterance_ids.map((uid) => (
                        <button
                          key={uid}
                          onClick={() => {
                            if (isSelected) {
                              onClearHighlight();
                            } else {
                              onHighlightUtterances(c.utterance_ids);
                            }
                          }}
                          className={`text-[10px] font-mono px-1.5 py-0.5 rounded transition ${
                            highlightedIds.includes(uid)
                              ? 'bg-amber-500 text-slate-950 font-bold'
                              : 'bg-slate-800 text-amber-400 hover:bg-slate-700 border border-amber-700/40'
                          }`}
                          title={`Click to view transcript ${uid}`}
                        >
                          {uid}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <p className="text-xs text-slate-200 leading-relaxed pl-0.5">{c.description}</p>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
