import asyncio
import unittest
from unittest.mock import AsyncMock

from parley_agent import AgentError, AgentLoop, Analysis, Answer, Highlight, SearchRequest, SearchResult


def utterance(uid="u1", start=0):
    return {"id": uid, "speaker_id": "speaker_0", "start": start, "end": start + 1,
            "text": "How much does this API cost?"}


class FakeAgent:
    supports_web_search = True

    def __init__(self):
        self.calls = []
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.release.set()
        self.search_entered = asyncio.Event()
        self.search_release = asyncio.Event()
        self.search_release.set()
        self.search_count = 0
        self.fail = False
        self.suggest_search = False

    async def update_analysis(self, transcript, previous_analysis, **kwargs):
        self.calls.append([u.id for u in transcript])
        self.entered.set()
        await self.release.wait()
        if self.fail:
            raise AgentError("simulated failure")
        result = Analysis.empty()
        result.meeting_summary = ",".join(u.id for u in transcript)
        if self.suggest_search and kwargs["auto_search"]:
            result.search_request = SearchRequest(query="API pricing", reason="Cost discussion",
                                                  utterance_ids=[transcript[0].id])
        return result

    async def answer_question(self, question, transcript, analysis, searches):
        await self.release.wait()
        return Answer(text=question, utterance_ids=[u.id for u in transcript], search_ids=[])

    async def search_web(self, query, related):
        self.search_count += 1
        self.search_entered.set()
        await self.search_release.wait()
        return SearchResult(text="Search result", citations=[])


class LoopTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.agent = FakeAgent()
        self.events = []

        async def emit(event):
            self.events.append(event)

        self.loop = AgentLoop(self.agent, emit, interval_seconds=3600, search_cooldown_seconds=0)
        await self.loop.start()

    async def asyncTearDown(self):
        self.agent.release.set()
        self.agent.search_release.set()
        await self.loop.aclose()

    async def test_partial_ignored_and_final_ids_deduplicated(self):
        self.assertEqual(self.loop.ingest({"type": "transcript.partial", "data": {"text": "draft"}}), 0)
        event = {"type": "transcript.final", "data": {"utterances": [utterance()]}}
        self.assertEqual(self.loop.ingest(event), 1)
        self.assertEqual(self.loop.ingest(event), 0)
        self.assertEqual(self.loop.version, 1)
        with self.assertRaises(ValueError):
            self.loop.append_final([utterance("u2"), {**utterance(), "text": "changed"}])
        self.assertEqual(self.loop.version, 1)  # Entire invalid batch rejected.

    async def test_transcript_sorted_without_text_based_deduplication(self):
        self.loop.append_final([utterance("u2", 4), utterance("u1", 1)])
        self.assertEqual([u.id for u in self.loop.transcript], ["u1", "u2"])

    async def test_slow_analysis_does_not_block_ingestion_or_mix_snapshots(self):
        self.loop.append_final([utterance()])
        self.agent.release.clear()
        task = asyncio.create_task(self.loop.analyze_now())
        await self.agent.entered.wait()
        self.loop.append_final([utterance("u2", 2)])
        self.agent.release.set()
        await task
        self.assertEqual(self.loop.analysis_version, 1)
        self.assertFalse(self.loop.export()["analysis_is_current"])
        await self.loop.analyze_now()
        self.assertEqual(self.agent.calls, [["u1"], ["u1", "u2"]])

    async def test_concurrent_analysis_runs_once_for_same_version(self):
        self.loop.append_final([utterance()])
        await asyncio.gather(self.loop.analyze_now(), self.loop.analyze_now())
        self.assertEqual(len(self.agent.calls), 1)

    async def test_failure_keeps_previous_analysis_and_transcript(self):
        self.loop.append_final([utterance()])
        await self.loop.analyze_now()
        self.loop.append_final([utterance("u2", 2)])
        self.agent.fail = True
        result = await self.loop.stop()
        self.assertEqual(result["analysis"]["meeting_summary"], "u1")
        self.assertEqual(len(result["transcript"]), 2)
        self.assertFalse(result["analysis_is_current"])
        self.assertIsNotNone(result["analysis_error"])
        self.assertEqual(result["status"], "stopped")

    async def test_stop_includes_tail_and_is_idempotent(self):
        self.loop.append_final([utterance()])
        await self.loop.analyze_now()
        self.loop.append_final([utterance("tail", 4)])
        exported = await self.loop.stop()
        self.assertEqual(exported["analysis"]["meeting_summary"], "u1,tail")
        self.assertEqual(exported, await self.loop.stop())
        with self.assertRaises(ValueError):
            self.loop.append_final([utterance("too-late", 5)])

    async def test_question_uses_snapshot(self):
        self.loop.append_final([utterance()])
        self.agent.release.clear()
        task = asyncio.create_task(self.loop.ask("q1", "What was said?"))
        await asyncio.sleep(0)
        self.loop.append_final([utterance("u2", 2)])
        self.agent.release.set()
        result = await task
        self.assertEqual(result["utterance_ids"], ["u1"])
        self.assertEqual(result["based_on_transcript_version"], 1)

    async def test_search_is_independent_and_deduplicated(self):
        self.agent.suggest_search = True
        self.agent.search_release.clear()
        self.loop.append_final([utterance()])
        await self.loop.analyze_now()
        await self.agent.search_entered.wait()
        self.loop.append_final([utterance("u2", 2)])
        await self.loop.analyze_now()
        self.assertEqual(self.loop.analysis_version, 2)
        self.assertEqual(self.agent.search_count, 1)
        self.agent.search_release.set()
        await self.loop.stop()
        self.assertEqual(self.loop.searches[0].status, "completed")
        self.assertEqual(self.agent.search_count, 1)

    async def test_stop_does_not_launch_new_search(self):
        self.agent.suggest_search = True
        self.loop.append_final([utterance()])
        await self.loop.stop()
        self.assertEqual(self.agent.search_count, 0)

    async def test_idea_search_purpose_and_highlights_reach_events_and_export(self):
        result = Analysis.empty()
        result.highlights = [Highlight(speaker_id="speaker_0", description="Build a meeting board",
                                       source="explicit_request", reason="Asked to record",
                                       utterance_ids=["u1"])]
        result.search_request = SearchRequest(purpose="idea_reference", query="similar meeting boards",
                                              reason="Find project references", utterance_ids=["u1"])
        self.agent.update_analysis = AsyncMock(return_value=result)
        self.loop.append_final([utterance()])
        await self.loop.analyze_now()
        await self.agent.search_entered.wait()
        self.assertEqual(self.loop.searches[0].purpose, "idea_reference")
        analysis_event = next(e for e in self.events if e["type"] == "analysis.updated")
        self.assertEqual(analysis_event["data"]["highlights"][0]["source"], "explicit_request")
        exported = self.loop.export()
        self.assertEqual(exported["analysis"]["highlights"][0]["utterance_ids"], ["u1"])
        self.assertEqual(exported["searches"][0]["purpose"], "idea_reference")

    async def test_stop_waits_for_old_analysis_then_analyzes_tail(self):
        self.loop.append_final([utterance()])
        self.agent.release.clear()
        pending = asyncio.create_task(self.loop.analyze_now())
        await self.agent.entered.wait()
        self.loop.append_final([utterance("tail", 4)])
        stopped = asyncio.create_task(self.loop.stop())
        await asyncio.sleep(0)
        self.assertFalse(stopped.done())
        self.agent.release.set()
        await pending
        result = await stopped
        self.assertEqual(self.agent.calls, [["u1"], ["u1", "tail"]])
        self.assertEqual(result["based_on_transcript_version"], 2)
        self.assertEqual(result["analysis"]["meeting_summary"], "u1,tail")

    async def test_periodic_analysis_runs_for_new_final_only(self):
        await self.loop.aclose()
        async def emit(event):
            self.events.append(event)
        self.loop = AgentLoop(self.agent, emit, interval_seconds=0.01, auto_search=False)
        await self.loop.start()
        self.loop.append_final([utterance()])
        await asyncio.wait_for(self.agent.entered.wait(), timeout=1)
        await asyncio.sleep(0.03)
        self.assertEqual(len(self.agent.calls), 1)
