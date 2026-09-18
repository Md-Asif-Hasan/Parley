# Parley 🎙️💬

**Parley** is a real-time meeting assistant, opinion analyzer, and autonomous desktop action executor that listens to discussions (2–5 participants), displays live speaker-labelled transcripts, summarizes participant views, flags potential conflicts, highlights consensus decisions, and executes automated computer actions on command.

Parley is available as a **Native Desktop Application for Windows** (with macOS/Linux support), a **Single-Container Docker App**, and a **Web Application**.

> **v1.1.0** — 🆓 **100% Free Local Mode** added: Faster-Whisper (offline STT) + Ollama (local LLM with auto-downloaded DeepSeek-R1) + DuckDuckGo (free web search). No API keys or internet required!

---

## 🚀 Quick Download & Install (Windows)

Download the ready-to-run desktop application from [**GitHub Releases**](https://github.com/Md-Asif-Hasan/Parley/releases):

| File | Type | Description |
|---|---|---|
| 📦 [**`Parley Setup 1.0.0.exe`**](https://github.com/Md-Asif-Hasan/Parley/releases/latest) | **NSIS Installer** | Recommended. Installs Parley with desktop shortcuts, auto-start, and uninstaller. |
| ⚡ [**`Parley 1.0.0.exe`**](https://github.com/Md-Asif-Hasan/Parley/releases/latest) | **Portable Executable** | Standalone zero-install executable. Runs immediately without installation. |

> **Zero Dependencies**: Parley includes an embedded Python backend runtime and Chromium automation engine. No Python or Node.js installation is required on the user machine!

---

## 🌿 Branches Overview

| Branch | Status | Description |
|---|---|---|
| **`master`** | 🌟 **Finished / Production Version** | Full complete release: Deepgram Nova-3 speech diarization, DeepSeek intelligence, Exa Neural Web Search, Autopilot OS & browser automation, Multimodal Image Chat, voice speaker renaming, PyInstaller self-contained backend binary, Docker containerization, and packaged Electron desktop installers. |
| **`main`** | 🧪 **Demo / Prototype Version** | Baseline MVP prototype and developmental iteration history. |

---

## 🆓 100% Free Local Mode (No API Keys Required)

Parley works **completely offline** without any paid subscriptions or API keys:

| Component | Free Local | Cloud (Optional) |
|---|---|---|
| 🎤 **Speech-to-Text** | [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) (runs on CPU/GPU locally) | Deepgram Nova-3 |
| 🧠 **AI / LLM** | [Ollama](https://ollama.ai) + DeepSeek-R1 (auto-downloaded on first run) | DeepSeek Cloud API |
| 🔍 **Web Search** | [DuckDuckGo](https://duckduckgo.com) (zero-key, no account needed) | Exa Neural Search |

### How Local Mode Works
1. **Install Parley** — that's it. No extra setup.
2. **First launch**: If [Ollama](https://ollama.com/download) is installed, Parley auto-downloads `deepseek-r1:1.5b` (~1 GB) in the background.
3. **Open Settings** → *Local Free Mode* tab to:
   - Install additional Ollama models (Phi-3 Mini, Gemma 2B, LLaMA 3.2) based on your hardware
   - Switch between Local / Cloud engines for STT, LLM, and Search independently
4. Parley auto-detects which mode to use: if no API keys are set, it falls back to the free local stack automatically.

> **Installing Ollama**: Download from [ollama.com/download](https://ollama.com/download) (free, runs models locally). Parley will auto-pull the default model on startup.

---

## ⚡ Core Features

- **Live Streaming Diarization**: Low-latency speech capture with Deepgram Nova-3 (`diarize=true`, `utterance_end_ms=5000`) — or **Faster-Whisper** locally for free.
- **Real-Time Interim Captions**: See live drafting captions that fluidly finalize into speaker-attributed transcript blocks.
- **Voice-Driven Speaker Renaming**: Spoken self-introductions (*"Hi, my name is Alex..."*, *"I am Sarah from design"*) and explicit commands (*"Speaker 1 is Bob"*) automatically update participant names in real time.
- **Dynamic Insight Extraction**: Periodic AI analysis powered by DeepSeek cloud (`deepseek-chat`) or **local Ollama** (DeepSeek-R1, Phi-3, Gemma 2B, LLaMA 3.2) — your choice.
- **Web Search & Scraping**: Built-in **DuckDuckGo** (free, no key) or Exa AI Neural Search (cloud, with key) — automatically looks up unknown processes, technologies, and external facts in real time.
- **Autonomous Autopilot Engine**:
  - **Browser Automation**: Automated social posting (Twitter/X, LinkedIn, Facebook), messaging (WhatsApp Web, Telegram), and web actions using persistent Chromium profiles (`~/.parley/browser_profile`) that remember your logins.
  - **OS & Screen Control**: Full-screen vision, screenshot inspection, and mouse/keyboard automation via PyAutoGUI & mss with global `Esc` emergency stop.
  - **Intent Classification**: Converts meeting agreements, action items, and chat commands into structured execution blueprints.
- **Multimodal Ask AI Panel**: Ask grounded questions using text or attached images (via drag-and-drop, file picker, or `Ctrl+V` clipboard paste).
- **Interactive Source Citations**: Click any `[u1, u3]` citation badge on a conflict or decision card to scroll and highlight the supporting utterances in the transcript.
- **Self-Contained Desktop App**: Native Electron shell with PyInstaller embedded Python runtime — runs on any Windows machine with zero setup.
- **Export**: One-click download of the complete meeting state and analysis as JSON.

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
│   │   ├── agent.py                  # DeepSeek/Ollama LLM agent loop & QA engine
│   │   ├── deepgram_client.py        # Deepgram Nova-3 live WebSocket client
│   │   ├── local_whisper.py          # 🆓 Faster-Whisper offline STT client
│   │   ├── ollama_client.py          # 🆓 Ollama local LLM client with auto model pull
│   │   ├── exa_client.py             # Exa AI Neural Web Search & content scraper
│   │   ├── duckduckgo_client.py      # 🆓 DuckDuckGo free web search client
│   │   ├── mock_data.py              # Offline multi-speaker meeting simulation
│   │   └── autopilot/                # Autonomous Agent System
│   │       ├── action_planner.py     # Intent classifier & blueprint generator
│   │       ├── browser_agent.py      # Playwright persistent-profile browser control
│   │       ├── os_agent.py           # PyAutoGUI + mss screen/keyboard/mouse agent
│   │       ├── voice_renamer.py      # Speech-driven speaker identification regex engine
│   │       └── utils.py              # Base64 image & media helpers
│   └── tests/
│       ├── test_agent.py             # Unit tests for agent analysis & QA
│       ├── test_autopilot.py         # Unit tests for intent classification & renamer
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
│       │   ├── AskAIPanel.tsx        # Multimodal Q&A with image upload & Exa Web Search
│       │   └── AutopilotDrawer.tsx   # Floating execution status drawer & emergency stop
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
