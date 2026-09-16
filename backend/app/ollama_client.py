import json
import logging
import urllib.request
import urllib.error
import asyncio
from typing import Dict, Any, List, Optional
from .config import settings

logger = logging.getLogger(__name__)

# Preset models tailored for different host machine capabilities
RECOMMENDED_MODELS = [
    {
        "id": "deepseek-r1:1.5b",
        "name": "DeepSeek-R1 (1.5B Light)",
        "description": "Fastest reasoning model, optimized for standard laptops & CPUs (1.1 GB download)",
        "size": "1.1 GB",
        "category": "light",
        "recommended": True
    },
    {
        "id": "qwen2.5:1.5b",
        "name": "Qwen 2.5 (1.5B Light)",
        "description": "Ultra-fast general intelligence, lightweight & responsive (1.0 GB download)",
        "size": "1.0 GB",
        "category": "light",
        "recommended": False
    },
    {
        "id": "deepseek-r1:7b",
        "name": "DeepSeek-R1 (7B Reasoning)",
        "description": "High accuracy reasoning & meeting analysis, best with 8GB+ VRAM/RAM (4.7 GB download)",
        "size": "4.7 GB",
        "category": "mid",
        "recommended": False
    },
    {
        "id": "llama3.2:3b",
        "name": "Llama 3.2 (3B Balanced)",
        "description": "Meta Llama 3.2 3B model for concise, intelligent meeting summaries (2.0 GB download)",
        "size": "2.0 GB",
        "category": "mid",
        "recommended": False
    }
]

# Pull progress tracker for active background downloads
pull_status: Dict[str, Any] = {
    "is_pulling": False,
    "model": None,
    "status": "idle",
    "completed_bytes": 0,
    "total_bytes": 0,
    "percent": 0,
    "error": None
}

def is_ollama_running(base_url: Optional[str] = None) -> bool:
    """Checks if Ollama service is active and listening at base_url."""
    url = (base_url or settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
    try:
        req = urllib.request.Request(f"{url}/api/tags", headers={"User-Agent": "Parley-Backend"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False

def get_installed_ollama_models(base_url: Optional[str] = None) -> List[str]:
    """Retrieves list of model names already downloaded in Ollama."""
    url = (base_url or settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
    try:
        req = urllib.request.Request(f"{url}/api/tags", headers={"User-Agent": "Parley-Backend"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = data.get("models", [])
            return [m.get("name") or m.get("model") for m in models if m]
    except Exception as e:
        logger.warning(f"Failed to fetch installed Ollama models: {e}")
        return []

def pull_ollama_model_sync(model_name: str, base_url: Optional[str] = None):
    """Synchronous / streaming pull of an Ollama model with global status updates."""
    global pull_status
    url = (base_url or settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
    pull_url = f"{url}/api/pull"

    pull_status.update({
        "is_pulling": True,
        "model": model_name,
        "status": f"Downloading {model_name}...",
        "completed_bytes": 0,
        "total_bytes": 0,
        "percent": 0,
        "error": None
    })

    try:
        body = json.dumps({"name": model_name, "stream": True}).encode("utf-8")
        req = urllib.request.Request(pull_url, data=body, headers={"Content-Type": "application/json"})
        
        with urllib.request.urlopen(req, timeout=1800) as resp:
            for line in resp:
                if not line:
                    continue
                try:
                    event = json.loads(line.decode("utf-8"))
                    status_str = event.get("status", "")
                    completed = event.get("completed", 0)
                    total = event.get("total", 0)

                    pct = round((completed / total) * 100, 1) if total > 0 else 0
                    pull_status.update({
                        "status": status_str,
                        "completed_bytes": completed,
                        "total_bytes": total,
                        "percent": pct
                    })
                except Exception:
                    pass

        pull_status.update({
            "is_pulling": False,
            "status": f"Successfully installed {model_name}",
            "percent": 100
        })
        logger.info(f"Finished pulling Ollama model: {model_name}")
    except Exception as e:
        logger.error(f"Error pulling Ollama model {model_name}: {e}")
        pull_status.update({
            "is_pulling": False,
            "status": "Download failed",
            "error": str(e)
        })

async def auto_ensure_default_model():
    """Autoconfigures Ollama and pulls default light model if Ollama is running but no model exists."""
    base_url = settings.OLLAMA_BASE_URL or "http://localhost:11434"
    if not is_ollama_running(base_url):
        logger.info("Ollama service not currently detected running on localhost.")
        return

    installed = get_installed_ollama_models(base_url)
    default_model = settings.OLLAMA_MODEL or "deepseek-r1:1.5b"

    # Check if target model or any variant is installed
    has_model = any(default_model in m for m in installed) or len(installed) > 0
    if not has_model and not pull_status["is_pulling"]:
        logger.info(f"Ollama running but no models found. Auto-pulling default light model: {default_model}")
        asyncio.create_task(asyncio.to_thread(pull_ollama_model_sync, default_model, base_url))
