"""
utils/realtime_bridge.py
OpenAI Realtime API WebSocket Bridge for Judicial Speech-to-Text.

Maintains an upstream WebSocket to wss://api.openai.com/v1/realtime,
streams 16-bit linear PCM audio from the client, buffers incoming
transcription tokens, applies spoken steno rules & legal normalization,
and emits real-time updates back to the UI via Flask-SocketIO.
"""

import asyncio
import base64
import json
import os
import threading
from typing import Optional, Dict, Any

import websockets
from dotenv import load_dotenv

# Ensure environment variables are loaded
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"), override=True)

from utils.transcription import process_voice_commands
from utils.legal_vocabulary import normalize_legal_terms

# Preferred realtime models in priority order
REALTIME_MODELS = ["gpt-realtime-mini", "gpt-realtime"]


class RealtimeTranscriptionSession:
    """
    Manages an active real-time transcription session between a single
    client socket and the OpenAI Realtime WebSocket API.
    """

    def __init__(self, sid: str, socketio, language_code: str = "en"):
        self.sid = sid
        self.socketio = socketio
        self.language_code = language_code
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model_name = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-mini").strip()

        self.audio_queue: Optional[asyncio.Queue] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.is_running = False
        self.ws = None

        # Buffers for multi-word steno translation
        self.current_utterance_text = ""
        self.sender_task = None
        self.receiver_task = None

    def start(self):
        """Starts the background event loop and WebSocket bridge thread."""
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()

    def _run_event_loop(self):
        """Event loop thread runner."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.audio_queue = asyncio.Queue()

        try:
            self.loop.run_until_complete(self._connect_and_stream())
        except Exception as e:
            print(f"[RealtimeBridge-{self.sid}] Event loop exception: {e}")
        finally:
            self.loop.close()

    def push_audio_chunk(self, chunk: bytes):
        """
        Thread-safe method called from Flask-SocketIO handler to enqueue
        raw PCM16 audio bytes from the client microphone.
        """
        if not self.is_running or not self.loop or not self.audio_queue:
            return
        try:
            self.loop.call_soon_threadsafe(self.audio_queue.put_nowait, chunk)
        except Exception as e:
            print(f"[RealtimeBridge-{self.sid}] Failed to enqueue audio chunk: {e}")

    async def _connect_and_stream(self):
        """Connects to OpenAI Realtime API and handles bidirectional streaming."""
        if not self.api_key:
            err = "OPENAI_API_KEY not configured in .env file."
            print(f"[RealtimeBridge-{self.sid}] {err}")
            self.socketio.emit("realtime_error", {"error": err}, room=self.sid)
            return

        url = f"wss://api.openai.com/v1/realtime?model={self.model_name}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            async with websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=20,
            ) as ws:
                self.ws = ws
                print(f"[RealtimeBridge-{self.sid}] Connected to OpenAI Realtime API ({self.model_name}).")

                # Configure session for judicial audio transcription
                session_update_event = {
                    "type": "session.update",
                    "session": {
                        "type": "realtime",
                        "audio": {
                            "input": {
                                "format": {
                                    "type": "audio/pcm",
                                    "rate": 24000,
                                },
                                "transcription": {
                                    "model": "whisper-1",
                                },
                                "turn_detection": {
                                    "type": "server_vad",
                                    "threshold": 0.5,
                                    "prefix_padding_ms": 300,
                                    "silence_duration_ms": 400,
                                    "create_response": False,
                                },
                            },
                        },
                    },
                }

                await ws.send(json.dumps(session_update_event))

                # Launch concurrent send and receive tasks
                self.sender_task = asyncio.create_task(self._sender_loop(ws))
                self.receiver_task = asyncio.create_task(self._receiver_loop(ws))

                # Wait until one finishes or cancels
                done, pending = await asyncio.wait(
                    [self.sender_task, self.receiver_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()

        except websockets.exceptions.InvalidStatusCode as e:
            err_msg = f"OpenAI Realtime connection failed: HTTP {e.status_code}. Please verify your .env API key."
            print(f"[RealtimeBridge-{self.sid}] {err_msg}")
            self.socketio.emit("realtime_error", {"error": err_msg}, room=self.sid)
        except Exception as e:
            if self.is_running:
                print(f"[RealtimeBridge-{self.sid}] WebSocket error: {e}")
                self.socketio.emit("realtime_error", {"error": str(e)}, room=self.sid)
        finally:
            self.is_running = False
            self.ws = None

    async def _sender_loop(self, ws):
        """Reads audio chunks from the queue and sends them to OpenAI."""
        while self.is_running:
            try:
                chunk = await self.audio_queue.get()
                if not chunk:
                    continue

                b64_audio = base64.b64encode(chunk).decode("ascii")
                event = {
                    "type": "input_audio_buffer.append",
                    "audio": b64_audio,
                }
                await ws.send(json.dumps(event))
                self.audio_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[RealtimeBridge-{self.sid}] Sender error: {e}")
                break

    async def _receiver_loop(self, ws):
        """Listens for incoming events from OpenAI and applies steno transformations."""
        async for raw_message in ws:
            if not self.is_running:
                break
            try:
                event = json.loads(raw_message)
                event_type = event.get("type", "")

                if event_type == "session.updated":
                    self.socketio.emit(
                        "realtime_status",
                        {"status": "ready", "model": self.model_name},
                        room=self.sid,
                    )

                elif event_type == "input_audio_buffer.speech_started":
                    self.socketio.emit(
                        "realtime_status",
                        {"status": "speaking"},
                        room=self.sid,
                    )

                elif event_type == "input_audio_buffer.speech_stopped":
                    self.socketio.emit(
                        "realtime_status",
                        {"status": "transcribing"},
                        room=self.sid,
                    )

                elif event_type == "conversation.item.input_audio_transcription.delta":
                    delta = event.get("delta", "")
                    if delta:
                        self.current_utterance_text += delta
                        # Real-time multi-word steno command replacement
                        interim_steno = process_voice_commands(
                            self.current_utterance_text, enabled=True
                        )
                        self.socketio.emit(
                            "transcript_update",
                            {
                                "delta": delta,
                                "buffer": interim_steno,
                                "is_final": False,
                            },
                            room=self.sid,
                        )

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = (
                        event.get("transcript", "") or self.current_utterance_text
                    ).strip()

                    if transcript:
                        # 1. Spoken stenographer commands (into bracket -> (, comma -> ,, etc.)
                        with_steno = process_voice_commands(transcript, enabled=True)
                        # 2. Judicial formatting (PW-1, Ex.P1, Section 302 IPC, RI, S/o.)
                        final_normalized = normalize_legal_terms(
                            with_steno, enabled=True, language_code=self.language_code
                        )

                        self.socketio.emit(
                            "transcript_final",
                            {
                                "text": final_normalized,
                                "raw_transcript": transcript,
                                "is_final": True,
                            },
                            room=self.sid,
                        )

                    self.current_utterance_text = ""
                    self.socketio.emit(
                        "realtime_status",
                        {"status": "ready"},
                        room=self.sid,
                    )

                elif event_type == "error":
                    err_info = event.get("error", {})
                    err_msg = err_info.get("message", "Realtime API error")
                    print(f"[RealtimeBridge-{self.sid}] OpenAI Realtime Error: {err_msg}")
                    self.socketio.emit(
                        "realtime_error",
                        {"error": err_msg},
                        room=self.sid,
                    )

            except Exception as e:
                print(f"[RealtimeBridge-{self.sid}] Error parsing message: {e}")

    def stop(self):
        """Gracefully stops the session and terminates connections."""
        self.is_running = False
        if self.loop and self.loop.is_running():
            if self.sender_task:
                self.loop.call_soon_threadsafe(self.sender_task.cancel)
            if self.receiver_task:
                self.loop.call_soon_threadsafe(self.receiver_task.cancel)
            if self.ws:
                self.loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(self.ws.close())
                )
        print(f"[RealtimeBridge-{self.sid}] Session closed.")


# Active session registry
_ACTIVE_SESSIONS: Dict[str, RealtimeTranscriptionSession] = {}


def get_or_create_session(sid: str, socketio, language_code: str = "en") -> RealtimeTranscriptionSession:
    """Returns the active session for a client SID or creates a new one."""
    if sid not in _ACTIVE_SESSIONS:
        session = RealtimeTranscriptionSession(sid=sid, socketio=socketio, language_code=language_code)
        _ACTIVE_SESSIONS[sid] = session
        session.start()
    return _ACTIVE_SESSIONS[sid]


def close_session(sid: str):
    """Closes and cleans up a client's active session."""
    if sid in _ACTIVE_SESSIONS:
        session = _ACTIVE_SESSIONS.pop(sid)
        session.stop()
