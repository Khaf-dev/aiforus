import pytest

from aiforus.intents import IntentRouter, IntentType, normalize

router = IntentRouter()
T = IntentType


@pytest.mark.parametrize(
    "utterance, expected",
    [
        # Emergency always wins, in both languages.
        ("tolong", T.EMERGENCY),
        ("Tolong!", T.EMERGENCY),
        ("tolong dong", T.EMERGENCY),
        ("help", T.EMERGENCY),
        ("help me", T.EMERGENCY),
        ("darurat", T.EMERGENCY),
        ("saya jatuh", T.EMERGENCY),
        ("aku butuh pertolongan", T.EMERGENCY),
        ("panggil ambulans", T.EMERGENCY),
        ("I'm hurt", T.EMERGENCY),
        ("call for help", T.EMERGENCY),
        ("darurat, baca tulisan ini", T.EMERGENCY),
        # Politeness is not an emergency when a command follows.
        ("tolong bacakan tulisan ini dong", T.READ_TEXT),
        ("help me read this sign", T.READ_TEXT),
        ("please describe the scene", T.DESCRIBE_SCENE),
        # Help menu is separate from the cry for help.
        ("bantuan", T.HELP_MENU),
        ("apa saja yang bisa kamu lakukan?", T.HELP_MENU),
        ("what can you do", T.HELP_MENU),
        # Vision
        ("apa di depan?", T.DESCRIBE_SCENE),
        ("ada apa di sekitar", T.DESCRIBE_SCENE),
        ("what's in front of me", T.DESCRIBE_SCENE),
        ("benda apa saja di sekitar", T.DETECT_OBJECTS),
        ("baca tulisan", T.READ_TEXT),
        ("what does it say", T.READ_TEXT),
        # Faces
        ("siapa ini", T.RECOGNIZE_FACES),
        # Found in the Windows test: "ini siapa" went to the LLM.
        ("ini siapa", T.RECOGNIZE_FACES),
        ("Itu siapa?", T.RECOGNIZE_FACES),
        ("dia siapa ya", T.RECOGNIZE_FACES),
        ("siapa orang ini", T.RECOGNIZE_FACES),
        ("siapa pria tersebut", T.RECOGNIZE_FACES),  # Windows test: went to the LLM
        ("siapa perempuan itu", T.RECOGNIZE_FACES),
        ("orang itu siapa", T.RECOGNIZE_FACES),
        ("ini siapa yang bikin lagunya", T.GENERAL_QUESTION),
        # Second Windows test: counting people went to the LLM.
        ("ada berapa orang", T.COUNT_OBJECTS),
        ("berapa orang di depan saya", T.COUNT_OBJECTS),
        ("berapa banyak benda", T.COUNT_OBJECTS),
        ("how many people are in front of me", T.COUNT_OBJECTS),
        ("berapa orang yang tinggal di jakarta", T.GENERAL_QUESTION),
        # "apakah ada <benda>?" - fourth Windows test
        ("apakah ada sepeda motor di depan?", T.FIND_OBJECT),
        ("ada motor nggak", T.FIND_OBJECT),
        ("ada kursi di sekitar saya ya", T.FIND_OBJECT),
        ("is there a chair in front of me", T.FIND_OBJECT),
        ("do you see my phone", T.FIND_OBJECT),
        # ...without stealing other commands
        ("ada apa di depan", T.DESCRIBE_SCENE),
        ("ada siapa", T.RECOGNIZE_FACES),
        ("ada berapa orang", T.COUNT_OBJECTS),
        ("ada halangan di depan", T.SOUND),
        ("apakah ada rintangan", T.SOUND),
        ("is there any obstacle", T.SOUND),
        ("who's there?", T.RECOGNIZE_FACES),
        ("siapa saja yang kamu kenal", T.LIST_FACES),
        ("who do you know", T.LIST_FACES),
        # Navigation
        ("arah berikutnya", T.NEXT_DIRECTION),
        ("next direction", T.NEXT_DIRECTION),
        ("ulangi arah", T.REPEAT_DIRECTION),
        ("aku di mana", T.WHERE_AM_I),
        ("where am I", T.WHERE_AM_I),
        ("navigasi", T.NAVIGATE),
        # Control
        ("diam", T.STOP_SPEAKING),
        ("stop", T.STOP_SPEAKING),
        ("berhenti membaca", T.STOP_SPEAKING),
        ("matikan asisten", T.EXIT),
        ("goodbye", T.EXIT),
        ("ya", T.CONFIRM_YES),
        ("iya", T.CONFIRM_YES),
        ("tidak", T.CONFIRM_NO),
        ("batal", T.CONFIRM_NO),
        # Sound features are routed so the assistant can say they're unavailable.
        ("apa yang kamu dengar", T.SOUND),
        ("check ahead", T.SOUND),
        # Vision-language model commands
        ("jelaskan lebih detail", T.DESCRIBE_DETAIL),
        ("tolong gambarkan sekitar dengan lengkap", T.DESCRIBE_DETAIL),
        ("describe it in detail", T.DESCRIBE_DETAIL),
        ("baca dokumen ini", T.READ_DOCUMENT),
        ("bacakan menu", T.READ_DOCUMENT),
        ("read this letter", T.READ_DOCUMENT),
        ("lihat, ini uang berapa?", T.VISUAL_QUESTION),
        ("look, what color is this shirt", T.VISUAL_QUESTION),
        # ...without stealing the quick commands or the honest obstacle answer
        ("lihat sekitar", T.DESCRIBE_SCENE),
        ("gambarkan", T.DESCRIBE_SCENE),
        ("baca tulisan", T.READ_TEXT),
        ("lihat ada rintangan", T.SOUND),
        ("", T.EMPTY),
        ("   ", T.EMPTY),
    ],
)
def test_routing(utterance, expected):
    assert router.parse(utterance).type is expected


@pytest.mark.parametrize(
    "utterance",
    [
        # Regressions from the old substring router.
        "is my friend here",  # "friend" contained "end" -> exit
        "is the door closed",  # "closed" contained "close" -> exit
        "can you stop by the store later",
        "please end the description",
        "speak louder",  # used to trigger language switching
        "remember to buy milk",  # used to trigger face enrollment
    ],
)
def test_substrings_no_longer_trigger_exit_or_side_effects(utterance):
    intent = router.parse(utterance)
    assert intent.type not in {T.EXIT, T.ENROLL_FACE, T.CHANGE_LANGUAGE}


def test_exit_requires_whole_phrase():
    assert router.parse("matikan asisten").type is T.EXIT
    assert router.parse("jangan matikan asisten").type is not T.EXIT


@pytest.mark.parametrize(
    "utterance, language",
    [
        ("ganti bahasa ke inggris", "en"),
        ("ubah bahasa menjadi indonesia", "id"),
        ("change language to Indonesian", "id"),
        ("switch to english", "en"),
        ("speak japanese", "unsupported"),
        ("bahasa jepang", "unsupported"),
    ],
)
def test_language_slots(utterance, language):
    intent = router.parse(utterance)
    assert intent.type is T.CHANGE_LANGUAGE
    assert intent.slots["language"] == language


@pytest.mark.parametrize(
    "utterance, expected_type, name",
    [
        ("kenali wajah sebagai Budi Santoso", T.ENROLL_FACE, "budi santoso"),
        ("simpan wajah Siti", T.ENROLL_FACE, "siti"),
        ("enroll John", T.ENROLL_FACE, "john"),
        ("register face as Sarah", T.ENROLL_FACE, "sarah"),
        ("lupakan Budi", T.FORGET_FACE, "budi"),
        ("hapus wajah Siti", T.FORGET_FACE, "siti"),
        ("forget John", T.FORGET_FACE, "john"),
    ],
)
def test_face_name_slots(utterance, expected_type, name):
    intent = router.parse(utterance)
    assert intent.type is expected_type
    assert intent.slots["name"] == name


def test_enroll_without_name_has_no_slot():
    intent = router.parse("kenali wajah")
    assert intent.type is T.ENROLL_FACE
    assert "name" not in intent.slots


@pytest.mark.parametrize(
    "utterance, destination",
    [
        ("arahkan aku ke Monas", "monas"),
        ("tolong antarkan saya ke stasiun Gambir", "stasiun gambir"),
        ("take me to the train station", "the train station"),
        ("how do I get to Blok M", "blok m"),
    ],
)
def test_navigation_destination(utterance, destination):
    intent = router.parse(utterance)
    assert intent.type is T.NAVIGATE
    assert intent.slots["destination"] == destination


def test_unknown_goes_to_general_question_with_original_text():
    intent = router.parse("Berapa suhu hari ini?")
    assert intent.type is T.GENERAL_QUESTION
    assert intent.slots["question"] == "Berapa suhu hari ini?"


def test_normalize():
    assert normalize("  Who’s THERE?! ") == "who's there"
    assert normalize("layang-layang") == "layang-layang"


def test_visual_question_slot():
    intent = router.parse("Coba lihat, baju ini warna apa?")
    assert intent.type is T.VISUAL_QUESTION
    assert intent.slots["question"] == "baju ini warna apa"


def test_count_slot_says_whether_people_were_asked_for():
    assert router.parse("ada berapa orang").slots == {"label": "person"}
    assert router.parse("how many people").slots == {"label": "person"}
    assert router.parse("ada berapa benda").slots == {}


def test_find_slot_is_the_object_name():
    assert router.parse("apakah ada sepeda motor di depan?").slots == {"thing": "sepeda motor"}
    assert router.parse("ada motor nggak").slots == {"thing": "motor"}
    assert router.parse("is there a chair in front of me").slots == {"thing": "a chair"}


# -- the assistant's name ("Nemo") ----------------------------------------------


@pytest.mark.parametrize(
    "utterance, expected",
    [
        ("Nemo, apa di depan?", T.DESCRIBE_SCENE),
        ("hai nemo apa di depan", T.DESCRIBE_SCENE),
        ("Halo Nemo, siapa ini", T.RECOGNIZE_FACES),
        ("nemo tolong", T.EMERGENCY),  # the name never hides an emergency
        ("nemo darurat", T.EMERGENCY),
        ("nemo diam", T.STOP_SPEAKING),
        ("nemo ya", T.CONFIRM_YES),
        ("matikan nemo", T.EXIT),
        ("Nemo", T.ATTENTION),
        ("hai nemo", T.ATTENTION),
        ("film finding nemo bagus nggak", T.GENERAL_QUESTION),  # the name mid-sentence is just a word
    ],
)
def test_assistant_name(utterance, expected):
    assert router.parse(utterance).type is expected


def test_other_name_from_config():
    other = IntentRouter(("Sinta",))
    assert other.parse("hai sinta apa di depan").type is T.DESCRIBE_SCENE
    assert other.parse("nemo apa di depan").type is T.DESCRIBE_SCENE  # "apa di depan" still matches
    assert other.parse("matikan sinta").type is T.EXIT
    assert other.parse("sinta").type is T.ATTENTION
