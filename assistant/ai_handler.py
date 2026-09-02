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

# Interval update streaming Telegram.
# Lebih kecil = tampilan lebih realtime,
# tapi terlalu kecil bisa menyebabkan flood/edit terlalu sering.
EDIT_INTERVAL = 0.3

# Batas aman panjang satu pesan Telegram.
STREAM_DISPLAY_LIMIT = 4000

STREAM_TIMEOUT = 120

# Trigger aktivasi.
TRIGGER = "xkiro"

# Trigger stop.
STOP_TRIGGER = "stop"


# =========================================================
# MEMORY
# =========================================================

# Memory dipisahkan berdasarkan:
#
#     (chat_id, user_id)
#
# Jadi setiap user punya conversation sendiri
# di masing-masing group.
#
MEMORY = {}


# =========================================================
# ASSISTANT STATUS
# =========================================================

# Status Xkiro berdasarkan group.
#
# Kalau seseorang mengetik:
#
#     xkiro
#
# maka Xkiro aktif untuk group tersebut.
#
ACTIVE_CHATS = {}


# =========================================================
# LOCK
# =========================================================

# Lock dipisahkan berdasarkan:
#
#     (chat_id, user_id)
#
# User berbeda tetap bisa request secara bersamaan.
#
LOCKS = {}


# =========================================================
# MEMORY HELPER
# =========================================================

def get_memory_key(chat_id, user_id):
    return (
        chat_id,
        user_id,
    )


def get_history(chat_id, user_id):
    """
    Ambil atau buat memory berdasarkan group + user.
    """

    memory_key = get_memory_key(
        chat_id,
        user_id,
    )

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
    """
    Batasi jumlah history conversation.
    """

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
    return ACTIVE_CHATS.get(
        chat_id,
        False,
    )


# =========================================================
# LOCK HELPER
# =========================================================

def get_lock(chat_id, user_id):
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
    """
    Request streaming ke Xkiro API.
    """

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
    """
    Update streaming message.
    """

    try:

        await message.edit_text(
            format_blockquote(text),
            parse_mode=ParseMode.HTML,
        )

    except Exception:

        pass


def decode_sse_line(raw_line):
    """
    Decode SSE byte secara eksplisit menggunakan UTF-8.

    Ini mencegah mojibake seperti:

        🤙 -> Ã°ÂŸÂ¤Â™

        —  -> â€”

        ™  -> â„¢
    """

    if isinstance(raw_line, bytes):

        try:
            return raw_line.decode(
                "utf-8"
            )

        except UnicodeDecodeError:

            return raw_line.decode(
                "utf-8",
                errors="replace",
            )

    return raw_line


def clean_non_owner_response(
    text,
    user_id,
):
    """
    Safety tambahan untuk member biasa.

    Prompt sudah melarang penyebutan 'zp'.
    Fungsi ini hanya sebagai filter tambahan.
    """

    if user_id == OWNER_ID:
        return text

    return text.replace(
        "zp",
        "[pemilik]",
    ).replace(
        "ZP",
        "[pemilik]",
    ).replace(
        "Zp",
        "[pemilik]",
    ).replace(
        "zP",
        "[pemilik]",
    )


async def remove_last_user_message(
    history,
):
    """
    Hapus pesan user terakhir jika request gagal.
    """

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

        if user_id != OWNER_ID:

            return await message.reply_text(
                "🚫 Lu siapa jir? "
                "Cuma owner yang bisa matiin Xkiro."
            )

        ACTIVE_CHATS[chat_id] = False

        return await message.reply_text(
            "🔴 Assistant dimatiin jir."
        )

    # =====================================================
    # GET PROMPT
    # =====================================================

    if is_active(chat_id):

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
    # OWNER ONLY
    # =====================================================

    if prompt.lower() in {
        "clear",
        "/clear",
    }:

        if user_id != OWNER_ID:

            return await message.reply_text(
                "🚫 Memory jangan lu obrak-abrik jir. "
                "Cuma owner yang bisa clear."
            )

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
            # FORCE UTF-8
            # =================================================

            response.encoding = "utf-8"

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
                decode_unicode=False
            ):

                # =============================================
                # SKIP EMPTY
                # =============================================

                if not raw_line:
                    continue

                # =============================================
                # UTF-8 DECODE
                # =============================================

                line = decode_sse_line(
                    raw_line
                ).strip()

                if not line:
                    continue

                # =============================================
                # SSE DATA
                # =============================================

                if not line.startswith(
                    "data:"
                ):
                    continue

                data = line[
                    5:
                ].strip()

                # =============================================
                # DONE
                # =============================================

                if data == "[DONE]":
                    break

                # =============================================
                # JSON
                # =============================================

                try:

                    chunk = json.loads(
                        data
                    )

                except json.JSONDecodeError:

                    continue

                # =============================================
                # CHOICES
                # =============================================

                choices = (
                    chunk.get("choices")
                    or []
                )

                if not choices:
                    continue

                # =============================================
                # DELTA
                # =============================================

                delta = (
                    choices[0].get(
                        "delta"
                    )
                    or {}
                )

                # =============================================
                # CONTENT
                # =============================================

                content = delta.get(
                    "content"
                )

                if not content:
                    continue

                # =============================================
                # APPEND
                # =============================================

                result += content

                # =============================================
                # LIVE UPDATE
                # =============================================

                now = time.monotonic()

                if (
                    now - last_edit
                    >= EDIT_INTERVAL
                ):

                    # Filter tambahan untuk member.
                    display_result = (
                        clean_non_owner_response(
                            result,
                            user_id,
                        )
                    )

                    await edit_progress(
                        progress,
                        display_result,
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
            # CLEAN FINAL RESPONSE
            # =================================================

            final_result = (
                clean_non_owner_response(
                    result,
                    user_id,
                )
            )

            # =================================================
            # SAVE ASSISTANT RESPONSE
            # =================================================

            history.append(
                {
                    "role": "assistant",
                    "content": final_result,
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
            # ESCAPE HTML
            # =================================================

            escaped_result = html.escape(
                final_result
            )

            # =================================================
            # NORMAL RESPONSE
            # =================================================

            if len(
                escaped_result
            ) <= STREAM_DISPLAY_LIMIT:

                return await progress.edit_text(
                    format_blockquote(
                        final_result
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
