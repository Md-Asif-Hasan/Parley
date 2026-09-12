# Parley 🎙️💬

**Parley** is a real-time meeting assistant and opinion analyzer that listens to discussions (2–5 participants), displays live speaker-labelled transcripts, summarizes participant views, flags potential scheduling or proposal conflicts, highlights agreed consensus decisions, and answers grounded questions about the meeting.

Parley is available as a **Web Application**, a **Single-Container Docker App**, and a **Native Cross-Platform Desktop Application** for Windows, macOS, and Linux.

---

## ⚡ Core Features

- **Live Streaming Diarization**: Low-latency speech capture with Deepgram Nova-3 (`diarize=true`, `utterance_end_ms=5000`).
- **Real-Time Interim Captions**: See live drafting captions that fluidly finalize into speaker-attributed transcript blocks.
- **Dynamic Insight Extraction**: Periodic AI analysis powered by DeepSeek Flash/Chat (`deepseek-chat`) detailing participant viewpoints, incompatible proposal warnings, and consensus checklists.
- **Interactive Source Citations**: Click any `[u1, u3]` citation badge on a conflict or decision card to scroll and highlight the supporting utterances in the transcript.
- **Grounded Q&A**: Ask natural language questions with responses citing specific transcript statements.
- **Export**: One-click download of the complete meeting state as JSON.
- **Desktop UX & Shortcuts**: Native frameless window, system tray, and keyboard shortcuts (`Space` toggle record, `Ctrl/Cmd+K` Ask AI, `Ctrl/Cmd+E` Export JSON).

---

## 🐳 Docker Deployment (Any Device)

Run the entire stack (FastAPI backend + React frontend + WebSocket) in a single unified container on port `8000`:

### Using Docker Compose
```bash
# Clone the repository
git clone https://github.com/Md-Asif-Hasan/Parley.git
cd Parley

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
  --name parley parley-app
```

---

## 🖥️ Cross-Platform Desktop Application (Windows / macOS / Linux)

Parley includes a native Electron desktop shell that automatically manages the backend server subprocess.

### Run in Development
```bash
# 1. Build the frontend assets
cd frontend && npm install && npm run build

# 2. Run the desktop app
cd ../desktop && npm install && npm start
```

### Build Installers for Windows, macOS, and Linux
```bash
cd desktop

# Build installer for current OS
npm run dist

# Targeted builds
npm run dist:win    # Generates Windows NSIS installer & Portable .exe
npm run dist:mac    # Generates macOS .dmg and .zip
npm run dist:linux  # Generates Linux .AppImage and .deb
```
The compiled installers will be saved in `desktop/dist/`.

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
