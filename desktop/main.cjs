const { app, BrowserWindow, ipcMain, session, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const http = require("http");
const { spawn } = require("child_process");

let mainWindow = null;
let backendProcess = null;

const BACKEND_PORT = 8000;
const HEALTH_URL = `http://127.0.0.1:${BACKEND_PORT}/health`;

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------
function checkBackendHealth() {
  return new Promise((resolve) => {
    const req = http.get(HEALTH_URL, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on("error", () => resolve(false));
    req.setTimeout(1200, () => {
      req.destroy();
      resolve(false);
    });
  });
}

// ---------------------------------------------------------------------------
// Find bundled backend binary or fallback to python
// ---------------------------------------------------------------------------
function findBackendBinary() {
  const binaryName =
    process.platform === "win32" ? "parley-server.exe" : "parley-server";

  const searchDirs = [
    process.resourcesPath,
    path.join(process.resourcesPath || "", "app.asar.unpacked"),
    path.dirname(app.getPath("exe")),
    path.join(path.dirname(app.getPath("exe")), "resources"),
    path.join(__dirname, "..", "backend", "dist"),
    path.join(__dirname, "dist"),
    __dirname,
  ].filter(Boolean);

  for (const dir of searchDirs) {
    const fullPath = path.join(dir, binaryName);
    try {
      if (fs.existsSync(fullPath)) {
        console.log(`[Parley] Found backend binary at: ${fullPath}`);
        return fullPath;
      }
    } catch (_) {}
  }
  return null;
}

// ---------------------------------------------------------------------------
// Launch process helper
// ---------------------------------------------------------------------------
function launchProcess(cmd, args, opts = {}) {
  try {
    const proc = spawn(cmd, args, {
      ...opts,
      stdio: "pipe",
      windowsHide: true,
    });

    if (proc.stdout) {
      proc.stdout.on("data", (d) => process.stdout.write(`[backend] ${d}`));
    }
    if (proc.stderr) {
      proc.stderr.on("data", (d) => process.stderr.write(`[backend] ${d}`));
    }
    proc.on("error", (err) => console.error(`[backend error] ${err.message}`));
    proc.on("close", (code) => console.log(`[backend closed] code ${code}`));

    return proc;
  } catch (err) {
    console.error(`[spawn exception for ${cmd}]`, err);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Start backend server
// ---------------------------------------------------------------------------
async function startBackendServer() {
  // Check if backend is already running on port 8000
  if (await checkBackendHealth()) {
    console.log("[Parley] Backend already running on port 8000.");
    return true;
  }

  const binaryPath = findBackendBinary();

  if (binaryPath) {
    console.log(`[Parley] Spawning bundled server: ${binaryPath}`);
    backendProcess = launchProcess(binaryPath, ["--port", String(BACKEND_PORT)], {
      cwd: path.dirname(binaryPath),
      env: { ...process.env },
    });
  } else {
    console.log("[Parley] No binary found. Attempting python fallback...");
    const backendDir = path.join(__dirname, "..", "backend");
    const pyCandidates =
      process.platform === "win32" ? ["py", "python", "python3"] : ["python3", "python"];

    for (const py of pyCandidates) {
      console.log(`[Parley] Trying python candidate: ${py}`);
      backendProcess = launchProcess(
        py,
        ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(BACKEND_PORT)],
        { cwd: backendDir, env: { ...process.env }, shell: true }
      );
      if (backendProcess && backendProcess.pid) {
        break;
      }
    }
  }

  // Poll for health (up to 40 seconds to allow PyInstaller unpacking on cold start)
  console.log("[Parley] Waiting for backend to become healthy...");
  for (let i = 0; i < 80; i++) {
    await new Promise((r) => setTimeout(r, 500));
    if (await checkBackendHealth()) {
      console.log("[Parley] Backend is ready and healthy!");
      return true;
    }
  }

  // If health check still failed after 40s
  dialog.showErrorBox(
    "Parley - Backend Startup Timeout",
    "The Parley backend server could not be started within 40 seconds.\n\n" +
      "Please make sure port 8000 is not blocked by a firewall or another application."
  );
  app.quit();
  return false;
}

// ---------------------------------------------------------------------------
// Create the browser window
// ---------------------------------------------------------------------------
function createWindow() {
  const iconPath =
    process.platform === "win32"
      ? path.join(__dirname, "icon.ico")
      : path.join(__dirname, "icon.png");

  mainWindow = new BrowserWindow({
    width: 1300,
    height: 850,
    minWidth: 980,
    minHeight: 640,
    title: "Parley - Real-time Meeting Assistant",
    icon: fs.existsSync(iconPath) ? iconPath : undefined,
    backgroundColor: "#020617",
    frame: false,
    titleBarStyle: "hidden",
    titleBarOverlay: {
      color: "#0f172a",
      symbolColor: "#94a3b8",
      height: 36,
    },
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  session.defaultSession.setPermissionRequestHandler(
    (webContents, permission, callback) => {
      callback(permission === "media");
    }
  );

  const isDev =
    process.env.NODE_ENV === "development" || process.argv.includes("--dev");
  const url = isDev
    ? "http://localhost:5173"
    : `http://127.0.0.1:${BACKEND_PORT}`;

  console.log(`[Parley] Loading UI from: ${url}`);
  mainWindow.loadURL(url);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// ---------------------------------------------------------------------------
// Window control IPC
// ---------------------------------------------------------------------------
ipcMain.on("window-minimize", () => mainWindow?.minimize());
ipcMain.on("window-maximize", () => {
  if (!mainWindow) return;
  mainWindow.isMaximized() ? mainWindow.unmaximize() : mainWindow.maximize();
});
ipcMain.on("window-close", () => mainWindow?.close());

// ---------------------------------------------------------------------------
// App lifecycle
// ---------------------------------------------------------------------------
app.whenReady().then(async () => {
  const ok = await startBackendServer();
  if (ok) createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

function stopBackend() {
  if (!backendProcess) return;
  console.log("[Parley] Stopping backend process...");
  try {
    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", String(backendProcess.pid), "/f", "/t"], {
        detached: true,
        stdio: "ignore",
      });
    } else {
      backendProcess.kill("SIGTERM");
    }
  } catch (_) {}
  backendProcess = null;
}

app.on("before-quit", stopBackend);
app.on("will-quit", stopBackend);
app.on("window-all-closed", () => {
  stopBackend();
  if (process.platform !== "darwin") app.quit();
});
