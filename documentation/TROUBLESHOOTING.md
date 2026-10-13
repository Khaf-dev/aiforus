# Troubleshooting

Start with:

```powershell
python -m aiforus --check
```

It lists every component with `ok` or the reason it isn't available, which
voices were found, whether the camera returns a frame and whether the LLM
server and models are reachable. Add `--debug` to any command for detailed
logs.

## Installation

| Symptom | Fix |
| --- | --- |
| `pip install` fails on **PyAudio** (Linux/macOS) | Install PortAudio first: `sudo apt install portaudio19-dev` (Debian/Ubuntu) or `brew install portaudio` (macOS), then install again. |
| `pip install` fails on **dlib** / `face_recognition` | You don't need it: the default face backend (`face.backend: opencv`) only needs OpenCV. Only install the `faces` extra if you want dlib, and then install CMake and C++ build tools first. |
| `Invalid configuration` at startup | The message names the key. Usually a typo (unknown keys are rejected) or a value out of range — see [CONFIGURATION.md](CONFIGURATION.md). |
| A component shows `unavailable - No module named …` | Install the matching extra: `voice`, `piper`, `vision`, `llm` (e.g. `pip install -e ".[vision]"`). |
| OpenCV 5 installed by something else | The `vision` extra pins `opencv-python<5` because the face models are OpenCV 4.x versions. `pip install "opencv-python>=4.8,<5"`. |

## Voice output

| Symptom | Fix |
| --- | --- |
| `TTS voice for 'id' (piper) NOT FOUND` | `python -m aiforus --download-models` (needs internet once). |
| `TTS voice for 'id' (pyttsx3) NOT FOUND` | Windows rarely ships an Indonesian voice that pyttsx3 can use. Install Piper instead: `pip install -e ".[piper]"` and `--download-models`. |
| Speaks too fast / too slow | Piper: `speech.piper_length_scale` (e.g. `1.15` = slower). pyttsx3: `speech.rate`. |
| No sound at all | Check the Windows default output device; test with `python -m aiforus --text`. With `--mute` replies are printed, not spoken. |

## Voice input

| Symptom | Fix |
| --- | --- |
| *"Pengenalan suara tidak bisa terhubung ke internet"* | Speech recognition uses Google's online service; check the connection. Use `--text` to type commands offline. |
| It ignores you while it is talking | Expected: it doesn't listen while speaking (otherwise it hears itself). Wait until it finishes, or say "diam" after it stops. Barge-in is planned. |
| **Windows:** nothing happens until you press Enter | Clicking in the console window turned on QuickEdit selection, which pauses the program. Fixed: QuickEdit is now disabled while the assistant runs. If you still see it, update to the latest version. |
| Wrong words recognised | Speak close to the microphone in a quiet place; check that `speech.recognition_locale` matches the language. `speech.listen_timeout_s` / `phrase_time_limit_s` control how long it listens. |

## Camera and seeing

| Symptom | Fix |
| --- | --- |
| `camera frame no frame` or the wrong camera | Set `camera.index` to `1`, `2`, …; close other apps using the camera (Zoom, Teams, browser tabs). |
| *"Gambar terlalu gelap"* / *"Kamera sepertinya tertutup"* | Really dark or covered image — more light, remove the lens cover. Thresholds: `camera.dark_threshold`, `camera.blank_std_threshold`. |
| The first "apa di depan" / "baca tulisan" is slow | YOLO and EasyOCR load (and on first use download) their models. Later requests are faster. |
| Objects missed or wrong | Raise or lower `vision.detection_confidence`; a larger model (`yolov8s.pt`) is more accurate but slower. |
| Distances consistently too large / small | [Calibrate](CONFIGURATION.md#calibrating-distances) `camera.horizontal_fov_deg` and `vision.face_height_m`. Expect roughly ±30 % anyway. |
| Directions look mirrored, or it describes *you* | A laptop webcam faces you, so "jam 1" is to the camera's right (your left) and you are the person in front. Smart glasses look where the user looks. For realistic tests point a camera forward: a USB webcam, or a phone used as a webcam. |
| You want to see what the assistant "sees" | Run with `--preview`: live boxes with labels, and the exact photo behind each answer. |
| A close person is *"sangat dekat"* with no number | Their body is cut off and no face is visible (facing away, too close). Expected; depth estimation is planned. |

## Faces

| Symptom | Fix |
| --- | --- |
| `face recognition … unavailable` / models missing | `python -m aiforus --download-models`. |
| Enrollment: *"Aku tidak menemukan wajah"* | Face the camera, enough light, about 0.5–2 m away. It tries for 4 s (`face.enroll_timeout_s`). |
| Enrollment: *"lebih dari satu wajah"* | Only the person being enrolled may be in view. |
| Someone isn't recognised | Enroll them again (adds 3 more samples, up to 10) in different light or angles. |
| A stranger is recognised as someone | Make matching stricter: lower `face.match_threshold` (default 1.128 for SFace, e.g. `1.0`). |
| Faces "forgotten" after switching `face.backend` or `quantized` | Expected: each model has its own embeddings. Enroll again. |

## LLM and detailed vision

| Symptom | Fix |
| --- | --- |
| `LLM server NOT reachable` | Start Ollama (tray app or `ollama serve`). Check `llm.base_url` (`http://localhost:11434/v1`). |
| `reachable, but model … not found` | `ollama pull gemma3:4b` (or whatever `llm.model` / `llm.vision_model` say). |
| `general questions (LLM) off - set llm.base_url …` | Neither a server nor an API key is configured. See [CONFIGURATION.md](CONFIGURATION.md#llm). |
| `detailed vision (VLM) blocked - images would leave this machine` | The endpoint isn't local. Set `llm.allow_images_to_cloud: true` only if you accept sending photos to that provider. |
| *"Penjelasan detail belum tersedia"* | Same as above: no usable vision model. Check `--check`. |
| *"model penglihatan tidak bisa dihubungi atau terlalu lama menjawab"* | Server stopped, or slower than `llm.vision_timeout_s` (60 s). Run `ollama ps`: `100% GPU` is fast, a CPU share is slow. Close other GPU-heavy apps, lower `llm.image_max_side`, or raise the timeout. The first request after starting also loads the model. |
| The model answers wrongly or invents text | Vision-language models can hallucinate. Use the fast commands for objects/text, and double-check money, medicine and anything important. |
| Wrong answers about current events ("presidennya Joko Widodo") | The local model only knows its training data. It is told today's date and to warn that its information may be outdated, but it can still be wrong. Live information (web search) is planned. |
| Log shows `Retrying request` | Fixed: requests are no longer retried; image requests use `llm.vision_timeout_s`. Update. |
| An image model error like "does not support images" | `llm.model` is text-only. Set `llm.vision_model` to a model that accepts images (e.g. `gemma3:4b`). |

## Live preview (`--preview`)

| Symptom | Fix |
| --- | --- |
| Log: `Preview window unavailable` | `opencv-python-headless` has no window support: `pip uninstall opencv-python-headless` then `pip install "opencv-python>=4.8,<5"`. A desktop session is needed (not SSH). |
| macOS: no window | OpenCV windows must run on the main thread on macOS; the preview is supported on Windows and Linux for now. |
| The laptop gets warm / fans spin | The preview runs object and face detection about 3 times a second. Close the window (q) when you don't need it; the assistant itself only detects when asked. |
| `--preview needs a camera` | No camera was found; see [Camera and seeing](#camera-and-seeing). |

## Navigation

| Symptom | Fix |
| --- | --- |
| Start point is far off | Location comes from your IP address and can be kilometres off. GPS from a phone is planned. |
| *"Aku tidak menemukan tempat bernama …"* | Say a better-known place name or add the city: "arahkan aku ke Monas Jakarta". |
| Walking time looks odd | The public OSRM server only has a car profile; time is estimated with `navigation.walking_speed_mps`. |

Still stuck? Open an issue with the `--check` output and the `--debug` log:
[GitHub issues](https://github.com/Khaf-dev/aiforus/issues).
