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


class VisionSettings(_Section):
    detector_model: str = "yolov8n.pt"
    detection_confidence: float = Field(0.5, ge=0.0, le=1.0)
    ocr_languages: list[str] = Field(default_factory=lambda: ["id", "en"])
    ocr_confidence: float = Field(0.5, ge=0.0, le=1.0)
    max_objects_spoken: int = Field(6, ge=1)
    max_text_regions_spoken: int = Field(5, ge=1)


class FaceSettings(_Section):
    enabled: bool = True
    detection_model: Literal["hog", "cnn"] = "hog"
    # Euclidean distance between 128-d dlib encodings. face_recognition's
    # default tolerance is 0.6; lower is stricter (fewer false matches).
    match_threshold: float = Field(0.55, gt=0.0, le=1.0)
    max_samples_per_person: int = Field(10, ge=1, le=100)


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
    model: str = "gpt-4o-mini"
    timeout_s: float = Field(15.0, gt=0)
    max_tokens: int = Field(200, ge=16)


class EmergencySettings(_Section):
    # Sending alerts is not implemented yet; contacts are kept so the
    # assistant can tell the user honestly what it can and cannot do.
    contacts: list[str] = Field(default_factory=list)
    local_emergency_number: str = "112"


class Settings(_Section):
    app: AppSettings = Field(default_factory=AppSettings)
    speech: SpeechSettings = Field(default_factory=SpeechSettings)
    camera: CameraSettings = Field(default_factory=CameraSettings)
    vision: VisionSettings = Field(default_factory=VisionSettings)
    face: FaceSettings = Field(default_factory=FaceSettings)
    navigation: NavigationSettings = Field(default_factory=NavigationSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    emergency: EmergencySettings = Field(default_factory=EmergencySettings)

    # Secrets never come from config.yaml.
    openai_api_key: SecretStr | None = Field(default=None, exclude=True)

    @property
    def data_dir(self) -> Path:
        path = self.app.data_dir
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def database_path(self) -> Path:
        return self.data_dir / "aiforus.db"

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
    api_key = environ.get("OPENAI_API_KEY", "").strip()
    if api_key:
        settings.openai_api_key = SecretStr(api_key)
    return settings
