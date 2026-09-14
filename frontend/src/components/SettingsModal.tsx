import React, { useState, useEffect } from 'react';
import { X, Key, CheckCircle2, AlertCircle, ExternalLink, Save, ShieldCheck } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface KeyStatus {
  has_deepgram_key: boolean;
  has_deepseek_key: boolean;
  has_exa_key: boolean;
  deepgram_key_masked?: string;
  deepseek_key_masked?: string;
  exa_key_masked?: string;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [deepgramKey, setDeepgramKey] = useState('');
  const [deepseekKey, setDeepseekKey] = useState('');
  const [exaKey, setExaKey] = useState('');
  const [status, setStatus] = useState<KeyStatus | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchSettings = async () => {
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        const data: KeyStatus = await res.json();
        setStatus(data);
      }
    } catch (err) {
      console.error('Failed to fetch settings:', err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchSettings();
      setMessage(null);
    }
  }, [isOpen]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    const payload: Record<string, string> = {};
    if (deepgramKey.trim()) payload.deepgram_api_key = deepgramKey.trim();
    if (deepseekKey.trim()) payload.deepseek_api_key = deepseekKey.trim();
    if (exaKey.trim()) payload.exa_api_key = exaKey.trim();

    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const updated = await res.json();
        setStatus(updated);
        setMessage({ type: 'success', text: 'API keys saved successfully!' });
        setDeepgramKey('');
        setDeepseekKey('');
        setExaKey('');
        setTimeout(() => {
          fetchSettings();
        }, 1000);
      } else {
        setMessage({ type: 'error', text: 'Failed to save settings.' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Network error while saving settings.' });
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/80">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-400">
              <Key className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">API Keys & Engine Settings</h2>
              <p className="text-xs text-slate-400">Configure speech diarization, AI intelligence, and web search</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className="p-6 space-y-5 overflow-y-auto max-h-[75vh]">
          {message && (
            <div
              className={`flex items-center gap-2 px-3.5 py-2.5 rounded-xl text-xs font-medium ${
                message.type === 'success'
                  ? 'bg-emerald-950/60 border border-emerald-800/60 text-emerald-300'
                  : 'bg-rose-950/60 border border-rose-800/60 text-rose-300'
              }`}
            >
              {message.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
              {message.text}
            </div>
          )}

          {/* Deepgram API Key */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-slate-200 flex items-center gap-1.5">
                <span>Deepgram API Key</span>
                <span className="text-[10px] text-slate-400 font-normal">(Nova-3 Streaming Diarization)</span>
              </label>
              {status?.has_deepgram_key ? (
                <span className="flex items-center gap-1 text-[11px] font-medium text-emerald-400">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Configured ({status.deepgram_key_masked})
                </span>
              ) : (
                <span className="flex items-center gap-1 text-[11px] font-medium text-rose-400">
                  <AlertCircle className="w-3.5 h-3.5" /> Missing
                </span>
              )}
            </div>
            <input
              type="password"
              value={deepgramKey}
              onChange={(e) => setDeepgramKey(e.target.value)}
              placeholder={status?.has_deepgram_key ? '••••••••••••••••••••••••••••••••' : 'Paste Deepgram API Key'}
              className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-sky-500 transition"
            />
            <div className="flex justify-end">
              <a
                href="https://console.deepgram.com"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300 hover:underline"
              >
                Get Deepgram Key <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </div>
          </div>

          {/* DeepSeek API Key */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-slate-200 flex items-center gap-1.5">
                <span>DeepSeek API Key</span>
                <span className="text-[10px] text-slate-400 font-normal">(Insights & Meeting Q&A)</span>
              </label>
              {status?.has_deepseek_key ? (
                <span className="flex items-center gap-1 text-[11px] font-medium text-emerald-400">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Configured ({status.deepseek_key_masked})
                </span>
              ) : (
                <span className="flex items-center gap-1 text-[11px] font-medium text-amber-400">
                  <AlertCircle className="w-3.5 h-3.5" /> Missing
                </span>
              )}
            </div>
            <input
              type="password"
              value={deepseekKey}
              onChange={(e) => setDeepseekKey(e.target.value)}
              placeholder={status?.has_deepseek_key ? '••••••••••••••••••••••••••••••••' : 'Paste DeepSeek API Key (sk-...)'}
              className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-sky-500 transition"
            />
            <div className="flex justify-end">
              <a
                href="https://platform.deepseek.com"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300 hover:underline"
              >
                Get DeepSeek Key <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </div>
          </div>

          {/* Exa API Key */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-slate-200 flex items-center gap-1.5">
                <span>Exa AI Search Key</span>
                <span className="text-[10px] text-slate-400 font-normal">(Neural Web Intelligence)</span>
              </label>
              {status?.has_exa_key ? (
                <span className="flex items-center gap-1 text-[11px] font-medium text-emerald-400">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Configured ({status.exa_key_masked})
                </span>
              ) : (
                <span className="flex items-center gap-1 text-[11px] font-medium text-slate-400">
                  Optional
                </span>
              )}
            </div>
            <input
              type="password"
              value={exaKey}
              onChange={(e) => setExaKey(e.target.value)}
              placeholder={status?.has_exa_key ? '••••••••••••••••••••••••••••••••' : 'Paste Exa API Key'}
              className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-sky-500 transition"
            />
            <div className="flex justify-end">
              <a
                href="https://dashboard.exa.ai"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300 hover:underline"
              >
                Get Exa Key <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </div>
          </div>

          <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl text-[11px] text-slate-400 flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
            <span>
              Keys are securely stored in your personal user profile (<code className="text-sky-300">~/.parley/.env</code>) and will never be shared or sent outside your machine.
            </span>
          </div>

          {/* Footer Buttons */}
          <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 rounded-xl transition"
            >
              Close
            </button>
            <button
              type="submit"
              disabled={saving || (!deepgramKey && !deepseekKey && !exaKey)}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-white bg-sky-600 hover:bg-sky-500 disabled:opacity-50 disabled:pointer-events-none rounded-xl shadow-md shadow-sky-900/30 transition active:scale-95"
            >
              <Save className="w-3.5 h-3.5" />
              {saving ? 'Saving...' : 'Save Keys'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
