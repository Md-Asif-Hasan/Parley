import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { initialState, reduceEvent, type MeetingEvent } from './state';
import { startSession } from './session';
import './style.css';

function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, React.ReactNode> = {
    mic: <><rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/></>,
    spark: <><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"/><path d="m20 2 1 2 2 1-2 1-1 2-1-2-2-1 2-1Z"/></>,
    globe: <><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/></>,
    pin: <><path d="m9 3 12 12-4 1-3 4-4-6-6-4 4-3Z M9 15l-6 6"/></>,
    arrow: <path d="M6 18 18 6M6 6h12v12"/>,
    download: <><path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/></>,
    play: <path d="m8 4 12 8-12 8Z"/>,
    stop: <rect x="5" y="5" width="14" height="14" rx="2"/>,
    check: <path d="m5 12 4 4L19 6"/>,
    board: <><rect x="3" y="3" width="7" height="11" rx="2"/><rect x="14" y="3" width="7" height="6" rx="2"/><rect x="14" y="13" width="7" height="8" rx="2"/><path d="M3 18h7"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.spark}</svg>;
}
const clock = (n: number) => `${Math.floor(n / 60).toString().padStart(2, '0')}:${Math.floor(n % 60).toString().padStart(2, '0')}`;
function color(id: string | null) { return id === null ? 'gray' : ['coral', 'blue', 'green', 'violet', 'gold'][Math.abs([...id].reduce((a, c) => a + c.charCodeAt(0), 0)) % 5]; }
function App() {
  const [state, setState] = useState(initialState);
  const [names, setNames] = useState<Record<string, string>>({});
  const [seconds, setSeconds] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const session = useRef<ReturnType<typeof startSession> | null>(null);
  const file = useRef<HTMLInputElement>(null);
  const transcriptList = useRef<HTMLDivElement>(null);
  const followTranscript = useRef(true);
  const running = ['connecting', 'recording', 'processing'].includes(state.status);
  const busy = state.status === 'processing';
  const speaker = (id: string | null) => id === null ? 'Unknown speaker' : names[id] || id.replace('speaker_', 'Speaker ');
  const emit = (event: MeetingEvent) => {
    const ids = event.type === 'transcript.final' ? event.data.utterances.map(u => u.speaker_id) : event.type === 'transcript.partial' ? [event.data.speaker_id] : [];
    setNames(previous => { const next = { ...previous }; ids.forEach(id => { if (id !== null && !(id in next)) next[id] = id.replace('speaker_', 'Speaker '); }); return next; });
    setState(s => reduceEvent(s, event));
  };
  useEffect(() => () => session.current?.dispose(), []);
  useEffect(() => { const list = transcriptList.current; if (list && followTranscript.current) list.scrollTop = list.scrollHeight; }, [state.transcript.length, state.partial]);
  useEffect(() => { if (state.status !== 'recording') return; const t = setInterval(() => setSeconds(s => s + 1), 1000); return () => clearInterval(t); }, [state.status]);
  function start() { session.current?.dispose(); setState(initialState); setSeconds(0); setSelected([]); followTranscript.current = true; setNames({}); setImported(false); session.current = startSession(emit); }
  function stop() { if (state.status === 'connecting') { session.current?.dispose(); emit({ type: 'status', data: { state: 'idle' } }); } else session.current?.stop(); }
  const [imported, setImported] = useState(false);
  function evidence(ids: string[]) { followTranscript.current = false; setSelected(ids); document.getElementById(ids[0])?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }
  const refs = (ids: string[]) => <button className="evidence" onClick={() => evidence(ids)}>↳ {ids.length} source{ids.length === 1 ? '' : 's'}</button>;
  const badge = (id: string | null) => <span className={`avatar ${color(id)}`}>{speaker(id).slice(0, 1).toUpperCase()}</span>;
  function download() {
    const blob = new Blob([JSON.stringify({ ...state, speakers: names, transcript_version: state.transcript.length, based_on_transcript_version: state.analysis.based_on_transcript_version, analysis_is_current: state.analysis.based_on_transcript_version === state.transcript.length, voice_input: imported ? 'saved' : 'deepgram', analysis_source: imported ? 'saved' : 'live_agent_loop' }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'parley-meeting.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function importMeeting(event: React.ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0]; if (!chosen) return;
    try {
      const data = JSON.parse(await chosen.text());
      if (!Array.isArray(data.transcript) || !data.analysis || !Array.isArray(data.searches)) throw new Error('Choose an AgentLoop meeting export JSON.');
      // Validate the fields rendered below before accepting a file.
      if (!data.transcript.every((u: any) => typeof u.id === 'string' && (u.speaker_id === null || typeof u.speaker_id === 'string') && typeof u.text === 'string' && Number.isFinite(u.start) && Number.isFinite(u.end)) || typeof data.analysis.meeting_summary !== 'string') throw new Error('Invalid transcript or analysis.');
      for (const key of ['speaker_summaries', 'decisions', 'conflicts', 'highlights']) {
        if (!Array.isArray(data.analysis[key]) || !data.analysis[key].every((x: any) => x && Array.isArray(x.utterance_ids) && x.utterance_ids.every((id: unknown) => typeof id === 'string') && typeof (key === 'speaker_summaries' ? x.summary : x.description) === 'string' && (key !== 'speaker_summaries' && key !== 'highlights' || x.speaker_id === null || typeof x.speaker_id === 'string'))) throw new Error(`Invalid ${key}.`);
      }
      if (!data.searches.every((s: any) => s && typeof s.id === 'string' && typeof s.query === 'string' && typeof s.reason === 'string' && Array.isArray(s.utterance_ids) && s.utterance_ids.every((id: unknown) => typeof id === 'string') && ['searching','completed','error'].includes(s.status) && (s.result === null || (Array.isArray(s.result?.sources) && s.result.sources.every((x: any) => typeof x.title === 'string' && typeof x.url === 'string' && typeof x.excerpt === 'string'))))) throw new Error('Invalid search results.');
      session.current?.dispose(); setImported(true); setSelected([]);
      const importedNames: Record<string, string> = {};
      data.transcript.forEach((u: { speaker_id: string | null }) => { if (u.speaker_id !== null) importedNames[u.speaker_id] = u.speaker_id.replace('speaker_', 'Speaker '); });
      setNames({ ...importedNames, ...(data.speakers && Object.values(data.speakers).every(x => typeof x === 'string') ? data.speakers : {}) });
      setState({ ...initialState, transcript: data.transcript, analysis: { ...data.analysis, based_on_transcript_version: Number(data.based_on_transcript_version) || 0 }, searches: data.searches, status: 'stopped', error: data.analysis_error || null });
      setSeconds(Math.max(0, ...data.transcript.map((u: any) => u.end)));
    } catch (e) { emit({ type: 'error', data: { scope: 'Import', message: e instanceof Error ? e.message : 'Unable to load export.' } }); }
    event.target.value = '';
  }
  return <div className="app">
    <aside className="rail"><a className="logo" href="#" aria-label="Parley home">p<span>✳</span></a><div className="rail-active" title="Meeting whiteboard"><Icon name="board"/></div><span className="rail-bottom">P.</span></aside>
    <div className="workspace">
      <header><div className="breadcrumb">Workspace <span>/</span> <strong>Meeting canvas</strong></div><span className="private-label">◉ Local prototype</span><button className="export" disabled={!state.transcript.length} onClick={download}><Icon name="download" size={16}/> Export</button></header>
      <main>
        <div className="intro"><div><div className="eyebrow">A LITTLE STRUCTURE. MORE POSSIBILITY.</div><h1>Room for ideas<span>.</span></h1><p>Your conversation, coming together.</p></div><div className="session-controls"><span className={`session-state ${running ? 'live' : ''}`}><i/>{state.status === 'connecting' ? 'Connecting microphone' : state.status === 'processing' ? 'Finalizing with agent' : state.status === 'recording' ? 'Listening' : state.status === 'stopped' ? 'Session ended' : state.status === 'error' ? 'Session failed' : 'Ready when you are'} <b>{clock(seconds)}</b></span><button className={`start ${running ? 'stop' : ''}`} disabled={busy} onClick={running ? stop : start}><Icon name={running ? 'stop' : 'play'} size={17}/>{busy ? 'Finalizing…' : state.status === 'connecting' ? 'Cancel' : running ? 'End meeting' : state.status === 'idle' ? 'Start meeting' : 'New meeting'}</button></div></div>
        <div className="board-meta"><div className="board-tab"><Icon name="board" size={16}/> Whiteboard <span>01</span></div><div className="participants">{Object.entries(names).map(([id, name]) => <label key={id} className={`person ${color(id)}`}>{badge(id)}<input aria-label={`Rename ${id}`} value={name} maxLength={24} onChange={e => setNames(n => ({ ...n, [id]: e.target.value }))}/></label>)}</div><span className="board-note">A shared view of the conversation</span></div>
        <div className="demo-notice"><span><b>{imported ? 'Imported meeting' : 'Live microphone · Deepgram'}</b> · {imported ? 'Saved Agent Loop output. No live microphone.' : 'Speak naturally. Each voice gets its own color; summaries, highlights, and references update as you talk.'}</span><button onClick={() => file.current?.click()} disabled={running}>Load agent export <span>↗</span></button><input ref={file} type="file" accept=".json,application/json" hidden onChange={importMeeting}/></div>
        {state.error && <div className="error" role="alert">{state.error}<button onClick={() => setState(s => ({ ...s, error: null }))}>Dismiss</button></div>}
        <div className="board">
          <section className="panel transcript-panel"><div className="panel-heading"><span className="section-icon peach"><Icon name="mic"/></span><div><h2>The conversation</h2><p>Every voice, in its own color</p></div><span className="count">{state.transcript.length.toString().padStart(2, '0')}</span></div><div ref={transcriptList} onScroll={e => { const list = e.currentTarget; followTranscript.current = list.scrollHeight - list.scrollTop - list.clientHeight < 40; }} className="transcript-list" aria-label="Meeting transcript">
            {!state.transcript.length && !state.partial && <div className="empty"><div className="wave">▂ ▅ ▃ ▇ ▄ ▂ ▆ ▃ ▅ ▂</div><h3>It starts with a conversation.</h3><p>Hit start. Each speaker’s words will find a place here.</p><span>{state.status === 'recording' ? 'LISTENING · NOVA-3' : 'MICROPHONE STARTS WITH THE MEETING'}</span></div>}
            {state.transcript.map(u => <article id={u.id} key={u.id} className={`utterance ${color(u.speaker_id)} ${selected.includes(u.id) ? 'selected' : ''}`}><div className="utterance-meta">{badge(u.speaker_id)}<strong>{speaker(u.speaker_id)}</strong><time>{clock(u.start)}</time></div><p>{u.text}</p></article>)}
            {state.partial && <article className={`utterance partial ${color(state.partial.speaker_id)}`}><div className="utterance-meta">{badge(state.partial.speaker_id)}<strong>{speaker(state.partial.speaker_id)}</strong><span className="typing">Speaking…</span></div><p>{state.partial.text}</p></article>}
          </div><div className="panel-footer"><i className={running ? 'pulse' : ''}/>{state.status === 'recording' ? 'Deepgram · Live transcription' : 'Deepgram · Nova-3'}<span>{state.transcript.length} entries</span></div></section>
          <div className="middle-column"><section className="panel summary-panel"><div className="panel-heading"><span className="section-icon lavender"><Icon name="spark"/></span><div><h2>The bigger picture</h2><p>A running summary of the room</p></div><span className="ai-tag">AI</span></div>
            {state.analysis.meeting_summary ? <div className="summary-content"><div className="eyebrow">WHERE WE ARE</div><p className="summary-text">{state.analysis.meeting_summary}</p><div className="perspectives">{state.analysis.speaker_summaries.map(s => <div className="perspective" key={s.speaker_id}>{badge(s.speaker_id)}<div><strong>{speaker(s.speaker_id)}</strong><p>{s.summary}</p>{refs(s.utterance_ids)}</div></div>)}</div>{state.analysis.decisions.map((d, i) => <div className="decision" key={i}><Icon name="check" size={18}/><div><strong>Agreed in the room</strong><p>{d.description}</p>{refs(d.utterance_ids)}</div></div>)}{state.analysis.conflicts.map((c, i) => <div className="conflict" key={i}><strong>Needs alignment · {c.type}</strong><p>{c.description}</p>{refs(c.utterance_ids)}</div>)}</div> : <div className="empty compact"><span className="empty-symbol">✳</span><h3>See the thread, not just the words.</h3><p>Key themes, each person’s perspective, and shared decisions will take shape here.</p></div>}
            <div className="panel-footer"><Icon name="spark" size={13}/>{state.analysis.based_on_transcript_version ? `Based on ${state.analysis.based_on_transcript_version} of ${state.transcript.length} entries` : 'Waiting for the first ideas'}<span>{imported ? 'Saved analysis' : 'DeepSeek · live'}</span></div></section>
          <section className="note"><span>↳</span><p>Good ideas don’t happen in a straight line.<br/><strong>Give them a little room.</strong></p><span className="doodle">✳</span></section></div>
          <div className="right-column"><section className="panel references-panel"><div className="panel-heading"><span className="section-icon mint"><Icon name="globe"/></span><div><h2>Beyond the room</h2><p>References for your next idea</p></div><span className="exa-tag">exa ↗</span></div><div className="search-list">
            {!state.searches.length && <div className="empty compact"><span className="orbit">↗</span><h3>A starting point, somewhere else.</h3><p>Related projects and useful sources appear here when an idea sparks a search.</p></div>}
            {state.searches.map(s => <div className="search-group" key={s.id}><div className="search-purpose">{s.purpose === 'idea_reference' ? 'SIMILAR PROJECTS' : 'FACT CHECK'}<span>{s.status === 'searching' ? 'Searching…' : s.status === 'error' ? 'Failed' : `${s.result?.sources.length || 0} sources`}</span></div><p className="query">{s.query}</p><p className="search-reason">{s.reason}</p>{s.status === 'error' && <p role="alert">{s.error || 'Search failed.'}</p>}{s.status === 'completed' && !s.result?.sources.length && <p>No results for this search.</p>}{s.result?.sources.map((source, i) => <a className="source" key={source.url + i} href={/^https?:\/\//i.test(source.url) ? source.url : undefined} target="_blank" rel="noreferrer"><span className="source-number">0{i + 1}</span><div><strong>{source.title}</strong><p>{source.excerpt}</p><small>{source.url.replace(/^https?:\/\//, '').split('/')[0]}</small></div><Icon name="arrow" size={16}/></a>)}{refs(s.utterance_ids)}</div>)}
          </div></section>
          <section className="panel highlights-panel"><div className="panel-heading"><span className="section-icon butter"><Icon name="pin"/></span><div><h2>Worth keeping</h2><p>The moments that matter</p></div><span className="count">{state.analysis.highlights.length.toString().padStart(2, '0')}</span></div><div className="highlights-list">{!state.analysis.highlights.length && <div className="empty compact"><span className="quote">“</span><h3>“Let’s make a note of that.”</h3><p>Explicit requests and important moments, collected as highlights.</p></div>}{state.analysis.highlights.map((h, i) => <article className={`highlight ${color(h.speaker_id)}`} key={i}><div className="highlight-top"><span>{h.source === 'explicit_request' ? '⌖ Asked to remember' : '✳ AI noticed'}</span>{badge(h.speaker_id)}</div><h3>{h.description}</h3><p className="highlight-reason">{h.reason}</p><div className="highlight-bottom"><span>{speaker(h.speaker_id)}</span>{refs(h.utterance_ids)}</div></article>)}</div></section></div>
        </div><footer><span className="wordmark">parley<span>✳</span></span><span>Less note-taking. More being here.</span><span>{imported ? 'SAVED MEETING' : 'LIVE VOICE / LIVE AGENT'}</span></footer>
      </main>
    </div>
  </div>;
}
createRoot(document.getElementById('root')!).render(<App/>);
