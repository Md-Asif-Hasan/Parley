# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

datas = []
binaries = []
hiddenimports = []

# Bundle compiled frontend static files directly inside the executable
frontend_dist = os.path.abspath(os.path.join("..", "frontend", "dist"))
if os.path.isdir(frontend_dist) and os.path.exists(os.path.join(frontend_dist, "index.html")):
    datas.append((frontend_dist, "static"))

for pkg in ["uvicorn", "fastapi", "starlette", "pydantic", "pydantic_settings",
            "websockets", "httpx", "anyio", "click", "h11",
            "python_dotenv", "dotenv", "playwright", "pyautogui", "mss", "pynput", "PIL"]:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

for pkg in ["uvicorn", "fastapi", "starlette", "pydantic", "anyio", "websockets", "app.autopilot"]:
    hiddenimports += collect_submodules(pkg)

hiddenimports += [
    "uvicorn.logging",
    "uvicorn.loops", "uvicorn.loops.auto", "uvicorn.loops.asyncio",
    "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl", "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan", "uvicorn.lifespan.off", "uvicorn.lifespan.on",
    "email.mime.text", "email.mime.multipart", "email.mime.base",
    "app", "app.main", "app.config", "app.models",
    "app.state", "app.agent", "app.deepgram_client", "app.mock_data",
    "app.exa_client",
    "app.autopilot", "app.autopilot.action_planner", "app.autopilot.browser_agent",
    "app.autopilot.os_agent", "app.autopilot.voice_renamer", "app.autopilot.utils",
    "PIL", "PIL.Image", "pyautogui", "mss", "pynput",
    "dotenv",
]

# Remove duplicates
hiddenimports = list(set(hiddenimports))

a = Analysis(
    ["parley_server.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "scipy", "cv2",
              "pytest", "pytest_asyncio", "_pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="parley-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r"..\desktop\icon.ico",
)
