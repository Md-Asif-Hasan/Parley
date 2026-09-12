import React, { useState, useRef } from 'react';
import { AgentMessage, ActionPlan } from '../types/meeting';
import { Bot, Send, Sparkles, Loader2, User, Globe, Image as ImageIcon, X, Play, ArrowUpRight } from 'lucide-react';

interface AskAIPanelProps {
  messages: AgentMessage[];
  isAsking: boolean;
  onAsk: (question: string) => void;
  onAskMultimodal?: (question: string, imageBase64?: string) => void;
  onExecutePlan?: (plan: ActionPlan, imageBase64?: string) => void;
}

const SUGGESTED_QUESTIONS = [
  'Post meeting summary to Twitter/X',
  'Send WhatsApp message with key updates',
  'What were the main objections raised?',
  'Search & explain technical terms mentioned',
];

export const AskAIPanel: React.FC<AskAIPanelProps> = ({
  messages,
  isAsking,
  onAsk,
  onAskMultimodal,
  onExecutePlan,
}) => {
  const [inputVal, setInputVal] = useState('');
  const [selectedImageBase64, setSelectedImageBase64] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const base64 = event.target?.result as string;
        setSelectedImageBase64(base64);
      };
      reader.readAsDataURL(file);
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (items) {
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          const file = items[i].getAsFile();
          if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
              const base64 = event.target?.result as string;
              setSelectedImageBase64(base64);
            };
            reader.readAsDataURL(file);
            break;
          }
        }
      }
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const base64 = event.target?.result as string;
        setSelectedImageBase64(base64);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if ((inputVal.trim() || selectedImageBase64) && !isAsking) {
      if (onAskMultimodal) {
        onAskMultimodal(inputVal.trim(), selectedImageBase64 || undefined);
      } else {
        onAsk(inputVal.trim());
      }
      setInputVal('');
      setSelectedImageBase64(null);
    }
  };

  const handleSuggestionClick = (q: string) => {
    if (!isAsking) {
      if (onAskMultimodal && selectedImageBase64) {
        onAskMultimodal(q, selectedImageBase64);
        setSelectedImageBase64(null);
      } else {
        onAsk(q);
      }
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`flex flex-col h-full bg-slate-900/50 border rounded-xl overflow-hidden shadow-lg transition-colors ${
        isDragging ? 'border-indigo-500 bg-indigo-950/20' : 'border-slate-800'
      }`}
    >
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900/80 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-semibold text-slate-200">Ask Parley & Autopilot</h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-2 py-0.5 rounded-full">
            <Globe className="w-3 h-3 text-emerald-400" />
            Exa Web Live
          </span>
          <span className="text-xs text-slate-400 hidden sm:inline">Multimodal</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center py-6 text-slate-500 text-center">
            <Sparkles className="w-8 h-8 mb-2 stroke-[1.5] text-indigo-500/50" />
            <p className="text-sm font-medium text-slate-300">Ask anything, upload images, or trigger Autopilot</p>
            <p className="text-xs text-slate-500 mt-1 max-w-xs">
              Drop an image or ask Parley to post to social media, send messages, or research topics.
            </p>

            <div className="mt-4 flex flex-wrap gap-1.5 justify-center max-w-sm">
              {SUGGESTED_QUESTIONS.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSuggestionClick(q)}
                  disabled={isAsking}
                  className="text-xs px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition active:scale-95 text-left flex items-center gap-1"
                >
                  {q}
                  <ArrowUpRight className="w-3 h-3 text-slate-500" />
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
                {m.image && (
                  <img
                    src={m.image.startsWith('data:') ? m.image : `data:image/png;base64,${m.image}`}
                    alt="Attached"
                    className="mt-2 rounded max-h-32 object-cover border border-white/20"
                  />
                )}
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

                {/* Detected Action Plan trigger */}
                {m.action_plan && (
                  <div className="mt-3 p-2.5 bg-indigo-950/60 border border-indigo-700/60 rounded-lg flex items-center justify-between gap-2">
                    <div>
                      <p className="text-[11px] font-bold text-indigo-300 flex items-center gap-1">
                        <Sparkles className="w-3 h-3 text-indigo-400" />
                        Autopilot Plan: {m.action_plan.platform}
                      </p>
                      <p className="text-[10px] text-slate-400 mt-0.5">{m.action_plan.description}</p>
                    </div>
                    {onExecutePlan && (
                      <button
                        onClick={() => onExecutePlan(m.action_plan!, selectedImageBase64 || undefined)}
                        className="px-2.5 py-1 text-[11px] font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-md transition active:scale-95 flex items-center gap-1 shadow-sm shrink-0"
                      >
                        <Play className="w-3 h-3 fill-current" />
                        Execute
                      </button>
                    )}
                  </div>
                )}
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
              Parley is analyzing and preparing action...
            </div>
          </div>
        )}
      </div>

      {/* Image Preview Strip */}
      {selectedImageBase64 && (
        <div className="px-3 pt-2 bg-slate-900/90 border-t border-slate-800/80 flex items-center gap-2">
          <div className="relative group inline-block">
            <img
              src={selectedImageBase64}
              alt="Preview"
              className="w-12 h-12 object-cover rounded-lg border border-indigo-500/60 shadow-md"
            />
            <button
              onClick={() => setSelectedImageBase64(null)}
              className="absolute -top-1.5 -right-1.5 bg-red-600 text-white rounded-full p-0.5 hover:bg-red-700 transition"
              title="Remove image"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
          <span className="text-[11px] text-slate-400">Image attached (Ready to post/analyze)</span>
        </div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="p-3 bg-slate-900/80 border-t border-slate-800 flex gap-2">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="image/*"
          className="hidden"
        />

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className={`p-2 rounded-lg border transition ${
            selectedImageBase64
              ? 'bg-indigo-950 text-indigo-300 border-indigo-700'
              : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200'
          }`}
          title="Attach an image (or paste with Ctrl+V)"
        >
          <ImageIcon className="w-4 h-4" />
        </button>

        <input
          type="text"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onPaste={handlePaste}
          placeholder="Ask a question, paste an image, or order an autopilot action..."
          className="flex-1 bg-slate-800 border border-slate-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none"
        />

        <button
          type="submit"
          disabled={(!inputVal.trim() && !selectedImageBase64) || isAsking}
          className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:pointer-events-none text-white rounded-lg transition active:scale-95 flex items-center justify-center shadow-md shadow-indigo-950/40"
        >
          {isAsking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
        </button>
      </form>
    </div>
  );
};
