import sys
import types

import pytest
from pydantic import SecretStr

from aiforus import cli
from aiforus.config import Settings
from aiforus.hal import ComponentUnavailable
from aiforus.services.llm import OpenAIAnswerer


class _Completions:
    def __init__(self, owner):
        self.owner = owner

    async def create(self, **kwargs):
        self.owner.requests.append(kwargs)
        message = types.SimpleNamespace(content="  Jakarta.  ")
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])


class FakeAsyncOpenAI:
    instances: list = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.requests = []
        self.chat = types.SimpleNamespace(completions=_Completions(self))
        FakeAsyncOpenAI.instances.append(self)


@pytest.fixture
def fake_openai(monkeypatch):
    FakeAsyncOpenAI.instances = []
    module = types.ModuleType("openai")
    module.AsyncOpenAI = FakeAsyncOpenAI
    monkeypatch.setitem(sys.modules, "openai", module)
    return FakeAsyncOpenAI


async def test_answerer_uses_base_url_and_spoken_prompt(fake_openai):
    answerer = OpenAIAnswerer(
        api_key="not-needed", base_url="http://localhost:11434/v1", model="qwen", timeout_s=30, max_tokens=99
    )
    assert await answerer.answer("Ibu kota Indonesia?", "id") == "Jakarta."
    client = fake_openai.instances[0]
    assert client.kwargs["base_url"] == "http://localhost:11434/v1"
    request = client.requests[0]
    assert request["model"] == "qwen" and request["max_tokens"] == 99
    assert "Bahasa Indonesia" in request["messages"][0]["content"]
    assert "safe" in request["messages"][0]["content"]


def test_missing_openai_package(monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", None)
    with pytest.raises(ComponentUnavailable):
        OpenAIAnswerer(api_key="x", model="m", timeout_s=1, max_tokens=16)


def _settings(**llm):
    return Settings.model_validate({"llm": llm})


def test_llm_off_without_endpoint_or_key(fake_openai):
    c = cli.Components()
    assert cli._build_answerer(c, _settings()) is None
    assert c.status[cli._LLM].startswith("off")
    c = cli.Components()
    assert cli._build_answerer(c, _settings(enabled=False)) is None
    assert c.status[cli._LLM] == "disabled in config"


def test_local_endpoint_needs_no_key(fake_openai):
    c = cli.Components()
    answerer = cli._build_answerer(c, _settings(base_url="http://localhost:11434/v1", model="qwen"))
    assert answerer is not None
    assert fake_openai.instances[0].kwargs["api_key"] == "not-needed"
    assert c.status[cli._LLM] == "ok - qwen @ http://localhost:11434/v1"


def test_hosted_provider_with_key(fake_openai):
    s = _settings(model="gpt-4o-mini")
    s.llm_api_key = SecretStr("sk-test")
    c = cli.Components()
    assert cli._build_answerer(c, s) is not None
    kwargs = fake_openai.instances[0].kwargs
    assert kwargs["api_key"] == "sk-test" and kwargs["base_url"] is None
    assert c.status[cli._LLM] == "ok - gpt-4o-mini @ api.openai.com"


class _Resp:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_probe_llm(monkeypatch):
    import requests

    s = _settings(base_url="http://localhost:11434/v1", model="qwen")
    monkeypatch.setattr(requests, "get", lambda url, timeout: _Resp({"data": [{"id": "qwen"}]}))
    assert cli._probe_llm(s) == "reachable, model found"
    monkeypatch.setattr(requests, "get", lambda url, timeout: _Resp({"data": [{"id": "other"}]}))
    assert "not found" in cli._probe_llm(s)

    def down(url, timeout):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(requests, "get", down)
    assert cli._probe_llm(s).startswith("NOT reachable")
    assert cli._probe_llm(_settings()) is None  # hosted default: not probed
