"""Command-line entry point: ``python -m aiforus`` (or ``python app.py``)."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import platform
import sys
import warnings
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from . import __version__
from .assistant import Assistant
from .config import PROJECT_ROOT, SUPPORTED_LANGUAGES, Settings, load_settings
from .hal import ComponentUnavailable
from .hal.console import quick_edit_disabled
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
    parser.add_argument(
        "--download-models",
        "--download-voices",
        dest="download_models",
        action="store_true",
        help="download the Piper voices and face models named in config.yaml",
    )
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
    vlm: Any = None
    vlm_remote: bool = False
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


def _build_voice(c: Components, s: Settings, language: str) -> Any:
    """Piper when configured/available, otherwise pyttsx3 (``engine: auto``)."""
    from .hal.piper_tts import PiperTTS
    from .hal.tts import Pyttsx3TTS

    engine = s.speech.engine
    if engine in ("auto", "piper"):
        piper = _try(
            c,
            "voice output (piper)",
            lambda: PiperTTS(
                voices=s.speech.piper_voices,
                model_dir=s.piper_dir,
                language=language,
                volume=s.speech.volume,
                length_scale=s.speech.piper_length_scale,
            ),
        )
        if piper is not None or engine == "piper":
            return piper
    return _try(
        c,
        "voice output (pyttsx3)",
        lambda: Pyttsx3TTS(
            rate=s.speech.rate,
            volume=s.speech.volume,
            voice_hints=s.speech.voice_hints,
            language=language,
        ),
    )


def build_components(settings: Settings, args: argparse.Namespace, language: str) -> Components:
    from .hal.camera import OpenCVCamera
    from .hal.stt import GoogleSpeechInput, KeyboardInput
    from .hal.tts import PrintTTS
    from .services.faces import DlibFaceEncoder, OpenCVFaceEncoder
    from .services.navigation import Navigator
    from .services.vision import EasyOcrReader, YoloDetector

    c = Components()
    s = settings

    voice = None if args.mute else _build_voice(c, s, language)
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
    if s.face.enabled and s.face.backend == "opencv":
        c.face_encoder = _try(
            c,
            "face recognition (opencv)",
            lambda: OpenCVFaceEncoder(
                s.face_model_dir, quantized=s.face.quantized, score_threshold=s.face.detection_confidence
            ),
        )
    elif s.face.enabled:
        c.face_encoder = _try(c, "face recognition (dlib)", lambda: DlibFaceEncoder(s.face.detection_model))
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
    c.answerer = _build_answerer(c, s)
    c.vlm, c.vlm_remote = _build_vlm(c, s, c.answerer)
    return c


_LLM = "general questions (LLM)"
_VLM = "detailed vision (VLM)"


def _build_vlm(c: Components, s: Settings, answerer: Any) -> tuple[Any, bool]:
    """The same client answers questions about camera images, but images only
    leave the machine when the user explicitly allows it."""
    from .services.llm import is_local_endpoint

    remote = not is_local_endpoint(s.llm.base_url)
    if answerer is None:
        c.status[_VLM] = "off - needs the LLM settings above"
        return None, remote
    if remote and not s.llm.allow_images_to_cloud:
        c.status[_VLM] = "blocked - images would leave this machine (set llm.allow_images_to_cloud)"
        return None, remote
    where = "cloud, announced every time" if remote else "local, images stay on this machine"
    c.status[_VLM] = f"ok - {s.llm.vision_model or s.llm.model} ({where})"
    return answerer, remote


def _build_answerer(c: Components, s: Settings) -> Any:
    from .services.llm import OpenAIAnswerer

    if not s.llm.enabled:
        c.status[_LLM] = "disabled in config"
        return None
    if s.llm.base_url is None and s.llm_api_key is None:
        c.status[_LLM] = "off - set llm.base_url (e.g. Ollama) or LLM_API_KEY"
        return None
    # Local servers such as Ollama ignore the key, but the client requires one.
    key = s.llm_api_key.get_secret_value() if s.llm_api_key is not None else "not-needed"
    answerer = _try(
        c,
        _LLM,
        lambda: OpenAIAnswerer(
            api_key=key,
            base_url=s.llm.base_url,
            model=s.llm.model,
            timeout_s=s.llm.timeout_s,
            max_tokens=s.llm.max_tokens,
            vision_model=s.llm.vision_model,
            vision_max_tokens=s.llm.vision_max_tokens,
            vision_timeout_s=s.llm.vision_timeout_s,
        ),
    )
    if answerer is not None:
        c.status[_LLM] = f"ok - {s.llm.model} @ {s.llm.base_url or 'api.openai.com'}"
    return answerer


def _probe_llm(s: Settings) -> str | None:
    """For local/self-hosted endpoints: is the server actually running?"""
    if not s.llm.enabled or s.llm.base_url is None:
        return None
    import requests

    try:
        response = requests.get(s.llm.base_url.rstrip("/") + "/models", timeout=3)
        response.raise_for_status()
        models = [m.get("id") for m in response.json().get("data", [])]
    except Exception as exc:
        return f"NOT reachable ({type(exc).__name__}) - is the server running?"
    wanted = list(dict.fromkeys([s.llm.model, s.llm.vision_model or s.llm.model]))
    missing = [m for m in wanted if m not in models]
    if missing:
        names = ", ".join(repr(m) for m in missing)
        return f"reachable, but model {names} not found (have: {', '.join(models) or 'none'})"
    return "reachable, model found"


def _close_quietly(*resources: Any) -> None:
    for resource in resources:
        close = getattr(resource, "close", None)
        if close is not None:
            with contextlib.suppress(Exception):
                close()


def download_models(settings: Settings) -> int:
    from .downloads import download_file
    from .hal.piper_tts import download_voice
    from .services.faces import opencv_face_model_files

    def report(msg: str) -> None:
        print(f"  {msg}")

    jobs: list[tuple[str, Any]] = [
        (
            f"voice [{lang}] {name}",
            lambda name=name: download_voice(name, settings.piper_dir, progress=report),
        )
        for lang, name in settings.speech.piper_voices.items()
    ]
    if settings.face.enabled and settings.face.backend == "opencv":
        for role, (url, filename) in opencv_face_model_files(settings.face.quantized).items():
            dest = settings.face_model_dir / filename
            jobs.append(
                (
                    f"face {role} {filename}",
                    lambda url=url, dest=dest: download_file(url, dest, progress=report),
                )
            )

    failures = 0
    for title, job in jobs:
        print(title)
        try:
            path = job()
        except Exception as exc:  # network, HTTP 404, disk
            failures += 1
            print(f"  FAILED: {exc}")
        else:
            print(f"  ok: {path}")
    return 1 if failures else 0


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
        engine = getattr(voice, "engine_name", "tts")
        if engine == "piper":
            hint = "run: python -m aiforus --download-models"
        else:
            hint = "install one, or use Piper (see README)"
        for lang in SUPPORTED_LANGUAGES:
            voice.set_language(lang)
            found = voice.voice_found.get(lang)
            label = f"TTS voice for {lang!r} ({engine})"
            print(f"  {label:<26} {'found' if found else 'NOT FOUND - ' + hint}")
        voice.set_language(language)
    if components.camera is not None:
        frame = components.camera.capture()
        print(f"  {'camera frame':<26} {'ok ' + str(frame.shape) if frame is not None else 'no frame'}")
    probe = _probe_llm(settings)
    if probe is not None:
        print(f"  {'LLM server':<26} {probe}")
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
            SqlFaceStore(db, model=components.face_encoder.model_name),
            match_threshold=settings.face.match_threshold or components.face_encoder.default_threshold,
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
        vlm=components.vlm,
        vlm_is_remote=components.vlm_remote,
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


def _quiet_third_party_noise() -> None:
    """Hide chatter from dependencies that isn't actionable for the user.

    Shown again with ``--debug``.
    """
    logging.getLogger("comtypes").setLevel(logging.WARNING)
    # Emitted by torch when EasyOCR loads its quantized model, and when its
    # DataLoader runs without a GPU. Neither affects results.
    warnings.filterwarnings("ignore", message=r".*quantize_per_(tensor|channel).*", category=UserWarning)
    warnings.filterwarnings(
        "ignore", message=r".*'pin_memory' argument is set as true.*", category=UserWarning
    )


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
        _quiet_third_party_noise()

    if args.download_models:
        return download_models(settings)
    if args.check:
        # The report already lists every problem; skip the duplicate warnings.
        logging.getLogger().setLevel(logging.ERROR)
        return run_check(settings, args)
    try:
        with quick_edit_disabled():
            return asyncio.run(run_assistant(settings, args))
    except KeyboardInterrupt:
        return 0
