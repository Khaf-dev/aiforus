import asyncio
import time

from aiforus.speech import Priority, SpeechQueue
from tests.fakes import FakeTTS


async def _until_started(tts, count=1, timeout=2.0):
    """Wait until the fake engine has started ``count`` utterances
    (robust against slow CI machines, unlike a fixed sleep)."""
    deadline = time.monotonic() + timeout
    while len(tts.started) < count:
        assert time.monotonic() < deadline, "speech never started"
        await asyncio.sleep(0.002)


async def _queue(tts):
    q = SpeechQueue(tts)
    q.start()
    return q


async def test_more_urgent_items_are_spoken_first():
    tts = FakeTTS(duration=0.05)
    q = await _queue(tts)
    q.say("first", Priority.NORMAL)
    await _until_started(tts)
    low = q.say("low", Priority.LOW)
    high = q.say("high", Priority.HIGH)
    await asyncio.gather(low, high)
    assert tts.started == ["first", "high", "low"]
    await q.close()


async def test_more_urgent_item_interrupts_current_one():
    tts = FakeTTS(duration=1.0)
    q = await _queue(tts)
    long = q.say("long description", Priority.NORMAL)
    await _until_started(tts)
    started = time.monotonic()
    # Set before queueing: the worker may start "urgent" before this
    # coroutine resumes after ``await long`` (the current wait keeps its 1 s).
    tts.duration = 0.0
    urgent = q.say("urgent", Priority.HIGH)
    assert await long is False
    assert await urgent is True
    assert time.monotonic() - started < 0.5
    assert tts.interrupted == ["long description"]
    await q.close()


async def test_critical_drops_stale_lower_priority_items():
    tts = FakeTTS(duration=1.0)
    q = await _queue(tts)
    current = q.say("reading text", Priority.HIGH)
    await _until_started(tts)
    tip = q.say("a tip", Priority.LOW)
    other = q.say("more text", Priority.HIGH)
    tts.duration = 0.0
    alert = q.say("emergency", Priority.CRITICAL)
    assert await alert is True
    assert await current is False
    assert await tip is False
    assert await other is False
    assert tts.spoken == ["emergency"]
    await q.close()


async def test_equal_priority_does_not_interrupt():
    tts = FakeTTS(duration=0.05)
    q = await _queue(tts)
    a = q.say("a", Priority.HIGH)
    await _until_started(tts)
    b = q.say("b", Priority.HIGH)
    assert await a is True and await b is True
    assert tts.spoken == ["a", "b"]
    await q.close()


async def test_stop_all_silences_everything():
    tts = FakeTTS(duration=1.0)
    q = await _queue(tts)
    a = q.say("a")
    await _until_started(tts)
    b = q.say("b")
    q.stop_all()
    assert await a is False
    assert await b is False
    await asyncio.wait_for(q.wait_idle(), 1)
    assert not q.is_speaking
    await q.close()


async def test_duplicate_pending_text_is_spoken_once():
    tts = FakeTTS(duration=0.05)
    q = await _queue(tts)
    q.say("busy")
    await _until_started(tts)
    first = q.say("same")
    second = q.say("same")
    assert first is second
    await q.wait_idle()
    assert tts.spoken.count("same") == 1
    await q.close()


async def test_empty_text_is_a_no_op():
    tts = FakeTTS()
    q = await _queue(tts)
    assert await q.say("   ") is True
    assert tts.started == []
    await q.close()


async def test_engine_failure_does_not_kill_the_queue():
    tts = FakeTTS(fail_on="boom")
    q = await _queue(tts)
    assert await q.say("boom") is False
    assert await q.say("still alive") is True
    await q.close()


async def test_on_say_hook_receives_text_and_priority():
    seen = []
    q = SpeechQueue(FakeTTS(), on_say=lambda text, prio: seen.append((text, prio)))
    q.start()
    await q.say("hello", Priority.LOW)
    assert seen == [("hello", Priority.LOW)]
    await q.close()
