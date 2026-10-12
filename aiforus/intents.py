"""Rule-based intent router for Indonesian and English voice commands.

Design notes
------------
* **Deterministic and ordered.** Safety-relevant routing must not depend on an
  LLM or on dictionary iteration order. Rules are checked top to bottom and the
  first match wins.
* **Emergency always wins.** It is checked first, on the raw utterance.
  False positives are cheap (the assistant only speaks guidance); a missed
  emergency is not.
* **Whole words only.** The old router matched substrings, so "friend"
  contained "end" and shut the app down. Every pattern here uses word
  boundaries or anchors.
* **Destructive intents are anchored.** Exiting requires the whole utterance to
  be an exit phrase, and the assistant still asks for confirmation.
* Politeness words ("tolong", "please", ...) are stripped before matching the
  remaining commands, so "tolong bacakan tulisan" is a read request, while a
  bare "tolong" is a cry for help.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum


class IntentType(str, Enum):
    EMERGENCY = "emergency"
    CONFIRM_YES = "confirm_yes"
    CONFIRM_NO = "confirm_no"
    STOP_SPEAKING = "stop_speaking"
    EXIT = "exit"
    HELP_MENU = "help_menu"
    CHANGE_LANGUAGE = "change_language"
    ENROLL_FACE = "enroll_face"
    FORGET_FACE = "forget_face"
    LIST_FACES = "list_faces"
    RECOGNIZE_FACES = "recognize_faces"
    READ_TEXT = "read_text"
    DETECT_OBJECTS = "detect_objects"
    DESCRIBE_SCENE = "describe_scene"
    DESCRIBE_DETAIL = "describe_detail"
    READ_DOCUMENT = "read_document"
    VISUAL_QUESTION = "visual_question"
    NEXT_DIRECTION = "next_direction"
    REPEAT_DIRECTION = "repeat_direction"
    NAVIGATE = "navigate"
    WHERE_AM_I = "where_am_i"
    SOUND = "sound"
    GENERAL_QUESTION = "general_question"
    EMPTY = "empty"


@dataclass(frozen=True)
class Intent:
    type: IntentType
    text: str
    slots: dict[str, str] = field(default_factory=dict)


def normalize(text: str) -> str:
    """Lowercase, unify quotes, drop punctuation (keeping apostrophes and
    hyphens inside words) and collapse whitespace."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"[^\w\s'-]", " ", text)
    text = re.sub(r"(?<!\w)['-]|['-](?!\w)", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


# --- Emergency (checked on the normalized raw utterance) -----------------

_EMERGENCY = [
    _rx(r"\b(?:darurat|sos|emergency|mayday)\b"),
    _rx(r"\b(?:minta|butuh|perlu) (?:pertolongan|bantuan segera)\b"),
    _rx(r"\b(?:aku|saya|gue|gua) (?:jatuh|terjatuh|terluka|luka|kecelakaan|tersesat|diserang)\b"),
    _rx(r"\b(?:panggil|telepon|telpon) (?:ambulans|ambulan|polisi|bantuan|pertolongan)\b"),
    _rx(r"\b(?:call (?:for )?(?:help|an ambulance|the police|911|112)|i need help|need help now)\b"),
    _rx(r"\b(?:i fell|i've fallen|i have fallen|i'm hurt|i am hurt|i'm injured|i'm lost)\b"),
    # A bare cry for help, with nothing else asked for.
    _rx(r"^(?:tolong|help|minta tolong|toloong+)(?: (?:aku|saya|me|dong|please|cepat|now))*$"),
]

# --- Anchored control phrases ---------------------------------------------

_YES = _rx(r"^(?:ya|iya|yes|yep|yup|yeah|betul|benar|oke|ok|okay|setuju)(?: (?:matikan|deh|dong|please))?$")
_NO = _rx(r"^(?:tidak|nggak|enggak|ngga|gak|ga|no|nope|batal|jangan|cancel|tidak usah|gak jadi|nggak jadi)$")
_STOP = _rx(
    r"^(?:diam|stop|berhenti|cukup|sudah|udah|hentikan|shh+|quiet|be quiet|silence|shut up)"
    r"(?: (?:dulu|bicara|ngomong|bicaranya|membaca|baca|talking|reading|speaking|it|please))?$"
)
_EXIT = _rx(
    r"^(?:matikan (?:asisten|aplikasi)|keluar(?: dari)? aplikasi|tutup aplikasi|selamat tinggal"
    r"|goodbye|good bye|exit(?: app| application)?|quit(?: app)?|shut down(?: the)?(?: assistant)?"
    r"|turn off(?: the)? assistant)$"
)

# --- Politeness stripped before the remaining rules ------------------------

_PREFIX = _rx(
    r"^(?:(?:tolong|minta tolong|coba|bisa|bisakah|bisa tolong|mohon|please|can you|could you"
    r"|would you|help me|hey|hai|halo|hi|oke|ok|asisten|assistant)\b\s*)+"
)
_SUFFIX = _rx(r"(?:\s*\b(?:dong|ya|deh|yah|please|sekarang|now|sih)\b)+$")

# --- Command rules, in priority order --------------------------------------

# Language names we recognise in requests, including ones we don't support
# yet (so the assistant can say so instead of treating it as a question).
_KNOWN_LANGS = (
    r"indonesia|indonesian|bahasa indonesia|inggris|english|spanish|spanyol|french|prancis|perancis"
    r"|german|jerman|japanese|jepang|chinese|mandarin|cina|china|arab|arabic|portuguese|portugis"
    r"|korean|korea|jawa|javanese|sunda|sundanese|malay|melayu"
)
_LANG_WORDS = r"(?P<lang>" + _KNOWN_LANGS + r"|\w+)"
_LANG_KNOWN = r"(?P<lang>" + _KNOWN_LANGS + r")"
_NAME = r"(?P<name>[\w' -]+?)"

_RULES: list[tuple[IntentType, re.Pattern[str]]] = [
    (
        IntentType.HELP_MENU,
        _rx(
            r"^(?:bantuan|menu|daftar perintah|perintah|help menu|commands|list commands|menu bantuan)$"
            r"|\b(?:apa (?:saja )?yang bisa kamu (?:lakukan|kerjakan)|kamu bisa apa(?: saja)?"
            r"|perintah apa saja|what can you do|what can i say|how do i use)\b"
        ),
    ),
    # Python's re forbids reusing a group name across alternatives, so rules
    # with several phrasings are listed once per phrasing.
    (
        IntentType.CHANGE_LANGUAGE,
        _rx(
            r"^(?:ganti|ubah|pakai|gunakan|switch|change|speak|use)\b(?: (?:the|ke|to|in|jadi|menjadi))*"
            r" (?:bahasa|language)(?: (?:ke|to|jadi|menjadi))? " + _LANG_WORDS + r"$"
        ),
    ),
    (IntentType.CHANGE_LANGUAGE, _rx(r"^(?:switch|change) to " + _LANG_KNOWN + r"$")),
    (IntentType.CHANGE_LANGUAGE, _rx(r"^(?:speak|pakai bahasa|bahasa) " + _LANG_KNOWN + r"$")),
    (
        IntentType.ENROLL_FACE,
        _rx(
            r"^(?:kenali|ingat|ingatlah|simpan|daftarkan|rekam|catat) wajah(?: (?:saya|aku|ini))?"
            r"(?: (?:sebagai|milik|bernama|namanya|si))?(?: " + _NAME + r")?$"
        ),
    ),
    (
        IntentType.ENROLL_FACE,
        _rx(r"^(?:enroll|register)(?: (?:my|the|this))?(?: face)?(?: (?:of|as|for))?(?: " + _NAME + r")?$"),
    ),
    (
        IntentType.ENROLL_FACE,
        _rx(r"^(?:remember|save|learn) (?:my |the |this )?face(?: (?:of|as|for))?(?: " + _NAME + r")?$"),
    ),
    (
        IntentType.FORGET_FACE,
        _rx(r"^(?:lupakan|hapus)(?: (?:wajah|data wajah))?(?: (?:si|milik))?(?: " + _NAME + r")?$"),
    ),
    (
        IntentType.FORGET_FACE,
        _rx(r"^(?:forget|delete|remove)(?: (?:the )?face(?: of)?)?(?: " + _NAME + r")?$"),
    ),
    (
        IntentType.LIST_FACES,
        _rx(
            r"\b(?:siapa saja yang (?:kamu|kau) kenal|(?:kamu|kau) kenal siapa saja|daftar (?:wajah|orang)"
            r"|who do you know|list (?:people|faces|known people))\b"
        ),
    ),
    (
        IntentType.RECOGNIZE_FACES,
        _rx(
            r"\b(?:siapa (?:ini|itu|dia|di depan(?: saya| aku| ku)?|yang ada di depan|di sini|di sana)"
            r"|ada siapa(?: saja)?|kenali (?:orang|wajah)(?: ini| di depan)?$|wajah siapa"
            r"|who(?: is|'s) (?:this|that|here|there|in front)|recognize (?:faces|people|this person)"
            r"|identify (?:the |this )?(?:person|people|faces))\b"
        ),
    ),
    # Vision-language model commands come before the quick YOLO/OCR ones
    # because they are more specific ("gambarkan *detail*", "baca *dokumen*").
    (
        IntentType.DESCRIBE_DETAIL,
        _rx(
            r"\b(?:jelaskan|gambarkan|deskripsikan|ceritakan|lihat)\b.*\b(?:detail|lebih detail|lengkap|rinci|secara rinci)\b"
            r"|\b(?:describe|tell me about)\b.*\b(?:in detail|in more detail|detailed)\b|\bmore detail\b"
        ),
    ),
    (
        IntentType.READ_DOCUMENT,
        _rx(
            r"\b(?:baca|bacakan|bacain|membaca)\b.*\b(?:dokumen|surat|menu|kertas|halaman|label|resep|struk|kemasan|buku|brosur)\b"
            r"|\bread\b.*\b(?:document|letter|menu|page|label|receipt|prescription|package|book)\b"
        ),
    ),
    (
        IntentType.READ_TEXT,
        _rx(
            r"\b(?:baca|bacakan|bacain|membaca|apa tulisannya|tulisannya apa|tulisan apa|read|what does (?:it|this|that) say)\b"
        ),
    ),
    (
        IntentType.DETECT_OBJECTS,
        _rx(
            r"\b(?:benda apa|ada benda|deteksi (?:benda|objek)|objek apa|barang apa"
            r"|what objects|detect objects|identify objects|what things)\b"
        ),
    ),
    (
        IntentType.DESCRIBE_SCENE,
        _rx(
            r"\b(?:apa (?:yang )?(?:ada )?di (?:depan|sekitar|sekeliling)|ada apa(?: saja)? di (?:depan|sekitar)"
            r"|gambarkan|deskripsikan|jelaskan (?:sekitar|keadaan|suasana)|lihat sekitar|apa yang kamu lihat"
            r"|describe|what do you see|what's (?:around|in front|ahead)|what is (?:around|in front)|look around)\b"
        ),
    ),
    (
        IntentType.NEXT_DIRECTION,
        _rx(
            r"\b(?:arah (?:selanjutnya|berikutnya)|langkah (?:selanjutnya|berikutnya)|lanjut(?:kan)? (?:arah|rute)"
            r"|next (?:direction|step)|guide me forward|continue (?:route|directions))\b"
        ),
    ),
    (
        IntentType.REPEAT_DIRECTION,
        _rx(
            r"\b(?:ulangi (?:arah|petunjuk|langkah)|arah (?:sekarang|saat ini)|repeat (?:the )?(?:direction|step)"
            r"|current (?:direction|step))\b"
        ),
    ),
    (
        IntentType.WHERE_AM_I,
        _rx(
            r"\b(?:(?:aku|saya) (?:di|ada di) (?:mana|manakah)|lokasi(?:ku| saya| aku)?(?: sekarang)?(?: di mana)?$"
            r"|di mana (?:aku|saya)|where am i|my location|current location)\b"
        ),
    ),
    (
        IntentType.NAVIGATE,
        _rx(
            r"^(?:arahkan|antar|antarkan|navigasi|navigasikan|tunjukkan (?:jalan|arah)|rute|cari rute|pergi"
            r"|jalan|aku mau|saya mau|aku ingin|saya ingin)(?: (?:aku|saya|kami))?(?: (?:pergi|jalan))?"
            r" (?:ke|menuju) (?P<dest>.+)$"
        ),
    ),
    (
        IntentType.NAVIGATE,
        _rx(
            r"^(?:navigate|take me|guide me|directions|route|walk|go|get me|how do i get|how to get)"
            r"(?: (?:me|us))? (?:to|towards|toward) (?P<dest>.+)$"
        ),
    ),
    (IntentType.NAVIGATE, _rx(r"^(?:navigasi|arahkan|navigate|directions|rute)$")),
    (
        IntentType.SOUND,
        _rx(
            r"\b(?:apa yang kamu dengar|suara apa|dengarkan(?: sekitar)?|ada rintangan|cek (?:jalan|depan)"
            r"|what do you hear|what sound|detect sounds|listen around|check ahead|any obstacles?|obstacles?)\b"
        ),
    ),
    # "lihat, ini uang berapa?" — a question about what the camera sees.
    # Last, so obstacle questions above get the honest "not available" answer
    # instead of a vision model's guess.
    (IntentType.VISUAL_QUESTION, _rx(r"^(?:lihat|look|lihatlah|tolong lihat)\s+(?P<question>.+)$")),
]

_LANGUAGE_CODES = {
    "indonesia": "id",
    "indonesian": "id",
    "bahasa indonesia": "id",
    "inggris": "en",
    "english": "en",
}


class IntentRouter:
    def parse(self, utterance: str) -> Intent:
        text = normalize(utterance)
        if not text:
            return Intent(IntentType.EMPTY, text)

        if any(rule.search(text) for rule in _EMERGENCY):
            return Intent(IntentType.EMERGENCY, text)
        for intent_type, rule in (
            (IntentType.CONFIRM_YES, _YES),
            (IntentType.CONFIRM_NO, _NO),
            (IntentType.STOP_SPEAKING, _STOP),
            (IntentType.EXIT, _EXIT),
        ):
            if rule.match(text):
                return Intent(intent_type, text)

        core = _SUFFIX.sub("", _PREFIX.sub("", text)).strip()
        if not core:
            # Only politeness words were said, e.g. "tolong dong".
            return Intent(IntentType.EMERGENCY, text)

        for intent_type, rule in _RULES:
            match = rule.search(core)
            if match:
                return Intent(intent_type, text, self._slots(intent_type, match))
        return Intent(IntentType.GENERAL_QUESTION, text, {"question": utterance.strip()})

    @staticmethod
    def _slots(intent_type: IntentType, match: re.Match[str]) -> dict[str, str]:
        groups = {k: v.strip() for k, v in match.groupdict().items() if v and v.strip()}
        if intent_type is IntentType.CHANGE_LANGUAGE:
            lang_word = groups.get("lang", "")
            return {"language": _LANGUAGE_CODES.get(lang_word, "unsupported"), "requested": lang_word}
        if intent_type is IntentType.NAVIGATE:
            dest = groups.get("dest")
            return {"destination": dest} if dest else {}
        if intent_type is IntentType.VISUAL_QUESTION:
            return {"question": groups.get("question", "")}
        if intent_type in (IntentType.ENROLL_FACE, IntentType.FORGET_FACE):
            name = groups.get("name")
            return {"name": name} if name else {}
        return {}
