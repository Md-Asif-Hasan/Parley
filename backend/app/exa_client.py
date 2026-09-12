import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any

logger = logging.getLogger(__name__)
EXA_SEARCH_URL = "https://api.exa.ai/search"

def search_exa_sync(api_key: str, query: str, num_results: int = 4) -> List[Dict[str, Any]]:
    if not api_key:
        logger.warning("EXA_API_KEY not set - skipping web search.")
        return []
    payload = {
        "query": query,
        "num_results": num_results,
        "use_autoprompt": True,
        "contents": {
            "text": {"max_characters": 1200}
        }
    }
    req = urllib.request.Request(
        EXA_SEARCH_URL,
        headers={
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Parley-App/1.0"
        },
        data=json.dumps(payload).encode("utf-8"),
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("results", [])
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.warning(f"Exa HTTP error {e.code}: {body[:200]}")
        return []
    except Exception as e:
        logger.warning(f"Exa search failed: {e}")
        return []

def format_exa_results(results: List[Dict[str, Any]]) -> str:
    if not results:
        return ""
    lines = ["### Web Search Results (via Exa)"]
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        text = (r.get("text") or "").strip()
        date = r.get("published_date", "")
        date_str = f" [{date[:10]}]" if date else ""
        lines.append(f"[{i}] {title}{date_str}")
        if url:
            lines.append(f"URL: {url}")
        if text:
            snippet = text[:600] + ("..." if len(text) > 600 else "")
            lines.append(snippet)
        lines.append("")
    return "\n".join(lines)
