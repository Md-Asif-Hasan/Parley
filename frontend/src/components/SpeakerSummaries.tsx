import React from 'react';
import { SpeakerSummary } from '../types/meeting';
import { getSpeakerColor } from '../utils/colors';
import { Users, User } from 'lucide-react';

interface SpeakerSummariesProps {
  summaries: SpeakerSummary[];
  speakers: Record<string, string>;
}

export const SpeakerSummaries: React.FC<SpeakerSummariesProps> = ({ summaries, speakers }) => {
  return (
    <div className="flex flex-col bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900/80 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-semibold text-slate-200">Participant Views</h2>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
          {summaries.length} participants
        </span>
      </div>

      <div className="p-4 space-y-3 max-h-72 overflow-y-auto">
        {summaries.length === 0 ? (
          <div className="text-center py-6 text-slate-500 text-xs">
            No participant views generated yet. Analysis updates automatically every 15s.
          </div>
        ) : (
          summaries.map((s) => {
            const displayName = speakers[s.speaker_id] || s.speaker_id;
            const colors = getSpeakerColor(s.speaker_id);

            return (
              <div
                key={s.speaker_id}
                className={`p-3 rounded-lg border ${colors.bg} ${colors.border} transition duration-200`}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <User className="w-3.5 h-3.5 text-slate-400" />
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${colors.badge}`}>
                    {displayName}
                  </span>
                </div>
                <p className="text-xs text-slate-200 leading-relaxed pl-1">{s.summary}</p>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
