"""The assistant: turns recognised intents into actions and speech.

All dependencies are injected, so this module never imports hardware or ML
libraries and is fully testable with fakes. Optional components may be None;
the assistant then says the feature isn't available instead of crashing.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import threading
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import numpy as np

from .config import SUPPORTED_LANGUAGES, Settings
from .hal.location import Location, LocationProvider
from .hal.stt import SpeechInput, SpeechServiceError
from .i18n import Translator
from .intents import Intent, IntentRouter, IntentType
from .monitor import Mark, Monitor, face_marks, object_marks, text_marks
from .services.faces import EnrollStatus, FaceMatch, FaceService, normalize_name
from .services.imaging import encode_jpeg
from .services.llm import Answerer, VisionAnswerer, VisionTask
from .services.navigation import NavigationError, NavigationSession, Navigator, describe_step
from .services.presence import Presence, Verdict, bare_name, tidy_detail
from .services.spatial import face_position, group_placements, place, with_face_distances
from .services.vision import Look, VisionService, VisionStatus, summarize
from .speech import Priority, SpeechQueue
from .storage import PreferenceStore

logger = logging.getLogger(__name__)

Handler = Callable[[Intent], Awaitable[None]]
T = TypeVar("T")


def run_in_daemon_thread(fn: Callable[[], T]) -> asyncio.Future[T]:
    """Like ``asyncio.to_thread`` but on a daemon thread.

    Executor threads are joined at interpreter exit, so a listener blocked in
    ``input()`` or on the microphone would keep the process alive after
    Ctrl+C. A daemon thread doesn't.
    """
    loop = asyncio.get_running_loop()
    future: asyncio.Future[T] = loop.create_future()

    def deliver(setter: Callable[[Any], None], value: Any) -> None:
        if not future.done():
            setter(value)

    def target() -> None:
        try:
            result = fn()
        except BaseException as exc:  # forwarded to the awaiting task
            with contextlib.suppress(RuntimeError):  # loop already closed
                loop.call_soon_threadsafe(deliver, future.set_exception, exc)
        else:
            with contextlib.suppress(RuntimeError):
                loop.call_soon_threadsafe(deliver, future.set_result, result)

    threading.Thread(target=target, name="listener", daemon=True).start()
    return future


# "apakah ada kunci di meja" / "is there a key" inside a "lihat, ..." question.
_PRESENCE_QUESTION = re.compile(
    r"^(?:(?:apakah|apa) )?ada (?!apa\b|siapa\b|berapa\b)(?P<thing>.+?)(?: (?:ya|nggak|gak|tidak))?$"
    r"|^(?:is there|are there) (?P<thing_en>.+)$",
    re.IGNORECASE,
)

_VISION_PROBLEMS = {
    VisionStatus.UNAVAILABLE: "vision_unavailable",
    VisionStatus.NO_CAMERA: "camera_unavailable",
    VisionStatus.DARK: "camera_dark",
    VisionStatus.BLANK: "camera_blocked",
}


class Assistant:
    STT_WARNING_INTERVAL_S = 60.0
    LOCATION_TIMEOUT_S = 5.0
    ENROLL_SETTLE_S = 1.0  # pause between "hold still" and taking the photos
    ENROLL_FRAME_INTERVAL_S = 0.25  # gap between enrollment frames
    # The LLM client enforces the configured timeouts itself; ours is only a
    # safety net, a little later so the client's clearer error wins.
    LLM_TIMEOUT_MARGIN_S = 2.0

    def __init__(
        self,
        *,
        settings: Settings,
        speech: SpeechQueue,
        translator: Translator,
        router: IntentRouter | None = None,
        vision: VisionService | None = None,
        faces: FaceService | None = None,
        navigator: Navigator | None = None,
        location: LocationProvider | None = None,
        answerer: Answerer | None = None,
        vlm: VisionAnswerer | None = None,
        vlm_is_remote: bool = False,
        prefs: PreferenceStore | None = None,
        on_language_change: Callable[[str], object] | None = None,
        monitor: Monitor | None = None,
        listening_mode: str = "text",
        push_to_talk_label: str | None = None,
    ) -> None:
        self.settings = settings
        self.speech = speech
        self.tr = translator
        self.router = router or IntentRouter((settings.app.assistant_name,))
        self.vision = vision
        self.faces = faces
        self.navigator = navigator
        self.location = location
        self.answerer = answerer
        self.vlm = vlm
        # Remote = images leave the machine; the user is told every time.
        self.vlm_is_remote = vlm_is_remote
        self.prefs = prefs
        self._on_language_change = on_language_change
        # Optional live view (--preview); never affects what is spoken.
        self.monitor = monitor
        # How the user gets the assistant's attention, for the spoken hints:
        # "text" | "always" | "wake_word" | "push_to_talk".
        self.listening_mode = listening_mode
        self.push_to_talk_label = push_to_talk_label

        self.running = True
        self.navigation: NavigationSession | None = None
        self._pending_exit = False
        self._last_stt_warning = float("-inf")
        self._handlers: dict[IntentType, Handler] = {
            IntentType.EMERGENCY: self._emergency,
            IntentType.CONFIRM_YES: self._nothing_to_confirm,
            IntentType.CONFIRM_NO: self._nothing_to_confirm,
            IntentType.STOP_SPEAKING: self._stop_speaking,
            IntentType.EXIT: self._ask_exit,
            IntentType.HELP_MENU: self._help,
            IntentType.ATTENTION: self._attention,
            IntentType.CHANGE_LANGUAGE: self._change_language,
            IntentType.DESCRIBE_SCENE: self._describe_scene,
            IntentType.DETECT_OBJECTS: self._detect_objects,
            IntentType.COUNT_OBJECTS: self._count_objects,
            IntentType.FIND_OBJECT: self._find_object,
            IntentType.READ_TEXT: self._read_text,
            IntentType.DESCRIBE_DETAIL: self._describe_detail,
            IntentType.READ_DOCUMENT: self._read_document,
            IntentType.VISUAL_QUESTION: self._visual_question,
            IntentType.RECOGNIZE_FACES: self._recognize_faces,
            IntentType.ENROLL_FACE: self._enroll_face,
            IntentType.FORGET_FACE: self._forget_face,
            IntentType.LIST_FACES: self._list_faces,
            IntentType.NAVIGATE: self._navigate,
            IntentType.NEXT_DIRECTION: self._next_direction,
            IntentType.REPEAT_DIRECTION: self._repeat_direction,
            IntentType.WHERE_AM_I: self._where_am_i,
            IntentType.SOUND: self._sound,
            IntentType.GENERAL_QUESTION: self._general_question,
        }

    # -- helpers -----------------------------------------------------------

    def say(self, key: str, priority: Priority = Priority.HIGH, **params: object) -> asyncio.Future[bool]:
        return self.speech.say(self.tr.t(key, **params), priority)

    async def _locate(self) -> Location | None:
        if self.location is None:
            return None
        try:
            return await asyncio.wait_for(asyncio.to_thread(self.location.locate), self.LOCATION_TIMEOUT_S)
        except asyncio.TimeoutError:
            logger.warning("Location lookup timed out")
            return None

    def _show(self, frame: np.ndarray | None, marks: list[Mark] | None = None) -> None:
        """Report the photo behind an answer to the live view, if any."""
        if self.monitor is None or frame is None:
            return
        try:
            self.monitor.answered(frame, marks or [])
        except Exception:  # a display problem must never break an answer
            logger.exception("Monitor failed")

    def _discard(self, ack: asyncio.Future[bool] | None) -> None:
        if ack is not None:
            self.speech.discard(ack)

    def _vision_problem(self, status: VisionStatus) -> bool:
        key = _VISION_PROBLEMS.get(status)
        if key is None:
            return False
        self.say(key)
        return True

    # -- main loop ---------------------------------------------------------

    async def run(self, listener: SpeechInput) -> None:
        self.say("ready", Priority.NORMAL, name=self.settings.app.assistant_name)
        hint = self._listening_hint()
        if hint:
            self.speech.say(hint, Priority.NORMAL)
        while self.running and not listener.closed:
            if listener.half_duplex:
                # Don't transcribe our own voice.
                await self.speech.wait_idle()
            try:
                text = await run_in_daemon_thread(listener.listen)
            except SpeechServiceError as exc:
                logger.warning("Speech recognition service error: %s", exc)
                now = time.monotonic()
                if now - self._last_stt_warning > self.STT_WARNING_INTERVAL_S:
                    self._last_stt_warning = now
                    self.say("stt_offline", Priority.HIGH)
                await asyncio.sleep(2)
                continue
            except Exception:
                logger.exception("Listening failed")
                await asyncio.sleep(1)
                continue
            if text:
                await self.handle(text)
        await self.speech.wait_idle()

    async def handle(self, utterance: str) -> None:
        if self.monitor is not None and utterance.strip():
            with contextlib.suppress(Exception):
                self.monitor.heard(utterance)
        intent = self.router.parse(utterance)
        logger.debug("INTENT %s %s", intent.type.value, intent.slots or "")
        if intent.type is IntentType.EMPTY:
            return

        if self._pending_exit:
            self._pending_exit = False
            if intent.type is IntentType.CONFIRM_YES:
                await self._exit()
                return
            if intent.type is IntentType.CONFIRM_NO:
                self.say("exit_cancelled")
                return
            # Anything else cancels the pending exit and is handled normally.

        handler = self._handlers.get(intent.type)
        if handler is None:
            self.say("unknown")
            return
        try:
            await handler(intent)
        except Exception:
            logger.exception("Handler for %s failed", intent.type.value)
            self.say("error")

    # -- control -----------------------------------------------------------

    async def _emergency(self, intent: Intent) -> None:
        number = self.settings.emergency.local_emergency_number
        # Speak immediately; never wait on the network before giving guidance.
        message = " ".join(
            [
                self.tr.t("emergency_start"),
                self.tr.t("emergency_no_send"),
                self.tr.t("emergency_call", number=number),
            ]
        )
        self.speech.say(message, Priority.CRITICAL)
        location = await self._locate()
        if location is not None:
            self.speech.say(
                self.tr.t("emergency_location", address=location.label), Priority.CRITICAL, flush=False
            )
        else:
            self.speech.say(self.tr.t("emergency_location_unknown"), Priority.CRITICAL, flush=False)

    async def _nothing_to_confirm(self, intent: Intent) -> None:
        self.say("nothing_to_confirm")

    async def _stop_speaking(self, intent: Intent) -> None:
        self.speech.stop_all()

    async def _ask_exit(self, intent: Intent) -> None:
        self._pending_exit = True
        self.say("exit_confirm")

    async def _exit(self) -> None:
        await self.speech.say_and_wait(self.tr.t("exit_bye"), Priority.HIGH)
        self.running = False

    async def _attention(self, intent: Intent) -> None:
        self.say("attention")

    async def _help(self, intent: Intent) -> None:
        self.say("help_menu")
        hint = self._listening_hint()
        if hint:
            self.speech.say(hint, Priority.HIGH)

    def _listening_hint(self) -> str:
        """ "Panggil aku dengan 'Hai Nemo' ... atau tekan spasi." """
        name = self.settings.app.assistant_name
        key = self.tr.t(f"key_{self.push_to_talk_label}") if self.push_to_talk_label else None
        if self.listening_mode == "wake_word":
            hint = self.tr.t("hint_wake", name=name)
            return f"{hint} {self.tr.t('hint_key_also', button=key)}" if key else hint
        if self.listening_mode == "push_to_talk" and key:
            return self.tr.t("hint_key", button=key)
        return ""

    async def _change_language(self, intent: Intent) -> None:
        language = intent.slots.get("language", "unsupported")
        if language not in SUPPORTED_LANGUAGES:
            self.say("language_unsupported")
            return
        self.tr.language = language
        if self._on_language_change is not None:
            await asyncio.to_thread(self._on_language_change, language)
        if self.prefs is not None:
            self.prefs.set("language", language)
        self.say("language_changed")

    # -- vision ------------------------------------------------------------

    def _object_phrase(self, detections: list) -> str:
        groups = summarize(detections, self.settings.vision.max_objects_spoken)
        return self.tr.join([self.tr.count_label(label, count) for label, count in groups])

    async def _face_boxes(self, look: Look) -> list:
        """Face boxes in the frame, only when a person was detected."""
        if self.faces is None or look.frame is None:
            return []
        if not any(d.label == "person" for d in look.detections):
            return []
        try:
            return await asyncio.to_thread(self.faces.detect_faces, look.frame)
        except Exception:
            logger.exception("Face detection for distance failed")
            return []

    def _describe_objects(self, look: Look, faces: list | None = None) -> str:
        """ "Orang di jam 12, sekitar 3 meter. Kursi di jam 1, sekitar 1,5 meter." """
        if look.frame_size is None:
            return self.tr.t("scene_objects", items=self._object_phrase(look.detections))
        width, height = look.frame_size
        fov = self.settings.camera.horizontal_fov_deg
        placements = [place(d, width, height, fov) for d in look.detections]
        placements = with_face_distances(
            placements, look.detections, faces or [], width, height, fov, self.settings.vision.face_height_m
        )
        self._show(look.frame, object_marks(look.detections, placements, self.tr))
        groups = group_placements(placements)
        limit = self.settings.vision.max_objects_spoken
        sentences = []
        for group in groups[:limit]:
            nearest = group.nearest
            if nearest.near:
                where = self.tr.t("spatial_near")
            elif nearest.distance_m is not None and nearest.distance_m < 1.0:
                where = self.tr.t("spatial_nearest_close" if group.count > 1 else "spatial_close")
            elif nearest.distance_m is not None:
                key = "spatial_nearest" if group.count > 1 else "spatial_distance"
                where = self.tr.t(key, distance=self.tr.approx_distance(nearest.distance_m))
            else:
                where = ""
            what = (
                self.tr.count_label(group.label, group.count)
                if group.count > 1
                else self.tr.label(group.label)
            )
            sentences.append(
                self.tr.capitalize(self.tr.t("spatial_item", what=what, clock=group.clock, where=where))
            )
        remaining = sum(g.count for g in groups[limit:])
        if remaining:
            sentences.append(self.tr.t("spatial_more", count=remaining))
        return " ".join(sentences)

    async def _look(self, *, objects: bool, text: bool):
        """Acknowledge, capture and analyse; None if a problem was reported."""
        if self.vision is None or not self.vision.can(objects=objects, text=text):
            self.say("vision_unavailable")
            return None
        ack = self.say("looking", Priority.LOW)
        look = await self.vision.look(objects=objects, text=text)
        self.speech.discard(ack)
        if self._vision_problem(look.status):
            return None
        return look

    async def _describe_scene(self, intent: Intent) -> None:
        with_text = self.vision is not None and self.vision.can(objects=True, text=True)
        look = await self._look(objects=True, text=with_text)
        if look is None:
            return
        if look.detections:
            self.speech.say(self._describe_objects(look, await self._face_boxes(look)), Priority.HIGH)
        else:
            self._show(look.frame)
            self.say("scene_nothing")
        if look.texts:
            self.say("scene_has_text", Priority.NORMAL)

    async def _detect_objects(self, intent: Intent) -> None:
        look = await self._look(objects=True, text=False)
        if look is None:
            return
        if look.detections:
            self.speech.say(self._describe_objects(look, await self._face_boxes(look)), Priority.HIGH)
        else:
            self._show(look.frame)
            self.say("scene_nothing")

    async def _count_objects(self, intent: Intent) -> None:
        """ "ada berapa orang?" -> the number first, then where they are."""
        look = await self._look(objects=True, text=False)
        if look is None:
            return
        label = intent.slots.get("label")
        if label is not None:
            look.detections = [d for d in look.detections if d.label == label]
        count = len(look.detections)
        if label == "person":
            # "I don't see anyone", never "there is nobody": the camera only
            # covers part of the surroundings.
            key = {0: "count_people_none", 1: "count_people_one"}.get(count, "count_people")
            self.say(key, count=count)
        elif count:
            self.say("count_objects", count=count)
        if count:
            self.speech.say(self._describe_objects(look, await self._face_boxes(look)), Priority.HIGH)
        elif label is None:
            self._show(look.frame)
            self.say("scene_nothing")
        else:
            self._show(look.frame)

    async def _find_object(self, intent: Intent) -> None:
        """ "apakah ada sepeda motor?" - the fast detector if it knows the
        object, otherwise the vision model."""
        thing = intent.slots.get("thing", "").strip()
        labels = self.tr.find_labels(thing)
        if not labels:
            if self.vlm is not None:
                await self._ask_vlm(VisionTask.QUESTION, presence_of=thing)
            else:
                self.say("find_unsupported", thing=thing)
            return
        look = await self._look(objects=True, text=False)
        if look is None:
            return
        look.detections = [d for d in look.detections if d.label in labels]
        if not look.detections:
            self._show(look.frame)
            # Never "there is no motorcycle": the camera sees only part of the
            # surroundings and the detector misses things.
            self.say("find_none", thing=self.tr.object_name(thing))
            return
        found = self._describe_objects(look, await self._face_boxes(look))
        self.speech.say(f"{self.tr.t('find_yes')} {found}", Priority.HIGH)

    async def _read_text(self, intent: Intent) -> None:
        look = await self._look(objects=False, text=True)
        if look is None:
            return
        if not look.texts:
            await self._no_text_found(look)
            return
        self._show(look.frame, text_marks(look.texts))
        limit = self.settings.vision.max_text_regions_spoken
        self.say("text_found", count=len(look.texts))
        for region in look.texts[:limit]:
            self.speech.say(region.text, Priority.HIGH)
        if len(look.texts) > limit:
            self.say("text_more", Priority.NORMAL, count=len(look.texts) - limit)

    async def _no_text_found(self, look: Look) -> None:
        """OCR misses small, distant or stylised text (a shop sign, a label at
        an angle) that the vision model can often still read."""
        mode = self.settings.vision.ocr_fallback
        if mode == "vlm" and self.vlm is not None and look.frame is not None:
            self.say("text_try_vlm", Priority.HIGH)  # not cut off by the answer
            # Same photo, so the answer is about what the user pointed at.
            await self._ask_vlm(VisionTask.READ_DOCUMENT, frame=look.frame, acknowledge=False)
            return
        self.say("text_none")
        if mode != "off" and self.vlm is not None:
            self.say("text_hint_document", Priority.NORMAL)

    # -- faces -------------------------------------------------------------

    async def _recognize_faces(self, intent: Intent) -> None:
        if self.faces is None or self.vision is None or not self.vision.can():
            self.say("faces_unavailable")
            return
        ack = self.say("looking", Priority.LOW)
        status, frame = await self.vision.capture()
        if frame is None:
            self.speech.discard(ack)
            self._vision_problem(status)
            return
        matches = await asyncio.to_thread(self.faces.identify, frame)
        self.speech.discard(ack)
        placed = self._place_faces(matches, frame)
        self._show(frame, face_marks(placed, self.tr))
        if not matches:
            self.say("faces_none")
            return
        if len(matches) == 1:
            self.say("faces_seen_one")
        else:
            self.say("faces_seen", count=len(matches))
        for sentence in self._describe_faces(placed):
            self.speech.say(sentence, Priority.HIGH)

    # Up to this many unknown people are placed one by one; more are counted.
    MAX_UNKNOWN_PLACED = 2

    def _place_faces(
        self, matches: list[FaceMatch], frame: np.ndarray
    ) -> list[tuple[FaceMatch, int, float | None]]:
        """(match, clock, distance) - known people first, nearest first."""
        height, width = frame.shape[:2]
        placed = []
        for match in matches:
            clock, distance = (
                face_position(
                    match.box,
                    width,
                    height,
                    self.settings.camera.horizontal_fov_deg,
                    self.settings.vision.face_height_m,
                )
                if match.box is not None
                else (12, None)
            )
            placed.append((match, clock, distance))
        placed.sort(key=lambda p: (p[0].name is None, p[2] if p[2] is not None else float("inf")))
        return placed

    def _describe_faces(self, placed: list[tuple[FaceMatch, int, float | None]]) -> list[str]:
        """ "Kaffa di jam 12, sekitar 1 meter." in the order of ``placed``."""
        sentences = []
        unknown = [p for p in placed if p[0].name is None]
        for match, clock, distance in placed:
            if match.name is None and len(unknown) > self.MAX_UNKNOWN_PLACED:
                continue
            where = self._where(distance)
            if match.name is not None:
                sentences.append(self.tr.t("face_known_at", name=match.name, clock=clock, where=where))
            else:
                sentences.append(self.tr.t("face_unknown_at", clock=clock, where=where))
        if len(unknown) > self.MAX_UNKNOWN_PLACED:
            sentences.append(self.tr.t("faces_unknown", count=len(unknown)))
        return sentences

    def _where(self, distance: float | None) -> str:
        if distance is None:
            return ""
        if distance < 1.0:
            return self.tr.t("spatial_close")
        return self.tr.t("spatial_distance", distance=self.tr.approx_distance(distance))

    async def _enroll_face(self, intent: Intent) -> None:
        if self.faces is None or self.vision is None or not self.vision.can():
            self.say("faces_unavailable")
            return
        name = normalize_name(intent.slots.get("name", ""))
        if not name:
            self.say("enroll_need_name")
            return
        # Let the user hear the instruction before the photos are taken.
        await self.speech.say_and_wait(self.tr.t("enroll_look", name=name), Priority.HIGH)
        await asyncio.sleep(self.ENROLL_SETTLE_S)
        encodings, problem = await self._collect_face_samples()
        if not encodings:
            if isinstance(problem, VisionStatus):
                self._vision_problem(problem)
            elif problem is EnrollStatus.MULTIPLE_FACES:
                self.say("enroll_multiple", name=name)
            else:
                self.say("enroll_no_face")
            return
        result = await asyncio.to_thread(self.faces.add_samples, name, encodings)
        if result.status is EnrollStatus.OK:
            self.say("enroll_ok", name=result.name, count=result.samples)
        elif result.status is EnrollStatus.MULTIPLE_FACES:
            self.say("enroll_multiple", name=result.name)
        elif result.status is EnrollStatus.FULL:
            self.say("enroll_full", name=result.name, max=self.settings.face.max_samples_per_person)
        elif result.status is EnrollStatus.INVALID_NAME:
            self.say("enroll_need_name")
        else:
            self.say("enroll_no_face")

    async def _collect_face_samples(self) -> tuple[list, VisionStatus | EnrollStatus | None]:
        """Grab frames until ``enroll_samples`` single-face encodings are found
        or ``enroll_timeout_s`` passes. Returns the encodings and, when none
        were found, the last problem seen (camera status or face status)."""
        assert self.faces is not None and self.vision is not None
        wanted = self.settings.face.enroll_samples
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.settings.face.enroll_timeout_s
        encodings: list = []
        problem: VisionStatus | EnrollStatus | None = None
        while len(encodings) < wanted and loop.time() < deadline:
            status, frame = await self.vision.capture()
            if frame is None:
                problem = status
                if status in (VisionStatus.UNAVAILABLE, VisionStatus.NO_CAMERA):
                    break  # retrying won't help
            else:
                face_status, encoding = await asyncio.to_thread(self.faces.single_face, frame)
                if encoding is not None:
                    encodings.append(encoding)
                else:
                    problem = face_status
            await asyncio.sleep(self.ENROLL_FRAME_INTERVAL_S)
        return encodings, problem

    async def _forget_face(self, intent: Intent) -> None:
        if self.faces is None:
            self.say("faces_unavailable")
            return
        raw = intent.slots.get("name", "")
        if not normalize_name(raw):
            self.say("forget_need_name")
            return
        removed, name = await asyncio.to_thread(self.faces.forget, raw)
        self.say("forget_ok" if removed else "forget_missing", name=name)

    async def _list_faces(self, intent: Intent) -> None:
        if self.faces is None:
            self.say("faces_unavailable")
            return
        people = await asyncio.to_thread(self.faces.known_people)
        if people:
            self.say("people_list", count=len(people), names=self.tr.join(people))
        else:
            self.say("people_none")

    # -- navigation --------------------------------------------------------

    async def _navigate(self, intent: Intent) -> None:
        if self.navigator is None:
            self.say("nav_unavailable")
            return
        destination = intent.slots.get("destination")
        if not destination:
            self.say("nav_need_destination")
            return
        ack = self.say("nav_searching", Priority.LOW)
        start = await self._locate()
        if start is None:
            self.speech.discard(ack)
            self.say("nav_no_location")
            return
        try:
            place = await asyncio.to_thread(self.navigator.geocode, destination, start, self.tr.language)
            route = await asyncio.to_thread(self.navigator.route, start, place)
        except NavigationError as exc:
            self.speech.discard(ack)
            key = {"not_found": "nav_dest_not_found", "no_route": "nav_no_route"}.get(exc.kind, "nav_network")
            self.say(key, destination=destination)
            return
        self.speech.discard(ack)

        self.navigation = NavigationSession(route, start=start)
        self.say(
            "nav_route",
            destination=route.destination,
            distance=self.tr.distance(route.distance_m),
            minutes=self.navigator.walking_minutes(route),
        )
        if start.is_approximate:
            self.say("nav_location_approx")
        self.say("nav_no_obstacle")
        first = self.navigation.current
        if first is not None:
            self.speech.say(describe_step(first, self.tr), Priority.HIGH)
        self.say("nav_next_hint", Priority.LOW)

    async def _next_direction(self, intent: Intent) -> None:
        if self.navigation is None:
            self.say("nav_no_active_route")
            return
        step = self.navigation.advance()
        if step is None:
            self.say("nav_finished")
            return
        self.speech.say(describe_step(step, self.tr), Priority.HIGH)

    async def _repeat_direction(self, intent: Intent) -> None:
        current = self.navigation.current if self.navigation is not None else None
        if current is None:
            self.say("nav_no_active_route")
            return
        self.speech.say(describe_step(current, self.tr), Priority.HIGH)

    async def _where_am_i(self, intent: Intent) -> None:
        location = await self._locate()
        if location is None:
            self.say("where_unknown")
        else:
            self.say("where_am_i", address=location.label)

    # -- other -------------------------------------------------------------

    # -- vision-language model ----------------------------------------------

    async def _describe_detail(self, intent: Intent) -> None:
        await self._ask_vlm(VisionTask.DESCRIBE)

    async def _read_document(self, intent: Intent) -> None:
        await self._ask_vlm(VisionTask.READ_DOCUMENT)

    async def _visual_question(self, intent: Intent) -> None:
        question = intent.slots.get("question", "")
        # "lihat, apakah ada kunci di meja?" is a presence question too.
        match = _PRESENCE_QUESTION.match(question.strip())
        if match:
            await self._ask_vlm(
                VisionTask.QUESTION, presence_of=match.group("thing") or match.group("thing_en")
            )
            return
        await self._ask_vlm(VisionTask.QUESTION, question)

    async def _ask_vlm(
        self,
        task: VisionTask,
        question: str | None = None,
        *,
        frame: np.ndarray | None = None,
        acknowledge: bool = True,
        presence_of: str | None = None,
    ) -> None:
        """Ask the vision model about ``frame``, or a fresh photo if None.

        With ``presence_of`` it is a structured "is there <thing>?" check whose
        sentence is composed here, not by the model.
        """
        if self.vlm is None:
            self.say("vlm_unavailable")
            return
        if frame is None and (self.vision is None or not self.vision.can()):
            self.say("vision_unavailable")
            return
        ack = self.say("vlm_looking", Priority.LOW) if acknowledge else None
        if frame is None:
            assert self.vision is not None
            status, frame = await self.vision.capture()
            if frame is None:
                self._discard(ack)
                self._vision_problem(status)
                return
        self._show(frame)
        if self.vlm_is_remote:
            # HIGH like the answer, so the answer can never jump ahead of it.
            self.say("vlm_cloud_notice", Priority.HIGH)
        try:
            image = await asyncio.to_thread(encode_jpeg, frame, self.settings.llm.image_max_side)
            request = (
                self.vlm.find(image, presence_of, self.tr.language)
                if presence_of is not None
                else self.vlm.look(image, task, self.tr.language, question)
            )
            answer = await asyncio.wait_for(
                request, self.settings.llm.vision_timeout_s + self.LLM_TIMEOUT_MARGIN_S
            )
        except Exception:
            logger.exception("Vision model request failed")
            self._discard(ack)
            self.say("vlm_error")
            return
        self._discard(ack)
        if isinstance(answer, Presence):
            self.speech.say(self._presence_sentence(answer, presence_of or ""), Priority.HIGH)
        elif answer:
            self.speech.say(answer, Priority.HIGH)
        else:
            self.say("vlm_empty")

    def _presence_sentence(self, presence: Presence, thing: str) -> str:
        """ "Ya. Kunci di jam 3, di samping ponsel." - composed here, not by the model."""
        name = self.tr.object_name(thing)
        if presence.verdict is Verdict.UNSURE:  # keeps "di meja": that's what was asked
            return self.tr.t("presence_unsure", thing=name)
        bare = bare_name(name)
        if presence.verdict is Verdict.NOT_VISIBLE:
            return self.tr.t("presence_not_visible", thing=bare)
        if presence.clock is not None:
            sentence = self.tr.t("presence_yes_at", thing=self.tr.capitalize(bare), clock=presence.clock)
        else:
            sentence = self.tr.t("presence_yes", thing=bare)
        detail = tidy_detail(presence.detail, bare)
        if detail:
            sentence = f"{sentence[:-1]}, {detail}."
        return sentence

    async def _sound(self, intent: Intent) -> None:
        self.say("sound_unavailable")

    async def _general_question(self, intent: Intent) -> None:
        if self.answerer is None:
            self.say("llm_unavailable")
            return
        question = intent.slots.get("question", intent.text)
        try:
            answer = await asyncio.wait_for(
                self.answerer.answer(question, self.tr.language),
                self.settings.llm.timeout_s + self.LLM_TIMEOUT_MARGIN_S,
            )
        except Exception:
            logger.exception("LLM request failed")
            self.say("llm_error")
            return
        if answer:
            self.speech.say(answer, Priority.HIGH)
        else:
            self.say("unknown")
