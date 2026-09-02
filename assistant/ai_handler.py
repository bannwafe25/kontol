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

    "Kamu bisa menggunakan formatting Telegram HTML. "
    "Gunakan <b>...</b> untuk bold. "
    "Gunakan <i>...</i> untuk italic. "
    "Gunakan <u>...</u> untuk underline. "
    "Gunakan <s>...</s> untuk strikethrough. "
    "Gunakan <code>...</code> untuk inline code. "
    "Gunakan <pre>...</pre> untuk code block. "
    "Gunakan <tg-spoiler>...</tg-spoiler> untuk spoiler. "
    "Gunakan <blockquote>...</blockquote> untuk blockquote. "
    "Jangan menggunakan Markdown seperti **bold**. "
    "Gunakan HTML Telegram."
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

    "Kamu bisa menggunakan formatting Telegram HTML. "
    "Gunakan <b>...</b> untuk bold. "
    "Gunakan <i>...</i> untuk italic. "
    "Gunakan <u>...</u> untuk underline. "
    "Gunakan <s>...</s> untuk strikethrough. "
    "Gunakan <code>...</code> untuk inline code. "
    "Gunakan <pre>...</pre> untuk code block. "
    "Gunakan <tg-spoiler>...</tg-spoiler> untuk spoiler. "
    "Gunakan <blockquote>...</blockquote> untuk blockquote. "
    "Jangan menggunakan Markdown seperti **bold**. "
    "Gunakan HTML Telegram."
)


# =========================================================
# CONFIG
# =========================================================

MAX_HISTORY = 20

# Interval edit streaming.
EDIT_INTERVAL = 0.3

# Batas tampilan satu pesan.
STREAM_DISPLAY_LIMIT = 4000

# Timeout request.
STREAM_TIMEOUT = 120

# Trigger.
TRIGGER = "xkiro"

# Stop.
STOP_TRIGGER = "stop"


# =========================================================
# MEMORY
# =========================================================

MEMORY = {}


# =========================================================
# ACTIVE CHAT
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
    """
    Mempertahankan HTML Telegram yang diperbolehkan
    dan meng-escape HTML lainnya.
    """

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
    """
    Fallback jika Telegram menolak HTML.
    """

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
    """
    Kirim message menggunakan Telegram HTML.
    """

    formatted = format_telegram(text)

    try:

        return await message.reply_text(
            formatted,
            parse_mode=ParseMode.HTML,
        )

    except Exception:

        return await message.reply_text(
            strip_html_tags(text)
        )


# =========================================================
# SAFE EDIT
# =========================================================

async def safe_edit(
    message,
    text,
):
    """
    Edit message dengan HTML.
    Jika gagal, fallback ke plain text.
    """

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

        if user_id == OWNER_ID:

            system_prompt = (
                SYSTEM_PROMPT_OWNER
            )

        else:

            system_prompt = (
                SYSTEM_PROMPT_USER
            )

        MEMORY[memory_key] = [
            {
                "role": "system",
                "content": system_prompt,
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

        LOCKS[lock_key] = (
            asyncio.Lock()
        )

    return LOCKS[lock_key]


# =========================================================
# UTF-8 DECODER
# =========================================================

def decode_sse_line(raw_line):
    """
    Decode response SSE sebagai UTF-8.

    Memperbaiki kasus seperti:

        🤙
        👊
        😂
        —
        ™

    yang berubah menjadi mojibake.
    """

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
    """
    Request streaming ke Xkiro API.
    """

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
# NON OWNER RESPONSE FILTER
# =========================================================

def clean_non_owner_response(
    text,
    user_id,
):
    """
    Member biasa tidak boleh mendapatkan
    penyebutan zp.
    """

    if user_id == OWNER_ID:
        return text

    replacements = {
        "zp": "[pemilik]",
        "ZP": "[pemilik]",
        "Zp": "[pemilik]",
        "zP": "[pemilik]",
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new,
        )

    return text


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
    # MESSAGE
    # =====================================================

    text = (
        message.text
        or ""
    ).strip()

    if not text:
        return

    # =====================================================
    # USER
    # =====================================================

    if not message.from_user:
        return

    user_id = (
        message.from_user.id
    )

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

        if user_id != OWNER_ID:

            return await safe_reply(
                message,
                (
                    "🚫 <b>Lu siapa jir?</b>\n"
                    "Cuma owner yang bisa matiin Xkiro."
                ),
            )

        ACTIVE_CHATS[
            chat_id
        ] = False

        return await safe_reply(
            message,
            "🔴 <b>Assistant dimatiin jir.</b>",
        )

    # =====================================================
    # CLEAR
    # =====================================================

    if text_lower in {
        "clear",
        "/clear",
    }:

        if user_id != OWNER_ID:

            return await safe_reply(
                message,
                (
                    "🚫 <b>Memory jangan lu obrak-abrik jir.</b>\n"
                    "Cuma owner yang bisa clear."
                ),
            )

        memory_key = get_memory_key(
            chat_id,
            user_id,
        )

        MEMORY.pop(
            memory_key,
            None,
        )

        return await safe_reply(
            message,
            "🧹 <b>Memory lu udah di-clear jir.</b>",
        )

    # =====================================================
    # CHECK ACTIVE
    # =====================================================

    if not is_active(chat_id):

        # Hanya trigger xkiro yang mengaktifkan.
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

        return await safe_reply(
            message,
            (
                "🟢 <b>Assistant aktif jir.</b>\n"
                "Ngomong aja sekarang.\n"
                "Ketik <code>stop</code> kalau mau matiin."
            ),
        )

    # =====================================================
    # API KEY
    # =====================================================

    if not XKIRO_API_KEY:

        return await safe_reply(
            message,
            "❌ <b>XKIRO_API_KEY belum diatur.</b>",
        )

    # =====================================================
    # LOCK
    # =====================================================

    lock = get_lock(
        chat_id,
        user_id,
    )

    if lock.locked():

        return await safe_reply(
            message,
            (
                "⏳ <i>Sabar napa jir, "
                "gue masih mikir yang tadi.</i>"
            ),
        )

    async with lock:

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
        # PROGRESS MESSAGE
        # =================================================

        reply_msg = await message.reply_text(
            "💭 <i>Berfikir...</i>",
            parse_mode=ParseMode.HTML,
        )

        # =================================================
        # VARIABLES
        # =================================================

        response = None

        full_response = ""

        last_edit_time = time.monotonic()

        try:

            # =============================================
            # CREATE STREAM
            # =============================================

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

                    return await safe_edit(
                        reply_msg,
                        (
                            "❌ <b>Xkiro API Error</b>\n"
                            f"Status: "
                            f"<code>{response.status_code}</code>\n"
                            f"<code>"
                            f"{html.escape(error_body)}"
                            f"</code>"
                        ),
                    )

                return await safe_edit(
                    reply_msg,
                    (
                        "❌ <b>Xkiro API Error</b>\n"
                        f"Status: "
                        f"<code>{response.status_code}</code>"
                    ),
                )

            # =============================================
            # STREAM LOOP
            # =============================================

            for raw_line in response.iter_lines(
                decode_unicode=False
            ):

                # -----------------------------------------
                # STOP CHECK
                # -----------------------------------------

                if not is_active(chat_id):

                    if full_response:

                        full_response += (
                            "\n\n"
                            "<i>[Dipotong ama owner.]</i>"
                        )

                    break

                # -----------------------------------------
                # EMPTY LINE
                # -----------------------------------------

                if not raw_line:
                    continue

                # -----------------------------------------
                # UTF-8
                # -----------------------------------------

                line = decode_sse_line(
                    raw_line
                ).strip()

                if not line:
                    continue

                # -----------------------------------------
                # SSE DATA
                # -----------------------------------------

                if not line.startswith(
                    "data:"
                ):
                    continue

                data_str = line[
                    5:
                ].strip()

                # -----------------------------------------
                # DONE
                # -----------------------------------------

                if data_str == "[DONE]":
                    break

                # -----------------------------------------
                # JSON
                # -----------------------------------------

                try:

                    data_json = json.loads(
                        data_str
                    )

                except json.JSONDecodeError:

                    continue

                # -----------------------------------------
                # CHOICES
                # -----------------------------------------

                choices = (
                    data_json.get(
                        "choices"
                    )
                    or []
                )

                if not choices:
                    continue

                # -----------------------------------------
                # DELTA
                # -----------------------------------------

                delta = (
                    choices[0].get(
                        "delta"
                    )
                    or {}
                )

                # -----------------------------------------
                # CONTENT
                # -----------------------------------------

                chunk = delta.get(
                    "content"
                )

                if not chunk:
                    continue

                # -----------------------------------------
                # APPEND
                # -----------------------------------------

                full_response += chunk

                # -----------------------------------------
                # MAX DISPLAY
                # -----------------------------------------

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

                # -----------------------------------------
                # LIVE EDIT
                # -----------------------------------------

                current_time = (
                    time.monotonic()
                )

                if (
                    current_time
                    - last_edit_time
                    >= EDIT_INTERVAL
                ):

                    display_response = (
                        clean_non_owner_response(
                            full_response,
                            user_id,
                        )
                    )

                    await safe_edit(
                        reply_msg,
                        display_response,
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

                return await safe_edit(
                    reply_msg,
                    "❌ <b>AI tidak memberikan response.</b>",
                )

            # =================================================
            # FINAL CLEAN
            # =================================================

            final_response = (
                clean_non_owner_response(
                    full_response,
                    user_id,
                )
            )

            # =================================================
            # SAVE MEMORY
            # =================================================

            history.append(
                {
                    "role": "assistant",
                    "content": final_response,
                }
            )

            trim_history(
                chat_id,
                user_id,
            )

            # =================================================
            # FINAL HTML
            # =================================================

            formatted_response = (
                format_telegram(
                    final_response
                )
            )

            # =================================================
            # NORMAL RESPONSE
            # =================================================

            if len(
                formatted_response
            ) <= STREAM_DISPLAY_LIMIT:

                return await safe_edit(
                    reply_msg,
                    final_response,
                )

            # =================================================
            # LONG RESPONSE
            # =================================================

            # HTML tidak boleh dipotong sembarangan karena
            # bisa memotong tag <b>, <code>, <pre>, dll.
            #
            # Jadi untuk response terlalu panjang,
            # fallback ke plain text chunks.

            plain_text = strip_html_tags(
                final_response
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
            # REMAINING CHUNKS
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

                    await message.reply_text(
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
        # CLOSE RESPONSE
        # =====================================================

        finally:

            if response is not None:

                try:

                    response.close()

                except Exception:

                    pass
