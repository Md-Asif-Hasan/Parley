"""One meeting per instance, running on the backend's existing asyncio loop."""

import asyncio
import copy
import time
from collections.abc import Awaitable, Callable, Sequence

from .agent import AgentError, MeetingAgent
from .schemas import Analysis, SearchRecord, SearchRequest, Utterance

Emit = Callable[[dict], Awaitable[None]]


class AgentLoop:
    def __init__(self, agent: MeetingAgent, emit: Emit, *, interval_seconds: float = 15,
                 auto_search: bool = True, search_cooldown_seconds: float = 30):
        if interval_seconds <= 0 or search_cooldown_seconds < 0:
            raise ValueError("Invalid analysis interval or search cooldown")
        self.agent = agent
        self.emit = emit
        self.interval_seconds = interval_seconds
        self.auto_search = auto_search and agent.supports_web_search
        self.search_cooldown_seconds = search_cooldown_seconds
        self._utterances: dict[str, Utterance] = {}
        self.version = 0
        self.analysis = Analysis.empty()
        self.analysis_version = 0
        self.analysis_error: str | None = None
        self.searches: list[SearchRecord] = []
        self.messages: list[dict] = []
        self.status = "idle"
        self._closing = asyncio.Event()
        self._analysis_lock = asyncio.Lock()
        self._stop_lock = asyncio.Lock()
        self._periodic_task: asyncio.Task | None = None
        self._search_task: asyncio.Task | None = None
        self._last_search = float("-inf")
        self._searched_queries: set[str] = set()

    @property
    def transcript(self) -> list[Utterance]:
        return sorted(self._utterances.values(), key=lambda u: (u.start, u.end, u.id))

    async def _emit(self, event_type: str, data: dict) -> None:
        await self.emit({"type": event_type, "data": data})

    async def start(self) -> None:
        if self.status != "idle":
            raise ValueError("Create a new AgentLoop for each meeting")
        self.status = "recording"
        self._periodic_task = asyncio.create_task(self._periodic())

    def append_final(self, utterances: Sequence[Utterance | dict]) -> int:
        """Synchronous ingestion; never waits for an LLM. IDs must be upstream-stable."""
        if self.status != "recording" or self._closing.is_set():
            raise ValueError("Final transcripts are accepted only before stop()")
        pending: dict[str, Utterance] = {}
        for value in utterances:
            utterance = value if isinstance(value, Utterance) else Utterance.model_validate(value)
            existing = pending.get(utterance.id, self._utterances.get(utterance.id))
            if existing is not None and existing != utterance:
                raise ValueError(f"Final utterance ID reused with different content: {utterance.id}")
            if existing is None:
                pending[utterance.id] = utterance
        self._utterances.update(pending)
        self.version += len(pending)
        return len(pending)

    def ingest(self, event: dict) -> int:
        """Accept normalized middleware events, NOT raw Deepgram responses."""
        if event.get("type") == "transcript.partial":
            return 0
        if event.get("type") != "transcript.final":
            raise ValueError("Expected transcript.final or transcript.partial")
        return self.append_final(event["data"]["utterances"])

    async def _periodic(self) -> None:
        while not self._closing.is_set():
            try:
                await asyncio.wait_for(self._closing.wait(), timeout=self.interval_seconds)
            except TimeoutError:
                await self.analyze_now()

    async def analyze_now(self, *, force: bool = False) -> bool:
        async with self._analysis_lock:
            if self.status not in {"recording", "processing"}:
                return False
            version = self.version
            if not self._utterances or (not force and version == self.analysis_version):
                return False
            snapshot = self.transcript
            search_enabled = self.auto_search and not self._closing.is_set()
            try:
                result = await self.agent.update_analysis(
                    snapshot, self.analysis.model_copy(deep=True),
                    search_history=[s.query for s in self.searches], auto_search=search_enabled,
                )
            except AgentError as exc:
                self.analysis_error = str(exc)
                await self._emit("error", {"scope": "analysis", "message": str(exc)})
                return False
            self.analysis = result
            self.analysis_version = version
            self.analysis_error = None
            await self._emit("analysis.updated", {
                **result.model_dump(), "based_on_transcript_version": version,
            })
            if result.search_request is not None:
                self._maybe_search(result.search_request, snapshot, version)
            return True

    def _maybe_search(self, request: SearchRequest, snapshot: list[Utterance], version: int) -> None:
        key = " ".join(request.query.casefold().split())
        if (not self.auto_search or self._closing.is_set()
                or key in self._searched_queries
                or (self._search_task is not None and not self._search_task.done())
                or time.monotonic() - self._last_search < self.search_cooldown_seconds):
            return
        self._searched_queries.add(key)
        self._last_search = time.monotonic()
        record = SearchRecord(
            id=f"s{len(self.searches) + 1}", purpose=request.purpose,
            query=request.query, reason=request.reason,
            utterance_ids=list(request.utterance_ids),
            based_on_transcript_version=version, status="searching",
        )
        self.searches.append(record)
        related = [u for u in snapshot if u.id in request.utterance_ids]
        self._search_task = asyncio.create_task(self._run_search(record, related))

    async def _run_search(self, record: SearchRecord, related: list[Utterance]) -> None:
        await self._emit("search.updated", record.model_dump())
        try:
            record.result = await self.agent.search_web(record.query, related)
            record.status = "completed"
        except AgentError as exc:
            record.status = "error"
            record.error = str(exc)
        await self._emit("search.updated", record.model_dump())

    async def ask(self, request_id: str, question: str) -> dict | None:
        if self.status == "idle" or not request_id.strip() or not question.strip():
            raise ValueError("Start a meeting and provide a request_id and nonblank question")
        version, snapshot = self.version, self.transcript
        analysis = self.analysis.model_copy(deep=True)
        searches = [s.model_copy(deep=True) for s in self.searches]
        try:
            answer = await self.agent.answer_question(question, snapshot, analysis, searches)
        except AgentError as exc:
            await self._emit("error", {"scope": "ask", "request_id": request_id, "message": str(exc)})
            return None
        data = {"request_id": request_id, **answer.model_dump(),
                "based_on_transcript_version": version}
        self.messages.append({"question": question, **data})
        await self._emit("agent.answer", data)
        return data

    async def stop(self) -> dict:
        """Call ONLY after middleware has flushed Deepgram and ingested the tail."""
        async with self._stop_lock:
            if self.status == "stopped":
                return self.export()
            if self.status == "idle":
                raise ValueError("Meeting has not started")
            self._closing.set()
            self.status = "processing"
            await self._emit("status", {"state": "processing"})
            if self._periodic_task is not None:
                await self._periodic_task
            await self.analyze_now(force=True)
            if self._search_task is not None:
                await self._search_task
            self.status = "stopped"
            await self._emit("status", {"state": "stopped"})
            return self.export()

    async def aclose(self) -> None:
        """Abort/disconnect cleanup; does not claim final analysis completed."""
        self._closing.set()
        tasks = [t for t in (self._periodic_task, self._search_task) if t is not None]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if self.status != "stopped":
            self.status = "error"

    def export(self) -> dict:
        return {
            "transcript": [u.model_dump() for u in self.transcript],
            "transcript_version": self.version,
            "analysis": self.analysis.model_dump(),
            "based_on_transcript_version": self.analysis_version,
            "analysis_is_current": self.analysis_version == self.version,
            "analysis_error": self.analysis_error,
            "searches": [s.model_dump() for s in self.searches],
            "messages": copy.deepcopy(self.messages), "status": self.status,
        }
