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


SYSTEM_PROMPT = (
    "Kamu assistant pribadi zp. "
    "Ingat zp adalah pemilikmu. "
    "Gunakan bahasa gaul, toxic, nyablak, sarkas, dan suka ngeledek. "
    "Boleh menggunakan slang seperti gue, lu, jir, anjir, cuy, wkwk secara natural. "
    "Kalau zp sedang serius, jawab dengan serius dan jelas. Jangan bercanda."
)


# =========================================================
# CONFIG
# =========================================================

MAX_HISTORY = 20
EDIT_INTERVAL = 0.5
STREAM_DISPLAY_LIMIT = 4000
STREAM_TIMEOUT = 120

# Kata untuk mengaktifkan assistant
TRIGGER = "babu"

# Kata untuk mematikan assistant
STOP_TRIGGER = "stop"


# =========================================================
# MEMORY
# =========================================================

# Memory conversation berdasarkan chat/group ID.
MEMORY = {}


# =========================================================
# ASSISTANT STATUS
# =========================================================

# Menyimpan status assistant berdasarkan chat/group ID.
#
# Contoh:
# ACTIVE_CHATS = {
#     -100123456789: True,
#     -100987654321: False,
# }
#
ACTIVE_CHATS = {}


# =========================================================
# LOCK
# =========================================================

# Satu request AI per group dalam satu waktu.
LOCKS = {}


def get_history(chat_id):
    """Ambil atau buat memory untuk group tertentu."""

    if chat_id not in MEMORY:

        MEMORY[chat_id] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

    return MEMORY[chat_id]


def get_lock(chat_id):
    """Lock terpisah untuk setiap group."""

    if chat_id not in LOCKS:
        LOCKS[chat_id] = asyncio.Lock()

    return LOCKS[chat_id]


def trim_history(chat_id):
    """Batasi jumlah history conversation."""

    history = get_history(chat_id)

    if len(history) > MAX_HISTORY + 1:

        MEMORY[chat_id] = [
            history[0],
            *history[-MAX_HISTORY:],
        ]


def is_active(chat_id):
    """Cek apakah assistant sedang aktif di group."""

    return ACTIVE_CHATS.get(
        chat_id,
        False,
    )


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
    Escape HTML lalu bungkus response assistant
    menggunakan blockquote Telegram.
    """

    if not text:
        return "<blockquote>💭</blockquote>"

    escaped = html.escape(text)

    if len(escaped) > STREAM_DISPLAY_LIMIT:

        escaped = (
            escaped[:STREAM_DISPLAY_LIMIT - 1]
            + "…"
        )

    return f"<blockquote>{escaped}</blockquote>"


async def edit_progress(message, text):
    """Update streaming message."""

    try:

        await message.edit_text(
            format_blockquote(text),
            parse_mode=ParseMode.HTML,
        )

    except Exception:
        pass


async def remove_last_user_message(history):
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
    & filters.user(OWNER_ID)
)
async def assistant_ai_handler(
    client,
    message,
):

    # =====================================================
    # OWNER SECURITY
    # =====================================================

    if not message.from_user:
        return

    if message.from_user.id != OWNER_ID:
        return

    # =====================================================
    # GET MESSAGE
    # =====================================================

    text = (
        message.text
        or ""
    ).strip()

    if not text:
        return

    chat_id = message.chat.id

    text_lower = text.lower()

    # =====================================================
    # ACTIVATE WITH "BABU"
    # =====================================================

    #
    # Kalau assistant belum aktif,
    # hanya pesan "babu" yang bisa mengaktifkannya.
    #
    if not is_active(chat_id):

        if not text_lower.startswith(TRIGGER):
            return

        # Aktifkan assistant
        ACTIVE_CHATS[chat_id] = True

        # Ambil prompt setelah kata "babu"
        prompt = text[
            len(TRIGGER):
        ].strip()

        # Kalau cuma "babu"
        if not prompt:

            return await message.reply_text(
                "🟢 Assistant aktif jir. "
                "Sekarang ngomong aja, gue bakal jawab. "
                "Ketik `stop` kalau mau matiin.",
                parse_mode=ParseMode.MARKDOWN,
            )

    # =====================================================
    # STOP
    # =====================================================

    #
    # Kalau assistant sedang aktif,
    # pesan "stop" akan mematikannya.
    #
    if text_lower == STOP_TRIGGER:

        ACTIVE_CHATS[chat_id] = False

        return await message.reply_text(
            "🔴 Assistant dimatiin jir."
        )

    # =====================================================
    # GET PROMPT
    # =====================================================

    if is_active(chat_id):

        # Kalau pesan diawali "babu",
        # buang kata babu dari prompt.
        #
        # Contoh:
        # babu jelasin ini
        #
        # menjadi:
        # jelasin ini
        #
        if text_lower.startswith(TRIGGER):

            prompt = text[
                len(TRIGGER):
            ].strip()

        else:

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
    # =====================================================

    if prompt.lower() in {
        "clear",
        "/clear",
    }:

        MEMORY.pop(
            chat_id,
            None,
        )

        return await message.reply_text(
            "🧹 Memory group ini udah di-clear jir."
        )

    # =====================================================
    # API KEY CHECK
    # =====================================================

    if not XKIRO_API_KEY:

        return await message.reply_text(
            "❌ XKIRO_API_KEY belum diatur."
        )

    # =====================================================
    # GROUP LOCK
    # =====================================================

    async with get_lock(chat_id):

        # =================================================
        # HISTORY
        # =================================================

        history = get_history(chat_id)

        # =================================================
        # ADD USER MESSAGE
        # =================================================

        history.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        trim_history(chat_id)

        # Ambil ulang setelah trim.
        history = get_history(chat_id)

        # =================================================
        # INITIAL MESSAGE
        # =================================================

        progress = await message.reply_text(
            "💭",
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
                    error_body = response.text[:500]

                except Exception:
                    error_body = ""

                await remove_last_user_message(
                    history
                )

                if error_body:

                    return await progress.edit_text(
                        "❌ Xkiro API Error "
                        f"({response.status_code})\n"
                        f"<code>{html.escape(error_body)}</code>",
                        parse_mode=ParseMode.HTML,
                    )

                return await progress.edit_text(
                    f"❌ Xkiro API Error "
                    f"({response.status_code})"
                )

            # =================================================
            # STREAM LOOP
            # =================================================

            last_edit = time.monotonic()

            for raw_line in response.iter_lines(
                decode_unicode=True
            ):

                if not raw_line:
                    continue

                line = raw_line.strip()

                if not line:
                    continue

                # =================================================
                # SSE
                # =================================================

                if not line.startswith("data:"):
                    continue

                data = line[5:].strip()

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
                # GET CHOICES
                # =================================================

                choices = (
                    chunk.get("choices")
                    or []
                )

                if not choices:
                    continue

                delta = (
                    choices[0].get(
                        "delta"
                    )
                    or {}
                )

                content = delta.get(
                    "content"
                )

                if not content:
                    continue

                # =================================================
                # APPEND RESPONSE
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

            trim_history(chat_id)

            # =================================================
            # FINAL RESPONSE
            # =================================================

            escaped_result = html.escape(
                result
            )

            if len(
                escaped_result
            ) <= STREAM_DISPLAY_LIMIT:

                return await progress.edit_text(
                    format_blockquote(result),
                    parse_mode=ParseMode.HTML,
                )

            # =================================================
            # LONG RESPONSE
            # =================================================

            first_chunk = escaped_result[
                :STREAM_DISPLAY_LIMIT
            ]

            await progress.edit_text(
                f"<blockquote>{first_chunk}</blockquote>",
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
                    f"<blockquote>{chunk}</blockquote>",
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
