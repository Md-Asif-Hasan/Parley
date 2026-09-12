"""Local WebSocket bridge: mock transcripts in, real AgentLoop events out."""

import asyncio
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .agent import MeetingAgent
from .loop import AgentLoop

app = FastAPI()
logger = logging.getLogger(__name__)


@app.websocket('/ws/meeting')
async def meeting(websocket: WebSocket) -> None:
    await websocket.accept()
    agent = None
    loop = None
    finish_task = None
    send_lock = asyncio.Lock()

    async def emit(event: dict) -> None:
        async with send_lock:
            await websocket.send_json(event)

    async def fail(exc: Exception) -> None:
        logger.exception('Meeting session failed')
        await emit({'type': 'error', 'data': {'scope': 'session', 'message': str(exc)}})
        await emit({'type': 'status', 'data': {'state': 'error'}})
        await websocket.close(code=1011)

    try:
        agent = MeetingAgent.from_env()
        if not agent.supports_web_search:
            raise ValueError('Exa API key is required for this live session. Search is not disabled automatically.')
        loop = AgentLoop(agent, emit, interval_seconds=15, auto_search=True)
        await loop.start()
        await emit({'type': 'status', 'data': {'state': 'recording'}})

        async def finish() -> None:
            try:
                result = await loop.stop()
                await emit({'type': 'meeting.export', 'data': result})
                await websocket.close(code=1000)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await fail(exc)

        while True:
            event = await websocket.receive_json()
            if finish_task is not None:
                # Finalization owns the session until export/close; no new input.
                continue
            kind = event.get('type')
            if kind == 'meeting.stop':
                finish_task = asyncio.create_task(finish())
            elif kind == 'transcript.final':
                loop.ingest(event)
                await emit(event)
            elif kind == 'transcript.partial':
                await emit(event)
            else:
                raise ValueError(f'Unsupported meeting event: {kind}')
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        # receive_json can report an already closed socket after normal finish.
        if finish_task is None or not finish_task.done():
            try:
                await fail(exc)
            except (RuntimeError, WebSocketDisconnect):
                pass
    finally:
        if finish_task is not None:
            if not finish_task.done():
                finish_task.cancel()
            await asyncio.gather(finish_task, return_exceptions=True)
        if loop is not None:
            await loop.aclose()
        if agent is not None:
            await agent.aclose()
