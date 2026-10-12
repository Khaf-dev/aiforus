import pytest
from pydantic import ValidationError

from aiforus.config import DEFAULT_CONFIG_PATH, PROJECT_ROOT, load_settings


def test_repo_config_is_valid():
    settings = load_settings(DEFAULT_CONFIG_PATH, environ={})
    assert settings.app.language == "id"
    assert settings.openai_api_key is None


def test_unknown_key_fails_loudly(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("speech:\n  speach_rate: 150\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_settings(cfg, environ={})


def test_missing_explicit_file_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_settings(tmp_path / "nope.yaml", environ={})


def test_api_key_comes_from_environment_only(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("app:\n  language: en\n", encoding="utf-8")
    settings = load_settings(cfg, environ={"OPENAI_API_KEY": "sk-test"})
    assert settings.openai_api_key.get_secret_value() == "sk-test"
    assert "sk-test" not in repr(settings)
    assert "openai_api_key" not in settings.model_dump()


def test_overrides_and_relative_data_dir():
    settings = load_settings(
        None,
        overrides={"app": {"language": "en"}, "vision": {"max_objects_spoken": 3}},
        environ={},
    )
    assert settings.app.language == "en"
    assert settings.vision.max_objects_spoken == 3
    assert settings.data_dir == PROJECT_ROOT / "data"


def test_unsupported_language_rejected():
    with pytest.raises(ValidationError):
        load_settings(overrides={"app": {"language": "fr"}}, environ={})
