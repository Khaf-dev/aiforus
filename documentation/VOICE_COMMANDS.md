# Voice commands

Bahasa Indonesia is the default language; English works the same way. Say
**"ganti bahasa ke Inggris"** / **"change language to Indonesian"** to switch
(the choice is remembered). Polite words like *tolong*, *coba*, *dong*,
*please* are fine before or after a command, and punctuation doesn't matter.

Commands are matched by fixed rules, not by AI, so they behave the same every
time. Anything that doesn't match a command is a
[general question](#general-questions).

## Safety and control

| What | Bahasa Indonesia | English |
| --- | --- | --- |
| Emergency | "tolong", "darurat", "saya jatuh", "minta pertolongan", "panggil ambulans" | "help", "help me", "emergency", "I fell", "call for help" |
| Stop talking | "diam", "stop", "berhenti membaca" | "stop", "be quiet" |
| List commands | "bantuan", "apa saja yang bisa kamu lakukan" | "help menu", "what can you do" |
| Language | "ganti bahasa ke Inggris" | "change language to Indonesian" |
| Exit | "matikan asisten", then "ya" | "turn off assistant", then "yes" |

- Emergency is checked **before every other command**. A bare **"tolong"** /
  **"help"** is an emergency; to hear the command list say **"bantuan"** /
  **"help menu"**.
- Emergency mode says honestly that no alert can be sent yet, tells you to
  call 112 (`emergency.local_emergency_number`) and reads your approximate
  location.
- Exiting always asks for confirmation; any other command cancels it.

## Seeing — fast (on this machine)

| What | Bahasa Indonesia | English |
| --- | --- | --- |
| Describe the scene | "apa di depan", "ada apa di sekitar", "gambarkan", "lihat sekitar" | "what's in front of me", "describe" |
| Objects only | "benda apa saja", "deteksi benda" | "what objects", "detect objects" |
| Count | "ada berapa orang", "berapa benda di depan" | "how many people", "how many objects" |
| Is there …? | "apakah ada sepeda motor di depan?", "ada kursi nggak?" | "is there a chair?", "do you see my phone?" |
| Read short text | "baca tulisan", "bacakan", "apa tulisannya" | "read text", "what does it say" |

The answer uses **clock directions** (12 = straight ahead, 3 = right,
9 = left) and a rough distance, nearest first:

> *"Kursi di jam 1, sekitar 2 meter. 2 orang di jam 12, yang terdekat
> sekitar 3 meter. Ada juga 2 benda lain."*

- Distances are estimates from the object's size in the image (often ±30%),
  so they are always said with *sekitar* / *about*. Only common objects with
  a predictable height get a distance; the rest get a direction only.
- People are measured by the size of their **face** when it is visible, so
  someone close whose body doesn't fit in the frame still gets a distance.
- An object cut off by the frame and filling most of it is *"sangat dekat"* /
  *"very close"*, without a number.
- Under 1 meter is said as *"kurang dari 1 meter"*.
- Counting gives the number first, then where: *"Aku melihat 2 orang. Orang
  di jam 1, sekitar 2 meter. Orang di jam 12, sekitar 3 meter."* With nobody
  in view it says *"Aku tidak melihat orang di kamera"* — never that nobody
  is there, because the camera only sees part of the surroundings.
- **"apakah ada …?"** answers *"Ya. Sepeda motor di jam 12, sekitar 2,5
  meter."* or *"Aku tidak melihat sepeda motor di kamera. Itu bukan berarti
  tidak ada."* — never "there is none". Everyday words work ("motor", "hp",
  "tas", "meja"). Objects the fast detector doesn't know ("kunci", "uang")
  go to the vision model instead. Obstacle words ("ada rintangan / halangan /
  lubang?") get the honest "not available yet" answer.
- If the camera is dark or covered the assistant says it **can't see** —
  never that nothing is there.
- If **"baca tulisan"** finds nothing (small, distant or stylised text such
  as a shop sign), the assistant says so and looks again at the same photo
  with the vision model: *"Tulisannya tidak terbaca dengan cara cepat. Aku
  coba lihat lebih teliti."* With `vision.ocr_fallback: hint` it only
  suggests saying "baca dokumen"; `off` disables both.

## Seeing — detailed (vision-language model)

Needs the LLM settings (local Ollama by default, see
[CONFIGURATION.md](CONFIGURATION.md#llm)). The assistant first says
*"Sebentar, aku perhatikan dulu"*; the answer takes a few seconds.

| What | Bahasa Indonesia | English |
| --- | --- | --- |
| Detailed description | "jelaskan lebih detail", "gambarkan secara rinci", "ceritakan dengan lengkap" | "describe it in detail", "more detail" |
| Read a document | "baca dokumen", "bacakan surat ini", "bacakan menu", "baca label obat", "baca struk" | "read this letter", "read the menu", "read the label" |
| Ask about the image | "lihat, ini uang berapa?", "lihat, baju ini warna apa?" | "look, what color is this shirt?" |

- *Document* words that switch "baca …" to the detailed reader: dokumen,
  surat, menu, kertas, halaman, label, resep, struk, kemasan, buku, brosur
  (English: document, letter, menu, page, label, receipt, prescription,
  package, book). Plain "baca tulisan" tries the fast OCR first.
- A question must **start** with *lihat* / *look*: "lihat, …".
- **"Is there …?"** questions the fast detector can't answer ("apakah ada
  kunci di meja?", or "lihat, apakah ada …") get a checked verdict. The vision
  model only fills in yes / not visible / not sure plus a position; the
  sentence is composed by the assistant:
  *"Ya. Kunci di jam 10."*, *"Aku tidak melihat kunci di foto. Itu bukan
  berarti tidak ada."* or *"Aku tidak yakin ada kunci atau tidak. Coba
  dekatkan kamera atau ubah sudutnya."* A reply that contradicts itself
  becomes "not sure".
- Other questions ("lihat, ini uang berapa?") are answered in the model's own
  words; yes/no ones start with *"Ya."*, *"Tidak terlihat."* or *"Tidak
  yakin."*.
  "lihat sekitar" is the fast scene description.
- The model is told to describe only what is visible, say when something is
  unclear, and never claim a path is clear or something is safe. It can
  still be wrong: **double-check money, medicine and anything important**.
- Obstacle questions ("ada rintangan?") are never sent to the model; they
  get the honest "not available yet" answer.
- If the configured model runs in the cloud, the assistant says *"Fotonya
  aku kirim ke layanan AI di internet"* every time.

## People

| What | Bahasa Indonesia | English |
| --- | --- | --- |
| Who is here | "siapa ini", "ini siapa", "siapa orang ini", "ada siapa" | "who is this", "who's there" |
| Save a face | "kenali wajah sebagai Budi" | "enroll face as Budi", "register face as Budi" |
| Known people | "siapa saja yang kamu kenal" | "who do you know" |
| Delete a face | "lupakan Budi", "hapus wajah Budi" | "forget Budi" |

- The answer says where each person is, known people first, nearest first:
  *"Aku melihat 2 wajah. Kaffa di jam 12, sekitar 1 meter. Orang yang belum
  aku kenal di jam 2, sekitar 3 meter."* More than two strangers are only
  counted ("3 orang belum aku kenal").
- "ini siapa" counts as this command only as the whole question; "ini siapa
  yang bikin lagunya?" is a general question.
- Enrollment needs **exactly one face** in view. It keeps looking for up to
  4 seconds and saves 3 samples from different frames
  (`face.enroll_samples`, `face.enroll_timeout_s`). Saying it again for the
  same name adds more samples (up to 10).
- Ask people before saving their face. Face data stays on this machine.

## Directions

| What | Bahasa Indonesia | English |
| --- | --- | --- |
| Route | "arahkan aku ke Monas" | "take me to Monas" |
| Next / repeat step | "arah berikutnya" / "ulangi arah" | "next direction" / "repeat direction" |
| Location | "aku di mana" | "where am I" |

Navigation is a demo: the start point comes from your IP address and can be
kilometres off, and obstacles are not detected. The assistant reminds you of
both.

## Not available yet

| What | Bahasa Indonesia | English | Answer |
| --- | --- | --- | --- |
| Obstacles, sounds | "ada rintangan", "cek jalan", "apa yang kamu dengar" | "any obstacles", "check ahead", "what do you hear" | Says it's not available and to keep using the cane |

## General questions

Anything else — *"apa ibu kota Jepang"*, *"berapa 15 kali 12"* — goes to the
LLM (local Ollama by default, or any OpenAI-compatible provider; see
[CONFIGURATION.md](CONFIGURATION.md#llm)). Answers are kept to a few short
sentences, without follow-up questions. The LLM can't see the camera in
this mode; for that use "lihat, …". It is never used to decide which
command to run.

A local model only knows what was in its training data. It is told today's
date and to say when its information may be out of date (who holds an
office, prices, news) — but it can still be wrong about recent events.
