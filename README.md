# Parley
Parley sits passively in the room during a meeting, listens to everyone, keeps per-person notes, flags when people are talking past each other (different ideas or conflicting schedules), and can be asked directly for its take — all visualized on a live shared whiteboard.

## Whiteboard frontend

`frontend/` contains the React + TypeScript card-based meeting canvas from the
MVP plan: speaker-colored transcripts, running summary and perspectives,
Exa reference cards, and highlights. It supports start/end, elapsed time,
speaker renaming, source-to-transcript navigation, and JSON export/import.
Desktop uses three columns; smaller screens stack the sections.

**Only the conversation is mocked. All analysis and search are live.** Start
connects to the local FastAPI WebSocket backend, then replays 33 seconds of sample
speech. The backend echoes partial/final transcripts and feeds finalized text to
the real `AgentLoop`. DeepSeek generates summaries, perspectives, decisions and
highlights; the agent decides when to search, and Exa supplies the actual results.
There are no hardcoded analysis/search results or offline fallback responses.
Missing Exa configuration fails the session instead of silently disabling search.

End cancels remaining sample speech and waits for final analysis and any active
search before the backend exports and closes the session. Partial draft speech is
not finalized artificially. Disconnect aborts pending work. Errors remain visible;
earlier successful analysis can remain on screen with its transcript coverage.
The microphone and Deepgram are still not connected.

From the repository root, install dependencies outside the repository:

```powershell
# Terminal 1: real backend (reads ../parley.local.json automatically)
$env:PYTHONPYCACHEPREFIX = (Join-Path (Resolve-Path ..) '.pycache')
..\.venv\Scripts\python.exe -m pip install --cache-dir ..\.pip-cache "fastapi>=0.115,<1" "uvicorn>=0.30,<1" "websockets>=14,<17"
..\.venv\Scripts\python.exe -m uvicorn parley_agent.server:app --host 127.0.0.1 --port 8000

# Terminal 2: frontend
npm install --prefix .. --cache ..\.npm-cache react@19 react-dom@19 @types/react@19 @types/react-dom@19 typescript@5.9 vite@7
cd frontend
npm run dev
# Validate types and produce ../whiteboard-dist relative to the repository:
npm run build
```

Open `http://127.0.0.1:5173`. Dependencies resolve from the parent `node_modules`;
Vite cache and build output also live outside the repository. The frontend's
`package.json` declares its dependencies for a conventional install elsewhere.

Use **Load agent export** to inspect an existing `AgentLoop.export()` JSON, such
as the local `../ideas-highlights-export.json`. Files are read in the browser,
without upload. The exported speaker mapping is optional. An imported meeting
is a saved snapshot and is not described as live recording.

`frontend/src/state.ts` defines the event boundary. `reduceEvent` consumes
`transcript.final`, `transcript.partial`, `analysis.updated`, `search.updated`,
`status`, `meeting.export`, and `error`. Analysis replaces the previous snapshot; search cards are
upserted by ID and repeated finalized utterance IDs are deduplicated. Analysis
shows how many transcript entries it covers. The frontend partial convention is
`{type: "transcript.partial", data: {speaker_id, text}}`.

`frontend/src/session.ts` connects to `/ws/meeting`, proxied by Vite to port 8000.
The backend starts one real loop per connection and emits `status: recording`;
only then does `demo.ts` replay speech. The browser sends `meeting.stop` when
the replay ends or End is clicked. The server emits `processing`, the final
analysis, `stopped`, and `meeting.export`, then closes the socket. Searches run
independently of transcript ingestion. Their results may arrive during finalization.

For the next middleware step, replace the speech replay with Deepgram normalized
events and follow the Deepgram flush lifecycle described below. Ask AI is not part of this frontend
iteration; its backend API remains available. This is a card canvas, not a
draggable infinite board. Google Stitch was unavailable in the tool session;
the interface was implemented directly in this repository.

## LLM Agent Loop

The implemented component is **downstream of Deepgram**. It consumes finalized,
normalized text and emits analysis, answer, and search events. It does not capture
audio or connect to Deepgram. `parley_agent/server.py` now imports it into the
local FastAPI backend; no extra service or agent framework is required.

The local default is **DeepSeek V4.1 Flash** (`deepseek-flash`) through the OpenAI
Python SDK. Network search uses **Exa**, never the OpenAI built-in search tool.

```text
Microphone → Deepgram → middleware normalization → AgentLoop
                                                  ├─ analysis.updated
                                                  ├─ agent.answer
                                                  └─ search.updated
```

### Setup

Python 3.11+ is required. Run these commands from the repository root. Keep the
virtual environment, temporary transcripts, exports, and caches in the parent
`AI TINKERERS/Parley` directory, outside this repository.

```powershell
python -m venv ..\.venv
..\.venv\Scripts\python.exe -m pip install "openai>=2.0,<3" "pydantic>=2.8,<3" "httpx>=0.27,<1"
$env:PYTHONPYCACHEPREFIX = (Join-Path (Resolve-Path ..) '.pycache')
```

`MeetingAgent.from_env()` automatically reads `../parley.local.json` relative to
the repository (independent of the current working directory). The local file
is already configured on this workstation. Its shape for a fresh checkout is:

```json
{
  "provider": "deepseek",
  "model": "deepseek-flash",
  "api_key": "<DeepSeek key>",
  "exa_api_key": "<Exa key>"
}
```

Optional environment overrides: `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `EXA_API_KEY`.
`.env.example` documents these variables but is not automatically loaded.
No repeated key entry is needed on this workstation. To supply a different local
file, call `MeetingAgent.from_env(config_path=...)`.

DeepSeek uses Responses JSON mode plus local Pydantic validation. The strict
schema endpoint rejected the nullable `search_request` schema during a live test,
so the schema and example are supplied in the prompt instead. Non-thinking mode
(`reasoning.effort=none`) and a 4096-token output limit keep prototype calls bounded.

The earlier OpenAI analysis path remains available with `PARLEY_PROVIDER=openai`,
`OPENAI_API_KEY`, and `OPENAI_MODEL`; its structured parsing uses Responses strict
schema mode. Search still uses Exa for either model provider.

### Deepgram / middleware boundary

The upstream adapter must handle `is_final`, split consecutive words by speaker,
assign stable utterance IDs, and forward this contract:

```json
{
  "type": "transcript.final",
  "data": {
    "utterances": [
      {
        "id": "u12",
        "speaker_id": "speaker_0",
        "start": 12.4,
        "end": 16.8,
        "text": "I prefer launching on Friday."
      }
    ]
  }
}
```

Times are seconds from recording start. Use `null` for unknown speaker IDs.
`transcript.partial` is ignored by the agent and should go straight to the UI.
Do not send raw Deepgram responses or audio to this module. `speech_final` alone
does not trigger analysis. Replayed utterances with the same ID and content are
ignored; reused IDs with changed content are rejected. Repeated words under
different IDs are retained. A whole invalid input batch is rejected atomically.

### Backend integration

```python
from parley_agent import AgentLoop, MeetingAgent

agent = MeetingAgent.from_env()  # Reuse its async HTTP client.

async def send_event(event):
    await websocket.send_json(event)  # Supplied by your middleware.

loop = AgentLoop(agent, send_event, interval_seconds=15, auto_search=True)
await loop.start()  # Once the upstream recording session is ready.

# Inside the Deepgram normalized-final handler; this does not await any LLM:
loop.ingest(normalized_event)
# Or: loop.append_final(list_of_utterance_dicts)

# Inside a SEPARATE request task, so the audio receive loop keeps running:
await loop.ask(request_id="q1", question="What remains unresolved?")

# Stop browser recording, flush Deepgram, ingest all final tail utterances FIRST.
# Await outstanding ask tasks if their answers must be included in this export.
meeting_export = await loop.stop()

# On disconnect/shutdown (also safe after stop):
await loop.aclose()
await agent.aclose()  # When the owning backend is done with the shared client.
```

Use one `AgentLoop` instance per meeting on the same asyncio event loop. The
middleware owns its WebSocket, speaker-name mapping, recording status, and any
tasks created for user questions. Combine the speaker mapping with this module's
export for the complete meeting JSON. Use `try/finally` to call `aclose()` on
disconnect; stop and clean up the previous meeting before starting a new one.

### Output contracts

All events use `{"type": "...", "data": {...}}`.

| Event | `data` |
| --- | --- |
| `analysis.updated` | `meeting_summary`, `speaker_summaries`, `conflicts`, `decisions`, `highlights`, `search_request`, `based_on_transcript_version` |
| `agent.answer` | `request_id`, `text`, `utterance_ids`, `search_ids`, `based_on_transcript_version` |
| `search.updated` | `id`, `purpose`, `query`, `reason`, `utterance_ids`, `based_on_transcript_version`, `status`, `result`, `error` |
| `error` | `scope` (`analysis` or `ask`), `message`, optional `request_id` |
| `status` | `state` (`processing` or `stopped`, emitted during stop) |

Analysis is a full replacement, not a patch. Speaker summaries contain
`speaker_id`, `summary`, and `utterance_ids`. Conflicts contain `type` (`schedule`
or `proposal`), `description`, and `utterance_ids`. Decisions contain
`description` and `utterance_ids`. A search request is null or contains `query`,
`reason`, `utterance_ids`, and `purpose` (`fact_check` or `idea_reference`).
Exact Pydantic contracts live in `schemas.py`.

The version counts unique finalized utterances. An analysis may legitimately
lag incoming speech; display its version rather than treating it as covering
the newest text. Renaming/coloring speakers is a UI/middleware concern and does
not change IDs. Existing whiteboard cards can update without changing position.

### Analysis and search behavior

- Every 15 seconds, analyze only if new finalized text exists. The first short
  meeting sends its full transcript; `analyze_now()` is available for explicit refresh.
- Serialize analysis requests while continuing to ingest speech. Questions use
  their own fixed transcript snapshot. Stop waits for active analysis, then
  performs a final analysis including the tail.
- Preserve the previous analysis on refusal, malformed output, invalid source
  references, timeout, or API failure. Emit an error and keep the transcript.
- Prompts distinguish suggestions from explicit agreement, preserve uncertainty,
  update changed opinions, and remove resolved conflicts. These semantic behaviors
  still need evaluation with a real model; schema validation cannot prove them.
- Automatic search is on by default for `AgentLoop` when an Exa key is configured.
  Analysis proposes at most one factual or similar-project query. A separate task calls
  `POST https://api.exa.ai/search` with `type=auto`, up to five results, and highlights.
  Only the self-contained query is sent to Exa. No extra search SDK is needed.
- At most one search runs at a time, with a 30-second cooldown and normalized
  query deduplication. The prompt also receives previous queries to discourage
  paraphrased duplicates. Candidates skipped during cooldown are reconsidered
  only by a later analysis; there is no search backlog or automatic retry queue.
- Searches emit `searching`, then `completed` or `error`. Completed results contain
  `sources` (title, URL, excerpt, optional published date), `text` combining the
  excerpts, and `citations` mapping text spans to actual Exa URLs. Excerpts are
  capped at 1500 characters per page; duplicate URLs are removed. These are search
  excerpts, not an additional LLM-generated summary. Render titles and links on
  whiteboard cards; Ask AI can synthesize the results when requested. An empty
  search explicitly reports no results rather than inventing an answer.
- Search results are available to Ask AI, but never automatically become meeting
  decisions. `search_ids` in an answer refer to top-level saved search cards (e.g.
  `s1`), not the page numbers inside a card. Each card retains its source citations.
- Stop disables new searches and waits for the existing search to finish. Provider
  operations have a 45-second overall timeout; shutdown can cancel tasks with `aclose()`.
- The serialized input limit is 80,000 characters (including prior analysis and
  supplied context), configurable on `MeetingAgent`. Over-limit requests fail
  visibly instead of silently truncating; transcript ingestion/export continues.

`export()` returns the transcript, analysis, searches, question/answer messages,
status, versions, `analysis_is_current`, and `analysis_error`. It returns a snapshot;
no files are written by the loop. State is intentionally in memory only.

### Idea references and meeting highlights

When a participant proposes a concrete product/project idea, the next periodic
analysis can proactively search for similar projects, products, repositories, or
demos via Exa, even without an explicit search question. Such requests/records have
`purpose: "idea_reference"`; ordinary factual queries use `fact_check`. Reference
queries retain the idea's distinctive capabilities and link to the original
utterances. Results remain candidate references, not proof of novelty or consensus.
New idea references take priority over routine factual lookups. The same one-search
limit, cooldown, and deduplication rules above apply.

`analysis.highlights` holds noteworthy meeting statements:

```json
{
  "speaker_id": "speaker_1",
  "description": "The demo must use one shared microphone and attribute each idea.",
  "source": "explicit_request",
  "reason": "The participant explicitly asked for this requirement to be recorded.",
  "utterance_ids": ["u2"]
}
```

- `explicit_request`: someone asks to record a specific point, including phrases
  such as "write this down" or "记一下这个". If they refer to another participant's
  point, keep the original speaker and cite both the point and the request.
- `agent_detected`: a central idea, important constraint, major risk, key insight,
  or specific commitment selected by the model. Casual remarks are excluded.
- Highlights remain in the full replacement analysis and JSON export, and are
  available to Ask AI. Prompts preserve important recorded points across updates,
  merge duplicates, and reflect corrections/retractions. They do not imply agreement.
- Source IDs and speaker attribution are validated locally. Model selection of
  what matters is semantic and can vary; the frontend can render descriptions
  with speaker colors and expand the cited original utterances.
- Meeting highlights are separate from Exa's `contents.highlights` excerpts, which
  stay inside search results.

The local `../ideas-highlights-transcript.json` exercises both highlight sources,
an unsolicited idea-reference search, a casual remark, and an unaccepted proposal.

### Run with a real model

Save a JSON array of finalized utterances, or `{"transcript": [...]}`, outside the
repository. From the repository root:

```powershell
..\.venv\Scripts\python.exe -m parley_agent ..\sample-transcript.json --question "What did we agree?" --output ..\meeting-export.json
# Also exercise automatic Exa search (the model may decide none is warranted):
..\.venv\Scripts\python.exe -m parley_agent ..\sample-transcript.json --search --output ..\meeting-export.json
```

Events are printed to stderr and export JSON to the requested output file (or
stdout). An unsuccessful final analysis or requested answer produces a nonzero
exit code while preserving the export. Search failures are recorded in individual
search cards. Without an Exa key, analysis/questions still work and the CLI warns
if `--search` was requested.

### Offline verification

```powershell
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests need no API key or network. They use the real OpenAI SDK with HTTP mocks
for strict/JSON output, an Exa HTTP mock for results and citations, and controlled
async fakes for scheduling.
Locally verified with Python 3.12, OpenAI SDK 2.54.0, and Pydantic 2.13.5.

Before a live demo, evaluate: compatible preferences (no conflict), incompatible
constraints (cited conflict), unanswered suggestion (no decision), explicit
agreement (decision), retracted opinion/resolved conflict (update), and a question
absent from the meeting (insufficient evidence). Live model accuracy and real
Deepgram integration are not established by offline tests.

Live smoke verification on this workstation: DeepSeek analyzed the sample and
identified the revised Tuesday decision; Exa returned five search sources; a
follow-up DeepSeek answer used the saved search record `s1`. Local artifacts are
`../deepseek-smoke-export.json`, `../deepseek-exa-smoke-export.json`, and
`../deepseek-exa-answer.json`. The last file is the successful follow-up answer
after correcting the source-ID prompt; the earlier combined export preserves
the first run, including its unanswered question.

Reference APIs: [DeepSeek models](https://api-docs.deepseek.com/quick_start/pricing/),
[DeepSeek Responses compatibility](https://api-docs.deepseek.com/guides/responses_api/),
[Exa Search](https://exa.ai/docs/reference/search).
