import asyncio
import threading

import numpy as np
import pytest

from aiforus.assistant import Assistant
from aiforus.config import Settings
from aiforus.hal.location import Location
from aiforus.hal.stt import SpeechServiceError
from aiforus.i18n import Translator
from aiforus.locales import MESSAGES
from aiforus.services.faces import FaceService
from aiforus.services.navigation import NavigationError, Place, parse_osrm_route
from aiforus.services.vision import Detection, TextRegion, VisionService
from aiforus.speech import SpeechQueue
from aiforus.storage import Database, PreferenceStore, SqlFaceStore
from tests.fakes import FakeCamera, FakeTTS, flat_frame, textured_frame, wait_until
from tests.test_navigation import OSRM_SAMPLE

# "One moment" acknowledgements may or may not be spoken depending on timing.
ACKS = {MESSAGES[lang][key] for lang in MESSAGES for key in ("looking", "nav_searching")}
JAKARTA = Location(-6.18, 106.82, "Jakarta, ID", 5000, "ip")


class StubLocation:
    def __init__(self, result=JAKARTA, gate: threading.Event | None = None):
        self.result, self.gate = result, gate

    def locate(self):
        if self.gate is not None:
            self.gate.wait(2)
        return self.result


class StubDetector:
    def __init__(self, items):
        self.items = items

    def detect(self, frame):
        return [i if isinstance(i, Detection) else Detection(i, 0.9, (0, 0, 1, 1)) for i in self.items]


HD = (720, 1280)  # frame (height, width)
FOCAL_PX = 914.3  # 70 deg horizontal FOV at 1280x720


def at(label, distance_m, center_x=640, real_height=None):
    """A detection of ``label`` standing ``distance_m`` away in an HD frame."""
    from aiforus.services.spatial import TYPICAL_HEIGHT_M

    h = (real_height or TYPICAL_HEIGHT_M[label]) * FOCAL_PX / distance_m
    return Detection(label, 0.9, (center_x - 40, 360 - h / 2, center_x + 40, 360 + h / 2))


class StubReader:
    def __init__(self, texts):
        self.texts = texts

    def read(self, frame):
        return [TextRegion(t, 0.9) for t in self.texts]


class StubEncoder:
    def __init__(self):
        self.next = []
        self.script = None  # optional list of per-call results
        self.calls = 0

    def encode(self, frame):
        self.calls += 1
        if self.script:
            return list(self.script.pop(0))
        return list(self.next)


class StubNavigator:
    def __init__(self, error=None):
        self.error = error

    def geocode(self, query, near, language):
        if self.error:
            raise self.error
        return Place("Monas", -6.17, 106.83)

    def route(self, start, place):
        return parse_osrm_route(OSRM_SAMPLE, place.name)

    def walking_minutes(self, route):
        return 17


class StubAnswerer:
    def __init__(self, answer="Ibu kota Indonesia adalah Jakarta.", error=None):
        self.answer_text, self.error = answer, error
        self.questions = []

    async def answer(self, question, language):
        self.questions.append((question, language))
        if self.error:
            raise self.error
        return self.answer_text


class Harness:
    def __init__(
        self,
        tmp_path,
        *,
        frames=None,
        labels=(),
        texts=(),
        camera=True,
        detector=True,
        reader=True,
        faces=True,
        location=None,
        navigator=None,
        answerer=None,
        language="id",
    ):
        self.tts = FakeTTS()
        self.speech = SpeechQueue(self.tts)
        self.db = Database(tmp_path / "t.db")
        self.prefs = PreferenceStore(self.db)
        self.encoder = StubEncoder()
        self.settings = Settings()
        vision = VisionService(
            FakeCamera(frames if frames is not None else [textured_frame()]) if camera else None,
            StubDetector(list(labels)) if detector else None,
            StubReader(list(texts)) if reader else None,
            self.settings.camera,
            self.settings.vision,
        )
        self.language_changes = []
        self.assistant = Assistant(
            settings=self.settings,
            speech=self.speech,
            translator=Translator(language),
            vision=vision,
            faces=FaceService(
                self.encoder, SqlFaceStore(self.db), match_threshold=0.5, max_samples_per_person=10
            )
            if faces
            else None,
            navigator=navigator,
            location=location,
            answerer=answerer,
            prefs=self.prefs,
            on_language_change=self.language_changes.append,
        )
        self.assistant.ENROLL_SETTLE_S = 0
        self.assistant.ENROLL_FRAME_INTERVAL_S = 0
        self.settings.face.enroll_timeout_s = 0.3

    async def __aenter__(self):
        self.speech.start()
        return self

    async def __aexit__(self, *exc):
        await self.speech.close()
        self.db.close()

    async def say(self, utterance):
        self.tts.spoken.clear()
        await self.assistant.handle(utterance)
        await asyncio.sleep(0)
        await asyncio.wait_for(self.speech.wait_idle(), 2)
        return [s for s in self.tts.spoken if s not in ACKS]


# -- safety ------------------------------------------------------------------


async def test_emergency_is_honest_and_gives_local_number(tmp_path):
    async with Harness(tmp_path, location=StubLocation()) as h:
        spoken = await h.say("tolong")
        assert "Mode darurat" in spoken[0]
        assert "belum bisa mengirim pesan darurat" in spoken[0]
        assert "112" in spoken[0]
        assert "Help is on the way" not in " ".join(spoken)
        assert "Jakarta, ID" in spoken[1]


async def test_emergency_speaks_before_location_lookup_finishes(tmp_path):
    gate = threading.Event()
    async with Harness(tmp_path, location=StubLocation(gate=gate)) as h:
        task = asyncio.create_task(h.assistant.handle("darurat"))
        assert await asyncio.to_thread(wait_until, lambda: any("112" in s for s in h.tts.spoken))
        gate.set()
        await task
        await h.speech.wait_idle()


async def test_emergency_without_location(tmp_path):
    async with Harness(tmp_path, location=StubLocation(result=None)) as h:
        spoken = await h.say("help me")
        assert spoken[-1] == "Lokasimu tidak bisa ditentukan."


async def test_exit_needs_confirmation(tmp_path):
    async with Harness(tmp_path) as h:
        assert "Mau mematikan asisten" in (await h.say("matikan asisten"))[0]
        assert h.assistant.running
        assert (await h.say("ya")) == ["Asisten dimatikan. Sampai jumpa."]
        assert not h.assistant.running


async def test_exit_cancelled_by_no_or_by_another_command(tmp_path):
    async with Harness(tmp_path) as h:
        await h.say("matikan asisten")
        assert await h.say("tidak") == ["Baik, asisten tetap menyala."]
        await h.say("matikan asisten")
        await h.say("bantuan")  # any other command cancels the pending exit
        assert await h.say("ya") == ["Tidak ada yang perlu dikonfirmasi."]
        assert h.assistant.running


async def test_friend_question_does_not_exit(tmp_path):
    async with Harness(tmp_path) as h:
        spoken = await h.say("is my friend here")
        assert h.assistant.running
        assert "layanan AI belum diatur" in spoken[0]


async def test_stop_interrupts_speech(tmp_path):
    async with Harness(tmp_path) as h:
        h.tts.duration = 2.0
        h.assistant.say("help_menu")
        await asyncio.sleep(0.05)
        await h.assistant.handle("diam")
        await asyncio.wait_for(h.speech.wait_idle(), 1)
        assert h.tts.interrupted


async def test_handler_crash_is_reported_and_assistant_survives(tmp_path):
    async with Harness(tmp_path) as h:

        async def boom(intent):
            raise RuntimeError("bug")

        h.assistant._handlers[h.assistant.router.parse("bantuan").type] = boom
        assert await h.say("bantuan") == ["Maaf, terjadi kesalahan. Coba lagi."]
        assert h.assistant.running


# -- vision ------------------------------------------------------------------


async def test_describe_scene_gives_clock_direction_and_distance(tmp_path):
    labels = [at("person", 3), at("chair", 2, center_x=1100), at("person", 5)]
    frame = textured_frame(size=HD)
    async with Harness(tmp_path, frames=[frame], labels=labels, texts=["KELUAR"]) as h:
        spoken = await h.say("apa di depan")
        assert spoken[0] == (
            "Kursi di jam 1, sekitar 2 meter. 2 orang di jam 12, yang terdekat sekitar 3 meter."
        )
        assert "Ada juga tulisan" in spoken[1]


async def test_describe_scene_in_english(tmp_path):
    labels = [at("person", 4, center_x=200), at("cup", 1.2, center_x=640, real_height=0.1)]
    async with Harness(
        tmp_path, frames=[textured_frame(size=HD)], labels=labels, texts=[], language="en"
    ) as h:
        assert (await h.say("what's in front of me"))[0] == (
            "Cup at 12 o'clock, about 1 meter. Person at 11 o'clock, about 4 meters."
        )


async def test_describe_scene_limits_and_summarises_the_rest(tmp_path):
    labels = [at("person", d, center_x=640) for d in (3, 4)] + [
        at(label, 2, center_x=x)
        for label, x in [("chair", 100), ("bench", 300), ("dog", 900), ("car", 1200), ("bottle", 700)]
    ]
    async with Harness(tmp_path, frames=[textured_frame(size=HD)], labels=labels, texts=[]) as h:
        h.settings.vision.max_objects_spoken = 3
        spoken = await h.say("benda apa")
        assert spoken[0].endswith("Ada juga 4 benda lain.")
        assert spoken[0].count(" di jam ") == 3


async def test_object_under_one_meter(tmp_path):
    labels = [at("cup", 0.6), at("cup", 0.8)]
    async with Harness(tmp_path, frames=[textured_frame(size=HD)], labels=labels, texts=[]) as h:
        assert await h.say("benda apa") == ["2 cangkir di jam 12, yang terdekat kurang dari 1 meter."]


async def test_object_cut_off_by_frame_is_very_close(tmp_path):
    close = Detection("person", 0.9, (500, 0, 800, 720))
    async with Harness(tmp_path, frames=[textured_frame(size=HD)], labels=[close], texts=[]) as h:
        assert await h.say("benda apa") == ["Orang di jam 12, sangat dekat."]


async def test_dark_or_covered_camera_is_reported(tmp_path):
    async with Harness(tmp_path, frames=[flat_frame(3)], labels=["person"]) as h:
        assert await h.say("apa di depan") == ["Gambar terlalu gelap. Aku tidak bisa melihat dengan jelas."]
    async with Harness(tmp_path, frames=[flat_frame(200)], labels=["person"]) as h:
        assert await h.say("benda apa") == ["Kamera sepertinya tertutup. Aku tidak bisa melihat apa pun."]
    async with Harness(tmp_path, frames=[], labels=["person"]) as h:
        assert await h.say("apa di depan") == ["Kamera tidak tersedia. Aku tidak bisa melihat sekarang."]


async def test_missing_vision_components_say_so_without_acknowledging(tmp_path):
    async with Harness(tmp_path, detector=False, reader=False) as h:
        h.tts.spoken.clear()
        await h.assistant.handle("baca tulisan")
        await h.speech.wait_idle()
        assert h.tts.spoken == ["Fitur penglihatan belum terpasang di perangkat ini."]


async def test_read_text_limits_and_reports_remaining(tmp_path):
    texts = [f"baris {i}" for i in range(7)]
    async with Harness(tmp_path, texts=texts) as h:
        spoken = await h.say("bacakan tulisan")
        assert spoken[0] == "Aku menemukan 7 tulisan."
        assert spoken[1:6] == texts[:5]
        assert spoken[6] == "Masih ada 2 tulisan lain yang tidak aku bacakan."


async def test_no_text(tmp_path):
    async with Harness(tmp_path, texts=[]) as h:
        assert await h.say("baca") == ["Aku tidak menemukan tulisan yang bisa dibaca."]


# -- faces -------------------------------------------------------------------


def v(x):
    out = np.zeros(128)
    out[0] = x
    return out


async def test_enroll_recognize_list_forget(tmp_path):
    async with Harness(tmp_path) as h:
        h.encoder.next = [v(1)]
        spoken = await h.say("kenali wajah sebagai budi")
        assert "Pastikan Budi setuju" in spoken[0]
        assert spoken[-1] == "Wajah Budi tersimpan. Sekarang ada 3 sampel."

        h.encoder.next = [v(1.1), v(9)]
        spoken = await h.say("siapa ini")
        assert spoken == ["Aku melihat 2 wajah.", "Yang aku kenal: Budi.", "1 orang belum aku kenal."]

        assert await h.say("siapa saja yang kamu kenal") == ["Aku mengenal 1 orang: Budi."]
        assert await h.say("lupakan budi") == ["Data wajah Budi sudah dihapus."]
        assert await h.say("lupakan budi") == ["Aku tidak punya data wajah bernama Budi."]
        assert await h.say("siapa saja yang kamu kenal") == ["Aku belum mengenal siapa pun."]


async def test_enroll_needs_name_and_single_face(tmp_path):
    async with Harness(tmp_path) as h:
        assert await h.say("kenali wajah") == ["Sebutkan namanya, misalnya: kenali wajah sebagai Budi."]
        h.encoder.next = [v(1), v(2)]
        spoken = await h.say("kenali wajah sebagai siti")
        assert spoken[-1] == "Aku melihat lebih dari satu wajah. Pastikan hanya Siti yang terlihat."


async def test_enroll_keeps_trying_until_a_single_face_is_seen(tmp_path):
    async with Harness(tmp_path) as h:
        h.encoder.script = [[], [v(1), v(2)], [v(1)], [], [v(1.01)], [v(1.02)]]
        spoken = await h.say("kenali wajah sebagai siti")
        assert spoken[-1] == "Wajah Siti tersimpan. Sekarang ada 3 sampel."
        assert h.encoder.calls == 6


async def test_enroll_saves_what_it_found_before_timeout(tmp_path):
    async with Harness(tmp_path) as h:
        h.encoder.script = [[v(1)]]  # then no faces at all
        spoken = await h.say("kenali wajah sebagai siti")
        assert spoken[-1] == "Wajah Siti tersimpan. Sekarang ada 1 sampel."


async def test_enroll_respects_the_sample_limit(tmp_path):
    async with Harness(tmp_path) as h:
        h.encoder.next = [v(1)]
        await h.say("kenali wajah sebagai budi")  # 3
        await h.say("kenali wajah sebagai budi")  # 6
        await h.say("kenali wajah sebagai budi")  # 9
        assert (await h.say("kenali wajah sebagai budi"))[
            -1
        ] == "Wajah Budi tersimpan. Sekarang ada 10 sampel."
        spoken = await h.say("kenali wajah sebagai budi")
        assert spoken[-1] == "Sampel wajah Budi sudah penuh, maksimal 10 sampel."


async def test_enroll_stops_immediately_without_camera(tmp_path):
    async with Harness(tmp_path, frames=[]) as h:
        h.settings.face.enroll_timeout_s = 5
        spoken = await asyncio.wait_for(h.say("kenali wajah sebagai siti"), 2)
        assert spoken[-1] == "Kamera tidak tersedia. Aku tidak bisa melihat sekarang."


async def test_faces_unavailable(tmp_path):
    async with Harness(tmp_path, faces=False) as h:
        assert await h.say("siapa ini") == ["Pengenalan wajah belum terpasang di perangkat ini."]


# -- navigation ----------------------------------------------------------------


async def test_navigation_flow(tmp_path):
    async with Harness(tmp_path, navigator=StubNavigator(), location=StubLocation()) as h:
        spoken = await h.say("arahkan aku ke monas")
        assert spoken[0] == "Rute ke Monas: sekitar 1,2 kilometer, kira-kira 17 menit berjalan kaki."
        assert any("bisa meleset beberapa kilometer" in s for s in spoken)
        assert "Aku belum bisa mendeteksi rintangan. Tetap gunakan tongkat." in spoken
        assert "Mulai berjalan ke Jalan Kebon Sirih, lalu jalan sekitar 120 meter." in spoken

        assert (await h.say("arah berikutnya"))[0].startswith("Belok kiri ke Jalan Medan Merdeka Selatan")
        assert (await h.say("ulangi arah"))[0].startswith("Belok kiri")
        for _ in range(3):
            await h.say("arah berikutnya")
        assert await h.say("arah berikutnya") == ["Itu langkah terakhir. Rute selesai."]


async def test_navigation_errors(tmp_path):
    async with Harness(
        tmp_path, navigator=StubNavigator(NavigationError("network")), location=StubLocation()
    ) as h:
        assert await h.say("arahkan ke monas") == [
            "Tidak bisa terhubung ke layanan peta. Periksa koneksi internet."
        ]
    async with Harness(
        tmp_path, navigator=StubNavigator(NavigationError("not_found")), location=StubLocation()
    ) as h:
        assert await h.say("arahkan ke xyz") == ["Aku tidak menemukan tempat bernama xyz."]
    async with Harness(tmp_path, navigator=StubNavigator(), location=StubLocation(result=None)) as h:
        assert await h.say("arahkan ke monas") == [
            "Lokasimu tidak bisa ditentukan, jadi aku tidak bisa membuat rute."
        ]
    async with Harness(tmp_path) as h:
        assert await h.say("arah berikutnya") == [
            "Belum ada rute aktif. Katakan 'arahkan ke' lalu nama tempat."
        ]
        assert await h.say("arahkan ke monas") == ["Navigasi sedang dimatikan di pengaturan."]


# -- language, questions, misc ------------------------------------------------


async def test_change_language_persists_and_switches_voice(tmp_path):
    async with Harness(tmp_path) as h:
        assert await h.say("ganti bahasa ke inggris") == ["Language changed to English."]
        assert h.assistant.tr.language == "en"
        assert h.language_changes == ["en"]
        assert h.prefs.get("language") == "en"
        assert await h.say("speak japanese") == [
            "That language is not supported yet. The options are Indonesian or English."
        ]


async def test_general_question_uses_answerer(tmp_path):
    answerer = StubAnswerer()
    async with Harness(tmp_path, answerer=answerer) as h:
        assert await h.say("Apa ibu kota Indonesia?") == ["Ibu kota Indonesia adalah Jakarta."]
        assert answerer.questions == [("Apa ibu kota Indonesia?", "id")]


async def test_general_question_failure(tmp_path):
    async with Harness(tmp_path, answerer=StubAnswerer(error=TimeoutError())) as h:
        assert await h.say("apa kabar dunia") == ["Maaf, layanan AI sedang tidak bisa dihubungi."]


async def test_sound_features_are_honestly_unavailable(tmp_path):
    async with Harness(tmp_path) as h:
        spoken = await h.say("ada rintangan?")
        assert "belum tersedia" in spoken[0] and "tongkat" in spoken[0]


class ScriptedListener:
    half_duplex = True

    def __init__(self, items):
        self.items = list(items)
        self.closed = False

    def listen(self):
        if not self.items:
            self.closed = True
            return None
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def set_language(self, language):
        pass

    def close(self):
        self.closed = True


async def test_run_loop_handles_commands_and_warns_once_when_offline(tmp_path, monkeypatch):
    async with Harness(tmp_path) as h:
        real_sleep = asyncio.sleep
        monkeypatch.setattr("aiforus.assistant.asyncio.sleep", lambda s: real_sleep(0))
        listener = ScriptedListener(
            [
                SpeechServiceError("offline"),
                SpeechServiceError("offline"),
                None,
                "bantuan",
                "matikan asisten",
                "ya",
            ]
        )
        await asyncio.wait_for(h.assistant.run(listener), 3)
        spoken = h.tts.spoken
        assert spoken[0].startswith("Asisten siap")
        assert spoken.count("Pengenalan suara tidak bisa terhubung ke internet. Periksa koneksi.") == 1
        assert spoken[-1] == "Asisten dimatikan. Sampai jumpa."
        assert not h.assistant.running
        assert listener.items == []


@pytest.mark.parametrize("utterance", ["", "   "])
async def test_empty_input_is_ignored(tmp_path, utterance):
    async with Harness(tmp_path) as h:
        assert await h.say(utterance) == []


async def test_run_in_daemon_thread_returns_and_raises():
    from aiforus.assistant import run_in_daemon_thread

    assert await run_in_daemon_thread(lambda: 42) == 42

    def boom():
        raise ValueError("x")

    with pytest.raises(ValueError):
        await run_in_daemon_thread(boom)
