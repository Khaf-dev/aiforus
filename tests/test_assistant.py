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
from tests.fakes import FakeCamera, FakeTTS, centered_boxes, flat_frame, textured_frame, wait_until
from tests.test_navigation import OSRM_SAMPLE

# "One moment" acknowledgements may or may not be spoken depending on timing.
ACKS = {MESSAGES[lang][key] for lang in MESSAGES for key in ("looking", "nav_searching", "vlm_looking")}
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

    face_boxes: list | None = None  # boxes for encode_faces; default: centred

    def encode_faces(self, frame):
        encodings = self.encode(frame)
        boxes = self.face_boxes or centered_boxes(frame, len(encodings))
        return list(zip(boxes, encodings, strict=True))

    boxes: list = []

    def detect(self, frame):
        return list(self.boxes)


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


class StubVLM:
    def __init__(self, reply="Ruang kerja dengan meja dan laptop di jam 12.", error=None, delay=0.0):
        self.reply, self.error, self.delay = reply, error, delay
        self.calls = []

    async def look(self, image_jpeg, task, language, question=None):
        self.calls.append((image_jpeg, task, language, question))
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.reply


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
        vlm=None,
        vlm_is_remote=False,
        monitor=None,
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
            vlm=vlm,
            vlm_is_remote=vlm_is_remote,
            prefs=self.prefs,
            on_language_change=self.language_changes.append,
            monitor=monitor,
        )
        self.assistant.ENROLL_SETTLE_S = 0
        self.assistant.ENROLL_FRAME_INTERVAL_S = 0
        self.assistant.LLM_TIMEOUT_MARGIN_S = 0
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


@pytest.mark.parametrize(
    "face_px, expected",
    [(240, "Orang di jam 12, kurang dari 1 meter."), (120, "Orang di jam 12, sekitar 1,5 meter.")],
)
async def test_person_cut_off_by_frame_is_measured_by_face(tmp_path, face_px, expected):
    body = Detection("person", 0.9, (500, 0, 800, 720))
    async with Harness(tmp_path, frames=[textured_frame(size=HD)], labels=[body], texts=[]) as h:
        h.encoder.boxes = [(600, 80, face_px * 0.8, face_px)]
        assert await h.say("apa di depan") == [expected]


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
        assert spoken == [
            "Aku melihat 2 wajah.",
            "Budi di jam 12.",
            "Orang yang belum aku kenal di jam 12.",
        ]

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


# -- vision-language model ------------------------------------------------------


@pytest.fixture
def fake_jpeg(monkeypatch):
    sizes = []

    def encode(frame, max_side):
        sizes.append(max_side)
        return b"jpeg"

    monkeypatch.setattr("aiforus.assistant.encode_jpeg", encode)
    return sizes


async def test_describe_in_detail_uses_vlm(tmp_path, fake_jpeg):
    from aiforus.services.llm import VisionTask

    vlm = StubVLM()
    async with Harness(tmp_path, vlm=vlm) as h:
        assert await h.say("jelaskan lebih detail") == ["Ruang kerja dengan meja dan laptop di jam 12."]
    assert vlm.calls == [(b"jpeg", VisionTask.DESCRIBE, "id", None)]
    assert fake_jpeg == [1024]


async def test_read_document_and_visual_question(tmp_path, fake_jpeg):
    from aiforus.services.llm import VisionTask

    vlm = StubVLM(reply="Lima puluh ribu rupiah.")
    async with Harness(tmp_path, vlm=vlm) as h:
        await h.say("bacakan menu ini")
        assert await h.say("lihat, ini uang berapa?") == ["Lima puluh ribu rupiah."]
    assert [c[1] for c in vlm.calls] == [VisionTask.READ_DOCUMENT, VisionTask.QUESTION]
    assert vlm.calls[1][3] == "ini uang berapa"


async def test_cloud_vlm_is_announced_every_time(tmp_path, fake_jpeg):
    async with Harness(tmp_path, vlm=StubVLM(reply="Ok."), vlm_is_remote=True) as h:
        assert await h.say("jelaskan lebih detail") == ["Fotonya aku kirim ke layanan AI di internet.", "Ok."]


async def test_vlm_unavailable_error_and_camera_problems(tmp_path, fake_jpeg):
    async with Harness(tmp_path) as h:
        assert await h.say("jelaskan lebih detail") == [
            "Penjelasan detail belum tersedia. Model penglihatan belum diatur."
        ]
    async with Harness(tmp_path, vlm=StubVLM(error=ConnectionError("down"))) as h:
        assert await h.say("baca dokumen") == [
            "Maaf, model penglihatan tidak bisa dihubungi atau terlalu lama menjawab."
        ]
    async with Harness(tmp_path, vlm=StubVLM(delay=1.0)) as h:
        h.settings.llm.vision_timeout_s = 0.05
        assert await h.say("jelaskan lebih detail") == [
            "Maaf, model penglihatan tidak bisa dihubungi atau terlalu lama menjawab."
        ]
    async with Harness(tmp_path, frames=[flat_frame(3)], vlm=StubVLM()) as h:
        assert await h.say("jelaskan lebih detail") == [
            "Gambar terlalu gelap. Aku tidak bisa melihat dengan jelas."
        ]
    async with Harness(tmp_path, vlm=StubVLM(reply="")) as h:
        assert await h.say("jelaskan lebih detail") == ["Aku tidak bisa menjelaskan gambar ini."]


# -- OCR found nothing ----------------------------------------------------------


async def test_unreadable_text_falls_back_to_the_vision_model(tmp_path, fake_jpeg):
    """The Windows test: EasyOCR read nothing on a shop sign the VLM could read."""
    from aiforus.services.llm import VisionTask

    vlm = StubVLM(reply="Tulisannya: WARUNG OP MAMANG.")
    frame = textured_frame()
    async with Harness(tmp_path, frames=[frame], texts=[], vlm=vlm) as h:
        camera = h.assistant.vision.camera
        assert await h.say("baca tulisan") == [
            "Tulisannya tidak terbaca dengan cara cepat. Aku coba lihat lebih teliti.",
            "Tulisannya: WARUNG OP MAMANG.",
        ]
        assert camera.captures == 1  # the same photo, not a new one
    assert [c[1] for c in vlm.calls] == [VisionTask.READ_DOCUMENT]


async def test_unreadable_text_hint_mode_and_off(tmp_path, fake_jpeg):
    vlm = StubVLM()
    async with Harness(tmp_path, texts=[], vlm=vlm) as h:
        h.settings.vision.ocr_fallback = "hint"
        assert await h.say("baca tulisan") == [
            "Aku tidak menemukan tulisan yang bisa dibaca.",
            "Coba katakan 'baca dokumen' supaya aku membaca lebih teliti.",
        ]
        h.settings.vision.ocr_fallback = "off"
        assert await h.say("baca tulisan") == ["Aku tidak menemukan tulisan yang bisa dibaca."]
    assert vlm.calls == []


async def test_unreadable_text_without_vision_model_says_so_plainly(tmp_path):
    async with Harness(tmp_path, texts=[]) as h:
        for mode in ("vlm", "hint"):
            h.settings.vision.ocr_fallback = mode
            assert await h.say("baca tulisan") == ["Aku tidak menemukan tulisan yang bisa dibaca."]


async def test_unreadable_text_fallback_to_cloud_model_is_announced(tmp_path, fake_jpeg):
    async with Harness(tmp_path, texts=[], vlm=StubVLM(reply="Ok."), vlm_is_remote=True) as h:
        spoken = await h.say("baca tulisan")
        assert "Fotonya aku kirim ke layanan AI di internet." in spoken
        assert spoken[-1] == "Ok."


# -- where people are --------------------------------------------------------


def face_at(distance_m, center_x=640, face_height_m=0.21):
    """A face box (x, y, w, h) ``distance_m`` away in an HD frame."""
    h = face_height_m * FOCAL_PX / distance_m
    return (center_x - h * 0.4, 200, h * 0.8, h)


async def test_people_are_placed_known_first_and_nearest_first(tmp_path):
    async with Harness(tmp_path, frames=[textured_frame(size=HD)]) as h:
        h.assistant.faces.add_samples("Kaffa", [v(1)])
        h.assistant.faces.add_samples("Siti", [v(3)])
        h.encoder.next = [v(9), v(3), v(1)]  # stranger, Siti, Kaffa (left to right)
        h.encoder.face_boxes = [face_at(3, 200), face_at(2.5, 640), face_at(0.8, 1100)]
        assert await h.say("ini siapa") == [
            "Aku melihat 3 wajah.",
            "Kaffa di jam 1, kurang dari 1 meter.",
            "Siti di jam 12, sekitar 2,5 meter.",
            "Orang yang belum aku kenal di jam 11, sekitar 3 meter.",
        ]


async def test_many_strangers_are_counted_not_placed(tmp_path):
    async with Harness(tmp_path, frames=[textured_frame(size=HD)], language="en") as h:
        h.encoder.next = [v(7), v(8), v(9)]
        h.encoder.face_boxes = [face_at(2, x) for x in (300, 640, 1000)]
        assert await h.say("who is this") == ["I see 3 faces.", "3 people I don't know yet."]


async def test_known_face_in_english_with_distance(tmp_path):
    async with Harness(tmp_path, frames=[textured_frame(size=HD)], language="en") as h:
        h.assistant.faces.add_samples("Kaffa", [v(1)])
        h.encoder.next = [v(1)]
        h.encoder.face_boxes = [face_at(2)]
        assert await h.say("who is this") == ["I see one face.", "Kaffa at 12 o'clock, about 2 meters."]


# -- live view (--preview) --------------------------------------------------------


class RecordingMonitor:
    def __init__(self, fail=False):
        self.heard_texts, self.answers, self.fail = [], [], fail

    def heard(self, text):
        self.heard_texts.append(text)

    def said(self, text):
        pass

    def answered(self, frame, marks):
        if self.fail:
            raise RuntimeError("window closed")
        self.answers.append((frame.shape, [(m.text, m.kind.value) for m in marks]))


async def test_monitor_sees_command_photo_and_marks(tmp_path):
    monitor = RecordingMonitor()
    labels = [at("chair", 2, center_x=1100), at("person", 3)]
    async with Harness(
        tmp_path, frames=[textured_frame(size=HD)], labels=labels, texts=[], monitor=monitor
    ) as h:
        await h.say("apa di depan")
    assert monitor.heard_texts == ["apa di depan"]
    shape, marks = monitor.answers[0]
    assert shape == (*HD, 3)
    assert ("kursi | jam 1 | ~2 m", "object") in marks
    assert ("orang | jam 12 | ~3 m", "object") in marks


async def test_monitor_gets_named_faces(tmp_path):
    monitor = RecordingMonitor()
    async with Harness(tmp_path, frames=[textured_frame(size=HD)], monitor=monitor) as h:
        h.assistant.faces.add_samples("Kaffa", [v(1)])
        h.encoder.next = [v(1), v(9)]
        h.encoder.face_boxes = [face_at(2, 640), face_at(3, 200)]
        await h.say("siapa ini")
    _, marks = monitor.answers[-1]
    assert marks == [("Kaffa | jam 12 | ~2 m", "known"), ("belum dikenal | jam 11 | ~3 m", "unknown")]


async def test_broken_monitor_never_breaks_an_answer(tmp_path):
    async with Harness(
        tmp_path,
        frames=[textured_frame(size=HD)],
        labels=[at("chair", 2)],
        texts=[],
        monitor=RecordingMonitor(fail=True),
    ) as h:
        assert await h.say("benda apa") == ["Kursi di jam 12, sekitar 2 meter."]


# -- counting ------------------------------------------------------------------


async def test_count_people_gives_the_number_first(tmp_path):
    """Third Windows test: "ada berapa orang" listed places but no number."""
    labels = [at("person", 3), at("person", 2, center_x=1000), at("chair", 2, center_x=200)]
    async with Harness(tmp_path, frames=[textured_frame(size=HD)], labels=labels, texts=[]) as h:
        spoken = await h.say("ada berapa orang")
        assert spoken[0] == "Aku melihat 2 orang."
        assert "Kursi" not in spoken[1] and spoken[1].startswith("Orang di jam 1")


async def test_count_people_never_says_nobody_is_there(tmp_path):
    async with Harness(
        tmp_path, frames=[textured_frame(size=HD)], labels=[at("chair", 2)], texts=[], language="en"
    ) as h:
        assert await h.say("how many people") == ["I don't see anyone on the camera."]
        h.assistant.vision.detector.items = [at("person", 3)]
        assert await h.say("how many people") == [
            "I see one person.",
            "Person at 12 o'clock, about 3 meters.",
        ]


async def test_count_objects(tmp_path):
    labels = [at("chair", 2, center_x=200), at("cup", 1.2, real_height=0.1)]
    async with Harness(tmp_path, frames=[textured_frame(size=HD)], labels=labels, texts=[]) as h:
        spoken = await h.say("ada berapa benda")
        assert spoken[0] == "Aku melihat 2 benda."


# -- "apakah ada ...?" -------------------------------------------------------------


async def test_find_object_says_where_it_is(tmp_path):
    labels = [at("motorcycle", 2.5), at("chair", 2, center_x=200)]
    async with Harness(tmp_path, frames=[textured_frame(size=HD)], labels=labels, texts=[]) as h:
        assert await h.say("apakah ada sepeda motor di depan?") == [
            "Ya. Sepeda motor di jam 12, sekitar 2,5 meter."
        ]
        assert await h.say("ada motor nggak") == ["Ya. Sepeda motor di jam 12, sekitar 2,5 meter."]


async def test_find_object_never_claims_it_is_absent(tmp_path):
    async with Harness(tmp_path, frames=[textured_frame(size=HD)], labels=[at("chair", 2)], texts=[]) as h:
        assert await h.say("apakah ada sepeda motor") == [
            "Aku tidak melihat sepeda motor di kamera. Itu bukan berarti tidak ada."
        ]


async def test_find_unknown_object_asks_the_vision_model(tmp_path, fake_jpeg):
    from aiforus.services.llm import VisionTask

    vlm = StubVLM(reply="Ya, ada kunci di meja, di arah jam 1.")
    async with Harness(tmp_path, vlm=vlm) as h:
        assert await h.say("apakah ada kunci di meja") == ["Ya, ada kunci di meja, di arah jam 1."]
    assert vlm.calls[0][1] is VisionTask.QUESTION
    assert vlm.calls[0][3] == "apakah ada kunci di meja"


async def test_find_unknown_object_without_vision_model(tmp_path):
    async with Harness(tmp_path, language="en") as h:
        assert await h.say("is there a key") == [
            "I can't search for a key quickly yet. Try saying 'describe it in detail'."
        ]


async def test_find_object_in_english(tmp_path):
    async with Harness(
        tmp_path, frames=[textured_frame(size=HD)], labels=[at("chair", 2)], texts=[], language="en"
    ) as h:
        assert await h.say("is there a chair in front of me") == ["Yes. Chair at 12 o'clock, about 2 meters."]
        h.assistant.vision.detector.items = []
        assert await h.say("are there any buses") == [
            "I don't see any buses on the camera. That doesn't mean there isn't one."
        ]
