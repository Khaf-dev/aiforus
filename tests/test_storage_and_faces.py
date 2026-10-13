import numpy as np
import pytest

from aiforus.services.faces import EnrollStatus, FaceService, normalize_name
from aiforus.storage import Database, PreferenceStore, SqlFaceStore
from tests.fakes import textured_frame


class FakeEncoder:
    def __init__(self):
        self.next: list[np.ndarray] = []

    def encode(self, frame):
        return list(self.next)


def vec(*values):
    v = np.zeros(128)
    v[: len(values)] = values
    return v


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "data" / "test.db")
    yield database
    database.close()


@pytest.fixture
def faces(db):
    encoder = FakeEncoder()
    service = FaceService(encoder, SqlFaceStore(db), match_threshold=0.5, max_samples_per_person=2)
    return service, encoder


def test_preferences_roundtrip(db):
    prefs = PreferenceStore(db)
    assert prefs.get("language", "id") == "id"
    prefs.set("language", "en")
    prefs.set("language", "id")
    assert prefs.get("language") == "id"


def test_vectors_roundtrip_without_pickle(db, tmp_path):
    store = SqlFaceStore(db)
    original = np.linspace(-1, 1, 128)
    assert store.add("Budi", original) == 1
    restored = store.all()["Budi"][0]
    np.testing.assert_array_equal(restored, original)
    assert not list(tmp_path.rglob("*.pkl"))


def test_names_are_case_insensitive(db):
    store = SqlFaceStore(db)
    store.add("Budi", vec(1))
    assert store.add("budi", vec(2)) == 2
    assert store.names() == ["Budi"]
    assert store.remove("BUDI") is True
    assert store.names() == []
    assert store.count("Budi") == 0


def test_rejects_bad_vectors(db):
    with pytest.raises(ValueError):
        SqlFaceStore(db).add("x", np.zeros((2, 2)))


def test_enroll_then_identify(faces):
    service, encoder = faces
    encoder.next = [vec(1.0)]
    result = service.enroll("budi santoso", textured_frame())
    assert result.status is EnrollStatus.OK
    assert result.name == "Budi Santoso"
    assert result.samples == 1

    encoder.next = [vec(1.1), vec(5.0)]  # Budi (close) and a stranger (far)
    matches = service.identify(textured_frame())
    assert [m.name for m in matches] == ["Budi Santoso", None]


def test_enroll_refuses_multiple_faces_and_no_face(faces):
    service, encoder = faces
    encoder.next = [vec(1), vec(2)]
    assert service.enroll("Budi", textured_frame()).status is EnrollStatus.MULTIPLE_FACES
    encoder.next = []
    assert service.enroll("Budi", textured_frame()).status is EnrollStatus.NO_FACE
    assert service.known_people() == []


def test_enroll_respects_max_samples(faces):
    service, encoder = faces
    encoder.next = [vec(1)]
    service.enroll("Budi", textured_frame())
    service.enroll("Budi", textured_frame())
    result = service.enroll("Budi", textured_frame())
    assert result.status is EnrollStatus.FULL
    assert result.samples == 2


def test_forget(faces):
    service, encoder = faces
    encoder.next = [vec(1)]
    service.enroll("Siti", textured_frame())
    assert service.forget("siti") == (True, "Siti")
    assert service.forget("siti") == (False, "Siti")


def test_identify_with_no_known_people(faces):
    service, encoder = faces
    encoder.next = [vec(1)]
    assert [m.name for m in service.identify(textured_frame())] == [None]


@pytest.mark.parametrize(
    "raw, expected",
    [("budi  santoso!", "Budi Santoso"), ("  ", ""), ("o'neil", "O'neil"), ("siti-nur", "Siti-nur")],
)
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected
