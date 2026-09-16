import io
import wave
import json
import asyncio
import logging
import tempfile
import os
from typing import Callable, Optional, List, Dict, Any
from .models import Utterance
from .config import settings

logger = logging.getLogger(__name__)

# Global cached WhisperModel instance to prevent reloading weights on every audio stream
_model_cache: Dict[str, Any] = {}

def get_whisper_model(model_name: str = "base.en"):
    """Loads and caches faster-whisper model in memory (CPU int8 or CUDA if available)."""
    if model_name in _model_cache:
        return _model_cache[model_name]

    try:
        from faster_whisper import WhisperModel
        logger.info(f"Initializing Local Faster-Whisper model: {model_name}")
        # Default to CPU with int8 quantization for high compatibility across PCs
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        _model_cache[model_name] = model
        return model
    except Exception as e:
        logger.error(f"Error initializing faster-whisper model '{model_name}': {e}")
        return None

class LocalWhisperClient:
    """
    Local zero-credentials Speech-to-Text client using Faster-Whisper.
    Matches the interface of DeepgramLiveClient (start, send_audio, stop).
    """
    def __init__(
        self,
        on_partial: Callable[[str], asyncio.Future | None],
        on_final: Callable[[List[Utterance]], asyncio.Future | None],
        id_generator: Callable[[], str],
        sample_rate: int = 16000,
        whisper_model_name: Optional[str] = None
    ):
        self.on_partial = on_partial
        self.on_final = on_final
        self.id_generator = id_generator
        self.sample_rate = sample_rate
        self.model_name = whisper_model_name or settings.WHISPER_MODEL or "base.en"
        self._is_running = False
        self._audio_buffer = bytearray()
        self._process_task: Optional[asyncio.Task] = None
        self._last_processed_pos = 0

    async def start(self):
        """Starts local transcription engine."""
        self._is_running = True
        self._audio_buffer = bytearray()
        # Pre-warm model cache in background
        asyncio.to_thread(get_whisper_model, self.model_name)
        self._process_task = asyncio.create_task(self._processing_loop())
        logger.info(f"Local Faster-Whisper STT engine active (Model: {self.model_name}).")

    async def send_audio(self, chunk: bytes):
        """Accumulates incoming PCM/WebM audio bytes from browser recorder."""
        if self._is_running and chunk:
            self._audio_buffer.extend(chunk)

    async def _processing_loop(self):
        """Processes audio buffer in sliding window chunks (every 3 seconds)."""
        while self._is_running:
            await asyncio.sleep(3.0)
            if len(self._audio_buffer) < 16000 * 2:  # Need at least ~1 second of 16kHz audio
                continue

            current_bytes = bytes(self._audio_buffer)
            try:
                utterances = await asyncio.to_thread(self._transcribe_chunk, current_bytes)
                if utterances:
                    # Emit final utterances to meeting state
                    res = self.on_final(utterances)
                    if asyncio.iscoroutine(res):
                        await res
                    # Reset buffer after successful transcription
                    self._audio_buffer.clear()
            except Exception as e:
                logger.error(f"Local Whisper transcription error: {e}")

    def _transcribe_chunk(self, audio_data: bytes) -> List[Utterance]:
        model = get_whisper_model(self.model_name)
        if not model:
            return []

        # Save raw buffer to temporary WAV file for faster-whisper reading
        temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_wav.name
        try:
            with wave.open(temp_wav, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data)
            temp_wav.close()

            segments, _ = model.transcribe(
                temp_path,
                beam_size=1,
                language="en",
                condition_on_previous_text=False
            )

            results: List[Utterance] = []
            for seg in segments:
                text = seg.text.strip()
                if not text:
                    continue
                results.append(
                    Utterance(
                        id=self.id_generator(),
                        speaker_id="speaker_0",  # Default local speaker attribution
                        start=round(seg.start, 2),
                        end=round(seg.end, 2),
                        text=text
                    )
                )
            return results
        except Exception as err:
            logger.error(f"Error running faster-whisper transcribe: {err}")
            return []
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    async def stop(self):
        """Stops the local transcription processing loop."""
        self._is_running = False
        if self._process_task:
            self._process_task.cancel()
        logger.info("Local Faster-Whisper engine stopped.")
