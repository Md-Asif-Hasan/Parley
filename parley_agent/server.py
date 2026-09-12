"""Browser microphone -> Deepgram -> AgentLoop -> whiteboard events."""
import asyncio
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from .agent import MeetingAgent
from .deepgram import DeepgramInput
from .loop import AgentLoop

app = FastAPI()
logger = logging.getLogger(__name__)


@app.websocket('/ws/meeting')
async def meeting(websocket: WebSocket):
    await websocket.accept()
    agent = loop = speech = None
    tasks = []
    send_lock = asyncio.Lock()
    stop_requested = asyncio.Event()

    async def emit(event):
        async with send_lock:
            await websocket.send_json(event)

    try:
        agent = MeetingAgent.from_env()
        if not agent.supports_web_search:
            raise ValueError('Exa API key is required for this live session')
        loop = AgentLoop(agent, emit, interval_seconds=15, auto_search=True)
        await loop.start()

        async def transcript(event):
            if event['type'] == 'transcript.final':
                loop.ingest(event)
            await emit(event)

        speech = await DeepgramInput.open(transcript)
        await emit({'type': 'status', 'data': {'state': 'recording'}})

        async def receive_browser():
            while True:
                message = await websocket.receive()
                if message['type'] == 'websocket.disconnect':
                    raise WebSocketDisconnect(message.get('code', 1000))
                if stop_requested.is_set():
                    continue
                if message.get('bytes') is not None:
                    await speech.send_audio(message['bytes'])
                elif json.loads(message['text']).get('type') == 'meeting.stop':
                    stop_requested.set()
                else:
                    raise ValueError('Expected binary microphone audio or meeting.stop')

        reader = asyncio.create_task(receive_browser())
        stop_waiter = asyncio.create_task(stop_requested.wait())
        tasks.extend([reader, stop_waiter])
        done, _ = await asyncio.wait([reader, stop_waiter, speech.task], return_when=asyncio.FIRST_COMPLETED)
        if reader in done:
            await reader
        if speech.task in done:
            await speech.task
            # Normal EOF with final metadata is also a completed audio source.
            stop_requested.set()

        async def finish():
            await emit({'type': 'status', 'data': {'state': 'processing'}})
            # Browser sends its final MediaRecorder blob BEFORE meeting.stop.
            # Drain every Deepgram final result before stopping the agent loop.
            await speech.finish()
            result = await loop.stop()
            result['voice_input'] = 'deepgram'
            result['deepgram_metadata'] = speech.metadata
            await emit({'type': 'meeting.export', 'data': result})
            await websocket.close(code=1000)

        finalizer = asyncio.create_task(finish())
        tasks.append(finalizer)
        done, _ = await asyncio.wait([reader, finalizer], return_when=asyncio.FIRST_COMPLETED)
        if finalizer in done:
            await finalizer
        else:
            await reader
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception('Meeting session failed')
        try:
            await emit({'type': 'error', 'data': {'scope': 'session', 'message': str(exc)}})
            await emit({'type': 'status', 'data': {'state': 'error'}})
            await websocket.close(code=1011)
        except (RuntimeError, WebSocketDisconnect):
            pass
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if speech is not None:
            await speech.aclose()
        if loop is not None:
            await loop.aclose()
        if agent is not None:
            await agent.aclose()
