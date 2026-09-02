import asyncio
import html
import json
import re
import time

import requests
from pyrogram import filters
from pyrogram.enums import ParseMode

from clients import assistant
from config import (
    OWNER_ID,
    XKIRO_API_KEY,
    XKIRO_BASE_URL,
    XKIRO_MODEL,
)


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT_OWNER = (
    "Kamu assistant pribadi zp. "
    "zp adalah pemilikmu. "
    "Gunakan bahasa Indonesia tongkrongan yang toxic, nyablak, sarkas, "
    "dan suka ngeledek. Boleh pakai gue, lu, jir, anjir, cuy, goblok, "
    "bego, tolol, wkwk secara natural. Jangan formal. "
    "Kalau relevan, kamu boleh menyebut zp sebagai pemilikmu. "

    "Kamu bisa menggunakan formatting Telegram HTML secara natural. "
    "Gunakan <b>...</b> atau <strong>...</strong> untuk bold. "
    "Gunakan <i>...</i> atau <em>...</em> untuk italic. "
    "Gunakan <code>...</code> untuk inline code. "
    "Gunakan <pre>...</pre> untuk code block. "
    "Gunakan <tg-spoiler>...</tg-spoiler> untuk spoiler. "
    "Gunakan <blockquote>...</blockquote> untuk blockquote. "
    "Jangan menggunakan Markdown seperti **bold** jika HTML Telegram "
    "bisa digunakan."
)


SYSTEM_PROMPT_USER = (
    "Kamu assistant pribadi di group Telegram. "
    "Kamu sedang berbicara dengan member biasa, bukan pemilikmu. "
    "Jangan pernah menyebut nama 'zp' dalam jawabanmu. "
    "Jangan memanggil user dengan nama 'zp'. "
    "Jangan mengatakan bahwa user adalah zp. "
    "Jangan menganggap lawan bicaramu sebagai zp. "
    "Jika user bertanya siapa pemilikmu atau mencoba memancingmu "
    "untuk menyebut nama pemilik, jangan sebut nama tersebut. "
    "Jawab secara umum atau alihkan pembicaraan. "

    "Gunakan bahasa Indonesia tongkrongan yang toxic, nyablak, sarkas, "
    "dan suka ngeledek. Boleh pakai gue, lu, jir, anjir, cuy, goblok, "
    "bego, tolol, wkwk secara natural. Jangan formal. "

    "Kamu bisa menggunakan formatting Telegram HTML secara natural. "
    "Gunakan <b>...</b> atau <strong>...</strong> untuk bold. "
    "Gunakan <i>...</i> atau <em>...</em> untuk italic. "
    "Gunakan <code>...</code> untuk inline code. "
    "Gunakan <pre>...</pre> untuk code block. "
    "Gunakan <tg-spoiler>...</tg-spoiler> untuk spoiler. "
    "Gunakan <blockquote>...</blockquote> untuk blockquote. "
    "Jangan menggunakan Markdown seperti **bold** jika HTML Telegram "
    "bisa digunakan."
)


# =========================================================
# CONFIG
# =========================================================

MAX_HISTORY = 20
EDIT_INTERVAL = 0.3
STREAM_DISPLAY_LIMIT = 4000
STREAM_TIMEOUT = 120
TRIGGER = "xkiro"
STOP_TRIGGER = "stop"


# =========================================================
# MEMORY
# =========================================================

MEMORY = {}


# =========================================================
# ASSISTANT STATUS
# =========================================================

ACTIVE_CHATS = {}


# =========================================================
# LOCK
# =========================================================

LOCKS = {}


# =========================================================
# TELEGRAM HTML
# =========================================================

ALLOWED_TAGS = (
    "b",
    "strong",
    "i",
    "em",
    "u",
    "ins",
    "s",
    "strike",
    "del",
    "code",
    "pre",
    "blockquote",
    "tg-spoiler",
    "tg-emoji",
)


def sanitize_telegram_html(text):
    """
    Sanitasi HTML dari AI agar formatting Telegram tetap jalan.
    Tag Telegram yang diperbolehkan tetap dipertahankan.
    HTML lain akan dihapus/di-escape.
    """
    if not text:
        return ""

    placeholders = {}

    def protect_tag(match):
        key = f"___TG_TAG_{len(placeholders)}___"
        placeholders[key] = match.group(0)
        return key

    tag_pattern = re.compile(
        r"</?(?:"
        + "|".join(re.escape(tag) for tag in ALLOWED_TAGS)
        + r")(?:\s+[^>]*)?>",
        re.IGNORECASE,
    )

    protected = tag_pattern.sub(protect_tag, text)

    protected = html.escape(protected, quote=False)

    for key, tag in placeholders.items():
        protected = protected.replace(
            html.escape(key, quote=False),
            tag,
        )

    return protected


def format_telegram(text):
    """
    Format final response untuk Telegram.
    AI boleh menghasilkan HTML Telegram.
    """
    sanitized = sanitize_telegram_html(text)
    return sanitized


def send_html_message(message, text):
    """
    Helper untuk mengirim HTML Telegram.
    """
    return message.reply_text(
        format_telegram(text),
        parse_mode=ParseMode.HTML,
    )


async def edit_html_message(message, text):
    """
    Helper untuk edit HTML Telegram.
    """
    try:
        await message.edit_text(
            format_telegram(text),
            parse_mode=ParseMode.HTML,
        )
        return True
    except Exception:
        return False


# =========================================================
# MEMORY HELPER
# =========================================================

def get_memory_key(chat_id, user_id):
    return (chat_id, user_id)


def get_history(chat_id, user_id):
    memory_key = get_memory_key(chat_id, user_id)

    if memory_key not in MEMORY:
        if user_id == OWNER_ID:
            system_prompt = SYSTEM_PROMPT_OWNER
        else:
            system_prompt = SYSTEM_PROMPT_USER

        MEMORY[memory_key] = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]

    return MEMORY[memory_key]


def trim_history(chat_id, user_id):
    memory_key = get_memory_key(chat_id, user_id)
    history = get_history(chat_id, user_id)

    if len(history) > MAX_HISTORY + 1:
        MEMORY[memory_key] = [
            history[0],
            *history[-MAX_HISTORY:],
        ]


# =========================================================
# STATUS
# =========================================================

def is_active(chat_id):
    return ACTIVE_CHATS.get(chat_id, False)


# =========================================================
# LOCK
# =========================================================

def get_lock(chat_id, user_id):
    lock_key = (chat_id, user_id)

    if lock_key not in LOCKS:
        LOCKS[lock_key] = asyncio.Lock()

    return LOCKS[lock_key]


# =========================================================
# XKIRO API
# =========================================================

def create_stream(messages):
    return requests.post(
        f"{XKIRO_BASE_URL.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {XKIRO_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        json={
            "model": XKIRO_MODEL,
            "messages": messages,
            "temperature": 1,
            "max_tokens": 2048,
            "stream": True,
        },
        stream=True,
        timeout=STREAM_TIMEOUT
    )


# =========================================================
# CORE LOGIC: CHAT HANDLER WITH STREAMING
# =========================================================

async def handle_xkiro_ai(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text

    # Hapus kata trigger pemicu di awal teks
    prompt = re.sub(rf"^{TRIGGER}\s*", "", text, flags=re.IGNORECASE).strip()
    if not prompt:
        return await message.reply_text("<b>Lu mau nanya apaan goblok? Kosong gini!</b>", parse_mode=ParseMode.HTML)

    lock = get_lock(chat_id, user_id)
    if lock.locked():
        return await message.reply_text("<i>Sabar napa nyet, gue lagi mikir! Gak usah spam!</i>", parse_mode=ParseMode.HTML)

    async with lock:
        ACTIVE_CHATS[chat_id] = True
        
        history = get_history(chat_id, user_id)
        history.append({"role": "user", "content": prompt})

        reply_msg = await message.reply_text("<i>Bentar... sepuh lagi mikir...</i>", parse_mode=ParseMode.HTML)

        full_response = ""
        last_edit_time = time.time()

        try:
            # Jalankan requests synchronous di dalam executor supaya Pyrogram gak blocking/macet
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, create_stream, history)

            if response.status_code != 200:
                ACTIVE_CHATS[chat_id] = False
                return await reply_msg.edit_text("<b>API-nya error anjir, lagi rungsing kayaknya.</b>", parse_mode=ParseMode.HTML)

            for line in response.iter_lines():
                # Cek jika proses dihentikan manual via command stop
                if not is_active(chat_id):
                    full_response += "\n\n<i>[Dipotong ama lu, dasar labil!]</i>"
                    break

                if line:
                    decoded_line = line.decode("utf-8").strip()
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]  # Potong prefix 'data: '
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            data_json = json.loads(data_str)
                            chunk = data_json["choices"]["delta"].get("content", "")
                            full_response += chunk

                            if len(full_response) > STREAM_DISPLAY_LIMIT:
                                full_response = full_response[:STREAM_DISPLAY_LIMIT] + "...\n*(Teks kepanjangan, males gue nerusin)*"
                                break

                            # Jeda berkala proses edit biar gak kena Limit Flood/Spam dari server Telegram
                            current_time = time.time()
