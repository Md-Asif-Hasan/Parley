import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from parley_agent.server import app
from parley_agent.deepgram import TranscriptNormalizer
from test_loop import FakeAgent, utterance


class FakeSpeech:
    def __init__(self, emit):
        self.emit = emit
        self.task = asyncio.create_task(asyncio.Event().wait())
        self.metadata = {'request_id': 'test'}
        self.audio = []
        self.closed = False

    async def send_audio(self, audio):
        self.audio.append(audio)
        await self.emit({'type': 'transcript.partial', 'data': {'text': 'draft', 'speaker_id': None}})

    async def finish(self):
        # Model the final tail arriving only after CloseStream.
        await self.emit({'type': 'transcript.final', 'data': {'utterances': [utterance()]}})

    async def aclose(self):
        self.closed = True
        self.task.cancel()
        await asyncio.gather(self.task, return_exceptions=True)


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.agent = FakeAgent()
        self.agent.aclose = AsyncMock()
        self.speech = None
        async def open_speech(emit):
            self.speech = FakeSpeech(emit)
            return self.speech
        self.patches = [patch('parley_agent.server.MeetingAgent.from_env', return_value=self.agent),
                        patch('parley_agent.server.DeepgramInput.open', side_effect=open_speech)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_audio_and_final_tail_reach_agent_before_export(self):
        with TestClient(app).websocket_connect('/ws/meeting') as ws:
            self.assertEqual(ws.receive_json()['data']['state'], 'recording')
            ws.send_bytes(b'container audio')
            self.assertEqual(ws.receive_json()['type'], 'transcript.partial')
            ws.send_json({'type': 'meeting.stop'})
            events = []
            while True:
                event = ws.receive_json()
                events.append(event)
                if event['type'] == 'meeting.export':
                    break
            self.assertTrue(events[-1]['data']['analysis_is_current'])
            self.assertEqual(self.agent.calls, [['u1']])
            self.assertEqual(self.speech.audio, [b'container audio'])
            kinds = [e['type'] for e in events]
            self.assertLess(kinds.index('transcript.final'), kinds.index('analysis.updated'))
        self.assertTrue(self.speech.closed)
        self.agent.aclose.assert_awaited_once()

    def test_missing_exa_fails_without_fallback(self):
        self.agent.supports_web_search = False
        with TestClient(app).websocket_connect('/ws/meeting') as ws:
            self.assertEqual(ws.receive_json()['type'], 'error')
            self.assertEqual(ws.receive_json()['data']['state'], 'error')
        self.assertIsNone(self.speech)

    def test_analysis_error_preserved_in_export(self):
        self.agent.fail = True
        with TestClient(app).websocket_connect('/ws/meeting') as ws:
            ws.receive_json()
            ws.send_json({'type': 'meeting.stop'})
            while True:
                event = ws.receive_json()
                if event['type'] == 'meeting.export':
                    break
            self.assertFalse(event['data']['analysis_is_current'])
            self.assertEqual(event['data']['analysis_error'], 'simulated failure')

    def test_disconnect_closes_speech_and_agent(self):
        with TestClient(app).websocket_connect('/ws/meeting') as ws:
            ws.receive_json()
        self.assertTrue(self.speech.closed)
        self.agent.aclose.assert_awaited_once()

    def test_flush_failure_does_not_claim_final_analysis(self):
        with TestClient(app).websocket_connect('/ws/meeting') as ws:
            ws.receive_json()
            self.speech.finish = AsyncMock(side_effect=RuntimeError('flush failed'))
            ws.send_json({'type': 'meeting.stop'})
            self.assertEqual(ws.receive_json()['data']['state'], 'processing')
            self.assertEqual(ws.receive_json()['data']['message'], 'flush failed')
            self.assertEqual(ws.receive_json()['data']['state'], 'error')
        self.assertEqual(self.agent.calls, [])


class NormalizerTests(unittest.TestCase):
    def message(self, final=True):
        return {'type': 'Results', 'is_final': final, 'speech_final': True, 'start': 0, 'duration': 3,
                'channel_index': [0, 1], 'channel': {'alternatives': [{'transcript': 'Hello. Yes. Again.', 'words': [
                    {'word': 'hello', 'punctuated_word': 'Hello.', 'start': 0, 'end': 1, 'speaker': 0},
                    {'word': 'yes', 'punctuated_word': 'Yes.', 'start': 1, 'end': 2, 'speaker': 1},
                    {'word': 'again', 'punctuated_word': 'Again.', 'start': 2, 'end': 3, 'speaker': 0}]}]}}

    def test_consecutive_speaker_runs_and_punctuation(self):
        rows = TranscriptNormalizer().normalize(self.message())['data']['utterances']
        self.assertEqual([u['speaker_id'] for u in rows], ['speaker_0', 'speaker_1', 'speaker_0'])
        self.assertEqual([u['text'] for u in rows], ['Hello.', 'Yes.', 'Again.'])
        self.assertEqual([u['id'] for u in rows], ['u1', 'u2', 'u3'])
        self.assertEqual(rows[-1]['end'], 3)

    def test_replayed_final_is_not_duplicated(self):
        n = TranscriptNormalizer()
        n.normalize(self.message())
        self.assertIsNone(n.normalize(self.message()))

    def test_partial_never_finalized_by_speech_final(self):
        event = TranscriptNormalizer().normalize(self.message(False))
        self.assertEqual(event['type'], 'transcript.partial')
        self.assertIsNone(event['data']['speaker_id'])

    def test_missing_words_keeps_text_and_unknown_speaker(self):
        message = self.message()
        message['channel']['alternatives'][0]['words'] = []
        row = TranscriptNormalizer().normalize(message)['data']['utterances'][0]
        self.assertIsNone(row['speaker_id'])
        self.assertEqual(row['text'], 'Hello. Yes. Again.')

    def test_single_speaker_preserves_smart_formatted_transcript(self):
        message = self.message()
        for word in message['channel']['alternatives'][0]['words']:
            word['speaker'] = 0
        message['channel']['alternatives'][0]['transcript'] = 'Call 123.'
        row = TranscriptNormalizer().normalize(message)['data']['utterances'][0]
        self.assertEqual(row['text'], 'Call 123.')

class DeepgramCloseTests(unittest.IsolatedAsyncioTestCase):
    async def test_completed_provider_stream_does_not_send_to_closed_socket(self):
        from parley_agent.deepgram import DeepgramInput
        speech = object.__new__(DeepgramInput)
        speech.socket = AsyncMock()
        speech.metadata = {'request_id': 'finished'}
        speech.task = asyncio.create_task(asyncio.sleep(0))
        await speech.task
        await speech.finish()
        speech.socket.send.assert_not_awaited()

    async def test_missing_metadata_is_not_a_completed_flush(self):
        from parley_agent.deepgram import DeepgramInput
        speech = object.__new__(DeepgramInput)
        speech.socket = AsyncMock()
        speech.metadata = None
        speech.task = asyncio.create_task(asyncio.sleep(0))
        await speech.task
        with self.assertRaisesRegex(RuntimeError, 'metadata'):
            await speech.finish()
