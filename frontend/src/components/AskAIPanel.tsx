import React, { useState } from 'react';
import { AgentMessage } from '../types/meeting';
import { Bot, Send, Sparkles, Loader2, User, Globe } from 'lucide-react';

interface AskAIPanelProps {
  messages: AgentMessage[];
  isAsking: boolean;
  onAsk: (question: string) => void;
}

const SUGGESTED_QUESTIONS = [
  'What were the main objections raised?',
  'What did QA say about the release timeline?',
  'What was the final decision?',
  'Search & explain technical terms mentioned in the meeting',
];

export const AskAIPanel: React.FC<AskAIPanelProps> = ({ messages, isAsking, onAsk }) => {
  const [inputVal, setInputVal] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputVal.trim() && !isAsking) {
      onAsk(inputVal.trim());
      setInputVal('');
    }
  };

  const handleSuggestionClick = (q: string) => {
    if (!isAsking) {
      onAsk(q);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900/80 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-semibold text-slate-200">Ask Parley AI</h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-2 py-0.5 rounded-full">
            <Globe className="w-3 h-3 text-emerald-400" />
            Exa Search Live
          </span>
          <span className="text-xs text-slate-400 hidden sm:inline">Grounded + Web</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center py-6 text-slate-500 text-center">
            <Sparkles className="w-8 h-8 mb-2 stroke-[1.5] text-sky-500/50" />
            <p className="text-sm font-medium text-slate-400">Ask anything or look up topics</p>
            <p className="text-xs text-slate-500 mt-1 max-w-xs">
              Parley analyzes speaker statements and uses Exa Neural Web Search to research unknown topics in real time.
            </p>

            <div className="mt-4 flex flex-wrap gap-1.5 justify-center max-w-sm">
              {SUGGESTED_QUESTIONS.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSuggestionClick(q)}
                  disabled={isAsking}
                  className="text-xs px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition active:scale-95 text-left"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, idx) => (
          <div key={idx} className="space-y-2">
            {/* User Question */}
            <div className="flex items-start gap-2 justify-end">
              <div className="bg-sky-600/90 text-white p-2.5 rounded-lg rounded-tr-none text-xs max-w-[85%] leading-relaxed">
                {m.question}
              </div>
              <div className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                <User className="w-3.5 h-3.5 text-slate-300" />
              </div>
            </div>

            {/* AI Answer */}
            <div className="flex items-start gap-2">
              <div className="w-6 h-6 rounded-full bg-sky-950 border border-sky-600/40 flex items-center justify-center shrink-0">
                <Bot className="w-3.5 h-3.5 text-sky-400" />
              </div>
              <div className="bg-slate-900/90 border border-slate-800 text-slate-100 p-3 rounded-lg rounded-tl-none text-xs max-w-[90%] leading-relaxed whitespace-pre-wrap">
                {m.answer}
              </div>
            </div>
          </div>
        ))}

        {isAsking && (
          <div className="flex items-start gap-2">
            <div className="w-6 h-6 rounded-full bg-sky-950 border border-sky-600/40 flex items-center justify-center shrink-0">
              <Bot className="w-3.5 h-3.5 text-sky-400" />
            </div>
            <div className="bg-slate-900 border border-slate-800 text-slate-300 p-3 rounded-lg text-xs flex items-center gap-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-400" />
              Parley is analyzing the meeting...
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="p-3 bg-slate-900/80 border-t border-slate-800 flex gap-2">
        <input
          type="text"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          placeholder="Ask a question about opinions, conflicts, or decisions..."
          className="flex-1 bg-slate-800 border border-slate-700 focus:border-sky-500 focus:ring-1 focus:ring-sky-500 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={!inputVal.trim() || isAsking}
          className="px-3 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-40 disabled:pointer-events-none text-white rounded-lg transition active:scale-95 flex items-center justify-center"
        >
          {isAsking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
        </button>
      </form>
    </div>
  );
};
