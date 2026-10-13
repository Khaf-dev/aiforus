"""Spoken message catalog.

Every sentence the assistant says lives here, in every supported language,
so no handler hard-codes English (or Indonesian) text. ``tests/test_i18n.py``
checks that both catalogs have the same keys and placeholders.
"""

from __future__ import annotations

MESSAGES: dict[str, dict[str, str]] = {
    "id": {
        # General
        "ready": "Asisten siap. Katakan 'bantuan' untuk daftar perintah.",
        "unknown": "Maaf, aku belum paham. Katakan 'bantuan' untuk daftar perintah.",
        "error": "Maaf, terjadi kesalahan. Coba lagi.",
        "help_menu": (
            "Ini yang bisa aku lakukan. "
            "Melihat: katakan 'apa di depan', 'benda apa saja', atau 'baca tulisan'. "
            "Untuk lebih rinci: 'jelaskan lebih detail', 'baca dokumen', atau 'lihat' "
            "lalu pertanyaanmu, misalnya 'lihat, ini uang berapa'. "
            "Wajah: 'siapa ini', 'kenali wajah sebagai Budi', 'siapa saja yang kamu kenal', "
            "atau 'lupakan Budi'. "
            "Arah: 'arahkan ke' lalu nama tempat, 'arah berikutnya', 'ulangi arah', "
            "atau 'aku di mana'. "
            "Bahasa: 'ganti bahasa ke Inggris'. "
            "Katakan 'diam' untuk menghentikan suaraku, 'darurat' saat butuh pertolongan, "
            "dan 'matikan asisten' untuk keluar."
        ),
        "looking": "Sebentar, aku lihat dulu.",
        "vlm_looking": "Sebentar, aku perhatikan dulu.",
        "vlm_unavailable": "Penjelasan detail belum tersedia. Model penglihatan belum diatur.",
        "vlm_error": "Maaf, model penglihatan tidak bisa dihubungi atau terlalu lama menjawab.",
        "vlm_cloud_notice": "Fotonya aku kirim ke layanan AI di internet.",
        "vlm_empty": "Aku tidak bisa menjelaskan gambar ini.",
        "stt_offline": "Pengenalan suara tidak bisa terhubung ke internet. Periksa koneksi.",
        # Camera / vision
        "vision_unavailable": "Fitur penglihatan belum terpasang di perangkat ini.",
        "camera_unavailable": "Kamera tidak tersedia. Aku tidak bisa melihat sekarang.",
        "camera_dark": "Gambar terlalu gelap. Aku tidak bisa melihat dengan jelas.",
        "camera_blocked": "Kamera sepertinya tertutup. Aku tidak bisa melihat apa pun.",
        "scene_objects": "Di depan, aku melihat {items}.",
        "scene_nothing": "Aku tidak mengenali benda apa pun di depan.",
        "scene_has_text": "Ada juga tulisan. Katakan 'baca tulisan' untuk membacanya.",
        "spatial_item": "{what} di jam {clock}{where}.",
        "spatial_distance": ", sekitar {distance}",
        "spatial_nearest": ", yang terdekat sekitar {distance}",
        "spatial_near": ", sangat dekat",
        "spatial_close": ", kurang dari 1 meter",
        "spatial_nearest_close": ", yang terdekat kurang dari 1 meter",
        "spatial_more": "Ada juga {count} benda lain.",
        "distance_under_1m": "kurang dari 1 meter",
        "text_found": "Aku menemukan {count} tulisan.",
        "text_none": "Aku tidak menemukan tulisan yang bisa dibaca.",
        "text_try_vlm": "Tulisannya tidak terbaca dengan cara cepat. Aku coba lihat lebih teliti.",
        "text_hint_document": "Coba katakan 'baca dokumen' supaya aku membaca lebih teliti.",
        "text_more": "Masih ada {count} tulisan lain yang tidak aku bacakan.",
        # Faces
        "faces_unavailable": "Pengenalan wajah belum terpasang di perangkat ini.",
        "faces_none": "Aku tidak melihat wajah.",
        "faces_seen": "Aku melihat {count} wajah.",
        "faces_seen_one": "Aku melihat 1 wajah.",
        "count_people": "Aku melihat {count} orang.",
        "count_people_one": "Aku melihat 1 orang.",
        "count_people_none": "Aku tidak melihat orang di kamera.",
        "count_objects": "Aku melihat {count} benda.",
        # Preview window labels (not spoken)
        "mark_clock": "jam {clock}",
        "mark_near": "sangat dekat",
        "mark_unknown": "belum dikenal",
        "preview_live": "LANGSUNG",
        "preview_answer": "FOTO JAWABAN TERAKHIR",
        "preview_heard": "Kamu",
        "preview_said": "Asisten",
        "preview_dark": "terlalu gelap",
        "preview_blank": "kamera tertutup",
        "preview_no_camera": "kamera tidak tersedia",
        "face_known_at": "{name} di jam {clock}{where}.",
        "face_unknown_at": "Orang yang belum aku kenal di jam {clock}{where}.",
        "faces_unknown": "{count} orang belum aku kenal.",
        "enroll_need_name": "Sebutkan namanya, misalnya: kenali wajah sebagai Budi.",
        "enroll_look": (
            "Pastikan {name} setuju wajahnya disimpan. Arahkan kamera ke wajah {name}, lalu tahan sebentar."
        ),
        "enroll_ok": "Wajah {name} tersimpan. Sekarang ada {count} sampel.",
        "enroll_no_face": "Aku tidak menemukan wajah. Coba lagi dengan cahaya yang cukup.",
        "enroll_multiple": "Aku melihat lebih dari satu wajah. Pastikan hanya {name} yang terlihat.",
        "enroll_full": "Sampel wajah {name} sudah penuh, maksimal {max} sampel.",
        "forget_need_name": "Siapa yang harus aku lupakan?",
        "forget_ok": "Data wajah {name} sudah dihapus.",
        "forget_missing": "Aku tidak punya data wajah bernama {name}.",
        "people_list": "Aku mengenal {count} orang: {names}.",
        "people_none": "Aku belum mengenal siapa pun.",
        # Navigation
        "nav_unavailable": "Navigasi sedang dimatikan di pengaturan.",
        "nav_need_destination": "Mau ke mana? Misalnya: arahkan ke Monas.",
        "nav_searching": "Sebentar, aku cari rutenya.",
        "nav_no_location": "Lokasimu tidak bisa ditentukan, jadi aku tidak bisa membuat rute.",
        "nav_dest_not_found": "Aku tidak menemukan tempat bernama {destination}.",
        "nav_no_route": "Aku tidak menemukan rute ke {destination}.",
        "nav_network": "Tidak bisa terhubung ke layanan peta. Periksa koneksi internet.",
        "nav_route": "Rute ke {destination}: sekitar {distance}, kira-kira {minutes} menit berjalan kaki.",
        "nav_location_approx": (
            "Perhatian: lokasimu diperkirakan dari internet dan bisa meleset beberapa kilometer, "
            "jadi rute ini belum bisa diandalkan untuk berjalan."
        ),
        "nav_no_obstacle": "Aku belum bisa mendeteksi rintangan. Tetap gunakan tongkat.",
        "nav_next_hint": "Katakan 'arah berikutnya' untuk langkah selanjutnya.",
        "nav_no_active_route": "Belum ada rute aktif. Katakan 'arahkan ke' lalu nama tempat.",
        "nav_finished": "Itu langkah terakhir. Rute selesai.",
        "step_walk": "{maneuver}{road}, lalu jalan sekitar {distance}.",
        "step_arrive": "Kamu tiba di tujuan{road}.",
        "step_road": " ke {road}",
        "step_arrive_road": ", {road}",
        "maneuver_depart": "Mulai berjalan",
        "maneuver_continue": "Jalan lurus",
        "maneuver_roundabout": "Masuk bundaran, ambil jalan keluar ke-{exit}",
        "modifier_uturn": "Putar balik",
        "modifier_sharp_right": "Belok tajam ke kanan",
        "modifier_right": "Belok kanan",
        "modifier_slight_right": "Agak serong ke kanan",
        "modifier_straight": "Jalan lurus",
        "modifier_slight_left": "Agak serong ke kiri",
        "modifier_left": "Belok kiri",
        "modifier_sharp_left": "Belok tajam ke kiri",
        "where_am_i": (
            "Perkiraan lokasimu: {address}. Ini perkiraan dari internet dan bisa meleset beberapa kilometer."
        ),
        "where_unknown": "Lokasimu tidak bisa ditentukan.",
        # Sound
        "sound_unavailable": (
            "Fitur pendengaran dan deteksi rintangan lewat suara belum tersedia, "
            "karena metode lamanya tidak bisa dipercaya. Tetap gunakan tongkat."
        ),
        # Language
        "language_changed": "Bahasa diganti ke Bahasa Indonesia.",
        "language_unsupported": (
            "Bahasa itu belum didukung. Pilihannya Bahasa Indonesia atau Bahasa Inggris."
        ),
        # General questions
        "llm_unavailable": ("Aku belum bisa menjawab pertanyaan umum karena layanan AI belum diatur."),
        "llm_error": "Maaf, layanan AI sedang tidak bisa dihubungi.",
        # Emergency
        "emergency_start": "Mode darurat.",
        "emergency_no_send": "Aku belum bisa mengirim pesan darurat ke siapa pun.",
        "emergency_call": (
            "Segera hubungi {number}, atau minta tolong orang di sekitarmu dengan suara keras."
        ),
        "emergency_location": (
            "Perkiraan lokasimu dari internet: {address}. Bisa meleset beberapa kilometer."
        ),
        "emergency_location_unknown": "Lokasimu tidak bisa ditentukan.",
        # Exit / confirmation
        "exit_confirm": ("Mau mematikan asisten? Katakan 'ya' untuk mematikan, atau 'tidak' untuk batal."),
        "exit_bye": "Asisten dimatikan. Sampai jumpa.",
        "exit_cancelled": "Baik, asisten tetap menyala.",
        "nothing_to_confirm": "Tidak ada yang perlu dikonfirmasi.",
        # Units / grammar
        "unit_meters": "{value} meter",
        "unit_kilometers": "{value} kilometer",
        "list_and": "dan",
    },
    "en": {
        "ready": "Assistant ready. Say 'help menu' for the list of commands.",
        "unknown": "Sorry, I didn't understand. Say 'help menu' for the list of commands.",
        "error": "Sorry, something went wrong. Please try again.",
        "help_menu": (
            "Here is what I can do. "
            "Seeing: say 'what's in front', 'what objects', or 'read text'. "
            "For more detail: 'describe in detail', 'read the document', or 'look' followed "
            "by your question, for example 'look, what color is this shirt'. "
            "Faces: 'who is this', 'enroll face as Budi', 'who do you know', or 'forget Budi'. "
            "Directions: 'take me to' and a place, 'next direction', 'repeat direction', "
            "or 'where am I'. "
            "Language: 'change language to Indonesian'. "
            "Say 'stop' to silence me, 'emergency' when you need help, "
            "and 'turn off assistant' to exit."
        ),
        "looking": "One moment, let me look.",
        "vlm_looking": "One moment, let me take a closer look.",
        "vlm_unavailable": "Detailed descriptions aren't available. No vision model is set up.",
        "vlm_error": "Sorry, the vision model can't be reached or took too long.",
        "vlm_cloud_notice": "I'm sending the photo to an AI service on the internet.",
        "vlm_empty": "I can't describe this image.",
        "stt_offline": "Speech recognition can't reach the internet. Please check the connection.",
        "vision_unavailable": "Vision features are not installed on this device.",
        "camera_unavailable": "The camera is not available. I can't see right now.",
        "camera_dark": "The image is too dark. I can't see clearly.",
        "camera_blocked": "The camera seems to be covered. I can't see anything.",
        "scene_objects": "In front of you, I see {items}.",
        "scene_nothing": "I don't recognize any objects in front of you.",
        "scene_has_text": "There is also some text. Say 'read text' to hear it.",
        "spatial_item": "{what} at {clock} o'clock{where}.",
        "spatial_distance": ", about {distance}",
        "spatial_nearest": ", the closest about {distance}",
        "spatial_near": ", very close",
        "spatial_close": ", less than 1 meter away",
        "spatial_nearest_close": ", the closest less than 1 meter away",
        "spatial_more": "There are also {count} more objects.",
        "distance_under_1m": "less than 1 meter",
        "text_found": "I found {count} pieces of text.",
        "text_none": "I didn't find any readable text.",
        "text_try_vlm": "I couldn't read it the quick way. Let me look more closely.",
        "text_hint_document": "Try saying 'read the document' for a closer look.",
        "text_more": "There are {count} more pieces of text I didn't read.",
        "faces_unavailable": "Face recognition is not installed on this device.",
        "faces_none": "I don't see any faces.",
        "faces_seen": "I see {count} faces.",
        "faces_seen_one": "I see one face.",
        "count_people": "I see {count} people.",
        "count_people_one": "I see one person.",
        "count_people_none": "I don't see anyone on the camera.",
        "count_objects": "I see {count} objects.",
        "mark_clock": "{clock} o'clock",
        "mark_near": "very close",
        "mark_unknown": "unknown",
        "preview_live": "LIVE",
        "preview_answer": "PHOTO OF THE LAST ANSWER",
        "preview_heard": "You",
        "preview_said": "Assistant",
        "preview_dark": "too dark",
        "preview_blank": "lens covered",
        "preview_no_camera": "no camera",
        "face_known_at": "{name} at {clock} o'clock{where}.",
        "face_unknown_at": "Someone I don't know at {clock} o'clock{where}.",
        "faces_unknown": "{count} people I don't know yet.",
        "enroll_need_name": "Tell me the name, for example: enroll face as Budi.",
        "enroll_look": (
            "Make sure {name} agrees to having their face saved. "
            "Point the camera at {name}'s face and hold still."
        ),
        "enroll_ok": "Saved {name}'s face. I now have {count} samples.",
        "enroll_no_face": "I couldn't find a face. Try again with enough light.",
        "enroll_multiple": "I see more than one face. Make sure only {name} is visible.",
        "enroll_full": "{name} already has the maximum of {max} face samples.",
        "forget_need_name": "Who should I forget?",
        "forget_ok": "Deleted the face data for {name}.",
        "forget_missing": "I don't have face data for {name}.",
        "people_list": "I know {count} people: {names}.",
        "people_none": "I don't know anyone yet.",
        "nav_unavailable": "Navigation is turned off in the settings.",
        "nav_need_destination": "Where do you want to go? For example: take me to the station.",
        "nav_searching": "One moment, I'm finding the route.",
        "nav_no_location": "I can't determine your location, so I can't plan a route.",
        "nav_dest_not_found": "I couldn't find a place called {destination}.",
        "nav_no_route": "I couldn't find a route to {destination}.",
        "nav_network": "I can't reach the map service. Please check the internet connection.",
        "nav_route": "Route to {destination}: about {distance}, roughly {minutes} minutes on foot.",
        "nav_location_approx": (
            "Warning: your location is estimated from the internet and may be off by several "
            "kilometers, so this route is not reliable for walking yet."
        ),
        "nav_no_obstacle": "I can't detect obstacles yet. Keep using your cane.",
        "nav_next_hint": "Say 'next direction' for the next step.",
        "nav_no_active_route": "There is no active route. Say 'take me to' and a place.",
        "nav_finished": "That was the last step. The route is complete.",
        "step_walk": "{maneuver}{road}, then walk about {distance}.",
        "step_arrive": "You have arrived at your destination{road}.",
        "step_road": " onto {road}",
        "step_arrive_road": ", {road}",
        "maneuver_depart": "Start walking",
        "maneuver_continue": "Continue straight",
        "maneuver_roundabout": "Enter the roundabout and take exit {exit}",
        "modifier_uturn": "Make a U-turn",
        "modifier_sharp_right": "Turn sharp right",
        "modifier_right": "Turn right",
        "modifier_slight_right": "Bear slightly right",
        "modifier_straight": "Go straight",
        "modifier_slight_left": "Bear slightly left",
        "modifier_left": "Turn left",
        "modifier_sharp_left": "Turn sharp left",
        "where_am_i": (
            "Your estimated location: {address}. "
            "This is estimated from the internet and may be off by several kilometers."
        ),
        "where_unknown": "I can't determine your location.",
        "sound_unavailable": (
            "Listening and sound-based obstacle detection are not available yet, because the "
            "old method was not reliable. Keep using your cane."
        ),
        "language_changed": "Language changed to English.",
        "language_unsupported": (
            "That language is not supported yet. The options are Indonesian or English."
        ),
        "llm_unavailable": "I can't answer general questions because the AI service is not set up.",
        "llm_error": "Sorry, the AI service can't be reached right now.",
        "emergency_start": "Emergency mode.",
        "emergency_no_send": "I can't send emergency messages to anyone yet.",
        "emergency_call": "Call {number} now, or shout for help from people around you.",
        "emergency_location": (
            "Your estimated location from the internet: {address}. It may be off by several kilometers."
        ),
        "emergency_location_unknown": "I can't determine your location.",
        "exit_confirm": "Turn off the assistant? Say 'yes' to turn it off, or 'no' to cancel.",
        "exit_bye": "Assistant turned off. Goodbye.",
        "exit_cancelled": "Okay, the assistant stays on.",
        "nothing_to_confirm": "There is nothing to confirm.",
        "unit_meters": "{value} meters",
        "unit_kilometers": "{value} kilometers",
        "list_and": "and",
    },
}

# Indonesian names for the 80 COCO classes detected by YOLOv8.
# fmt: off
COCO_LABELS_ID: dict[str, str] = {
    "person": "orang", "bicycle": "sepeda", "car": "mobil", "motorcycle": "sepeda motor",
    "airplane": "pesawat", "bus": "bus", "train": "kereta", "truck": "truk", "boat": "perahu",
    "traffic light": "lampu lalu lintas", "fire hydrant": "hidran", "stop sign": "rambu stop",
    "parking meter": "meteran parkir", "bench": "bangku", "bird": "burung", "cat": "kucing",
    "dog": "anjing", "horse": "kuda", "sheep": "domba", "cow": "sapi", "elephant": "gajah",
    "bear": "beruang", "zebra": "zebra", "giraffe": "jerapah", "backpack": "ransel",
    "umbrella": "payung", "handbag": "tas tangan", "tie": "dasi", "suitcase": "koper",
    "frisbee": "frisbee", "skis": "ski", "snowboard": "papan seluncur salju",
    "sports ball": "bola", "kite": "layang-layang", "baseball bat": "tongkat bisbol",
    "baseball glove": "sarung tangan bisbol", "skateboard": "papan luncur",
    "surfboard": "papan selancar", "tennis racket": "raket tenis", "bottle": "botol",
    "wine glass": "gelas anggur", "cup": "cangkir", "fork": "garpu", "knife": "pisau",
    "spoon": "sendok", "bowl": "mangkuk", "banana": "pisang", "apple": "apel",
    "sandwich": "roti lapis", "orange": "jeruk", "broccoli": "brokoli", "carrot": "wortel",
    "hot dog": "hot dog", "pizza": "pizza", "donut": "donat", "cake": "kue", "chair": "kursi",
    "couch": "sofa", "potted plant": "tanaman pot", "bed": "tempat tidur",
    "dining table": "meja makan", "toilet": "toilet", "tv": "televisi", "laptop": "laptop",
    "mouse": "mouse", "remote": "remote", "keyboard": "keyboard", "cell phone": "ponsel",
    "microwave": "microwave", "oven": "oven", "toaster": "pemanggang roti",
    "sink": "wastafel", "refrigerator": "kulkas", "book": "buku", "clock": "jam",
    "vase": "vas", "scissors": "gunting", "teddy bear": "boneka beruang",
    "hair drier": "pengering rambut", "toothbrush": "sikat gigi",
}

# English plurals that don't follow the simple "+s / +es" rule.
EN_IRREGULAR_PLURALS: dict[str, str] = {
    "person": "people", "mouse": "mice", "knife": "knives", "sheep": "sheep",
    "skis": "skis", "scissors": "scissors", "bus": "buses", "couch": "couches",
    "sandwich": "sandwiches", "toothbrush": "toothbrushes", "hair drier": "hair driers",
}
# fmt: on
