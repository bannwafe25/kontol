import asyncio
import html
import json
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
    "Kalau relevan, kamu boleh menyebut zp sebagai pemilikmu."
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
    "bego, tolol, wkwk secara natural. Jangan formal."
)


# =========================================================
# CONFIG
# =========================================================

MAX_HISTORY = 20

# Semakin kecil = update streaming semakin cepat.
EDIT_INTERVAL = 0.3

STREAM_DISPLAY_LIMIT = 4000

STREAM_TIMEOUT = 120

# Trigger untuk mengaktifkan assistant.
TRIGGER = "xkiro"

# Trigger untuk mematikan assistant.
STOP_TRIGGER = "stop"


# =========================================================
# MEMORY
# =========================================================

# Memory dipisahkan berdasarkan:
#
#     (chat_id, user_id)
#
# Contoh:
#
# MEMORY = {
#     (-100123, 111111): [...],
#     (-100123, 222222): [...],
# }
#
# Jadi memory owner tidak bercampur dengan memory member.
#
MEMORY = {}


# =========================================================
# ASSISTANT STATUS
# =========================================================

# Status aktif berdasarkan GROUP.
#
# Kalau satu orang mengetik:
#
#     xkiro
#
# maka Xkiro aktif untuk seluruh group.
#
ACTIVE_CHATS = {}


# =========================================================
# LOCK
# =========================================================

# Lock berdasarkan GROUP + USER.
#
# User berbeda tetap bisa request bersamaan.
#
LOCKS = {}


# =========================================================
# MEMORY HELPER
# =========================================================

def get_memory_key(chat_id, user_id):
    """Buat key memory berdasarkan group + user."""

    return (
        chat_id,
        user_id,
    )


def get_history(chat_id, user_id):
    """
    Ambil atau buat memory conversation
    berdasarkan group + user.
    """

    memory_key = get_memory_key(
        chat_id,
        user_id,
    )

    if memory_key not in MEMORY:

        # Owner mendapatkan prompt khusus.
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
    """Batasi jumlah history conversation."""

    memory_key = get_memory_key(
        chat_id,
        user_id,
    )

    history = get_history(
        chat_id,
        user_id,
    )

    if len(history) > MAX_HISTORY + 1:

        MEMORY[memory_key] = [
            history[0],
            *history[-MAX_HISTORY:],
        ]


# =========================================================
# STATUS HELPER
# =========================================================

def is_active(chat_id):
    """Cek apakah Xkiro aktif di group."""

    return ACTIVE_CHATS.get(
        chat_id,
        False,
    )


# =========================================================
# LOCK HELPER
# =========================================================

def get_lock(chat_id, user_id):
    """Lock terpisah berdasarkan group + user."""

    lock_key = (
        chat_id,
        user_id,
    )

    if lock_key not in LOCKS:

        LOCKS[lock_key] = asyncio.Lock()

    return LOCKS[lock_key]


# =========================================================
# XKIRO API
# =========================================================

def create_stream(messages):
    """Request streaming ke Xkiro API."""

    return requests.post(
        f"{XKIRO_BASE_URL.rstrip('/')}/chat/completions",

        headers={
            "Authorization": f"Bearer {XKIRO_API_KEY}",
            "Content-Type": "application/json",
        },

        json={
            "model": XKIRO_MODEL,
            "messages": messages,
            "temperature": 1,
            "max_tokens": 2048,
            "stream": True,
        },

        stream=True,
        timeout=STREAM_TIMEOUT,
    )


# =========================================================
# TELEGRAM MESSAGE HELPER
# =========================================================

def format_blockquote(text):
    """
    Escape HTML lalu bungkus response
    menggunakan blockquote Telegram.
    """

    if not text:

        return "<blockquote>💭 Berfikir</blockquote>"

    escaped = html.escape(text)

    if len(escaped) > STREAM_DISPLAY_LIMIT:

        escaped = (
            escaped[:STREAM_DISPLAY_LIMIT - 1]
            + "…"
        )

    return (
        f"<blockquote>{escaped}</blockquote>"
    )


async def edit_progress(
    message,
    text,
):
    """Update streaming message."""

    try:

        await message.edit_text(
            format_blockquote(text),
            parse_mode=ParseMode.HTML,
        )

    except Exception:

        pass


async def remove_last_user_message(
    history,
):
    """Hapus pesan user terakhir jika request gagal."""

    if (
        history
        and history[-1].get("role") == "user"
    ):

        history.pop()


# =========================================================
# AI HANDLER
# =========================================================

@assistant.on_message(
    filters.group
    & filters.incoming
    & filters.text
)
async def assistant_ai_handler(
    client,
    message,
):

    # =====================================================
    # GET MESSAGE
    # =====================================================

    text = (
        message.text
        or ""
    ).strip()

    if not text:

        return

    # =====================================================
    # CHAT ID
    # =====================================================

    chat_id = message.chat.id

    # =====================================================
    # USER ID
    # =====================================================

    if not message.from_user:

        return

    user_id = message.from_user.id

    # =====================================================
    # LOWERCASE
    # =====================================================

    text_lower = text.lower()

    # =====================================================
    # ACTIVATE
    # =====================================================

    if not is_active(chat_id):

        # Semua member boleh mengaktifkan.
        if not text_lower.startswith(TRIGGER):

            return

        # Aktifkan untuk group.
        ACTIVE_CHATS[chat_id] = True

        # Ambil prompt setelah xkiro.
        prompt = text[
            len(TRIGGER):
        ].strip()

        # Kalau cuma "xkiro".
        if not prompt:

            return await message.reply_text(
                "🟢 Assistant aktif jir. "
                "Sekarang ngomong aja, gue bakal jawab. "
                "Ketik `stop` kalau mau matiin."
            )

    # =====================================================
    # STOP
    # OWNER ONLY
    # =====================================================

    if text_lower == STOP_TRIGGER:

        # Bukan owner.
        if user_id != OWNER_ID:

            return await message.reply_text(
                "🚫 Lu siapa jir? "
                "Cuma owner yang bisa matiin Xkiro."
            )

        # Owner boleh mematikan.
        ACTIVE_CHATS[chat_id] = False

        return await message.reply_text(
            "🔴 Assistant dimatiin jir."
        )

    # =====================================================
    # GET PROMPT
    # =====================================================

    if is_active(chat_id):

        # Jika menggunakan:
        #
        # xkiro halo
        #
        # maka prompt menjadi:
        #
        # halo

        if text_lower.startswith(TRIGGER):

            prompt = text[
                len(TRIGGER):
            ].strip()

        else:

            # Jika Xkiro sudah aktif,
            # semua pesan menjadi prompt.
            prompt = text

    else:

        return

    # =====================================================
    # EMPTY PROMPT
    # =====================================================

    if not prompt:

        return await message.reply_text(
            "💭 Ngomong sesuatu dong jir."
        )

    # =====================================================
    # CLEAR MEMORY
    # OWNER ONLY
    # =====================================================

    if prompt.lower() in {
        "clear",
        "/clear",
    }:

        # Hanya owner.
        if user_id != OWNER_ID:

            return await message.reply_text(
                "🚫 Memory jangan lu obrak-abrik jir. "
                "Cuma owner yang bisa clear."
            )

        # Clear memory owner untuk group ini.
        memory_key = get_memory_key(
            chat_id,
            user_id,
        )

        MEMORY.pop(
            memory_key,
            None,
        )

        return await message.reply_text(
            "🧹 Memory lu udah di-clear jir."
        )

    # =====================================================
    # API KEY CHECK
    # =====================================================

    if not XKIRO_API_KEY:

        return await message.reply_text(
            "❌ XKIRO_API_KEY belum diatur."
        )

    # =====================================================
    # USER LOCK
    # =====================================================

    async with get_lock(
        chat_id,
        user_id,
    ):

        # =================================================
        # HISTORY
        # =================================================

        history = get_history(
            chat_id,
            user_id,
        )

        # =================================================
        # ADD USER MESSAGE
        # =================================================

        history.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        # =================================================
        # TRIM
        # =================================================

        trim_history(
            chat_id,
            user_id,
        )

        # Ambil ulang setelah trim.
        history = get_history(
            chat_id,
            user_id,
        )

        # =================================================
        # INITIAL MESSAGE
        # =================================================

        progress = await message.reply_text(
            "💭 Berfikir..."
        )

        response = None

        result = ""

        try:

            # =================================================
            # CREATE STREAM
            # =================================================

            response = await asyncio.to_thread(
                create_stream,
                history,
            )

            # =================================================
            # API ERROR
            # =================================================

            if response.status_code != 200:

                try:

                    error_body = (
                        response.text[:500]
                    )

                except Exception:

                    error_body = ""

                await remove_last_user_message(
                    history
                )

                if error_body:

                    return await progress.edit_text(
                        "❌ Xkiro API Error "
                        f"({response.status_code})\n"
                        f"<code>"
                        f"{html.escape(error_body)}"
                        f"</code>",
                        parse_mode=ParseMode.HTML,
                    )

                return await progress.edit_text(
                    "❌ Xkiro API Error "
                    f"({response.status_code})"
                )

            # =================================================
            # STREAM LOOP
            # =================================================

            last_edit = time.monotonic()

            for raw_line in response.iter_lines(
                decode_unicode=True
            ):

                # Skip kosong.
                if not raw_line:

                    continue

                line = raw_line.strip()

                if not line:

                    continue

                # =================================================
                # SSE
                # =================================================

                if not line.startswith(
                    "data:"
                ):

                    continue

                data = line[
                    5:
                ].strip()

                # =================================================
                # DONE
                # =================================================

                if data == "[DONE]":

                    break

                # =================================================
                # PARSE JSON
                # =================================================

                try:

                    chunk = json.loads(
                        data
                    )

                except json.JSONDecodeError:

                    continue

                # =================================================
                # CHOICES
                # =================================================

                choices = (
                    chunk.get("choices")
                    or []
                )

                if not choices:

                    continue

                # =================================================
                # DELTA
                # =================================================

                delta = (
                    choices[0].get(
                        "delta"
                    )
                    or {}
                )

                # =================================================
                # CONTENT
                # =================================================

                content = delta.get(
                    "content"
                )

                if not content:

                    continue

                # =================================================
                # APPEND
                # =================================================

                result += content

                # =================================================
                # LIVE UPDATE
                # =================================================

                now = time.monotonic()

                if (
                    now - last_edit
                    >= EDIT_INTERVAL
                ):

                    await edit_progress(
                        progress,
                        result,
                    )

                    last_edit = now

            # =================================================
            # EMPTY RESPONSE
            # =================================================

            if not result.strip():

                await remove_last_user_message(
                    history
                )

                return await progress.edit_text(
                    "❌ AI tidak memberikan response."
                )

            # =================================================
            # SAVE ASSISTANT RESPONSE
            # =================================================

            history.append(
                {
                    "role": "assistant",
                    "content": result,
                }
            )

            # =================================================
            # TRIM AGAIN
            # =================================================

            trim_history(
                chat_id,
                user_id,
            )

            # =================================================
            # FINAL RESPONSE
            # =================================================

            escaped_result = html.escape(
                result
            )

            # =================================================
            # NORMAL RESPONSE
            # =================================================

            if len(
                escaped_result
            ) <= STREAM_DISPLAY_LIMIT:

                return await progress.edit_text(
                    format_blockquote(
                        result
                    ),
                    parse_mode=ParseMode.HTML,
                )

            # =================================================
            # LONG RESPONSE
            # =================================================

            first_chunk = escaped_result[
                :STREAM_DISPLAY_LIMIT
            ]

            await progress.edit_text(
                (
                    "<blockquote>"
                    f"{first_chunk}"
                    "</blockquote>"
                ),
                parse_mode=ParseMode.HTML,
            )

            # =================================================
            # SEND REMAINING CHUNKS
            # =================================================

            for i in range(
                STREAM_DISPLAY_LIMIT,
                len(escaped_result),
                STREAM_DISPLAY_LIMIT,
            ):

                chunk = escaped_result[
                    i:i + STREAM_DISPLAY_LIMIT
                ]

                await message.reply_text(
                    (
                        "<blockquote>"
                        f"{chunk}"
                        "</blockquote>"
                    ),
                    parse_mode=ParseMode.HTML,
                )

                await asyncio.sleep(
                    0.2
                )

        # =====================================================
        # TIMEOUT
        # =====================================================

        except requests.exceptions.Timeout:

            await remove_last_user_message(
                history
            )

            await progress.edit_text(
                "❌ Xkiro timeout jir."
            )

        # =====================================================
        # REQUEST ERROR
        # =====================================================

        except requests.exceptions.RequestException:

            await remove_last_user_message(
                history
            )

            await progress.edit_text(
                "❌ Gagal konek ke Xkiro."
            )

        # =====================================================
        # GENERAL ERROR
        # =====================================================

        except Exception as error:

            await remove_last_user_message(
                history
            )

            await progress.edit_text(
                "❌ Error: "
                + html.escape(
                    str(error)[:1000]
                ),
                parse_mode=ParseMode.HTML,
            )

        # =====================================================
        # CLOSE STREAM
        # =====================================================

        finally:

            if response is not None:

                try:

                    response.close()

                except Exception:

                    pass
