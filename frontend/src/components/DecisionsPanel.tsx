import React from 'react';
import { Decision } from '../types/meeting';
import { CheckCircle2, Link as LinkIcon } from 'lucide-react';

interface DecisionsPanelProps {
  decisions: Decision[];
  highlightedIds: string[];
  onHighlightUtterances: (utteranceIds: string[]) => void;
  onClearHighlight: () => void;
}

export const DecisionsPanel: React.FC<DecisionsPanelProps> = ({
  decisions,
  highlightedIds,
  onHighlightUtterances,
  onClearHighlight,
}) => {
  return (
    <div className="flex flex-col bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900/80 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-semibold text-slate-200">Agreed Decisions</h2>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-950/60 text-emerald-400 border border-emerald-800/40 font-mono">
          {decisions.length} agreed
        </span>
      </div>

      <div className="p-4 space-y-3 max-h-72 overflow-y-auto">
        {decisions.length === 0 ? (
          <div className="text-center py-6 text-slate-500 text-xs">
            No explicit consensus or decisions reached yet.
          </div>
        ) : (
          decisions.map((d, idx) => {
            const isSelected =
              d.utterance_ids.length > 0 &&
              d.utterance_ids.every((id) => highlightedIds.includes(id));

            return (
              <div
                key={idx}
                className={`p-3 rounded-lg border transition-all duration-200 ${
                  isSelected
                    ? 'bg-emerald-950/40 border-emerald-500 ring-1 ring-emerald-500/50'
                    : 'bg-slate-900/80 border-emerald-900/30 hover:border-emerald-700/50'
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <div className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                    <p className="text-xs text-slate-100 font-medium leading-relaxed">{d.description}</p>
                  </div>

                  {d.utterance_ids.length > 0 && (
                    <div className="flex items-center gap-1 shrink-0 ml-2">
                      <span className="text-[10px] text-slate-400 flex items-center gap-0.5">
                        <LinkIcon className="w-2.5 h-2.5" />
                      </span>
                      {d.utterance_ids.map((uid) => (
                        <button
                          key={uid}
                          onClick={() => {
                            if (isSelected) {
                              onClearHighlight();
                            } else {
                              onHighlightUtterances(d.utterance_ids);
                            }
                          }}
                          className={`text-[10px] font-mono px-1.5 py-0.5 rounded transition ${
                            highlightedIds.includes(uid)
                              ? 'bg-emerald-500 text-slate-950 font-bold'
                              : 'bg-slate-800 text-emerald-400 hover:bg-slate-700 border border-emerald-700/40'
                          }`}
                          title={`Click to view transcript ${uid}`}
                        >
                          {uid}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
