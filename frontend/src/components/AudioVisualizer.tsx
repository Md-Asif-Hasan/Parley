import React from 'react';

interface AudioVisualizerProps {
  volume: number; // 0 to 1
  isRecording: boolean;
}

export const AudioVisualizer: React.FC<AudioVisualizerProps> = ({ volume, isRecording }) => {
  const bars = 5;

  return (
    <div className="flex items-center gap-1 h-5 px-2 py-1 bg-slate-900/60 border border-slate-800 rounded-md">
      {Array.from({ length: bars }).map((_, i) => {
        const threshold = (i + 1) / (bars + 1);
        const active = isRecording && volume >= threshold * 0.4;
        const height = isRecording
          ? Math.max(4, Math.min(18, Math.round(volume * 20 * (1 + (i % 2) * 0.5))))
          : 4;

        return (
          <div
            key={i}
            className={`w-1 rounded-full transition-all duration-75 ${
              active
                ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]'
                : 'bg-slate-700'
            }`}
            style={{ height: `${height}px` }}
          />
        );
      })}
    </div>
  );
};
