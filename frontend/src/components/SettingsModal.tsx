import React, { useState, useEffect } from 'react';
import { X, Key, CheckCircle2, AlertCircle, ExternalLink, Save, ShieldCheck, Cpu, Download, RefreshCw, Sparkles } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface RecommendedModel {
  id: string;
  name: string;
  description: string;
  size: string;
  category: string;
  is_installed: boolean;
  is_active: boolean;
}

interface SettingsState {
  has_deepgram_key: boolean;
  has_deepseek_key: boolean;
  has_exa_key: boolean;
  deepgram_key_masked?: string;
  deepseek_key_masked?: string;
  exa_key_masked?: string;
  stt_engine?: string;
  whisper_model?: string;
  llm_engine?: string;
  ollama_model?: string;
  search_engine?: string;
  ollama_running?: boolean;
}

interface PullStatus {
  is_pulling: boolean;
  model: string | null;
  status: string;
  percent: number;
  error: string | null;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<'cloud' | 'local'>('local');
  const [deepgramKey, setDeepgramKey] = useState('');
  const [deepseekKey, setDeepseekKey] = useState('');
  const [exaKey, setExaKey] = useState('');
  
  const [sttEngine, setSttEngine] = useState('auto');
  const [whisperModel, setWhisperModel] = useState('base.en');
  const [llmEngine, setLlmEngine] = useState('auto');
  const [ollamaModel, setOllamaModel] = useState('deepseek-r1:1.5b');
  const [searchEngine, setSearchEngine] = useState('auto');

  const [status, setStatus] = useState<SettingsState | null>(null);
  const [models, setModels] = useState<RecommendedModel[]>([]);
  const [pullProgress, setPullProgress] = useState<PullStatus | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchSettings = async () => {
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        const data: SettingsState = await res.json();
        setStatus(data);
        if (data.stt_engine) setSttEngine(data.stt_engine);
        if (data.whisper_model) setWhisperModel(data.whisper_model);
        if (data.llm_engine) setLlmEngine(data.llm_engine);
        if (data.ollama_model) setOllamaModel(data.ollama_model);
        if (data.search_engine) setSearchEngine(data.search_engine);
      }
    } catch (err) {
      console.error('Failed to fetch settings:', err);
    }
  };

  const fetchModels = async () => {
    try {
      const res = await fetch('/api/ollama/models');
      if (res.ok) {
        const data = await res.json();
        setModels(data.recommended_models || []);
      }
    } catch (err) {
      console.error('Failed to fetch Ollama models:', err);
    }
  };

  const fetchPullStatus = async () => {
    try {
      const res = await fetch('/api/ollama/status');
      if (res.ok) {
        const data = await res.json();
        setPullProgress(data.pull_status);
        if (data.installed_models) {
          fetchModels();
        }
      }
    } catch (err) {
      console.error('Failed to fetch Ollama pull status:', err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchSettings();
      fetchModels();
      fetchPullStatus();
      setMessage(null);
    }
  }, [isOpen]);

  // Poll status while background model pulling is active
  useEffect(() => {
    let timer: any;
    if (isOpen && pullProgress?.is_pulling) {
      timer = setInterval(() => {
        fetchPullStatus();
      }, 1500);
    }
    return () => clearInterval(timer);
  }, [isOpen, pullProgress?.is_pulling]);

  const handlePullModel = async (modelId: string) => {
    try {
      setMessage(null);
      const res = await fetch('/api/ollama/pull', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: modelId }),
      });
      if (res.ok) {
        setOllamaModel(modelId);
        fetchPullStatus();
      } else {
        const err = await res.json();
        setMessage({ type: 'error', text: err.error || 'Failed to start download.' });
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Error starting Ollama model download.' });
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    const payload: Record<string, string> = {
      stt_engine: sttEngine,
      whisper_model: whisperModel,
      llm_engine: llmEngine,
      ollama_model: ollamaModel,
      search_engine: searchEngine,
    };

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
        setMessage({ type: 'success', text: 'Settings & engine configuration saved successfully!' });
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="w-full max-w-xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/90">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Engine & API Settings</h2>
              <p className="text-xs text-slate-400">Configure 100% Free Local Mode or Cloud API Keys</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-slate-800 bg-slate-950/60 p-1.5 gap-1.5">
          <button
            type="button"
            onClick={() => setActiveTab('local')}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-xl transition ${
              activeTab === 'local'
                ? 'bg-sky-600 text-white shadow-md shadow-sky-900/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" /> 100% Free Local Mode (Zero-Creds)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('cloud')}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-xl transition ${
              activeTab === 'cloud'
                ? 'bg-sky-600 text-white shadow-md shadow-sky-900/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Key className="w-3.5 h-3.5" /> Cloud API Keys
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className="p-6 space-y-5 overflow-y-auto max-h-[65vh]">
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

          {activeTab === 'local' && (
            <div className="space-y-5">
              {/* Ollama Connection & Model Manager */}
              <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-sky-400" />
                    <span className="text-xs font-semibold text-white">Ollama Local AI Engine</span>
                  </div>
                  {status?.ollama_running ? (
                    <span className="flex items-center gap-1 text-[11px] font-medium text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded-full border border-emerald-800/60">
                      <CheckCircle2 className="w-3 h-3" /> Connected (http://localhost:11434)
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[11px] font-medium text-amber-400 bg-amber-950/80 px-2 py-0.5 rounded-full border border-amber-800/60">
                      <AlertCircle className="w-3 h-3" /> Not Detected (Run `ollama serve`)
                    </span>
                  )}
                </div>

                {/* Background Pull Status Progress Bar */}
                {pullProgress?.is_pulling && (
                  <div className="p-3 bg-sky-950/80 border border-sky-800/80 rounded-xl text-xs space-y-1.5 animate-pulse">
                    <div className="flex items-center justify-between text-sky-200 font-medium">
                      <span className="flex items-center gap-1.5">
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" /> {pullProgress.status}
                      </span>
                      <span>{pullProgress.percent}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-sky-400 transition-all duration-300"
                        style={{ width: `${pullProgress.percent}%` }}
                      ></div>
                    </div>
                  </div>
                )}

                {/* Models List */}
                <div className="space-y-2 pt-1">
                  <label className="text-[11px] font-semibold text-slate-300">
                    Select & Download AI Reasoning Model (Zero API Key):
                  </label>
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                    {models.map((m) => (
                      <div
                        key={m.id}
                        className={`p-3 rounded-xl border transition flex items-center justify-between ${
                          ollamaModel === m.id
                            ? 'bg-sky-950/50 border-sky-600/80'
                            : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        <div className="space-y-0.5 max-w-[70%]">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-white">{m.name}</span>
                            {m.is_installed && (
                              <span className="text-[9px] font-semibold text-emerald-400 bg-emerald-950 px-1.5 py-0.2 rounded border border-emerald-800">
                                Installed
                              </span>
                            )}
                            {m.category === 'light' && (
                              <span className="text-[9px] font-medium text-sky-300 bg-sky-950 px-1.5 py-0.2 rounded border border-sky-800">
                                CPU Optimized
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-400 leading-tight">{m.description}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          {!m.is_installed ? (
                            <button
                              type="button"
                              onClick={() => handlePullModel(m.id)}
                              disabled={pullProgress?.is_pulling}
                              className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-sky-300 bg-sky-900/60 hover:bg-sky-800 rounded-lg border border-sky-700/60 transition"
                            >
                              <Download className="w-3 h-3" /> Download ({m.size})
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => setOllamaModel(m.id)}
                              className={`px-3 py-1 text-[11px] font-medium rounded-lg transition ${
                                ollamaModel === m.id
                                  ? 'bg-sky-600 text-white'
                                  : 'bg-slate-800 hover:bg-slate-700 text-slate-200'
                              }`}
                            >
                              {ollamaModel === m.id ? 'Active' : 'Select'}
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Local STT Engine Selection */}
              <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
                <label className="text-xs font-semibold text-slate-200 flex items-center justify-between">
                  <span>Speech-to-Text Engine</span>
                  <span className="text-[10px] text-sky-400 font-normal">Faster-Whisper (100% Free Offline)</span>
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <select
                    value={sttEngine}
                    onChange={(e) => setSttEngine(e.target.value)}
                    className="px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-sky-500"
                  >
                    <option value="auto">Auto (Whisper if no key)</option>
                    <option value="whisper">Faster-Whisper (Local $0)</option>
                    <option value="deepgram">Deepgram Nova-3 (Cloud Key)</option>
                  </select>
                  <select
                    value={whisperModel}
                    onChange={(e) => setWhisperModel(e.target.value)}
                    className="px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-sky-500"
                  >
                    <option value="tiny.en">Whisper Tiny (Fastest)</option>
                    <option value="base.en">Whisper Base (Recommended)</option>
                    <option value="small.en">Whisper Small (High Acc)</option>
                  </select>
                </div>
              </div>

              {/* Web Search Engine Selection */}
              <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
                <label className="text-xs font-semibold text-slate-200 flex items-center justify-between">
                  <span>Web Search Intelligence</span>
                  <span className="text-[10px] text-sky-400 font-normal">DuckDuckGo (Free $0 No Key)</span>
                </label>
                <select
                  value={searchEngine}
                  onChange={(e) => setSearchEngine(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-sky-500"
                >
                  <option value="auto">Auto (DuckDuckGo if no Exa key)</option>
                  <option value="duckduckgo">DuckDuckGo Free Search ($0)</option>
                  <option value="exa">Exa Neural Search (Cloud Key)</option>
                </select>
              </div>
            </div>
          )}

          {activeTab === 'cloud' && (
            <div className="space-y-4">
              {/* Deepgram API Key */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-slate-200 flex items-center gap-1.5">
                    <span>Deepgram API Key</span>
                    <span className="text-[10px] text-slate-400 font-normal">(Nova-3 Diarization)</span>
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
                    <span className="text-[10px] text-slate-400 font-normal">(Cloud Reasoning)</span>
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
                    <span className="text-[10px] text-slate-400 font-normal">(Neural Web Search)</span>
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
            </div>
          )}

          <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl text-[11px] text-slate-400 flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
            <span>
              All configurations and local models are stored securely on your machine (<code className="text-sky-300">~/.parley/.env</code>).
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
              disabled={saving}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-white bg-sky-600 hover:bg-sky-500 disabled:opacity-50 rounded-xl shadow-md shadow-sky-900/30 transition active:scale-95"
            >
              <Save className="w-3.5 h-3.5" />
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
