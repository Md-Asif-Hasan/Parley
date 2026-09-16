import asyncio
import json
import logging
import re
import urllib.request
from typing import Optional, Dict, Any
from .models import AnalysisResult, MeetingState
from .config import settings
from .exa_client import search_exa_sync, format_exa_results

logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM_PROMPT = """You are an objective, precise meeting analyst assistant for Parley.
Your task is to analyze the meeting transcript and produce a structured JSON object reflecting:
1. Per-speaker opinion summaries: Grounded summary of each participant's viewpoints, arguments, or preferences.
2. Potential conflicts: Incompatible proposals, scheduling conflicts, or hard resource constraints. Explain clearly WHY they conflict. Different ideas are NOT automatically conflicts unless they cannot both happen or directly contradict. Link each conflict to the exact source utterance IDs (e.g., ["u12", "u15"]).
3. Agreed decisions: Points that were explicitly agreed upon by participants (e.g., "Yes, let's do that", "Agreed"). Do not mark mere suggestions as agreed decisions. Link each decision to source utterance IDs.

CRITICAL RULES:
- Attribute opinions using the participant's speaker_id (e.g., "speaker_0", "speaker_1").
- Link every conflict and decision to the relevant utterance IDs (e.g. "u1", "u2").
- Do NOT hallucinate or invent availability, constraints, or agreements not stated in the transcript.
- Return ONLY a valid JSON object strictly matching this schema:
{
  "speaker_summaries": [
    {"speaker_id": "speaker_0", "summary": "..."}
  ],
  "conflicts": [
    {"type": "schedule", "description": "...", "utterance_ids": ["u1", "u3"]}
  ],
  "decisions": [
    {"description": "...", "utterance_ids": ["u4"]}
  ]
}
"""

QA_SYSTEM_PROMPT = """You are an intelligent, helpful meeting and research assistant for Parley.
Answer the user's question accurately, thoroughly, and in clear human-readable language.

Rules:
1. Ground your answer in the meeting transcript and analysis when referencing meeting events. Refer to participants by their display names and cite relevant utterance IDs (e.g., [u3]).
2. When external web search results (via Exa) are provided, process and synthesize the information to explain unknown processes, industry terms, technologies, competitors, or external facts clearly.
3. Highlight key takeaways and provide URLs/sources if web information was used.
4. If a topic was neither discussed in the meeting nor found in web search, state that clearly.
"""

def clean_json_string(raw: str) -> str:
    """Strip markdown code blocks or backticks if returned by LLM."""
    text = raw.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()
    return text

from .duckduckgo_client import search_duckduckgo_sync, format_ddg_results
from .ollama_client import is_ollama_running

class MeetingAgent:
    def __init__(self):
        use_ollama = settings.LLM_ENGINE == "ollama" or (
            settings.LLM_ENGINE == "auto" and not settings.DEEPSEEK_API_KEY and not settings.OPENAI_API_KEY
        )

        if use_ollama:
            base_url = (settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
            self.endpoint = f"{base_url}/v1/chat/completions"
            self.api_key = "ollama"
            self.model = settings.OLLAMA_MODEL or "deepseek-r1:1.5b"
            self.is_local = True
            logger.info(f"MeetingAgent initialized with Ollama Local LLM ({self.model} at {self.endpoint}).")
        elif settings.DEEPSEEK_API_KEY:
            self.api_key = settings.DEEPSEEK_API_KEY
            base_url = settings.DEEPSEEK_BASE_URL.rstrip("/")
            self.model = settings.DEEPSEEK_MODEL or "deepseek-chat"
            self.endpoint = f"{base_url}/chat/completions" if not base_url.endswith("/chat/completions") else base_url
            self.is_local = False
        else:
            self.api_key = settings.OPENAI_API_KEY
            base_url = (settings.OPENAI_BASE_URL or "https://api.deepseek.com").rstrip("/")
            self.model = settings.OPENAI_MODEL or "deepseek-chat"
            self.endpoint = f"{base_url}/chat/completions" if not base_url.endswith("/chat/completions") else base_url
            self.is_local = False

    def _sync_post(self, messages: list, json_mode: bool = False, temperature: float = 0.2) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        if json_mode and not self.is_local:
            body["response_format"] = {"type": "json_object"}

        req = urllib.request.Request(
            self.endpoint,
            headers=headers,
            data=json.dumps(body).encode("utf-8")
        )

        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"] or ""
            # Strip reasoning tokens <think>...</think> if returned by local DeepSeek-R1 model
            if "<think>" in content and "</think>" in content:
                content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
            return content

    async def update_analysis(
        self,
        transcript_text: str,
        previous_analysis: Optional[AnalysisResult] = None
    ) -> AnalysisResult:
        if not transcript_text.strip():
            return previous_analysis or AnalysisResult()

        if not self.is_local and (not self.api_key or self.api_key == "mock-key"):
            logger.warning("No API key or Local LLM configured. Returning previous or empty analysis.")
            return previous_analysis or AnalysisResult()

        prompt = f"""Current Meeting Transcript:
{transcript_text}

Previous Analysis:
{json.dumps(previous_analysis.model_dump() if previous_analysis else {}, indent=2)}

Please provide the updated, complete replacement analysis JSON object based on the full transcript."""

        messages = [
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

        try:
            raw_content = await asyncio.to_thread(self._sync_post, messages, True, 0.2)
            cleaned_json = clean_json_string(raw_content)
            data = json.loads(cleaned_json)
            analysis = AnalysisResult.model_validate(data)
            return analysis
        except Exception as e:
            logger.error(f"Error generating analysis: {e}", exc_info=True)
            return previous_analysis or AnalysisResult()

    async def answer_question(
        self,
        question: str,
        transcript_text: str,
        analysis: AnalysisResult
    ) -> str:
        trimmed_q = question.strip()
        if not trimmed_q:
            return "Please provide a question."

        if not self.is_local and (not self.api_key or self.api_key == "mock-key"):
            return f"Agent Question Answering requires API key or Local Ollama configured. Question asked: '{question}'"

        # Determine web search engine (Exa Cloud vs DuckDuckGo Free)
        web_context = ""
        should_search = any(
            keyword in trimmed_q.lower()
            for keyword in [
                "search", "lookup", "look up", "what is", "what are", "who is", "how to", "how does",
                "explain", "overview", "documentation", "latest", "news", "trend", "pricing", "cost",
                "competitor", "vs", "versus", "article", "website", "online", "github", "exa", "process",
                "concept", "tool", "framework", "library", "spec", "standard"
            ]
        ) or len(transcript_text.strip()) == 0 or len(trimmed_q.split()) <= 4

        if should_search:
            use_exa = (settings.SEARCH_ENGINE == "exa" or (settings.SEARCH_ENGINE == "auto" and settings.EXA_API_KEY))
            if use_exa and settings.EXA_API_KEY:
                try:
                    logger.info(f"Triggering Exa web search for query: {trimmed_q}")
                    search_results = await asyncio.to_thread(search_exa_sync, settings.EXA_API_KEY, trimmed_q, 4)
                    if search_results:
                        web_context = "\n\n" + format_exa_results(search_results)
                except Exception as e:
                    logger.warning(f"Exa search during QA failed: {e}")
            else:
                try:
                    logger.info(f"Triggering DuckDuckGo Free Web Search for query: {trimmed_q}")
                    ddg_results = await asyncio.to_thread(search_duckduckgo_sync, trimmed_q, 4)
                    if ddg_results:
                        web_context = "\n\n" + format_ddg_results(ddg_results)
                except Exception as e:
                    logger.warning(f"DuckDuckGo search during QA failed: {e}")


        context_blocks = []
        if transcript_text.strip():
            context_blocks.append(f"Meeting Transcript:\n{transcript_text}")
            context_blocks.append(f"Current Analysis Summary:\n{json.dumps(analysis.model_dump(), indent=2)}")
        else:
            context_blocks.append("Meeting Transcript: (No meeting discussion recorded yet)")

        if web_context:
            context_blocks.append(f"External Research Context (Exa Live Web Search):{web_context}")

        context_blocks.append(f"User Question:\n{trimmed_q}")
        context = "\n\n".join(context_blocks)

        messages = [
            {"role": "system", "content": QA_SYSTEM_PROMPT},
            {"role": "user", "content": context}
        ]

        try:
            return await asyncio.to_thread(self._sync_post, messages, False, 0.3)
        except Exception as e:
            logger.error(f"Error answering question: {e}", exc_info=True)
            return f"Error answering question: {str(e)}"

    async def answer_multimodal(
        self,
        question: str,
        image_base64: Optional[str],
        transcript_text: str,
        analysis: AnalysisResult
    ) -> Dict[str, Any]:
        """
        Handles multimodal chat queries containing text instructions and/or image uploads.
        Detects action plans (e.g. social media posting, message drafting) and generates response text.
        """
        from .autopilot.action_planner import classify_action_intent

        trimmed_q = question.strip() if question else ""
        action_plan = classify_action_intent(trimmed_q, image_base64)

        if not trimmed_q and image_base64:
            prompt_q = "Please inspect this attached image and summarize its content or how we can use it."
        else:
            prompt_q = trimmed_q

        text_response = await self.answer_question(prompt_q, transcript_text, analysis)

        return {
            "text": text_response,
            "has_image": bool(image_base64),
            "action_plan": action_plan.to_dict() if action_plan else None
        }

