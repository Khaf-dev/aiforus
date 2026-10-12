"""Command-line entry point: ``python -m aiforus`` (or ``python app.py``)."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import platform
import sys
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from . import __version__
from .assistant import Assistant
from .config import PROJECT_ROOT, SUPPORTED_LANGUAGES, Settings, load_settings
from .hal import ComponentUnavailable
from .hal.location import IpLocationProvider
from .i18n import Translator
from .speech import SpeechQueue
from .storage import Database, PreferenceStore, SqlFaceStore

logger = logging.getLogger("aiforus")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aiforus", description="AIForUs voice-first vision assistant (research prototype)."
    )
    parser.add_argument("--config", help="path to config.yaml (default: project root)")
    parser.add_argument("--lang", choices=SUPPORTED_LANGUAGES, help="override the language")
    parser.add_argument("--text", action="store_true", help="type commands instead of speaking them")
    parser.add_argument("--mute", action="store_true", help="print replies instead of speaking them")
    parser.add_argument("--check", action="store_true", help="report which components work, then exit")
    parser.add_argument("--debug", action="store_true", help="verbose logging")
    parser.add_argument("--version", action="version", version=f"aiforus {__version__}")
    return parser


@dataclass
class Components:
    tts: Any = None
    listener: Any = None
    camera: Any = None
    detector: Any = None
    reader: Any = None
    face_encoder: Any = None
    navigator: Any = None
    location: Any = None
    answerer: Any = None
    status: dict[str, str] = field(default_factory=dict)


def _try(components: Components, name: str, factory: Any) -> Any:
    try:
        value = factory()
    except ComponentUnavailable as exc:
        components.status[name] = f"unavailable - {exc}"
        logger.warning("%s unavailable: %s", name, exc)
        return None
    except Exception as exc:  # unexpected failure in an optional component
        components.status[name] = f"failed - {exc}"
        logger.exception("%s failed to initialise", name)
        return None
    components.status[name] = "ok"
    return value


def build_components(settings: Settings, args: argparse.Namespace, language: str) -> Components:
    from .hal.camera import OpenCVCamera
    from .hal.stt import GoogleSpeechInput, KeyboardInput
    from .hal.tts import PrintTTS, Pyttsx3TTS
    from .services.faces import DlibFaceEncoder
    from .services.llm import OpenAIAnswerer
    from .services.navigation import Navigator
    from .services.vision import EasyOcrReader, YoloDetector

    c = Components()
    s = settings

    voice = None
    if not args.mute:
        voice = _try(
            c,
            "voice output",
            lambda: Pyttsx3TTS(
                rate=s.speech.rate,
                volume=s.speech.volume,
                voice_hints=s.speech.voice_hints,
                language=language,
            ),
        )
    c.tts = PrintTTS(voice) if (args.text or args.mute) else voice

    if args.text:
        c.listener = KeyboardInput("Kamu: " if language == "id" else "You: ")
        c.status["voice input"] = "keyboard (--text)"
    else:
        c.listener = _try(
            c,
            "voice input",
            lambda: GoogleSpeechInput(
                locales=s.speech.recognition_locale,
                language=language,
                timeout_s=s.speech.listen_timeout_s,
                phrase_limit_s=s.speech.phrase_time_limit_s,
            ),
        )

    c.camera = _try(c, "camera", lambda: OpenCVCamera(s.camera))
    model = s.vision.detector_model
    if (PROJECT_ROOT / model).exists():  # don't re-download when run from another folder
        model = str(PROJECT_ROOT / model)
    c.detector = _try(c, "object detection", lambda: YoloDetector(model, s.vision.detection_confidence))
    c.reader = _try(c, "text reading", lambda: EasyOcrReader(s.vision.ocr_languages, s.vision.ocr_confidence))
    if s.face.enabled:
        c.face_encoder = _try(c, "face recognition", lambda: DlibFaceEncoder(s.face.detection_model))
    else:
        c.status["face recognition"] = "disabled in config"
    if s.navigation.enabled:
        c.navigator = _try(c, "navigation", lambda: Navigator(s.navigation))
        c.location = _try(
            c,
            "location",
            lambda: IpLocationProvider(
                s.navigation.ip_location_url, s.navigation.http_timeout_s, s.navigation.user_agent
            ),
        )
    else:
        c.status["navigation"] = "disabled in config"
    if s.llm.enabled and s.openai_api_key is not None:
        key = s.openai_api_key.get_secret_value()
        c.answerer = _try(
            c,
            "general questions (LLM)",
            lambda: OpenAIAnswerer(
                api_key=key, model=s.llm.model, timeout_s=s.llm.timeout_s, max_tokens=s.llm.max_tokens
            ),
        )
    else:
        c.status["general questions (LLM)"] = (
            "off - set OPENAI_API_KEY to enable" if s.llm.enabled else "disabled"
        )
    return c


def _close_quietly(*resources: Any) -> None:
    for resource in resources:
        close = getattr(resource, "close", None)
        if close is not None:
            with contextlib.suppress(Exception):
                close()


def run_check(settings: Settings, args: argparse.Namespace) -> int:
    language = args.lang or settings.app.language
    print(f"AIForUs {__version__} - Python {platform.python_version()} on {platform.system()}")
    print("config: OK")
    print(f"language: {language}")
    components = build_components(settings, args, language)
    for name, status in components.status.items():
        print(f"  {name:<26} {status}")

    voice = getattr(components.tts, "_inner", components.tts)
    if voice is not None and hasattr(voice, "voice_found"):
        for lang in SUPPORTED_LANGUAGES:
            voice.set_language(lang)
            found = voice.voice_found.get(lang)
            print(
                f"  TTS voice for {lang!r:<13} {'found' if found else 'NOT FOUND - install one (see README)'}"
            )
        voice.set_language(language)
    if components.camera is not None:
        frame = components.camera.capture()
        print(f"  {'camera frame':<26} {'ok ' + str(frame.shape) if frame is not None else 'no frame'}")
    _close_quietly(components.camera, components.tts, components.listener)
    return 0


async def run_assistant(settings: Settings, args: argparse.Namespace) -> int:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db = Database(settings.database_path)
    prefs = PreferenceStore(db)
    saved = prefs.get("language")
    language = args.lang or (saved if saved in SUPPORTED_LANGUAGES else None) or settings.app.language

    components = build_components(settings, args, language)
    if components.tts is None:
        print("Voice output is unavailable. Install it (pip install -e .[voice]) or run with --mute.")
        db.close()
        return 2
    if components.listener is None:
        print("Voice input is unavailable. Install it (pip install -e .[voice]) or run with --text.")
        _close_quietly(components.tts, components.camera)
        db.close()
        return 2

    from .services.faces import FaceService
    from .services.vision import VisionService

    vision = VisionService(
        components.camera, components.detector, components.reader, settings.camera, settings.vision
    )
    faces = None
    if components.face_encoder is not None:
        faces = FaceService(
            components.face_encoder,
            SqlFaceStore(db),
            match_threshold=settings.face.match_threshold,
            max_samples_per_person=settings.face.max_samples_per_person,
        )

    speech = SpeechQueue(components.tts)
    speech.start()
    listener = components.listener

    def on_language_change(lang: str) -> None:
        components.tts.set_language(lang)
        listener.set_language(lang)

    assistant = Assistant(
        settings=settings,
        speech=speech,
        translator=Translator(language),
        vision=vision,
        faces=faces,
        navigator=components.navigator,
        location=components.location,
        answerer=components.answerer,
        prefs=prefs,
        on_language_change=on_language_change,
    )
    warm_up = asyncio.create_task(vision.warm_up(), name="vision-warm-up")
    try:
        await assistant.run(listener)
    finally:
        warm_up.cancel()
        await speech.close()
        _close_quietly(listener, components.camera, components.tts)
        db.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        settings = load_settings(args.config)
    except (ValidationError, ValueError, FileNotFoundError) as exc:
        print(f"Invalid configuration:\n{exc}", file=sys.stderr)
        return 1
    if not args.debug:
        logging.getLogger().setLevel(settings.app.log_level)

    if args.check:
        # The report already lists every problem; skip the duplicate warnings.
        logging.getLogger().setLevel(logging.ERROR)
        return run_check(settings, args)
    try:
        return asyncio.run(run_assistant(settings, args))
    except KeyboardInterrupt:
        return 0
