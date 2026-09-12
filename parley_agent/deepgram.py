"""Nova-3 streaming input and speaker-normalized transcript events."""
import asyncio
import json
import os
import ssl
from itertools import groupby
from pathlib import Path
from urllib.parse import urlencode
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosedOK

OPTIONS = dict(diarize='true', punctuate='true', interim_results='true', smart_format='true', model='nova-3')


class TranscriptNormalizer:
    def __init__(self):
        self.count = 0
        self.seen = set()

    def normalize(self, message):
        if message.get('type') != 'Results':
            return None
        alternative = message['channel']['alternatives'][0]
        text = alternative.get('transcript', '').strip()
        words = alternative.get('words', [])
        speakers = {w.get('speaker') for w in words}
        speaker = next(iter(speakers)) if len(speakers) == 1 else None
        if not message.get('is_final'):
            return {'type': 'transcript.partial', 'data': {'text': text, 'speaker_id': f'speaker_{speaker}' if speaker is not None else None}}
        if not text:
            return {'type': 'transcript.partial', 'data': {'text': '', 'speaker_id': None}}
        key = (message.get('start'), message.get('duration'), tuple(message.get('channel_index', [])))
        if key in self.seen:
            return None
        self.seen.add(key)
        groups = [(label, list(items)) for label, items in groupby(words, lambda w: w.get('speaker'))]
        if not groups:
            groups = [(None, [{'start': message['start'], 'end': message['start'] + message['duration']}])]
        utterances = []
        for label, items in groups:
            self.count += 1
            utterances.append({'id': f'u{self.count}', 'speaker_id': f'speaker_{label}' if label is not None else None,
                               'start': items[0]['start'], 'end': items[-1]['end'],
                               'text': text if len(groups) == 1 else ' '.join(w.get('punctuated_word') or w['word'] for w in items)})
        return {'type': 'transcript.final', 'data': {'utterances': utterances}}


class DeepgramInput:
    def __init__(self, socket, emit):
        self.socket, self.emit = socket, emit
        self.closing = False
        self.metadata = None
        self.normalizer = TranscriptNormalizer()
        self.task = asyncio.create_task(self._receive())

    @classmethod
    async def open(cls, emit):
        path = Path(__file__).resolve().parents[2] / 'parley.local.json'
        config = json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
        key = os.environ.get('DEEPGRAM_API_KEY', config.get('deepgram_api_key', '')).strip()
        if not key:
            raise ValueError('Set DEEPGRAM_API_KEY or deepgram_api_key in parent parley.local.json')
        # Containerized WebM/Opus: omit raw encoding/sample_rate parameters.
        socket = await connect('wss://api.deepgram.com/v1/listen?' + urlencode(OPTIONS),
                               additional_headers={'Authorization': f'Token {key}'},
                               ssl=ssl.create_default_context(), open_timeout=15, close_timeout=5)
        return cls(socket, emit)

    async def send_audio(self, audio):
        if self.closing:
            raise ValueError('Audio arrived after Deepgram finalization started')
        await self.socket.send(audio)

    async def _receive(self):
        try:
            while True:
                try:
                    raw = await asyncio.wait_for(self.socket.recv(), timeout=4)
                except TimeoutError:
                    if not self.closing:
                        await self.socket.send(json.dumps({'type': 'KeepAlive'}))
                    continue
                message = json.loads(raw)
                if message.get('type') == 'Error':
                    raise RuntimeError('Deepgram: ' + message.get('description', str(message)))
                if message.get('type') == 'Metadata':
                    self.metadata = message
                event = self.normalizer.normalize(message)
                if event is not None:
                    await self.emit(event)
        except ConnectionClosedOK:
            if self.metadata is None:
                raise RuntimeError('Deepgram closed without final metadata')

    async def finish(self):
        self.closing = True
        if not self.task.done():
            try:
                await self.socket.send(json.dumps({'type': 'CloseStream'}))
            except ConnectionClosedOK:
                # A finite container can reach EOF just before CloseStream.
                pass
        await asyncio.wait_for(asyncio.shield(self.task), timeout=20)
        if self.metadata is None:
            raise RuntimeError('Deepgram closed without final metadata; tail transcription was not confirmed')

    async def aclose(self):
        self.task.cancel()
        await asyncio.gather(self.task, return_exceptions=True)
        await self.socket.close()
