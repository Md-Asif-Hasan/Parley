import json
import asyncio
import logging
from typing import Callable, Optional, List, Dict, Any
import websockets
from .models import Utterance
from .config import settings

logger = logging.getLogger(__name__)

class DeepgramLiveClient:
    def __init__(
        self,
        api_key: str,
        on_partial: Callable[[str], asyncio.Future | None],
        on_final: Callable[[List[Utterance]], asyncio.Future | None],
        id_generator: Callable[[], str],
        sample_rate: int = 16000,
        encoding: Optional[str] = None,
        model: Optional[str] = None,
        utterance_end_ms: Optional[int] = None
    ):
        self.api_key = api_key
        self.on_partial = on_partial
        self.on_final = on_final
        self.id_generator = id_generator
        self.sample_rate = sample_rate
        self.encoding = encoding
        self.model = model or settings.DEEPGRAM_MODEL or "nova-3"
        self.utterance_end_ms = utterance_end_ms or settings.DEEPGRAM_UTTERANCE_END_MS or 5000
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self):
        if not self.api_key:
            raise ValueError("Deepgram API Key is required for live transcription.")

        query_params = [
            f"model={self.model}",
            "diarize=true",
            "punctuate=true",
            "interim_results=true",
            "smart_format=true",
            f"utterance_end_ms={self.utterance_end_ms}"
        ]
        if self.encoding:
            query_params.append(f"encoding={self.encoding}")
            query_params.append(f"sample_rate={self.sample_rate}")

        url = f"wss://api.deepgram.com/v1/listen?{'&'.join(query_params)}"
        headers = {
            "Authorization": f"Token {self.api_key}"
        }

        logger.info(f"Connecting to Deepgram: {url}")
        try:
            self.ws = await websockets.connect(url, additional_headers=headers)
        except TypeError:
            self.ws = await websockets.connect(url, extra_headers=headers)
        self._is_running = True
        self._receive_task = asyncio.create_task(self._receiver_loop())

    async def send_audio(self, chunk: bytes):
        if self.ws and self._is_running:
            try:
                await self.ws.send(chunk)
            except Exception as e:
                logger.error(f"Error sending audio chunk to Deepgram: {e}")

    async def _receiver_loop(self):
        try:
            async for message in self.ws:
                if isinstance(message, str):
                    await self._handle_message(json.loads(message))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Deepgram receiver error: {e}")
        finally:
            self._is_running = False

    async def _handle_message(self, data: Dict[str, Any]):
        msg_type = data.get("type")
        if msg_type == "Results":
            channel = data.get("channel", {})
            alternatives = channel.get("alternatives", [])
            if not alternatives:
                return

            alt = alternatives[0]
            transcript = alt.get("transcript", "").strip()
            is_final = data.get("is_final", False)

            if not transcript:
                return

            if not is_final:
                # Interim partial result
                res = self.on_partial(transcript)
                if asyncio.iscoroutine(res):
                    await res
            else:
                # Finalized result with speaker diarization
                words = alt.get("words", [])
                utterances = self._group_words_by_speaker(words, transcript, data.get("start", 0.0), data.get("duration", 0.0))
                if utterances:
                    res = self.on_final(utterances)
                    if asyncio.iscoroutine(res):
                        await res
        elif msg_type == "UtteranceEnd":
            logger.debug(f"Deepgram UtteranceEnd event triggered after {self.utterance_end_ms}ms pause.")

    def _group_words_by_speaker(
        self,
        words: List[Dict[str, Any]],
        fallback_transcript: str,
        start_offset: float,
        duration: float
    ) -> List[Utterance]:
        if not words:
            return [
                Utterance(
                    id=self.id_generator(),
                    speaker_id=None,
                    start=round(start_offset, 2),
                    end=round(start_offset + duration, 2),
                    text=fallback_transcript
                )
            ]

        utterances: List[Utterance] = []
        current_speaker: Optional[str] = None
        current_words: List[str] = []
        seg_start = words[0].get("start", start_offset)
        seg_end = words[0].get("end", start_offset)

        for w in words:
            speaker_idx = w.get("speaker")
            speaker_id = f"speaker_{speaker_idx}" if speaker_idx is not None else None
            word_text = w.get("punctuated_word") or w.get("word") or ""
            w_start = w.get("start", seg_start)
            w_end = w.get("end", seg_end)

            if current_speaker is None:
                current_speaker = speaker_id
                current_words.append(word_text)
                seg_start = w_start
                seg_end = w_end
            elif speaker_id == current_speaker:
                current_words.append(word_text)
                seg_end = max(seg_end, w_end)
            else:
                # Speaker switch - flush current group
                text = " ".join(current_words).strip()
                if text:
                    utterances.append(
                        Utterance(
                            id=self.id_generator(),
                            speaker_id=current_speaker,
                            start=round(seg_start, 2),
                            end=round(seg_end, 2),
                            text=text
                        )
                    )
                current_speaker = speaker_id
                current_words = [word_text]
                seg_start = w_start
                seg_end = w_end

        # Flush trailing words
        if current_words:
            text = " ".join(current_words).strip()
            if text:
                utterances.append(
                    Utterance(
                        id=self.id_generator(),
                        speaker_id=current_speaker,
                        start=round(seg_start, 2),
                        end=round(seg_end, 2),
                        text=text
                    )
                )

        return utterances

    async def stop(self):
        self._is_running = False
        if self.ws:
            try:
                await self.ws.send(json.dumps({"type": "CloseStream"}))
                await asyncio.sleep(0.5)
                await self.ws.close()
            except Exception as e:
                logger.warning(f"Error during Deepgram client shutdown: {e}")
        if self._receive_task:
            self._receive_task.cancel()
