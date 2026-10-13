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


@pytest.mark.parametrize(
    "url, local",
    [
        (None, False),
        ("http://localhost:11434/v1", True),
        ("http://127.0.0.1:8080/v1", True),
        ("http://192.168.1.20:11434/v1", True),
        ("http://my-pc.local:11434/v1", True),
        ("https://api.groq.com/openai/v1", False),
        ("https://8.8.8.8/v1", False),
    ],
)
def test_is_local_endpoint(url, local):
    from aiforus.services.llm import is_local_endpoint

    assert is_local_endpoint(url) is local


async def test_look_sends_image_as_data_url(fake_openai):
    from aiforus.services.llm import VisionTask

    answerer = OpenAIAnswerer(
        api_key="x",
        base_url="http://localhost:11434/v1",
        model="gemma3:4b",
        timeout_s=30,
        max_tokens=50,
        vision_model="qwen3-vl:4b",
        vision_max_tokens=321,
    )
    reply = await answerer.look(b"\xff\xd8jpeg", VisionTask.QUESTION, "id", "ini uang berapa")
    assert reply == "Jakarta."
    request = fake_openai.instances[0].requests[0]
    assert request["model"] == "qwen3-vl:4b" and request["max_tokens"] == 321
    system, user = request["messages"]
    assert "Bahasa Indonesia" in system["content"] and "safe" in system["content"]
    text, image = user["content"]
    assert "ini uang berapa" in text["text"]
    assert image["image_url"]["url"] == "data:image/jpeg;base64,/9hqcGVn"


async def test_requests_have_own_timeout_and_no_retries(fake_openai):
    """A retry re-sends the whole image request; the Windows test showed the
    first (model-loading) request being cut off at the chat timeout and
    started again."""
    from aiforus.services.llm import VisionTask

    answerer = OpenAIAnswerer(
        api_key="x", model="gemma3:4b", timeout_s=30, max_tokens=50, vision_timeout_s=75
    )
    await answerer.answer("halo", "id")
    await answerer.look(b"jpeg", VisionTask.DESCRIBE, "id")
    client = fake_openai.instances[0]
    assert client.kwargs["max_retries"] == 0
    assert [r["timeout"] for r in client.requests] == [30, 75]


async def test_answer_knows_today_and_hedges_on_changing_facts(fake_openai):
    from datetime import date

    answerer = OpenAIAnswerer(
        api_key="x", model="m", timeout_s=30, max_tokens=50, today=lambda: date(2026, 10, 13)
    )
    await answerer.answer("siapa presiden indonesia", "id")
    system = fake_openai.instances[0].requests[0]["messages"][0]["content"]
    assert "Today is Tuesday, 13 October 2026 " in system
    assert "may be out of date" in system
    assert "do not ask follow-up questions" in system
    # Second Windows test: it announced the date and "may be out of date" on
    # an unrelated question.
    assert "mention it only when asked" in system
    assert "do not add that warning to other answers" in system


@pytest.mark.parametrize(
    "language, phrase, absent",
    [("id", "di arah jam 3", "o'clock"), ("en", "at 3 o'clock", "di arah jam")],
)
async def test_vision_prompt_uses_clock_wording_of_the_reply_language(fake_openai, language, phrase, absent):
    """gemma3 translated "3 o'clock" literally as "di 3 jam" (= in 3 hours)."""
    from aiforus.services.llm import VisionTask

    answerer = OpenAIAnswerer(api_key="x", model="m", timeout_s=30, max_tokens=50)
    await answerer.look(b"jpeg", VisionTask.DESCRIBE, language)
    system, user = fake_openai.instances[0].requests[0]["messages"]
    assert phrase in system["content"]
    assert absent not in system["content"]
    assert "clock positions" in user["content"][0]["text"]
    # It said "jam 6" (behind the user) and took the person in front for the user.
    assert ("jam 4 sampai 8" if language == "id" else "4 to 8 are behind") in system["content"]
    assert "the user is not in it" in system["content"]


def test_vision_model_defaults_to_chat_model(fake_openai):
    answerer = OpenAIAnswerer(api_key="x", model="gemma3:4b", timeout_s=30, max_tokens=50)
    assert answerer._vision_model == "gemma3:4b"


def test_build_vlm_privacy(fake_openai):
    local = _settings(base_url="http://localhost:11434/v1", model="gemma3:4b")
    c = cli.Components()
    vlm, remote = cli._build_vlm(c, local, object())
    assert vlm is not None and remote is False
    assert "images stay on this machine" in c.status[cli._VLM]

    cloud = _settings(base_url="https://api.example.com/v1", model="m")
    c = cli.Components()
    vlm, remote = cli._build_vlm(c, cloud, object())
    assert vlm is None and remote is True
    assert c.status[cli._VLM].startswith("blocked")

    allowed = _settings(base_url="https://api.example.com/v1", model="m", allow_images_to_cloud=True)
    c = cli.Components()
    vlm, remote = cli._build_vlm(c, allowed, object())
    assert vlm is not None and remote is True
    assert "announced" in c.status[cli._VLM]

    c = cli.Components()
    assert cli._build_vlm(c, local, None) == (None, False)


@pytest.mark.parametrize(
    "language, verdicts",
    [
        ("id", ("'Ya.'", "'Tidak terlihat.'", "'Tidak yakin.'")),
        ("en", ("'Yes.'", "'Not visible.'", "'Not sure.'")),
    ],
)
async def test_yes_no_questions_must_start_with_a_clear_verdict(fake_openai, language, verdicts):
    """Fourth Windows test: two opposite, hedged answers to the same question."""
    from aiforus.services.llm import VisionTask

    answerer = OpenAIAnswerer(api_key="x", model="m", timeout_s=30, max_tokens=50)
    await answerer.look(b"jpeg", VisionTask.QUESTION, language, "apakah ada kunci di meja")
    text = fake_openai.instances[0].requests[0]["messages"][1]["content"][0]["text"]
    assert "apakah ada kunci di meja" in text
    assert all(v in text for v in verdicts)
    # Only questions get the verdict rule, not descriptions or documents.
    await answerer.look(b"jpeg", VisionTask.DESCRIBE, language)
    text = fake_openai.instances[0].requests[1]["messages"][1]["content"][0]["text"]
    assert verdicts[0] not in text


class _JsonModeRejected(Exception):
    pass


_JsonModeRejected.__name__ = "BadRequestError"


async def test_find_asks_for_json_and_parses_the_verdict(fake_openai, monkeypatch):
    from aiforus.services.presence import Presence, Verdict

    replies = iter(['{"visible": "yes", "clock": 11, "detail": "di kiri laptop"}'])

    async def create(**kwargs):
        client.requests.append(kwargs)
        message = types.SimpleNamespace(content=next(replies))
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    answerer = OpenAIAnswerer(api_key="x", model="m", timeout_s=30, max_tokens=50, vision_timeout_s=70)
    client = fake_openai.instances[0]
    monkeypatch.setattr(client.chat.completions, "create", create)
    presence = await answerer.find(b"jpeg", "kunci", "id")
    assert presence == Presence(Verdict.YES, 11, "di kiri laptop")
    request = client.requests[0]
    assert request["response_format"] == {"type": "json_object"}
    assert request["temperature"] == 0.0 and request["timeout"] == 70
    text = request["messages"][1]["content"][0]["text"]
    assert "Is there kunci in this photo?" in text and "Bahasa Indonesia" in text


async def test_find_retries_without_json_mode_when_the_server_rejects_it(fake_openai, monkeypatch):
    from aiforus.services.presence import Verdict

    answerer = OpenAIAnswerer(api_key="x", model="m", timeout_s=30, max_tokens=50)
    client = fake_openai.instances[0]

    async def create(**kwargs):
        client.requests.append(kwargs)
        if "response_format" in kwargs:
            raise _JsonModeRejected("response_format not supported")
        message = types.SimpleNamespace(content='{"visible": "no", "clock": null, "detail": ""}')
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    monkeypatch.setattr(client.chat.completions, "create", create)
    assert (await answerer.find(b"jpeg", "kunci", "id")).verdict is Verdict.NOT_VISIBLE
    assert ["response_format" in r for r in client.requests] == [True, False]
