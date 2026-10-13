# Configuration

AIForUs reads two things at startup:

- **`config.yaml`** (project root, or `--config path`) — non-secret settings.
  Every key is optional; missing keys use the built-in defaults from
  `aiforus/config.py`. **Unknown keys are an error**, so a typo fails at
  startup instead of being silently ignored. Values are range-checked too.
- **Environment / `.env`** — secrets only. Copy `.env.example` to `.env`.

After changing anything, run `python -m aiforus --check`.

Contents: [Environment](#environment) · [app](#app) · [speech](#speech) ·
[camera](#camera) · [vision](#vision) · [face](#face) ·
[navigation](#navigation) · [llm](#llm) · [emergency](#emergency) ·
[Recipes](#recipes)

## Environment

| Variable | Used for |
| --- | --- |
| `LLM_API_KEY` | API key for a hosted LLM provider. Not needed for local servers such as Ollama. |
| `OPENAI_API_KEY` | Accepted as a fallback for `LLM_API_KEY`. |

Keys are never read from `config.yaml` and never printed.

## app

| Key | Default | Meaning |
| --- | --- | --- |
| `name` | `"AIForUs Vision Assistant"` | Display name. |
| `language` | `id` | Starting language: `id` or `en`. A language chosen by voice is remembered and wins; `--lang` wins over both. |
| `data_dir` | `data` | Folder for `aiforus.db` (face embeddings, preferences). Relative paths are relative to the project root. Keep it private. |
| `log_level` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`. `--debug` forces `DEBUG`. |

## speech

| Key | Default | Meaning |
| --- | --- | --- |
| `engine` | `auto` | `auto` = Piper when installed and the voice is downloaded, else pyttsx3. Or force `piper` / `pyttsx3`. |
| `piper_voices` | `id: id_ID-news_tts-medium`, `en: en_US-lessac-medium` | Piper voice per language ([list](https://huggingface.co/rhasspy/piper-voices)). Download with `--download-models`. |
| `piper_dir` | `models/piper` | Where Piper voices are stored. |
| `piper_length_scale` | `1.0` | Piper speed: > 1 slower, < 1 faster (0.3–3.0). |
| `rate` | `170` | pyttsx3 only: words per minute (80–320). |
| `volume` | `1.0` | 0.0–1.0. |
| `voice_hints` | see `config.yaml` | pyttsx3 only: substrings used to pick an installed OS voice per language. |
| `recognition_locale` | `id: id-ID`, `en: en-US` | Locale sent to speech recognition. |
| `listen_timeout_s` | `5` | How long to wait for you to start speaking. |
| `phrase_time_limit_s` | `10` | Longest single command. |

## camera

| Key | Default | Meaning |
| --- | --- | --- |
| `index` | `0` | Which camera. Try `1`, `2`, … if the wrong one opens. |
| `width`, `height` | `1280`, `720` | Requested resolution (the camera may pick another). |
| `flush_frames` | `4` | Frames discarded before each capture so the image is fresh, not seconds old. |
| `dark_threshold` | `25` | Mean brightness (0–255) below which the frame counts as too dark. |
| `blank_std_threshold` | `6` | Pixel variation below which the lens counts as covered. |
| `horizontal_fov_deg` | `70` | Horizontal field of view. Drives clock directions and distances — see [calibrating](#calibrating-distances). Typical webcams 60–78, wide glasses cameras ~110–120. |

## vision

| Key | Default | Meaning |
| --- | --- | --- |
| `detector_model` | `yolov8n.pt` | YOLOv8 weights (downloaded by ultralytics on first use). Larger = slower but more accurate (`yolov8s.pt`). |
| `detection_confidence` | `0.5` | Minimum confidence for an object to be spoken. |
| `ocr_languages` | `[id, en]` | EasyOCR languages. |
| `ocr_confidence` | `0.5` | Minimum confidence for a text region. |
| `max_objects_spoken` | `6` | Object groups spoken before "there are also N more". |
| `max_text_regions_spoken` | `5` | Text regions read by "baca tulisan". |
| `ocr_fallback` | `vlm` | When "baca tulisan" finds nothing: `vlm` looks again at the same photo with the vision model (if one is available), `hint` suggests saying "baca dokumen", `off` just says no text was found. |
| `face_height_m` | `0.21` | Typical face box height, used to measure how far people are. See [calibrating](#calibrating-distances). |

## face

| Key | Default | Meaning |
| --- | --- | --- |
| `enabled` | `true` | Face commands on/off. |
| `backend` | `opencv` | `opencv` = YuNet + SFace (small ONNX models, also on edge devices). `dlib` = `face_recognition` library (`pip install -e ".[faces]"`, needs a C++ build, desktop only). |
| `quantized` | `false` | int8 models (~10 MB instead of ~39 MB), for edge devices. A different model, so faces must be enrolled again. |
| `model_dir` | `models/opencv` | Where the ONNX models are stored (`--download-models`). |
| `detection_confidence` | `0.8` | opencv only: minimum face detection score. |
| `detection_model` | `hog` | dlib only: `hog` (CPU) or `cnn` (GPU). |
| `match_threshold` | empty | Max embedding distance to count as the same person. Empty = backend default (SFace 1.128 ≈ cosine 0.363; dlib 0.55). Lower = stricter, fewer false matches, more "unknown". |
| `max_samples_per_person` | `10` | Samples kept per name. |
| `enroll_samples` | `3` | Samples saved per "kenali wajah" command, from different frames. |
| `enroll_timeout_s` | `4` | How long enrollment keeps trying to see exactly one face. |

Embeddings are stored per model, so switching `backend` or `quantized`
never mixes incompatible vectors — but people need to be enrolled again
for the new model.

## navigation

| Key | Default | Meaning |
| --- | --- | --- |
| `enabled` | `true` | Navigation commands on/off. |
| `routing_url` | `https://router.project-osrm.org` | OSRM server. The public demo only has a car profile. |
| `routing_profile` | `foot` | OSRM profile (honoured by self-hosted servers). |
| `geocoding_url` | Nominatim | Destination search. |
| `ip_location_url` | `https://ipinfo.io/json` | Approximate location from your IP. |
| `user_agent` | `aiforus-vision-assistant/0.2 (+repo URL)` | Required by Nominatim's usage policy. |
| `http_timeout_s` | `8` | Timeout for every HTTP call. |
| `walking_speed_mps` | `1.2` | Used to estimate walking time. |

## llm

General questions and the detailed vision commands ("jelaskan lebih
detail", "baca dokumen", "lihat, …"). The LLM never decides which command
runs.

| Key | `config.yaml` | Built-in default | Meaning |
| --- | --- | --- | --- |
| `enabled` | `true` | `true` | Both features on/off. |
| `base_url` | `http://localhost:11434/v1` | empty (= OpenAI) | Any OpenAI-compatible endpoint. |
| `model` | `gemma3:4b` | `gpt-4o-mini` | Model for general questions. |
| `timeout_s` | `30` | `30` | Per question; CPU-only local models can be slow. Requests are not retried automatically (a retry would start over and double the wait). |
| `max_tokens` | `200` | `200` | Answer length limit. |
| `vision_model` | empty | empty | Model for images. Empty = same as `model` (it must then accept images). |
| `vision_timeout_s` | `60` | `60` | Per image request, including loading the model on the first one. |
| `vision_max_tokens` | `400` | `400` | Longer, for documents. |
| `image_max_side` | `1024` | `1024` | Photos are downscaled so the longest side is at most this (256–4096). Smaller = faster, but small print gets harder to read. |
| `allow_images_to_cloud` | `false` | `false` | Must be `true` before a photo may go to a non-local endpoint. Every such request is announced. |

"Local" means `localhost`, a `*.local` host name, or a loopback / private
network IP address. `--check` shows the result:

```
  general questions (LLM)    ok - gemma3:4b @ http://localhost:11434/v1
  detailed vision (VLM)      ok - gemma3:4b (local, images stay on this machine)
  LLM server                 reachable, model found
```

## emergency

| Key | Default | Meaning |
| --- | --- | --- |
| `contacts` | `[]` | Kept for the future; sending alerts is **not implemented** and the assistant says so. |
| `local_emergency_number` | `112` | Number the assistant tells you to call. |

## Recipes

### Local LLM and VLM with Ollama (default)

1. Install [Ollama](https://ollama.com) and `pip install -e ".[llm]"`.
2. `ollama pull gemma3:4b` — multilingual (incl. Indonesian) and accepts
   images, so one model covers both features.
3. Keep the defaults in `config.yaml` and run `python -m aiforus --check`.

Tips:

- The first request after starting loads the model and is slow. `ollama ps`
  shows whether it runs on the GPU (`100% GPU`) or partly on the CPU.
- A different text model and vision model are possible:
  `model: "qwen2.5:7b"`, `vision_model: "gemma3:4b"`. Both must be pulled.
- On another machine in your network:
  `base_url: "http://192.168.1.20:11434/v1"` still counts as local.

### Hosted provider

```yaml
llm:
  base_url:            # empty = OpenAI; or the provider's OpenAI-compatible URL
  model: "gpt-4o-mini"
  allow_images_to_cloud: false   # true only if you accept sending photos
```

```
# .env
LLM_API_KEY=...
```

With `allow_images_to_cloud: false` general questions work and the
detailed vision commands are blocked (`--check`: `blocked - images would
leave this machine`). With `true`, every photo sent is announced: *"Fotonya
aku kirim ke layanan AI di internet."*

### Calibrating distances

Distances come from the pinhole model, so two settings matter:

1. **`camera.horizontal_fov_deg`** — affects every distance and direction.
   Use the webcam's specification. Spec sheets usually give the *diagonal*
   FOV; for a 16:9 camera the horizontal FOV is a bit smaller (78° diagonal
   ≈ 70° horizontal). If **all** distances are too large, the FOV is set
   too small, and vice versa.
2. **`vision.face_height_m`** — affects people whose face is visible. Stand
   at a measured distance (e.g. 2 m), ask "apa di depan" a few times and
   note the spoken distance. Then:

   ```
   new face_height_m = face_height_m × real distance / spoken distance
   ```

   Example: real 2 m, spoken "sekitar 2,5 meter" → 0.21 × 2 / 2.5 ≈ 0.17.
   Check again at 1 m and 3 m.

Even calibrated, expect roughly ±30 %; that is why distances are always
spoken as *about*.

### Edge device / smaller models

```yaml
face:
  quantized: true          # int8 YuNet + SFace (~10 MB)
vision:
  detector_model: "yolov8n.pt"
llm:
  image_max_side: 768
```

Run `python -m aiforus --download-models` again after switching
`quantized`, then enroll faces again.
