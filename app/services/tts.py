import logging
import queue
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from app.config.settings import settings

logger = logging.getLogger("bulloch-transport.tts")


class TTSInitializationError(RuntimeError):
    """Raised when the text-to-speech engine cannot be initialized."""


@dataclass
class _SpeechRequest:
    text: str
    block: bool
    complete_event: Optional[threading.Event] = None
    stop_requested: bool = False


class TTSManager:
    """Thread-safe text-to-speech manager for onboard voice prompts."""

    def __init__(
        self,
        voice_name: Optional[str] = None,
        rate: int = 150,
        volume: float = 1.0,
        engine_choice: str = "auto",
    ) -> None:
        self._voice_name = voice_name
        self._rate = max(50, min(rate, 300))
        self._volume = max(0.0, min(volume, 1.0))
        self._engine_choice = engine_choice.lower().strip()
        self._request_queue: "queue.Queue[_SpeechRequest]" = queue.Queue()
        self._stop_event = threading.Event()
        self._engine: Optional[Any] = None
        self._use_pygame_playback = False
        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="TTSManagerThread")
        self._initialization_error: Optional[Exception] = None
        self._thread.start()

    def _worker_loop(self) -> None:
        try:
            self._initialize_engine()
        except Exception as exc:
            self._initialization_error = exc
            logger.exception("Failed to initialize speech engine.")
            return

        while not self._stop_event.is_set():
            try:
                request = self._request_queue.get(timeout=0.25)
            except queue.Empty:
                continue

            if request.stop_requested:
                self._stop_playback()
                if request.complete_event:
                    request.complete_event.set()
                continue

            if not request.text.strip():
                if request.complete_event:
                    request.complete_event.set()
                continue

            self._speak(request.text, request.block)
            if request.complete_event:
                request.complete_event.set()

        self._shutdown_engine()

    def _initialize_engine(self) -> None:
        try:
            import pyttsx3
        except ImportError as exc:
            raise TTSInitializationError("pyttsx3 is required for TTS engine initialization") from exc

        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", self._rate)
        self._engine.setProperty("volume", self._volume)

        if self._voice_name:
            try:
                self._engine.setProperty("voice", self._voice_name)
            except Exception:
                logger.warning("Voice '%s' not available; using default voice.", self._voice_name)

        if self._engine_choice == "pygame":
            try:
                import pygame  # type: ignore

                pygame.mixer.init(frequency=22050)
                self._use_pygame_playback = True
            except Exception as exc:
                logger.warning("pygame playback unavailable: %s; falling back to pyttsx3.", exc)
                self._use_pygame_playback = False

        logger.debug(
            "Initialized TTSManager(engine_choice=%s, voice=%s, rate=%s, volume=%s, pygame=%s)",
            self._engine_choice,
            self._voice_name,
            self._rate,
            self._volume,
            self._use_pygame_playback,
        )

    def _speak(self, text: str, block: bool) -> None:
        if self._engine is None:
            raise TTSInitializationError("Speech engine is not initialized")

        if self._use_pygame_playback:
            self._speak_with_pygame(text)
            if block:
                self._wait_for_pygame()
            return

        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as exc:
            logger.exception("Error while speaking text: %s", exc)

    def _speak_with_pygame(self, text: str) -> None:
        if self._engine is None:
            raise TTSInitializationError("Speech engine is not initialized")

        temp_path = Path(tempfile.gettempdir()) / f"bulloch_tts_{uuid.uuid4().hex}.wav"
        try:
            self._engine.save_to_file(text, str(temp_path))
            self._engine.runAndWait()

            import pygame  # type: ignore

            sound = pygame.mixer.Sound(str(temp_path))
            sound.play()
            while pygame.mixer.get_busy():
                time.sleep(0.1)
        except Exception as exc:
            logger.exception("Error during pygame TTS playback: %s", exc)
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                logger.debug("Failed to delete temporary TTS file %s", temp_path)

    def _wait_for_pygame(self) -> None:
        try:
            import pygame  # type: ignore
            while pygame.mixer.get_busy():
                time.sleep(0.05)
        except Exception:
            logger.debug("Pygame mixer not active while waiting for playback.")

    def _stop_playback(self) -> None:
        if self._engine is None:
            return

        try:
            self._engine.stop()
        except Exception as exc:
            logger.debug("TTS stop request failed: %s", exc)

        if self._use_pygame_playback:
            try:
                import pygame  # type: ignore
                pygame.mixer.stop()
            except Exception:
                logger.debug("Failed to stop pygame playback.")

    def _shutdown_engine(self) -> None:
        if self._engine is None:
            return

        try:
            self._engine.stop()
        except Exception:
            pass

        if self._use_pygame_playback:
            try:
                import pygame  # type: ignore
                pygame.mixer.quit()
            except Exception:
                pass

        self._engine = None

    def speak(self, text: str, block: bool = False, timeout: float = 30.0) -> None:
        """Queue text for speech playback.

        Args:
            text: The string to speak.
            block: If True, wait until speech playback completes.
            timeout: Maximum seconds to wait when block=True.
        """
        if self._initialization_error:
            raise self._initialization_error

        request = _SpeechRequest(text=text, block=block)
        if block:
            request.complete_event = threading.Event()

        self._request_queue.put(request)

        if block and request.complete_event:
            if not request.complete_event.wait(timeout=timeout):
                logger.warning("TTS speak timed out after %s seconds", timeout)

    def queue_message(self, text: str) -> None:
        """Add speech text to the internal queue without blocking."""
        self.speak(text, block=False)

    def stop(self) -> None:
        """Stop current speech playback immediately."""
        self._request_queue.put(_SpeechRequest(text="", block=False, stop_requested=True))

    def shutdown(self, timeout: float = 5.0) -> None:
        """Shutdown the TTS background thread and release audio resources."""
        self._stop_event.set()
        self._request_queue.put(_SpeechRequest(text="", block=False))
        self._thread.join(timeout=timeout)
        if self._thread.is_alive():
            logger.warning("TTSManager thread did not terminate within %s seconds", timeout)


def create_default_tts_manager() -> TTSManager:
    """Create a default TTS manager instance using application settings."""
    engine_choice = "pygame" if getattr(settings, "ENV", "development") == "production" else "auto"
    return TTSManager(engine_choice=engine_choice)


# --- Global Singleton and Convenience Helper ---

_global_tts_manager: Optional[TTSManager] = None


def get_global_tts_manager() -> TTSManager:
    """Lazy initializer for the global TTSManager instance."""
    global _global_tts_manager
    if _global_tts_manager is None:
        try:
            _global_tts_manager = create_default_tts_manager()
        except Exception as exc:
            logger.warning("Falling back to basic TTSManager due to initialization error: %s", exc)
            _global_tts_manager = TTSManager()
    return _global_tts_manager


def announce_route_status(message: str) -> None:
    """Speak route status updates over the vehicle audio system."""
    try:
        manager = get_global_tts_manager()
        manager.speak(message, block=False)
    except Exception as exc:
        logger.error("Failed to announce route status: %s", exc)