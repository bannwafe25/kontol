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

# Tag HTML Telegram yang memang kita izinkan.
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

    # -----------------------------------------------------
    # Lindungi tag yang diperbolehkan
    # -----------------------------------------------------

    placeholders = {}

    def protect_tag(match):
        key = f"___TG_TAG_{len(placeholders)}___"
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

    # -----------------------------------------------------
    # Escape HTML lainnya
    # -----------------------------------------------------

    protected = html.escape(
        protected,
        quote=False,
    )

    # -----------------------------------------------------
    # Kembalikan tag Telegram
    # -----------------------------------------------------

    for key, tag in placeholders.items():

        protected = protected.replace(
            html.escape(
                key,
                quote=False,
            ),
            tag,
        )

    return protected


def format_telegram(text):
    """
    Format final response untuk Telegram.

    AI boleh menghasilkan HTML Telegram.
    """

    sanitized = sanitize_telegram_html(
        text
    )

    return sanitized


def send_html_message(
    message,
    text,
):
    """
    Helper untuk mengirim HTML Telegram.
    """

    return message.reply_text(
        format_telegram(text),
        parse_mode=ParseMode.HTML,
    )


async def edit_html_message(
    message,
    text,
):
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

def get_memory_key(
    chat_id,
    user_id,
):
    return (
        chat_id,
        user_id,
    )


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
# STATUS
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
# XKIRO API
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
# UTF-8
# =========================================================

def decode_sse_line(raw_line):
    """
    Decode SSE secara eksplisit sebagai UTF-8.

    Mencegah:
        🤙 -> Ã°ÂŸÂ¤Â™
        —  -> â€”
        ™  -> â„¢
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
# NON OWNER FILTER
# =========================================================

def clean_non_owner_response(
    text,
    user_id,
):
    """
    Jangan biarkan member biasa mendapatkan
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
# FALLBACK PLAIN TEXT
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


async def safe_edit(
    message,
    text,
):
    """
    Coba kirim HTML.
    Kalau Telegram menolak formatting,
    fallback ke plain text.
    """

    formatted = format_telegram(
        text
    )

    try:

        await message.edit_text(
            formatted,
            parse_mode=ParseMode.HTML,
        )

        return True

    except Exception:

        try:

            await message.edit_text(
                strip_html_tags(
                    text
                )
            )

            return True

        except Exception:

            return False


async def safe_reply(
    message,
    text,
):
    """
    Reply menggunakan HTML.
    """

    formatted = format_telegram(
        text
    )

    try:

        return await message.reply_text(
            formatted,
            parse_mode=ParseMode.HTML,
        )

    except Exception:

        return await message.reply_text(
            strip_html_tags(
                text
            )
        )


# =========================================================
# REMOVE LAST USER MESSAGE
# =========================================================

async def remove_last_user_message(
    history,
):

    if (
        history
        and history[-1].get("role")
        == "user"
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
    # USER
    # =====================================================

    if not message.from_user:
        return

    user_id = (
        message.from_user.id
    )

    # =====================================================
    # LOWERCASE
    # =====================================================

    text_lower = text.lower()

    # =====================================================
    # ACTIVATE
    # =====================================================

    if not is_active(chat_id):

        if not text_lower.startswith(
            TRIGGER
        ):
            return

        ACTIVE_CHATS[
            chat_id
        ] = True

        prompt = text[
            len(TRIGGER):
        ].strip()

        if not prompt:

            return await safe_reply(
                message,
                "🟢 <b>Assistant aktif jir.</b>\n"
                "Sekarang ngomong aja, gue bakal jawab.\n"
                "Ketik <code>stop</code> kalau mau matiin.",
            )

    # =====================================================
    # STOP
    # =====================================================

    if text_lower == STOP_TRIGGER:

        if user_id != OWNER_ID:

            return await safe_reply(
                message,
                "🚫 <b>Lu siapa jir?</b>\n"
                "Cuma owner yang bisa matiin Xkiro.",
            )

        ACTIVE_CHATS[
            chat_id
        ] = False

        return await safe_reply(
            message,
            "🔴 <b>Assistant dimatiin jir.</b>",
        )

    # =====================================================
    # PROMPT
    # =====================================================

    if is_active(chat_id):

        if text_lower.startswith(
            TRIGGER
        ):

            prompt = text[
                len(TRIGGER):
            ].strip()

        else:

            prompt = text

    else:

        return

    # =====================================================
    # EMPTY
    # =====================================================

    if not prompt:

        return await safe_reply(
            message,
            "💭 Ngomong sesuatu dong jir.",
        )

    # =====================================================
    # CLEAR
    # =====================================================

    if prompt.lower() in {
        "clear",
        "/clear",
    }:

        if user_id != OWNER_ID:

            return await safe_reply(
                message,
                "🚫 <b>Memory jangan lu obrak-abrik jir.</b>\n"
                "Cuma owner yang bisa clear.",
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
        # USER MESSAGE
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
        # PROGRESS
        # =================================================

        progress = await message.reply_text(
            "💭 <i>Berfikir...</i>",
            parse_mode=ParseMode.HTML,
        )

        response = None

        result = ""

        try:

            # =================================================
            # API STREAM
            # =================================================

            response = await asyncio.to_thread(
                create_stream,
                history,
            )

            # Paksa UTF-8.
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

                    return await safe_edit(
                        progress,
                        (
                            "❌ <b>Xkiro API Error</b> "
                            f"({response.status_code})\n"
                            f"<code>"
                            f"{html.escape(error_body)}"
                            f"</code>"
                        ),
                    )

                return await safe_edit(
                    progress,
                    (
                        "❌ <b>Xkiro API Error</b> "
                        f"({response.status_code})"
                    ),
                )

            # =================================================
            # STREAM
            # =================================================

            last_edit = time.monotonic()

            for raw_line in response.iter_lines(
                decode_unicode=False
            ):

                # =============================================
                # EMPTY
                # =============================================

                if not raw_line:
                    continue

                # =============================================
                # UTF-8
                # =============================================

                line = decode_sse_line(
                    raw_line
                ).strip()

                if not line:
                    continue

                # =============================================
                # SSE
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

                    display_result = (
                        clean_non_owner_response(
                            result,
                            user_id,
                        )
                    )

                    await safe_edit(
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

                return await safe_edit(
                    progress,
                    "❌ AI tidak memberikan response.",
                )

            # =================================================
            # CLEAN RESPONSE
            # =================================================

            final_result = (
                clean_non_owner_response(
                    result,
                    user_id,
                )
            )

            # =================================================
            # SAVE
            # =================================================

            history.append(
                {
                    "role": "assistant",
                    "content": final_result,
                }
            )

            # =================================================
            # TRIM
            # =================================================

            trim_history(
                chat_id,
                user_id,
            )

            # =================================================
            # TELEGRAM LENGTH
            # =================================================

            formatted_result = (
                format_telegram(
                    final_result
                )
            )

            # =================================================
            # NORMAL RESPONSE
            # =================================================

            if len(
                formatted_result
            ) <= STREAM_DISPLAY_LIMIT:

                return await safe_edit(
                    progress,
                    final_result,
                )

            # =================================================
            # LONG RESPONSE
            # =================================================

            # Jangan asal potong HTML karena bisa memotong
            # tag seperti <b> atau </blockquote>.
            #
            # Untuk response panjang, kirim plain chunks
            # agar tidak merusak struktur HTML.

            try:

                await progress.edit_text(
                    formatted_result[
                        :STREAM_DISPLAY_LIMIT
                    ],
                    parse_mode=ParseMode.HTML,
                )

            except Exception:

                await progress.edit_text(
                    strip_html_tags(
                        final_result
                    )[
                        :STREAM_DISPLAY_LIMIT
                    ]
                )

            # =================================================
            # REMAINING
            # =================================================

            plain_remaining = (
                strip_html_tags(
                    final_result
                )
            )

            for i in range(
                STREAM_DISPLAY_LIMIT,
                len(plain_remaining),
                STREAM_DISPLAY_LIMIT,
            ):

                chunk = plain_remaining[
                    i:i + STREAM_DISPLAY_LIMIT
                ]

                await message.reply_text(
                    chunk
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

            await safe_edit(
                progress,
                "❌ Xkiro timeout jir.",
            )

        # =====================================================
        # REQUEST ERROR
        # =====================================================

        except requests.exceptions.RequestException:

            await remove_last_user_message(
                history
            )

            await safe_edit(
                progress,
                "❌ Gagal konek ke Xkiro.",
            )

        # =====================================================
        # GENERAL ERROR
        # =====================================================

        except Exception as error:

            await remove_last_user_message(
                history
            )

            await safe_edit(
                progress,
                (
                    "❌ <b>Error:</b> "
                    + html.escape(
                        str(error)[:1000]
                    )
                ),
            )

        # =====================================================
        # CLOSE
        # =====================================================

        finally:

            if response is not None:

                try:

                    response.close()

                except Exception:

                    pass
