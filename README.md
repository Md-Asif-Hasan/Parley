# Parley 🎙️💬

**Parley** is a real-time meeting assistant and opinion analyzer that listens to discussions (2–5 participants), displays live speaker-labelled transcripts, summarizes participant views, flags potential scheduling or proposal conflicts, highlights agreed consensus decisions, and answers grounded questions about the meeting with live web intelligence.

Parley is available as a **Web Application**, a **Single-Container Docker App**, and a **Native Self-Contained Desktop Application** for Windows, macOS, and Linux.

---

## 🌿 Branches Overview

| Branch | Status | Description |
|---|---|---|
| **`master`** | 🌟 **Finished / Production Version** | Full complete release: Deepgram Nova-3 speech diarization, DeepSeek intelligence, Exa Neural Web Search, custom brand logo, PyInstaller self-contained backend binary, Docker containerization, and packaged Electron desktop installers (`.exe`, `.dmg`, `.AppImage`). |
| **`main`** | 🧪 **Demo / Prototype Version** | Baseline MVP prototype and developmental iteration history. |

---

## ⚡ Core Features

- **Live Streaming Diarization**: Low-latency speech capture with Deepgram Nova-3 (`diarize=true`, `utterance_end_ms=5000`).
- **Real-Time Interim Captions**: See live drafting captions that fluidly finalize into speaker-attributed transcript blocks.
- **Dynamic Insight Extraction**: Periodic AI analysis powered by DeepSeek (`deepseek-chat`) detailing participant viewpoints, incompatible proposal warnings, and consensus checklists.
- **Exa Neural Web Search & Scraping**: Built-in Exa AI search engine that automatically looks up unknown processes, technologies, documentation, and external facts in real time, synthesizing raw web data into human-readable insights with citations.
- **Interactive Source Citations**: Click any `[u1, u3]` citation badge on a conflict or decision card to scroll and highlight the supporting utterances in the transcript.
- **Grounded Q&A**: Ask natural language questions with responses strictly grounded in the meeting context and live web search.
- **Self-Contained Desktop App**: Native Electron shell with PyInstaller embedded Python runtime — runs on any Windows/macOS/Linux machine with **zero dependencies or Python installation required**.
- **Export**: One-click download of the complete meeting state and analysis as JSON.
- **Desktop UX & Shortcuts**: Frameless dark-mode UI with custom application branding and global keyboard shortcuts.

---

## 📂 Project Structure

```
Parley/
├── .dockerignore                     # Docker build exclusions
├── .gitignore                        # Git exclusion rules (.env, dist, node_modules)
├── Dockerfile                        # Multi-stage container build (Node UI + Python API)
├── docker-compose.yml                # Single-command stack launcher
├── Parley logo.jpg                   # Source brand logo asset
├── README.md                         # Documentation & branch guide
│
├── backend/                          # FastAPI Backend & AI Services
│   ├── .env.example                  # Environment template (Deepgram, DeepSeek, Exa)
│   ├── requirements.txt              # Python runtime dependencies
│   ├── parley_server.py              # Self-contained PyInstaller server entry point
│   ├── parley_server.spec            # PyInstaller build spec with embedded UI & icons
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI REST, WebSockets & SPA static server
│   │   ├── config.py                 # Pydantic settings & environment manager
│   │   ├── models.py                 # Pydantic data schemas (Utterance, Analysis, etc.)
│   │   ├── state.py                  # In-memory thread-safe meeting state manager
│   │   ├── agent.py                  # DeepSeek LLM agent loop & QA engine
│   │   ├── deepgram_client.py        # Deepgram Nova-3 live WebSocket client
│   │   ├── exa_client.py             # Exa AI Neural Web Search & content scraper
│   │   └── mock_data.py              # Offline multi-speaker meeting simulation
│   └── tests/
│       ├── test_agent.py             # Unit tests for agent analysis & QA
│       ├── test_models.py            # Unit tests for schemas & state manager
│       └── test_websocket.py         # Unit tests for REST & WebSocket endpoints
│
├── frontend/                         # React + TypeScript + Vite UI
│   ├── index.html                    # Single-page app entry point with custom favicon
│   ├── package.json                  # Frontend dependencies (Lucide, Tailwind, etc.)
│   ├── vite.config.ts                # Vite build configuration
│   ├── tailwind.config.js            # Tailwind CSS styling configuration
│   ├── public/
│   │   ├── favicon.ico               # Brand favicon
│   │   ├── favicon.png               # High-res PNG icon
│   │   └── logo.jpg                  # Application logo
│   └── src/
│       ├── App.tsx                   # Main layout, tabs & keyboard shortcuts
│       ├── main.tsx                  # React DOM mount point
│       ├── index.css                 # Global CSS & Tailwind layers
│       ├── components/
│       │   ├── Header.tsx            # App header with logo, mic toggle & audio meter
│       │   ├── AudioVisualizer.tsx   # Real-time microphone volume visualizer
│       │   ├── TranscriptPanel.tsx   # Live transcript & inline speaker renaming
│       │   ├── SpeakerSummaries.tsx  # Per-participant viewpoints & summaries
│       │   ├── ConflictsPanel.tsx    # Potential scheduling & proposal conflicts
│       │   ├── DecisionsPanel.tsx    # Consensus agreements checklist
│       │   └── AskAIPanel.tsx        # Grounded Q&A with Exa Web Search live badge
│       ├── hooks/
│       │   ├── useAudioRecorder.ts   # Browser MediaRecorder PCM stream hook
│       │   └── useMeetingSocket.ts   # WebSocket client connection & state sync hook
│       ├── types/
│       │   └── meeting.ts            # Shared TypeScript interfaces
│       └── utils/
│           └── colors.ts             # Dynamic speaker color palette
│
└── desktop/                          # Electron Desktop Application
    ├── package.json                  # Electron & electron-builder packaging config
    ├── main.cjs                      # Electron main process & server process manager
    ├── preload.cjs                   # Secure IPC bridge for window controls
    ├── icon.ico                      # Multi-resolution Windows application icon
    ├── icon.png                      # 512x512 macOS / Linux application icon
    └── dist/                         # Output folder for compiled installers
```

---

## 🐳 Docker Deployment (Any Device)

Run the entire stack (FastAPI backend + React frontend + WebSocket) in a single unified container on port `8000`:

### Using Docker Compose
```bash
# Clone the repository
git clone https://github.com/Md-Asif-Hasan/Parley.git
cd Parley
git checkout master

# Launch container
docker compose up --build
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

### Using Docker CLI
```bash
docker build -t parley-app .
docker run -d -p 8000:8000 \
  -e DEEPGRAM_API_KEY="your_deepgram_api_key" \
  -e DEEPSEEK_API_KEY="your_deepseek_api_key" \
  -e EXA_API_KEY="your_exa_api_key" \
  --name parley parley-app
```

---

## 🖥️ Cross-Platform Desktop Application (Windows / macOS / Linux)

Parley packages into a native desktop app with an embedded backend executable — **no Python install needed** on the user's computer.

### Ready-Built Windows Installers
Generated inside `desktop/dist/`:
- **`Parley Setup 1.0.0.exe`**: Full Windows NSIS installer
- **`Parley 1.0.0.exe`**: Standalone portable executable

### Build Installers from Source
```bash
# 1. Build frontend assets
cd frontend && npm install && npm run build

# 2. Build self-contained backend binary
cd ../backend && pip install -r requirements.txt pyinstaller
pyinstaller parley_server.spec --distpath dist --workpath build/pyinstaller --noconfirm

# 3. Package desktop installer
cd ../desktop && npm install
npm run dist:win    # Windows (.exe installer & portable)
npm run dist:mac    # macOS (.dmg and .zip)
npm run dist:linux  # Linux (.AppImage and .deb)
```

---

## ⌨️ Desktop Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| <kbd>Space</kbd> | Toggle live recording start / stop (when not typing) |
| <kbd>Ctrl</kbd> / <kbd>Cmd</kbd> + <kbd>K</kbd> | Open and focus Ask AI search bar |
| <kbd>Ctrl</kbd> / <kbd>Cmd</kbd> + <kbd>E</kbd> | Export meeting transcript & insights as JSON |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd> | Run mock multi-speaker simulation |
| <kbd>?</kbd> | Toggle keyboard shortcuts cheatsheet |

---

## 🛠️ Local Web Development

### 1. Backend Server
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Server
```bash
cd frontend
npm install
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser.

---

## 🧪 Testing

Run backend test suite:
```bash
python -m pytest backend/tests -v
```

Run frontend build check:
```bash
cd frontend && npm run build
```

---

## 📄 License
MIT License.
