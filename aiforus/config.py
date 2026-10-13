"""Typed application configuration.

Settings are loaded once at startup:

* non-secret settings from ``config.yaml``
* secrets (API keys) from the environment or a ``.env`` file

Modules receive the settings they need through their constructors instead of
reading files themselves, so behaviour no longer depends on the current
working directory and tests can build settings in memory.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"

LanguageCode = Literal["id", "en"]
SUPPORTED_LANGUAGES: tuple[str, ...] = ("id", "en")


class _Section(BaseModel):
    # Unknown keys are an error: a typo in config.yaml should fail loudly
    # instead of being silently ignored.
    model_config = ConfigDict(extra="forbid")


class AppSettings(_Section):
    name: str = "AIForUs Vision Assistant"
    # What the assistant calls itself and answers to ("Hai Nemo, apa di depan?").
    assistant_name: str = Field("Nemo", min_length=2, max_length=20, pattern=r"^[A-Za-z][A-Za-z ]*$")
    language: LanguageCode = "id"
    data_dir: Path = Path("data")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


class SpeechSettings(_Section):
    rate: int = Field(170, ge=80, le=320)
    volume: float = Field(1.0, ge=0.0, le=1.0)
    listen_timeout_s: float = Field(5.0, gt=0)
    phrase_time_limit_s: float = Field(10.0, gt=0)
    # Substrings matched (case-insensitively) against the installed TTS
    # voices' id, name and languages to pick a voice for each language.
    voice_hints: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "id": ["indonesian", "id-id", "id_id", "andika", "gadis"],
            "en": ["english", "en-us", "en_us", "en-gb", "zira", "david"],
        }
    )
    recognition_locale: dict[str, str] = Field(default_factory=lambda: {"id": "id-ID", "en": "en-US"})
    # Voice output engine. "auto" uses Piper when it is installed and the
    # voice model for the language has been downloaded, otherwise pyttsx3.
    engine: Literal["auto", "piper", "pyttsx3"] = "auto"
    piper_voices: dict[str, str] = Field(
        default_factory=lambda: {"id": "id_ID-news_tts-medium", "en": "en_US-lessac-medium"}
    )
    piper_dir: Path = Path("models/piper")
    piper_length_scale: float = Field(1.0, gt=0.3, le=3.0)  # > 1 speaks slower


class ListeningSettings(_Section):
    """When the assistant listens (voice mode only; ``--text`` is unaffected)."""

    # wake_word: say the assistant's name ("Hai Nemo") or press the key
    # push_to_talk: press the key, then speak
    # always: every utterance is a command (all audio goes to the recogniser)
    mode: Literal["wake_word", "push_to_talk", "always"] = "wake_word"
    # vosk: works without training (English model; listens for the name and "help")
    # openwakeword: trained ONNX models ("hai nemo", "tolong/darurat"), see tools/wakeword
    wake_engine: Literal["vosk", "openwakeword"] = "vosk"
    model_dir: Path = Path("models")
    vosk_model: str = "vosk-model-small-en-us-0.15"
    # English words closest to "hai" / "halo" for the Vosk model.
    vosk_greetings: list[str] = Field(default_factory=lambda: ["hi", "hey", "hello"])
    openwakeword_wake_model: str = "hai_nemo.onnx"
    openwakeword_emergency_model: str = "tolong.onnx"
    wake_threshold: float = Field(0.5, gt=0.0, lt=1.0)
    # Hear "tolong"/"darurat" (openWakeWord) or "help" (Vosk) without the name.
    emergency_without_name: bool = True
    push_to_talk_key: Literal["space", "enter", "none"] = "space"
    # With headphones the microphone can't hear the assistant, so its name
    # may also interrupt it while it speaks.
    headset: bool = False
    beep: bool = True
    end_silence_s: float = Field(0.8, ge=0.3, le=3.0)


class CameraSettings(_Section):
    index: int = Field(0, ge=0)
    width: int | None = 1280
    height: int | None = 720
    # OpenCV buffers frames; on-demand capture would otherwise return a stale
    # frame from seconds ago. Grab and discard this many before reading.
    flush_frames: int = Field(4, ge=0, le=30)
    # Below this mean brightness (0-255) the frame is reported as too dark.
    dark_threshold: float = Field(25.0, ge=0, le=255)
    # Below this pixel standard deviation the lens is likely covered.
    blank_std_threshold: float = Field(6.0, ge=0)
    # Horizontal field of view of the camera. Used to turn image positions into
    # clock directions and box sizes into distances. Typical webcams: 60-78;
    # wide glasses cameras: ~110-120. If distances are consistently off,
    # adjust this.
    horizontal_fov_deg: float = Field(70.0, ge=20.0, le=170.0)


class VisionSettings(_Section):
    detector_model: str = "yolov8n.pt"
    detection_confidence: float = Field(0.5, ge=0.0, le=1.0)
    ocr_languages: list[str] = Field(default_factory=lambda: ["id", "en"])
    ocr_confidence: float = Field(0.5, ge=0.0, le=1.0)
    max_objects_spoken: int = Field(6, ge=1)
    max_text_regions_spoken: int = Field(5, ge=1)
    # What "baca tulisan" does when the quick OCR finds nothing (it misses
    # small, distant or stylised text that a vision model can still read):
    # vlm  = look again with the vision model, if one is available
    # hint = suggest saying "baca dokumen"
    # off  = just say no text was found
    ocr_fallback: Literal["vlm", "hint", "off"] = "vlm"
    # Typical height of a detected face box (forehead to chin), used to
    # estimate how far away a person is from the size of their face. Works
    # even when their body is cut off by the frame. Calibrate if needed.
    face_height_m: float = Field(0.21, gt=0.1, lt=0.4)


class FaceSettings(_Section):
    enabled: bool = True
    # opencv: YuNet detector + SFace recogniser (small ONNX models that also run
    #         on Raspberry Pi, Jetson and phones). Needs only OpenCV.
    # dlib:   the face_recognition library (needs a C++ build; desktop only).
    backend: Literal["opencv", "dlib"] = "opencv"
    # int8 models are ~4x smaller and faster on edge devices, slightly less accurate.
    quantized: bool = False
    model_dir: Path = Path("models/opencv")
    detection_confidence: float = Field(0.8, gt=0.0, lt=1.0)  # opencv only
    detection_model: Literal["hog", "cnn"] = "hog"  # dlib only
    # Max Euclidean distance between embeddings to count as the same person.
    # Empty = the backend's recommended value (SFace 1.128 on unit vectors,
    # i.e. cosine similarity >= 0.363; dlib 0.55). Lower is stricter.
    match_threshold: float | None = Field(None, gt=0.0, le=2.0)
    max_samples_per_person: int = Field(10, ge=1, le=100)
    # One "kenali wajah" command collects this many samples from different
    # frames (angles/lighting vary slightly), trying for up to the timeout.
    enroll_samples: int = Field(3, ge=1, le=10)
    enroll_timeout_s: float = Field(4.0, gt=0.0, le=20.0)


class NavigationSettings(_Section):
    enabled: bool = True
    routing_url: str = "https://router.project-osrm.org"
    routing_profile: str = "foot"
    geocoding_url: str = "https://nominatim.openstreetmap.org/search"
    ip_location_url: str = "https://ipinfo.io/json"
    # Nominatim's usage policy requires an identifying User-Agent.
    user_agent: str = "aiforus-vision-assistant/0.2 (+https://github.com/Khaf-dev/aiforus)"
    http_timeout_s: float = Field(8.0, gt=0)
    # Used to estimate walking time; the public OSRM demo server only has a
    # car profile, so its durations are not walking durations.
    walking_speed_mps: float = Field(1.2, gt=0)


class LLMSettings(_Section):
    enabled: bool = True
    # Any OpenAI-compatible chat endpoint. Empty = OpenAI itself.
    # Local and free, works offline: Ollama -> "http://localhost:11434/v1"
    base_url: str | None = None
    model: str = "gpt-4o-mini"
    # Local models on a CPU can take a while to answer.
    timeout_s: float = Field(30.0, gt=0)
    max_tokens: int = Field(200, ge=16)
    # Vision-language model for detailed descriptions, documents and
    # questions about the camera image. Empty = same as `model`.
    vision_model: str | None = None
    vision_timeout_s: float = Field(60.0, gt=0)
    vision_max_tokens: int = Field(400, ge=16)
    image_max_side: int = Field(1024, ge=256, le=4096)
    # Camera images never leave the machine unless this is true. Local
    # endpoints (localhost / private network) are always allowed.
    allow_images_to_cloud: bool = False


class EmergencySettings(_Section):
    # Sending alerts is not implemented yet; contacts are kept so the
    # assistant can tell the user honestly what it can and cannot do.
    contacts: list[str] = Field(default_factory=list)
    local_emergency_number: str = "112"


class Settings(_Section):
    app: AppSettings = Field(default_factory=AppSettings)
    speech: SpeechSettings = Field(default_factory=SpeechSettings)
    listening: ListeningSettings = Field(default_factory=ListeningSettings)
    camera: CameraSettings = Field(default_factory=CameraSettings)
    vision: VisionSettings = Field(default_factory=VisionSettings)
    face: FaceSettings = Field(default_factory=FaceSettings)
    navigation: NavigationSettings = Field(default_factory=NavigationSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    emergency: EmergencySettings = Field(default_factory=EmergencySettings)

    # Secrets never come from config.yaml.
    # From LLM_API_KEY (any provider) or OPENAI_API_KEY.
    llm_api_key: SecretStr | None = Field(default=None, exclude=True)

    @property
    def data_dir(self) -> Path:
        path = self.app.data_dir
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def database_path(self) -> Path:
        return self.data_dir / "aiforus.db"

    @property
    def face_model_dir(self) -> Path:
        path = self.face.model_dir
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def listening_model_dir(self) -> Path:
        path = self.listening.model_dir
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def piper_dir(self) -> Path:
        path = self.speech.piper_dir
        return path if path.is_absolute() else PROJECT_ROOT / path


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # optional convenience
        return
    load_dotenv(PROJECT_ROOT / ".env", override=False)


def load_settings(
    path: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
    *,
    environ: dict[str, str] | None = None,
) -> Settings:
    """Load and validate settings.

    ``path`` defaults to ``config.yaml`` in the project root; a missing default
    file falls back to built-in defaults, a missing explicit file is an error.
    """
    if environ is None:
        _load_dotenv()
        environ = dict(os.environ)

    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    data: Any = {}
    if config_path.exists():
        with config_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    elif path is not None:
        raise FileNotFoundError(f"Config file not found: {config_path}")

    if not isinstance(data, dict):
        raise ValueError(f"{config_path} must contain a mapping at the top level")
    if overrides:
        data = _deep_merge(data, overrides)

    settings = Settings.model_validate(data)
    api_key = (environ.get("LLM_API_KEY") or environ.get("OPENAI_API_KEY") or "").strip()
    if api_key:
        settings.llm_api_key = SecretStr(api_key)
    return settings
