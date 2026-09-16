import asyncio
import json
import logging
import os
import sys
from typing import Optional, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .models import Utterance, WSEvent, AnalysisResult
from .state import MeetingStateManager
from .deepgram_client import DeepgramLiveClient
from .agent import MeetingAgent
from .mock_data import MOCK_TRANSCRIPT_SAMPLE, MOCK_SPEAKERS_SAMPLE, MOCK_ANALYSIS_SAMPLE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("parley")

app = FastAPI(title="Parley Meeting Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

state_manager = MeetingStateManager()
agent = MeetingAgent()

# Active WebSocket connections
active_connections: Set[WebSocket] = set()

# Background analysis task tracker
analysis_in_flight = False
last_analyzed_utterance_count = 0
analysis_timer_task: Optional[asyncio.Task] = None
deepgram_client: Optional[DeepgramLiveClient] = None
simulation_task: Optional[asyncio.Task] = None

async def broadcast_event(event_type: str, data: dict):
    """Broadcast a JSON event envelope to all connected WebSocket clients."""
    payload = json.dumps({"type": event_type, "data": data})
    disconnected = set()
    for ws in list(active_connections):
        try:
            await ws.send_text(payload)
        except Exception as e:
            logger.warning(f"Error broadcasting to client: {e}")
            disconnected.add(ws)
    for ws in disconnected:
        active_connections.discard(ws)

async def handle_partial_transcript(text: str):
    await broadcast_event("transcript.partial", {"text": text})

async def handle_final_utterances(utterances: list[Utterance]):
    added = state_manager.add_utterances(utterances)
    await broadcast_event("transcript.final", {"utterances": [u.model_dump() for u in added]})
    
    # Check for voice speaker rename in new utterances
    from .autopilot.voice_renamer import extract_speaker_rename
    for u in added:
        rename_res = extract_speaker_rename(u.text, u.speaker_id)
        if rename_res:
            target_spk, new_name = rename_res
            logger.info(f"[Voice Renamer] Auto-renamed {target_spk} to '{new_name}' from speech: '{u.text}'")
            state_manager.rename_speaker(target_spk, new_name)

    await broadcast_event("speaker.updated", {"speakers": state_manager.state.speakers})

async def run_analysis_cycle():
    global analysis_in_flight, last_analyzed_utterance_count
    if analysis_in_flight:
        return
    if len(state_manager.state.transcript) == last_analyzed_utterance_count:
        return
    if len(state_manager.state.transcript) == 0:
        return

    analysis_in_flight = True
    try:
        current_count = len(state_manager.state.transcript)
        transcript_text = state_manager.get_transcript_for_prompt()
        logger.info(f"Running agent analysis update with {current_count} utterances...")
        new_analysis = await agent.update_analysis(transcript_text, state_manager.state.analysis)
        state_manager.update_analysis(new_analysis)
        last_analyzed_utterance_count = current_count
        await broadcast_event("analysis.updated", state_manager.state.analysis.model_dump())
    except Exception as e:
        logger.error(f"Analysis cycle failed: {e}", exc_info=True)
        await broadcast_event("error", {"message": f"Analysis update failed: {str(e)}"})
    finally:
        analysis_in_flight = False

async def periodic_analysis_loop():
    logger.info("Starting periodic analysis loop.")
    try:
        while state_manager.state.status == "recording":
            await asyncio.sleep(settings.ANALYSIS_INTERVAL_SECONDS)
            if state_manager.state.status == "recording":
                await run_analysis_cycle()
    except asyncio.CancelledError:
        pass
    logger.info("Periodic analysis loop stopped.")

async def run_simulation_scenario():
    """Simulates a live meeting with progressive speech, draft captions, and analysis."""
    logger.info("Starting simulated meeting scenario...")
    state_manager.reset()
    state_manager.set_status("recording", "Running simulated meeting.")
    await broadcast_event("status", {"state": "recording", "message": "Running simulated meeting..."})
    await broadcast_event("meeting.reset", state_manager.get_export_data())

    global analysis_timer_task
    if analysis_timer_task and not analysis_timer_task.done():
        analysis_timer_task.cancel()
    analysis_timer_task = asyncio.create_task(periodic_analysis_loop())

    for utt in MOCK_TRANSCRIPT_SAMPLE:
        if state_manager.state.status != "recording":
            break
        # Simulate typing/draft interim captions
        words = utt.text.split()
        current_draft = ""
        for i in range(0, len(words), 2):
            if state_manager.state.status != "recording":
                break
            current_draft = " ".join(words[: i + 2])
            await broadcast_event("transcript.partial", {"text": current_draft})
            await asyncio.sleep(0.4)

        # Finalize utterance
        state_manager.add_utterances([utt])
        # Set speaker display name
        if utt.speaker_id in MOCK_SPEAKERS_SAMPLE:
            state_manager.rename_speaker(utt.speaker_id, MOCK_SPEAKERS_SAMPLE[utt.speaker_id])

        await broadcast_event("transcript.final", {"utterances": [utt.model_dump()]})
        await broadcast_event("speaker.updated", {"speakers": state_manager.state.speakers})
        await broadcast_event("transcript.partial", {"text": ""})
        await asyncio.sleep(1.0)

    # If no LLM key is configured, push pre-baked mock analysis; otherwise run live agent
    has_key = bool(settings.DEEPSEEK_API_KEY or settings.OPENAI_API_KEY)
    if not has_key:
        state_manager.update_analysis(MOCK_ANALYSIS_SAMPLE)
        await broadcast_event("analysis.updated", state_manager.state.analysis.model_dump())
    else:
        await run_analysis_cycle()

    state_manager.set_status("stopped", "Simulated meeting completed.")
    await broadcast_event("status", {"state": "stopped", "message": "Simulated meeting completed."})

@app.on_event("startup")
async def startup_event():
    logger.info("Parley backend server initialized.")
    from .ollama_client import auto_ensure_default_model
    asyncio.create_task(auto_ensure_default_model())

@app.get("/health")
async def health_check():
    from .ollama_client import is_ollama_running
    return {
        "status": "ok",
        "has_deepgram_key": bool(settings.DEEPGRAM_API_KEY),
        "has_llm_key": bool(settings.DEEPSEEK_API_KEY or settings.OPENAI_API_KEY or is_ollama_running()),
        "has_exa_key": bool(settings.EXA_API_KEY),
        "ollama_running": is_ollama_running(),
        "deepgram_model": settings.DEEPGRAM_MODEL,
        "llm_model": settings.DEEPSEEK_MODEL or settings.OLLAMA_MODEL
    }

@app.get("/api/ollama/status")
async def get_ollama_status_endpoint():
    from .ollama_client import is_ollama_running, get_installed_ollama_models, pull_status
    running = is_ollama_running()
    installed = get_installed_ollama_models() if running else []
    return {
        "running": running,
        "installed_models": installed,
        "active_model": settings.OLLAMA_MODEL,
        "pull_status": pull_status
    }

@app.get("/api/ollama/models")
async def get_ollama_models_endpoint():
    from .ollama_client import is_ollama_running, get_installed_ollama_models, RECOMMENDED_MODELS
    running = is_ollama_running()
    installed = get_installed_ollama_models() if running else []
    
    # Annotate recommendations with installation state
    models_annotated = []
    for m in RECOMMENDED_MODELS:
        item = dict(m)
        item["is_installed"] = any(m["id"] in inst for inst in installed)
        item["is_active"] = (settings.OLLAMA_MODEL == m["id"])
        models_annotated.append(item)

    return {
        "running": running,
        "active_model": settings.OLLAMA_MODEL,
        "installed_models": installed,
        "recommended_models": models_annotated
    }

@app.post("/api/ollama/pull")
async def pull_ollama_model_endpoint(payload: dict):
    from .ollama_client import is_ollama_running, pull_ollama_model_sync, pull_status
    model_name = payload.get("model") or settings.OLLAMA_MODEL
    if not is_ollama_running():
        return JSONResponse(status_code=400, content={"error": "Ollama service is not running on http://localhost:11434"})

    if pull_status.get("is_pulling"):
        return {"status": "already_pulling", "pull_status": pull_status}

    asyncio.create_task(asyncio.to_thread(pull_ollama_model_sync, model_name))
    return {"status": "started", "model": model_name}

@app.get("/api/settings")
async def get_settings_endpoint():
    from .config import settings, reload_settings
    from .ollama_client import is_ollama_running
    reload_settings()
    return {
        "has_deepgram_key": bool(settings.DEEPGRAM_API_KEY),
        "has_deepseek_key": bool(settings.DEEPSEEK_API_KEY),
        "has_exa_key": bool(settings.EXA_API_KEY),
        "deepgram_key_masked": f"{settings.DEEPGRAM_API_KEY[:4]}...{settings.DEEPGRAM_API_KEY[-4:]}" if len(settings.DEEPGRAM_API_KEY) > 8 else ("configured" if settings.DEEPGRAM_API_KEY else ""),
        "deepseek_key_masked": f"{settings.DEEPSEEK_API_KEY[:4]}...{settings.DEEPSEEK_API_KEY[-4:]}" if len(settings.DEEPSEEK_API_KEY) > 8 else ("configured" if settings.DEEPSEEK_API_KEY else ""),
        "exa_key_masked": f"{settings.EXA_API_KEY[:4]}...{settings.EXA_API_KEY[-4:]}" if len(settings.EXA_API_KEY) > 8 else ("configured" if settings.EXA_API_KEY else ""),
        "stt_engine": settings.STT_ENGINE,
        "whisper_model": settings.WHISPER_MODEL,
        "llm_engine": settings.LLM_ENGINE,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "ollama_model": settings.OLLAMA_MODEL,
        "search_engine": settings.SEARCH_ENGINE,
        "ollama_running": is_ollama_running(),
    }

@app.post("/api/settings")
async def save_settings_endpoint(payload: dict):
    from .config import save_api_keys
    deepgram_key = payload.get("deepgram_api_key")
    deepseek_key = payload.get("deepseek_api_key")
    exa_key = payload.get("exa_api_key")
    stt_engine = payload.get("stt_engine")
    whisper_model = payload.get("whisper_model")
    llm_engine = payload.get("llm_engine")
    ollama_base_url = payload.get("ollama_base_url")
    ollama_model = payload.get("ollama_model")
    search_engine = payload.get("search_engine")

    new_settings = save_api_keys(
        deepgram_key=deepgram_key.strip() if deepgram_key is not None else None,
        deepseek_key=deepseek_key.strip() if deepseek_key is not None else None,
        exa_key=exa_key.strip() if exa_key is not None else None,
        stt_engine=stt_engine.strip() if stt_engine is not None else None,
        whisper_model=whisper_model.strip() if whisper_model is not None else None,
        llm_engine=llm_engine.strip() if llm_engine is not None else None,
        ollama_base_url=ollama_base_url.strip() if ollama_base_url is not None else None,
        ollama_model=ollama_model.strip() if ollama_model is not None else None,
        search_engine=search_engine.strip() if search_engine is not None else None,
    )
    return {
        "status": "saved",
        "has_deepgram_key": bool(new_settings.DEEPGRAM_API_KEY),
        "has_deepseek_key": bool(new_settings.DEEPSEEK_API_KEY),
        "has_exa_key": bool(new_settings.EXA_API_KEY),
        "stt_engine": new_settings.STT_ENGINE,
        "whisper_model": new_settings.WHISPER_MODEL,
        "llm_engine": new_settings.LLM_ENGINE,
        "ollama_model": new_settings.OLLAMA_MODEL,
        "search_engine": new_settings.SEARCH_ENGINE,
    }

@app.get("/api/state")
async def get_state():
    return state_manager.get_export_data()

@app.get("/api/export")
async def export_meeting():
    return JSONResponse(
        content=state_manager.get_export_data(),
        headers={"Content-Disposition": "attachment; filename=meeting_summary.json"}
    )

@app.websocket("/ws/meeting")
async def websocket_meeting_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    logger.info("New WebSocket connection established.")

    try:
        await websocket.send_text(
            json.dumps({"type": "state.init", "data": state_manager.get_export_data()})
        )
        await websocket.send_text(
            json.dumps({"type": "status", "data": {"state": state_manager.state.status, "message": "Connected to Parley backend."}})
        )
    except Exception as e:
        logger.error(f"Error sending init state: {e}")

    global deepgram_client, analysis_timer_task, simulation_task

    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                # Binary audio chunk from microphone
                audio_bytes = message["bytes"]
                if deepgram_client and state_manager.state.status == "recording":
                    await deepgram_client.send_audio(audio_bytes)

            elif "text" in message and message["text"]:
                try:
                    payload = json.loads(message["text"])
                    event_type = payload.get("type")
                    event_data = payload.get("data", {})
                except Exception as e:
                    logger.warning(f"Invalid JSON received on websocket: {e}")
                    continue

                if event_type == "meeting.start":
                    logger.info("Received meeting.start event")
                    if simulation_task and not simulation_task.done():
                        simulation_task.cancel()

                    sample_rate = event_data.get("sample_rate", 16000)
                    encoding = event_data.get("encoding", None)

                    state_manager.set_status("recording", "Recording in progress...")
                    await broadcast_event("status", {"state": "recording", "message": "Recording started."})

                    from .config import reload_settings
                    curr_settings = reload_settings()

                    use_whisper = (curr_settings.STT_ENGINE == "whisper") or (
                        curr_settings.STT_ENGINE == "auto" and not curr_settings.DEEPGRAM_API_KEY
                    )

                    if use_whisper:
                        from .local_whisper import LocalWhisperClient
                        try:
                            logger.info(f"Starting Local Faster-Whisper client (Model: {curr_settings.WHISPER_MODEL})")
                            deepgram_client = LocalWhisperClient(
                                on_partial=handle_partial_transcript,
                                on_final=handle_final_utterances,
                                id_generator=state_manager.next_utterance_id,
                                sample_rate=sample_rate,
                                whisper_model_name=curr_settings.WHISPER_MODEL
                            )
                            await deepgram_client.start()
                        except Exception as e:
                            logger.error(f"Failed to start Local Faster-Whisper client: {e}")
                            await broadcast_event("error", {"message": f"Local Whisper engine error: {str(e)}"})
                    elif curr_settings.DEEPGRAM_API_KEY:
                        try:
                            deepgram_client = DeepgramLiveClient(
                                api_key=curr_settings.DEEPGRAM_API_KEY,
                                on_partial=handle_partial_transcript,
                                on_final=handle_final_utterances,
                                id_generator=state_manager.next_utterance_id,
                                sample_rate=sample_rate,
                                encoding=encoding,
                                model=curr_settings.DEEPGRAM_MODEL,
                                utterance_end_ms=curr_settings.DEEPGRAM_UTTERANCE_END_MS
                            )
                            await deepgram_client.start()
                        except Exception as e:
                            logger.error(f"Failed to start Deepgram client: {e}")
                            await broadcast_event("error", {"message": f"Deepgram connection failed: {str(e)}"})

                    else:
                        logger.warning("No DEEPGRAM_API_KEY set. Audio input will not be transcribed without key. Use simulation mode or provide key in .env.")
                        await broadcast_event("error", {"message": "No DEEPGRAM_API_KEY configured in backend. Use Mock Simulation or add key."})

                    # Start periodic analysis loop
                    if analysis_timer_task and not analysis_timer_task.done():
                        analysis_timer_task.cancel()
                    analysis_timer_task = asyncio.create_task(periodic_analysis_loop())

                elif event_type == "meeting.stop":
                    logger.info("Received meeting.stop event")
                    state_manager.set_status("processing", "Finalizing transcript and analysis...")
                    await broadcast_event("status", {"state": "processing", "message": "Finalizing recording..."})

                    if deepgram_client:
                        await deepgram_client.stop()
                        deepgram_client = None

                    if analysis_timer_task and not analysis_timer_task.done():
                        analysis_timer_task.cancel()

                    if simulation_task and not simulation_task.done():
                        simulation_task.cancel()

                    # Run final agent analysis pass
                    await run_analysis_cycle()

                    state_manager.set_status("stopped", "Meeting ended.")
                    await broadcast_event("status", {"state": "stopped", "message": "Meeting stopped."})

                elif event_type == "meeting.reset":
                    logger.info("Received meeting.reset event")
                    if deepgram_client:
                        await deepgram_client.stop()
                        deepgram_client = None
                    if analysis_timer_task and not analysis_timer_task.done():
                        analysis_timer_task.cancel()
                    if simulation_task and not simulation_task.done():
                        simulation_task.cancel()

                    state_manager.reset()
                    await broadcast_event("meeting.reset", state_manager.get_export_data())
                    await broadcast_event("status", {"state": "idle", "message": "Meeting reset."})

                elif event_type == "simulation.start":
                    logger.info("Received simulation.start event")
                    if simulation_task and not simulation_task.done():
                        simulation_task.cancel()
                    simulation_task = asyncio.create_task(run_simulation_scenario())

                elif event_type == "speaker.rename":
                    speaker_id = event_data.get("speaker_id")
                    name = event_data.get("name", "").strip()
                    if speaker_id and name:
                        state_manager.rename_speaker(speaker_id, name)
                        await broadcast_event("speaker.updated", {"speakers": state_manager.state.speakers})

                elif event_type == "agent.ask":
                    req_id = event_data.get("request_id", "req-1")
                    question = event_data.get("question", "").strip()
                    if question:
                        logger.info(f"Answering question: {question}")
                        transcript_text = state_manager.get_transcript_for_prompt()
                        answer = await agent.answer_question(question, transcript_text, state_manager.state.analysis)
                        state_manager.add_message(req_id, question, answer)
                        await broadcast_event("agent.answer", {"request_id": req_id, "text": answer})

                elif event_type == "agent.ask_multimodal":
                    req_id = event_data.get("request_id", "req-1")
                    question = event_data.get("question", "").strip()
                    image_base64 = event_data.get("image", None)
                    logger.info(f"Multimodal question received: '{question}' (has_image: {bool(image_base64)})")
                    transcript_text = state_manager.get_transcript_for_prompt()
                    res = await agent.answer_multimodal(question, image_base64, transcript_text, state_manager.state.analysis)
                    state_manager.add_message(req_id, question or "(Image Upload)", res["text"])
                    await broadcast_event("agent.answer", {
                        "request_id": req_id,
                        "text": res["text"],
                        "action_plan": res.get("action_plan")
                    })

                elif event_type == "autopilot.execute":
                    plan = event_data.get("plan", {})
                    image_base64 = event_data.get("image", None)
                    action_type = plan.get("action_type")
                    platform = plan.get("platform", "web")
                    params = plan.get("params", {})
                    
                    logger.info(f"Executing autopilot task: {action_type} on {platform}")
                    await broadcast_event("autopilot.status", {"status": "running", "step": "init", "message": f"Starting Autopilot on {platform}..."})
                    
                    async def step_reporter(step: str, msg: str):
                        await broadcast_event("autopilot.step", {"step": step, "message": msg})
                        
                    image_paths = []
                    if image_base64:
                        from .autopilot.utils import save_base64_image
                        img_path = save_base64_image(image_base64)
                        image_paths.append(img_path)
                        
                    try:
                        if action_type == "social_post":
                            from .autopilot.browser_agent import BrowserAutopilot
                            bot = BrowserAutopilot(step_callback=step_reporter)
                            result = await bot.post_to_social(platform, params.get("text", ""), image_paths=image_paths, headless=False)
                            await broadcast_event("autopilot.completed", {"success": result.get("success", True), "result": result})
                        elif action_type == "chat_message":
                            from .autopilot.browser_agent import BrowserAutopilot
                            bot = BrowserAutopilot(step_callback=step_reporter)
                            result = await bot.send_whatsapp_message(params.get("contact", ""), params.get("message", ""), headless=False)
                            await broadcast_event("autopilot.completed", {"success": result.get("success", True), "result": result})
                        else:
                            from .autopilot.os_agent import OSAutopilot
                            os_bot = OSAutopilot(step_callback=step_reporter)
                            await os_bot.open_url_in_browser(f"https://www.{platform.lower()}.com")
                            await broadcast_event("autopilot.completed", {"success": True, "message": f"Opened {platform}"})
                    except Exception as err:
                        logger.error(f"Autopilot execution error: {err}", exc_info=True)
                        await broadcast_event("autopilot.failed", {"error": str(err)})

                elif event_type == "autopilot.cancel":
                    logger.info("Received autopilot.cancel event")
                    await broadcast_event("autopilot.status", {"status": "cancelled", "message": "Autopilot operation cancelled."})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        active_connections.discard(websocket)

# Mount frontend static distribution if present (for single-container Docker, PyInstaller, and standalone serving)
possible_dist_dirs = [
    # PyInstaller bundled static path
    os.path.join(getattr(sys, "_MEIPASS", ""), "static"),
    # Next to frozen binary or executable directory (e.g. resources/static)
    os.path.join(os.path.dirname(sys.executable), "static"),
    os.path.join(os.path.dirname(sys.executable), "..", "static"),
    os.path.join(os.path.dirname(sys.executable), "..", "frontend", "dist"),
    # Local dev paths relative to main.py
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"),
    os.path.join(os.path.dirname(__file__), "..", "static"),
    os.path.join(os.getcwd(), "frontend", "dist"),
    os.path.join(os.getcwd(), "static"),
    # Docker standard paths
    "/app/frontend/dist",
    "/app/static"
]

frontend_dist_path = None
for p in possible_dist_dirs:
    if p and os.path.isdir(p) and os.path.exists(os.path.join(p, "index.html")):
        frontend_dist_path = os.path.abspath(p)
        break

if frontend_dist_path:
    logger.info(f"Serving static frontend UI from: {frontend_dist_path}")
    assets_dir = os.path.join(frontend_dist_path, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_target = os.path.join(frontend_dist_path, full_path)
        if full_path and os.path.isfile(file_target):
            return FileResponse(file_target)
        return FileResponse(os.path.join(frontend_dist_path, "index.html"))
else:
    logger.warning("No frontend dist directory found. Root URL '/' will not serve SPA.")
