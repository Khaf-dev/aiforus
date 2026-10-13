import string

import pytest

from aiforus.i18n import Translator
from aiforus.locales import COCO_LABELS_ID, MESSAGES


def _fields(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_catalogs_have_identical_keys():
    assert set(MESSAGES["id"]) == set(MESSAGES["en"])


@pytest.mark.parametrize("key", sorted(MESSAGES["id"]))
def test_placeholders_match_across_languages(key):
    assert _fields(MESSAGES["id"][key]) == _fields(MESSAGES["en"][key])


def test_all_80_coco_labels_translated():
    assert len(COCO_LABELS_ID) == 80


def test_join_and_counts():
    id_ = Translator("id")
    en = Translator("en")
    assert id_.join(["a", "b", "c"]) == "a, b, dan c"
    assert en.join(["a", "b", "c"]) == "a, b and c"
    assert id_.join(["a", "b"]) == "a dan b"
    assert id_.count_label("person", 2) == "2 orang"
    assert en.count_label("person", 2) == "2 people"
    assert en.count_label("bus", 3) == "3 buses"
    assert en.count_label("chair", 1) == "1 chair"


def test_distance_formatting():
    id_ = Translator("id")
    en = Translator("en")
    assert id_.distance(123) == "120 meter"
    assert id_.distance(1500) == "1,5 kilometer"
    assert en.distance(1500) == "1.5 kilometers"
    assert en.distance(2000) == "2 kilometers"
    assert id_.distance(3) == "3 meter"


def test_missing_key_does_not_crash():
    assert Translator("id").t("does_not_exist") == "does_not_exist"


def test_rejects_unsupported_language():
    with pytest.raises(ValueError):
        Translator("fr")


def test_find_labels_maps_everyday_words_to_detector_labels():
    tr = Translator("id")
    assert tr.find_labels("sepeda motor") == ("motorcycle",)
    assert tr.find_labels("motor") == ("motorcycle",)
    assert tr.find_labels("sebuah kursi") == ("chair",)
    assert tr.find_labels("kursi-kursi") == ("chair",)
    assert tr.find_labels("hp") == ("cell phone",)
    assert tr.find_labels("tas") == ("backpack", "handbag", "suitcase")
    assert tr.find_labels("kunci") == ()  # not something the detector knows
    en = Translator("en")
    assert en.find_labels("a chair") == ("chair",)
    assert en.find_labels("any chairs") == ("chair",)
    assert en.find_labels("buses") == ("bus",)
    assert en.find_labels("people") == ("person",)
    assert en.find_labels("my keys") == ()
