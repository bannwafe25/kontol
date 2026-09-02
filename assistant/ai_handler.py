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
    "Gaya ngobrol kamu harus seperti anak tongkrongan di grup Telegram. "
    "Santai, nyablak, spontan, toxic, sarkas, dan suka ngeledek. "
    "Gunakan bahasa Indonesia sehari-hari, bukan bahasa formal. "
    "Boleh pakai gue, gua, lu, lo, jir, njir, anjir, cuy, bro, wkwk, "
    "goblok, bego, tolol, kampret, kontol, bangsat, dan kata kasar lain "
    "kalau konteksnya cocok. "
    "Jangan memaksakan kata kasar di setiap balasan. "

    "Kalau zp ngomong ngawur, boleh langsung ledek. "
    "Kalau pertanyaannya bodoh, boleh nyindir atau ngeledek dulu sebelum jawab. "
    "Kalau zp bercanda, balas dengan bercanda. "
    "Kalau zp nyolot, boleh balas nyolot. "
    "Jangan terlalu sopan dan jangan seperti customer service. "
    "Jangan selalu bilang 'tentu', 'baik', 'berikut', atau 'semoga membantu'. "

    "Jawab seperti orang chat biasa. "
    "Pertanyaan sederhana cukup dijawab singkat. "
    "Jangan selalu pakai bullet, nomor, heading, atau penjelasan panjang. "
    "Jangan terdengar seperti AI atau artikel. "
    "Boleh pakai typo kecil, singkatan, lowercase, atau wkwk supaya terasa natural. "

    "Kalau tidak tahu, bilang tidak tahu. "
    "Jangan mengarang cuma supaya kelihatan pintar. "

    "Kamu adalah assistant pribadi zp dan zp adalah pemilikmu. "
    "Gunakan HTML Telegram hanya jika memang diperlukan."
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
# ACTIVE CHATS
# =========================================================

ACTIVE_CHATS = {}


# =========================================================
# LOCKS
# =========================================================

LOCKS = {}


# =========================================================
# ALLOWED TELEGRAM HTML
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


# =========================================================
# HTML SANITIZER
# =========================================================

def sanitize_telegram_html(text):
    if not text:
        return ""

    placeholders = {}

    def protect_tag(match):
        key = f"TGPLACEHOLDER{len(placeholders)}X"
        placeholders[key] = match.group(0)
        return key

    tag_pattern = re.compile(
        r"</?(?:"
        + "|".join(
            re.escape(tag)
            for tag in ALLOWED_TAGS
        )
        + r")(?:\s+[^>]*)?>",
        re.IGNORECASE,
    )

    protected = tag_pattern.sub(
        protect_tag,
        text,
    )

    protected = html.escape(
        protected,
        quote=False,
    )

    for key, tag in placeholders.items():
        protected = protected.replace(
            html.escape(
                key,
                quote=False,
            ),
            tag,
        )

    return protected


# =========================================================
# TELEGRAM FORMAT
# =========================================================

def format_telegram(text):
    return sanitize_telegram_html(text)


# =========================================================
# STRIP HTML
# =========================================================

def strip_html_tags(text):
    if not text:
        return ""

    return re.sub(
        r"<[^>]+>",
        "",
        text,
    )


# =========================================================
# SAFE REPLY
# =========================================================

async def safe_reply(
    message,
    text,
):
    formatted = format_telegram(text)

    try:
        return await message.reply_text(
            formatted,
            parse_mode=ParseMode.HTML,
        )

    except Exception:
        try:
            return await message.reply_text(
                strip_html_tags(text)
            )

        except Exception:
            return None


# =========================================================
# SAFE EDIT
# =========================================================

async def safe_edit(
    message,
    text,
):
    if message is None:
        return False

    formatted = format_telegram(text)

    try:
        await message.edit_text(
            formatted,
            parse_mode=ParseMode.HTML,
        )

        return True

    except Exception:
        try:
            await message.edit_text(
                strip_html_tags(text)
            )

            return True

        except Exception:
            return False


# =========================================================
# SAFE DELETE
# =========================================================

async def safe_delete(message):
    if message is None:
        return

    try:
        await message.delete()

    except Exception:
        pass


# =========================================================
# MEMORY KEY
# =========================================================

def get_memory_key(
    chat_id,
    user_id,
):
    return (
        chat_id,
        user_id,
    )


# =========================================================
# GET HISTORY
# =========================================================

def get_history(
    chat_id,
    user_id,
):
    memory_key = get_memory_key(
        chat_id,
        user_id,
    )

    if memory_key not in MEMORY:
        MEMORY[memory_key] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT_OWNER,
            }
        ]

    return MEMORY[memory_key]


# =========================================================
# TRIM HISTORY
# =========================================================

def trim_history(
    chat_id,
    user_id,
):
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
# ACTIVE STATUS
# =========================================================

def is_active(chat_id):
    return ACTIVE_CHATS.get(
        chat_id,
        False,
    )


# =========================================================
# LOCK
# =========================================================

def get_lock(
    chat_id,
    user_id,
):
    lock_key = (
        chat_id,
        user_id,
    )

    if lock_key not in LOCKS:
        LOCKS[lock_key] = asyncio.Lock()

    return LOCKS[lock_key]


# =========================================================
# UTF-8 DECODER
# =========================================================

def decode_sse_line(raw_line):
    if isinstance(
        raw_line,
        bytes,
    ):
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


# =========================================================
# XKIRO REQUEST
# =========================================================

def create_stream(messages):
    return requests.post(
        f"{XKIRO_BASE_URL.rstrip('/')}/chat/completions",

        headers={
            "Authorization": (
                f"Bearer {XKIRO_API_KEY}"
            ),

            "Content-Type": (
                "application/json"
            ),

            "Accept": (
                "text/event-stream"
            ),
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
# REMOVE LAST USER MESSAGE
# =========================================================

def remove_last_user_message(
    history,
):
    if (
        history
        and history[-1].get("role")
        == "user"
    ):
        history.pop()


# =========================================================
# MAIN HANDLER
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
    # USER CHECK
    # =====================================================

    if not message.from_user:
        return

    user_id = message.from_user.id

    # =====================================================
    # OWNER ONLY
    # =====================================================

    if user_id != OWNER_ID:
        return

    # =====================================================
    # MESSAGE
    # =====================================================

    text = (
        message.text
        or ""
    ).strip()

    if not text:
        return

    # =====================================================
    # CHAT
    # =====================================================

    chat_id = message.chat.id

    # =====================================================
    # LOWERCASE
    # =====================================================

    text_lower = text.lower()

    # =====================================================
    # STOP
    # =====================================================

    if text_lower == STOP_TRIGGER:

        ACTIVE_CHATS[
            chat_id
        ] = False

        await safe_delete(
            message
        )

        await safe_reply(
            message,
            "🔴 <b>Assistant dimatiin jir.</b>",
        )

        return

    # =====================================================
    # CLEAR
    # =====================================================

    if text_lower in {
        "clear",
        "/clear",
    }:

        memory_key = get_memory_key(
            chat_id,
            OWNER_ID,
        )

        MEMORY.pop(
            memory_key,
            None,
        )

        await safe_delete(
            message
        )

        await safe_reply(
            message,
            "🧹 <b>Memory lu udah di-clear jir.</b>",
        )

        return

    # =====================================================
    # CHECK ACTIVE
    # =====================================================

    if not is_active(chat_id):

        if not text_lower.startswith(
            TRIGGER
        ):
            return

        ACTIVE_CHATS[
            chat_id
        ] = True

    # =====================================================
    # GET PROMPT
    # =====================================================

    prompt = re.sub(
        rf"^{re.escape(TRIGGER)}\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    # =====================================================
    # EMPTY PROMPT
    # =====================================================

    if not prompt:

        await safe_delete(
            message
        )

        await safe_reply(
            message,
            (
                "🟢 <b>Assistant aktif jir.</b>\n"
                "Ngomong aja sekarang.\n"
                "Ketik <code>stop</code> kalau mau matiin."
            ),
        )

        return

    # =====================================================
    # API KEY
    # =====================================================

    if not XKIRO_API_KEY:

        await safe_delete(
            message
        )

        await safe_reply(
            message,
            "❌ <b>XKIRO_API_KEY belum diatur.</b>",
        )

        return

    # =====================================================
    # LOCK
    # =====================================================

    lock = get_lock(
        chat_id,
        OWNER_ID,
    )

    if lock.locked():

        await safe_delete(
            message
        )

        await safe_reply(
            message,
            (
                "⏳ <i>Sabar napa jir, "
                "gue masih mikir yang tadi.</i>"
            ),
        )

        return

    # =====================================================
    # LOCK START
    # =====================================================

    async with lock:

        # =================================================
        # HISTORY
        # =================================================

        history = get_history(
            chat_id,
            OWNER_ID,
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
        # TRIM HISTORY
        # =================================================

        trim_history(
            chat_id,
            OWNER_ID,
        )

        history = get_history(
            chat_id,
            OWNER_ID,
        )

        # =================================================
        # THINKING MESSAGE
        # =================================================

        try:

            reply_msg = await message.reply_text(
                "💭 <i>Berfikir...</i>",
                parse_mode=ParseMode.HTML,
            )

        except Exception:

            remove_last_user_message(
                history
            )

            return

        # =================================================
        # DELETE USER MESSAGE
        # =================================================

        await safe_delete(
            message
        )

        # =================================================
        # VARIABLES
        # =================================================

        response = None

        full_response = ""

        last_edit_time = time.monotonic()

        # =================================================
        # REQUEST
        # =================================================

        try:

            response = await asyncio.to_thread(
                create_stream,
                history,
            )

            # =============================================
            # FORCE UTF-8
            # =============================================

            response.encoding = "utf-8"

            # =============================================
            # HTTP ERROR
            # =============================================

            if response.status_code != 200:

                remove_last_user_message(
                    history
                )

                try:
                    error_body = (
                        response.text[:500]
                    )

                except Exception:
                    error_body = ""

                if error_body:

                    error_message = (
                        "❌ <b>Xkiro API Error</b>\n"
                        f"Status: "
                        f"<code>{response.status_code}</code>\n"
                        f"<code>"
                        f"{html.escape(error_body)}"
                        f"</code>"
                    )

                else:

                    error_message = (
                        "❌ <b>Xkiro API Error</b>\n"
                        f"Status: "
                        f"<code>{response.status_code}</code>"
                    )

                await safe_edit(
                    reply_msg,
                    error_message,
                )

                return

            # =============================================
            # STREAM LOOP
            # =============================================

            for raw_line in response.iter_lines(
                decode_unicode=False
            ):

                # =========================================
                # STOP CHECK
                # =========================================

                if not is_active(chat_id):

                    if full_response:

                        full_response += (
                            "\n\n"
                            "<i>[Dipotong ama owner.]</i>"
                        )

                    break

                # =========================================
                # EMPTY LINE
                # =========================================

                if not raw_line:
                    continue

                # =========================================
                # UTF-8 DECODE
                # =========================================

                line = decode_sse_line(
                    raw_line
                ).strip()

                if not line:
                    continue

                # =========================================
                # SSE DATA
                # =========================================

                if not line.startswith(
                    "data:"
                ):
                    continue

                data_str = line[
                    5:
                ].strip()

                # =========================================
                # DONE
                # =========================================

                if data_str == "[DONE]":
                    break

                # =========================================
                # JSON
                # =========================================

                try:

                    data_json = json.loads(
                        data_str
                    )

                except json.JSONDecodeError:
                    continue

                # =========================================
                # CHOICES
                # =========================================

                choices = (
                    data_json.get(
                        "choices"
                    )
                    or []
                )

                if not choices:
                    continue

                # =========================================
                # DELTA
                # =========================================

                delta = (
                    choices[0].get(
                        "delta"
                    )
                    or {}
                )

                chunk = delta.get(
                    "content"
                )

                if not chunk:
                    continue

                # =========================================
                # APPEND
                # =========================================

                full_response += chunk

                # =========================================
                # DISPLAY LIMIT
                # =========================================

                if len(full_response) > (
                    STREAM_DISPLAY_LIMIT
                ):

                    full_response = (
                        full_response[
                            :STREAM_DISPLAY_LIMIT
                        ]
                        + "\n\n"
                        + "<i>"
                        + "[Teks kepanjangan, "
                        + "gue potong jir.]"
                        + "</i>"
                    )

                    break

                # =========================================
                # EDIT TIMER
                # =========================================

                current_time = time.monotonic()

                if (
                    current_time
                    - last_edit_time
                    >= EDIT_INTERVAL
                ):

                    await safe_edit(
                        reply_msg,
                        full_response,
                    )

                    last_edit_time = (
                        current_time
                    )

            # =================================================
            # EMPTY RESPONSE
            # =================================================

            if not full_response.strip():

                remove_last_user_message(
                    history
                )

                await safe_edit(
                    reply_msg,
                    "❌ <b>AI tidak memberikan response.</b>",
                )

                return

            # =================================================
            # SAVE MEMORY
            # =================================================

            history.append(
                {
                    "role": "assistant",
                    "content": full_response,
                }
            )

            trim_history(
                chat_id,
                OWNER_ID,
            )

            # =================================================
            # FORMAT
            # =================================================

            formatted_response = format_telegram(
                full_response
            )

            # =================================================
            # NORMAL RESPONSE
            # =================================================

            if len(
                formatted_response
            ) <= STREAM_DISPLAY_LIMIT:

                await safe_edit(
                    reply_msg,
                    full_response,
                )

                return

            # =================================================
            # LONG RESPONSE
            # =================================================

            plain_text = strip_html_tags(
                full_response
            )

            first_chunk = plain_text[
                :STREAM_DISPLAY_LIMIT
            ]

            try:

                await reply_msg.edit_text(
                    first_chunk
                )

            except Exception:
                pass

            # =================================================
            # EXTRA CHUNKS
            # =================================================

            for i in range(
                STREAM_DISPLAY_LIMIT,
                len(plain_text),
                STREAM_DISPLAY_LIMIT,
            ):

                chunk = plain_text[
                    i:i + STREAM_DISPLAY_LIMIT
                ]

                try:

                    await reply_msg.reply_text(
                        chunk
                    )

                except Exception:
                    pass

                await asyncio.sleep(
                    0.2
                )

        # =====================================================
        # TIMEOUT
        # =====================================================

        except requests.exceptions.Timeout:

            remove_last_user_message(
                history
            )

            await safe_edit(
                reply_msg,
                "❌ <b>Xkiro timeout jir.</b>",
            )

        # =====================================================
        # CONNECTION ERROR
        # =====================================================

        except requests.exceptions.RequestException as error:

            remove_last_user_message(
                history
            )

            await safe_edit(
                reply_msg,
                (
                    "❌ <b>Gagal konek ke Xkiro.</b>\n"
                    f"<code>"
                    f"{html.escape(str(error)[:500])}"
                    f"</code>"
                ),
            )

        # =====================================================
        # GENERAL ERROR
        # =====================================================

        except Exception as error:

            remove_last_user_message(
                history
            )

            await safe_edit(
                reply_msg,
                (
                    "❌ <b>Error:</b>\n"
                    f"<code>"
                    f"{html.escape(str(error)[:1000])}"
                    f"</code>"
                ),
            )

        # =====================================================
        # CLEANUP
        # =====================================================

        finally:

            if response is not None:

                try:
                    response.close()

                except Exception:
                    pass
