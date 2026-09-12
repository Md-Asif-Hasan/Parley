"""Offline SDK contract tests: real OpenAI parsing over a fake HTTP transport."""

import asyncio
import json
import unittest

import httpx
from openai import AsyncOpenAI

from parley_agent import AgentError, Analysis, MeetingAgent, Utterance


def utterance(uid="u1", speaker="speaker_0"):
    return Utterance(id=uid, speaker_id=speaker, start=0, end=2,
                     text="I prefer launching on Friday.")


def response_body(value=None, *, content=None, status="completed", extra_output=()):
    return {
        "id": "resp_test", "object": "response", "created_at": 1,
        "status": status, "model": "test-model", "parallel_tool_calls": False,
        "tool_choice": "auto", "tools": [],
        "output": [*extra_output, {
            "id": "msg_test", "type": "message", "role": "assistant",
            "status": "completed", "content": content if content is not None else [{
                "type": "output_text", "text": json.dumps(value), "annotations": [],
            }],
        }],
    }


class AgentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.body = response_body(Analysis.empty().model_dump())
        self.requests = []
        self.exa_requests = []
        self.exa_status = 200
        self.exa_body = {"results": [{"title": "Docs", "url": "https://example.com/docs",
                                      "highlights": ["Official feature description."]}]}

        async def handler(request):
            self.requests.append(json.loads(request.content))
            return httpx.Response(200, json=self.body)

        self.client = AsyncOpenAI(api_key="offline-test", max_retries=0,
                                  http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        async def exa_handler(request):
            self.exa_requests.append(request)
            return httpx.Response(self.exa_status, json=self.exa_body)
        self.agent = MeetingAgent(self.client, "test-model", exa_api_key="exa-offline-test",
                                  exa_client=httpx.AsyncClient(transport=httpx.MockTransport(exa_handler)))

    async def asyncTearDown(self):
        await self.agent.aclose()

    async def test_real_sdk_structured_parse_and_request_contract(self):
        result = await self.agent.update_analysis([utterance()], Analysis.empty())
        self.assertEqual(result, Analysis.empty())
        request = self.requests[0]
        self.assertEqual(request["text"]["format"]["type"], "json_schema")
        self.assertTrue(request["text"]["format"]["strict"])
        self.assertFalse(request["store"])
        self.assertNotIn("tools", request)

    async def test_unknown_source_is_rejected(self):
        value = Analysis.empty().model_dump()
        value["decisions"] = [{"description": "Agreed", "utterance_ids": ["u999"]}]
        self.body = response_body(value)
        with self.assertRaisesRegex(AgentError, "unknown source"):
            await self.agent.update_analysis([utterance()], Analysis.empty())

    async def test_wrong_speaker_attribution_is_rejected(self):
        value = Analysis.empty().model_dump()
        value["speaker_summaries"] = [{"speaker_id": "speaker_0", "summary": "Friday",
                                       "utterance_ids": ["u2"]}]
        self.body = response_body(value)
        with self.assertRaisesRegex(AgentError, "another speaker"):
            await self.agent.update_analysis([utterance(), utterance("u2", "speaker_1")], Analysis.empty())

    async def test_refusal_and_incomplete_results_are_rejected(self):
        for content, status in [([{"type": "refusal", "refusal": "No"}], "completed"),
                                (None, "incomplete")]:
            with self.subTest(status=status):
                self.body = response_body(Analysis.empty().model_dump(), content=content, status=status)
                with self.assertRaises(AgentError):
                    await self.agent.update_analysis([utterance()], Analysis.empty())

    async def test_malformed_schema_is_rejected(self):
        self.body = response_body({"unexpected": "result"})
        with self.assertRaises(AgentError):
            await self.agent.update_analysis([utterance()], Analysis.empty())

    async def test_input_limit_does_not_send_request(self):
        self.agent.max_input_chars = 10
        with self.assertRaisesRegex(AgentError, "input limit"):
            await self.agent.update_analysis([utterance()], Analysis.empty())
        self.assertEqual(self.requests, [])

    async def test_question_rejects_unknown_web_source(self):
        self.body = response_body({"text": "A claim", "utterance_ids": [], "search_ids": ["s99"]})
        with self.assertRaises(AgentError):
            await self.agent.answer_question("Why?", [utterance()], Analysis.empty())

    async def test_search_preserves_provider_citations(self):
        result = await self.agent.search_web("docs", [utterance()])
        self.assertEqual(result.citations[0].url, "https://example.com/docs")
        self.assertEqual(result.citations[0].start_index, 0)
        self.assertEqual(result.citations[0].end_index, len(result.text))
        self.assertEqual(result.sources[0].excerpt, "Official feature description.")
        request = self.exa_requests[0]
        self.assertEqual(str(request.url), "https://api.exa.ai/search")
        self.assertEqual(request.headers["x-api-key"], "exa-offline-test")
        self.assertEqual(json.loads(request.content)["query"], "docs")
        self.assertEqual(self.requests, [])  # No OpenAI built-in tool or extra LLM call.

    async def test_empty_search_is_explicit(self):
        self.exa_body = {"results": []}
        result = await self.agent.search_web("docs", [])
        self.assertIn("no results", result.text)
        self.assertEqual(result.citations, [])

    async def test_exa_http_error_is_recoverable(self):
        self.exa_status = 401
        self.exa_body = {"error": "invalid key"}
        with self.assertRaisesRegex(AgentError, "Exa search failed HTTP 401"):
            await self.agent.search_web("docs", [])

    async def test_exa_deduplicates_urls_and_citation_spans(self):
        item = self.exa_body["results"][0]
        self.exa_body["results"] = [item, item, {"title": "Other", "url": "https://example.com/other"}]
        result = await self.agent.search_web("docs", [])
        self.assertEqual(len(result.sources), 2)
        second = result.citations[1]
        self.assertEqual(result.text[second.start_index:second.end_index], "[2] Other\nNo excerpt returned.")

    async def test_deepseek_json_mode_parses_locally_without_strict_schema(self):
        self.agent.json_mode = True
        self.agent.reasoning_effort = "none"
        result = await self.agent.update_analysis([utterance()], Analysis.empty())
        self.assertEqual(result, Analysis.empty())
        request = self.requests[0]
        self.assertEqual(request["text"]["format"], {"type": "json_object"})
        self.assertEqual(request["reasoning"], {"effort": "none"})
        self.assertIn("search_request", request["instructions"])

    async def test_deepseek_json_mode_still_rejects_bad_shape(self):
        self.agent.json_mode = True
        self.body = response_body({"unknown": "field"})
        with self.assertRaises(AgentError):
            await self.agent.update_analysis([utterance()], Analysis.empty())

    async def test_deepseek_json_mode_rejects_incomplete_content(self):
        self.agent.json_mode = True
        self.body = response_body(Analysis.empty().model_dump(), status="incomplete")
        with self.assertRaises(AgentError):
            await self.agent.update_analysis([utterance()], Analysis.empty())

    async def test_empty_transcript_needs_no_model(self):
        self.assertEqual(await self.agent.update_analysis([], Analysis.empty()), Analysis.empty())
        self.assertEqual(self.requests, [])

    async def test_idea_reference_and_highlights_survive_parsing(self):
        self.agent.json_mode = True
        value = Analysis.empty().model_dump()
        value["search_request"] = {"purpose": "idea_reference", "query": "meeting whiteboard similar projects",
                                   "reason": "Find comparable implementations", "utterance_ids": ["u1"]}
        value["highlights"] = [{"speaker_id": "speaker_0", "description": "Record the launch constraint",
                                "source": "explicit_request", "reason": "Requested by participant",
                                "utterance_ids": ["u1"]}]
        self.body = response_body(value)
        result = await self.agent.update_analysis([utterance()], Analysis.empty())
        self.assertEqual(result.search_request.purpose, "idea_reference")
        self.assertEqual(result.highlights[0].source, "explicit_request")
        self.assertEqual(result.decisions, [])

    async def test_highlight_unknown_source_is_rejected(self):
        value = Analysis.empty().model_dump()
        value["highlights"] = [{"speaker_id": "speaker_0", "description": "Important point",
                                "source": "agent_detected", "reason": "Critical constraint",
                                "utterance_ids": ["missing"]}]
        self.body = response_body(value)
        with self.assertRaisesRegex(AgentError, "unknown source"):
            await self.agent.update_analysis([utterance()], Analysis.empty())

    async def test_highlight_wrong_speaker_is_rejected(self):
        value = Analysis.empty().model_dump()
        value["highlights"] = [{"speaker_id": "speaker_1", "description": "Important point",
                                "source": "agent_detected", "reason": "Critical constraint",
                                "utterance_ids": ["u1"]}]
        self.body = response_body(value)
        with self.assertRaisesRegex(AgentError, "Highlight attributed"):
            await self.agent.update_analysis([utterance(), utterance("u2", "speaker_1")], Analysis.empty())

    async def test_disabling_search_keeps_highlights(self):
        value = Analysis.empty().model_dump()
        value["search_request"] = {"purpose": "idea_reference", "query": "project references",
                                   "reason": "Related work", "utterance_ids": ["u1"]}
        value["highlights"] = [{"speaker_id": None, "description": "Important point",
                                "source": "agent_detected", "reason": "Critical constraint",
                                "utterance_ids": ["u1"]}]
        self.body = response_body(value)
        result = await self.agent.update_analysis([utterance(speaker=None)], Analysis.empty(), auto_search=False)
        self.assertIsNone(result.search_request)
        self.assertEqual(len(result.highlights), 1)

    async def test_timeout_becomes_recoverable_agent_error(self):
        async def slow_handler(request):
            await asyncio.sleep(1)
            return httpx.Response(200, json=self.body)
        client = AsyncOpenAI(api_key="offline-test", max_retries=0,
                             http_client=httpx.AsyncClient(transport=httpx.MockTransport(slow_handler)))
        agent = MeetingAgent(client, "test-model", timeout_seconds=0.01)
        try:
            with self.assertRaisesRegex(AgentError, "TimeoutError"):
                await agent.update_analysis([utterance()], Analysis.empty())
        finally:
            await agent.aclose()

    async def test_api_error_becomes_recoverable_agent_error(self):
        async def error_handler(request):
            return httpx.Response(429, json={"error": {"message": "rate limited", "type": "rate_limit"}})
        client = AsyncOpenAI(api_key="offline-test", max_retries=0,
                             http_client=httpx.AsyncClient(transport=httpx.MockTransport(error_handler)))
        agent = MeetingAgent(client, "test-model")
        try:
            with self.assertRaisesRegex(AgentError, "RateLimitError"):
                await agent.update_analysis([utterance()], Analysis.empty())
        finally:
            await agent.aclose()
