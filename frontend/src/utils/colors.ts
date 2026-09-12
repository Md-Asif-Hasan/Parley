export interface SpeakerColor {
  bg: string;
  text: string;
  border: string;
  badge: string;
  accent: string;
}

const PALETTE: SpeakerColor[] = [
  {
    bg: 'bg-blue-950/40',
    text: 'text-blue-200',
    border: 'border-blue-700/50',
    badge: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    accent: '#3b82f6',
  },
  {
    bg: 'bg-emerald-950/40',
    text: 'text-emerald-200',
    border: 'border-emerald-700/50',
    badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    accent: '#10b981',
  },
  {
    bg: 'bg-amber-950/40',
    text: 'text-amber-200',
    border: 'border-amber-700/50',
    badge: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    accent: '#f59e0b',
  },
  {
    bg: 'bg-purple-950/40',
    text: 'text-purple-200',
    border: 'border-purple-700/50',
    badge: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
    accent: '#a855f7',
  },
  {
    bg: 'bg-rose-950/40',
    text: 'text-rose-200',
    border: 'border-rose-700/50',
    badge: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
    accent: '#f43f5e',
  },
  {
    bg: 'bg-cyan-950/40',
    text: 'text-cyan-200',
    border: 'border-cyan-700/50',
    badge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
    accent: '#06b6d4',
  },
];

export function getSpeakerColor(speakerId: string | null): SpeakerColor {
  if (!speakerId) {
    return {
      bg: 'bg-slate-900/40',
      text: 'text-slate-300',
      border: 'border-slate-700/40',
      badge: 'bg-slate-700/30 text-slate-300 border-slate-600/30',
      accent: '#64748b',
    };
  }

  // Extract number if speaker_X or hash string
  const match = speakerId.match(/\d+/);
  if (match) {
    const idx = parseInt(match[0], 10) % PALETTE.length;
    return PALETTE[idx];
  }

  let hash = 0;
  for (let i = 0; i < speakerId.length; i++) {
    hash = (hash << 5) - hash + speakerId.charCodeAt(i);
    hash |= 0;
  }
  const idx = Math.abs(hash) % PALETTE.length;
  return PALETTE[idx];
}
