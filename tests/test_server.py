import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from parley_agent.server import app
from test_loop import FakeAgent, utterance


class ServerTests(unittest.TestCase):
    def agent(self):
        agent = FakeAgent()
        agent.aclose = AsyncMock()
        return agent

    def test_final_tail_reaches_loop_and_export_before_close(self):
        agent = self.agent()
        with patch('parley_agent.server.MeetingAgent.from_env', return_value=agent):
            with TestClient(app).websocket_connect('/ws/meeting') as ws:
                self.assertEqual(ws.receive_json()['data']['state'], 'recording')
                partial = {'type': 'transcript.partial', 'data': {'text': 'draft', 'speaker_id': None}}
                ws.send_json(partial)
                self.assertEqual(ws.receive_json(), partial)
                event = {'type': 'transcript.final', 'data': {'utterances': [utterance()]}}
                ws.send_json(event)
                self.assertEqual(ws.receive_json(), event)
                ws.send_json({'type': 'meeting.stop'})
                events = []
                while True:
                    output = ws.receive_json()
                    events.append(output)
                    if output['type'] == 'meeting.export':
                        break
                result = events[-1]['data']
                self.assertTrue(result['analysis_is_current'])
                self.assertEqual(result['transcript_version'], 1)
                self.assertEqual(agent.calls, [['u1']])
                self.assertEqual([e['type'] for e in events], ['status', 'analysis.updated', 'status', 'meeting.export'])
        agent.aclose.assert_awaited_once()

    def test_missing_exa_fails_instead_of_disabling_search(self):
        agent = self.agent()
        agent.supports_web_search = False
        with patch('parley_agent.server.MeetingAgent.from_env', return_value=agent):
            with TestClient(app).websocket_connect('/ws/meeting') as ws:
                self.assertEqual(ws.receive_json()['type'], 'error')
                self.assertEqual(ws.receive_json()['data']['state'], 'error')
        agent.aclose.assert_awaited_once()

    def test_analysis_failure_is_exported_without_replacement(self):
        agent = self.agent()
        agent.fail = True
        with patch('parley_agent.server.MeetingAgent.from_env', return_value=agent):
            with TestClient(app).websocket_connect('/ws/meeting') as ws:
                ws.receive_json()
                ws.send_json({'type': 'transcript.final', 'data': {'utterances': [utterance()]}})
                ws.receive_json()
                ws.send_json({'type': 'meeting.stop'})
                events = []
                while True:
                    event = ws.receive_json()
                    events.append(event)
                    if event['type'] == 'meeting.export':
                        break
                self.assertNotIn('analysis.updated', [e['type'] for e in events])
                self.assertFalse(events[-1]['data']['analysis_is_current'])
                self.assertEqual(events[-1]['data']['analysis_error'], 'simulated failure')

    def test_disconnect_closes_agent(self):
        agent = self.agent()
        with patch('parley_agent.server.MeetingAgent.from_env', return_value=agent):
            with TestClient(app).websocket_connect('/ws/meeting') as ws:
                ws.receive_json()
        agent.aclose.assert_awaited_once()
