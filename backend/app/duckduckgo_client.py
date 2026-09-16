import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def search_duckduckgo_sync(query: str, max_results: int = 4) -> List[Dict[str, Any]]:
    """
    Performs a free, zero-credentials web search via duckduckgo_search or fallback urllib scraping.
    """
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", "") or r.get("link", ""),
                    "snippet": r.get("body", "") or r.get("snippet", "")
                })
        return results
    except Exception as e:
        logger.warning(f"DuckDuckGo search package exception: {e}. Falling back to basic web search.")
        return fallback_ddg_search(query, max_results)

def fallback_ddg_search(query: str, max_results: int = 4) -> List[Dict[str, Any]]:
    """Fallback DuckDuckGo HTML parser if ddgs library encounters rate limits or environment issues."""
    import urllib.request
    import urllib.parse
    import re

    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            
        matches = re.findall(r'<a class="result__url" href="([^"]+)">[\s\S]*?<a class="result__snippet[^"]*">([\s\S]*?)</a>', html)
        results = []
        for link, snippet in matches[:max_results]:
            clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
            results.append({
                "title": link,
                "url": link,
                "snippet": clean_snippet
            })
        return results
    except Exception as err:
        logger.error(f"Fallback DuckDuckGo search failed: {err}")
        return []

def format_ddg_results(results: List[Dict[str, Any]]) -> str:
    """Formats DuckDuckGo search results into a clean markdown string for QA context."""
    if not results:
        return "No external web search results found."
    formatted = ["### DuckDuckGo Live Search Results:"]
    for idx, r in enumerate(results, 1):
        formatted.append(f"{idx}. **[{r['title']}]({r['url']})**\n   {r['snippet']}")
    return "\n\n".join(formatted)
