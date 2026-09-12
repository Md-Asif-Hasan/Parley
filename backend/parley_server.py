"""
Parley Backend - PyInstaller entry point.

This script is the target for pyinstaller parley_server.spec.
It embeds the Python runtime and all dependencies into a single binary.
The Electron desktop app spawns this binary directly - no Python install required.
"""
import multiprocessing
import sys
import os

# Required for PyInstaller multiprocessing support on Windows
multiprocessing.freeze_support()


def _patch_env():
    """Load .env from the same directory as the frozen binary."""
    if getattr(sys, "frozen", False):
        bundle_dir = os.path.dirname(sys.executable)
        env_path = os.path.join(bundle_dir, ".env")
        if os.path.isfile(env_path):
            from dotenv import load_dotenv
            load_dotenv(env_path, override=False)


def main():
    _patch_env()

    port = 8000
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--port" and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except ValueError:
                pass

    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()