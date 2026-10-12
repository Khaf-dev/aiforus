# Voice commands

Bahasa Indonesia is the default language; English works the same way. Say
**"ganti bahasa ke Inggris"** / **"change language to Indonesian"** to switch.
Polite words like *tolong*, *coba*, *dong*, *please* are fine before or after
a command.

| What | Bahasa Indonesia | English |
| --- | --- | --- |
| Emergency | "tolong", "darurat", "saya jatuh", "minta pertolongan", "panggil ambulans" | "help", "help me", "emergency", "I fell", "call for help" |
| Stop talking | "diam", "stop", "berhenti membaca" | "stop", "be quiet" |
| List commands | "bantuan", "apa saja yang bisa kamu lakukan" | "help menu", "what can you do" |
| Describe the scene | "apa di depan", "ada apa di sekitar", "gambarkan" | "what's in front of me", "describe" |
| Objects only | "benda apa saja", "deteksi benda" | "what objects", "detect objects" |
| Read text | "baca tulisan", "bacakan", "apa tulisannya" | "read text", "what does it say" |
| Detailed description (VLM) | "jelaskan lebih detail", "gambarkan secara detail" | "describe it in detail" |
| Read a document (VLM) | "baca dokumen", "bacakan surat ini", "bacakan menu" | "read this letter", "read the menu" |
| Ask about the image (VLM) | "lihat, ini uang berapa?", "lihat, baju ini warna apa?" | "look, what color is this shirt?" |
| Who is here | "siapa ini", "ada siapa" | "who is this", "who's there" |
| Save a face | "kenali wajah sebagai Budi" | "enroll face as Budi", "register face as Budi" |
| Known people | "siapa saja yang kamu kenal" | "who do you know" |
| Delete a face | "lupakan Budi", "hapus wajah Budi" | "forget Budi" |
| Route | "arahkan aku ke Monas" | "take me to Monas" |
| Next / repeat step | "arah berikutnya" / "ulangi arah" | "next direction" / "repeat direction" |
| Location | "aku di mana" | "where am I" |
| Language | "ganti bahasa ke Inggris" | "change language to Indonesian" |
| Exit | "matikan asisten", then "ya" | "turn off assistant", then "yes" |

Anything else is treated as a general question and answered by the LLM when
`OPENAI_API_KEY` is set.

Describing the scene answers with **clock directions** (12 = straight ahead,
3 = right, 9 = left) and a rough distance, nearest first, e.g. *"Kursi di jam
1, sekitar 2 meter. 2 orang di jam 12, yang terdekat sekitar 3 meter."*
Distances are estimates from the object's size in the image (often ±30%), so
they are always said with "sekitar" / "about".

Notes:

- A bare **"tolong"** or **"help"** is treated as an emergency. To hear the
  command list, say **"bantuan"** / **"help menu"**.
- Exiting always asks for confirmation; any other command cancels it.
