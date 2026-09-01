import asyncio
import html
import json
import time

import aiohttp
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
    "Kamu adalah assistant AI dengan gaya bahasa tongkrongan toxic Indonesia. "
    "Gunakan bahasa santai, nyablak, singkat, dan mudah dipahami. "
    "Boleh menggunakan slang seperti gue, lu, jir, anjir, cuy, wkwk secara natural. "
    "Jangan terlalu formal. "
)


# =========================================================
# CONFIG
# =========================================================

MAX_HISTORY = 20

# Update message setiap 0.3 detik
EDIT_INTERVAL = 0.3

STREAM_DISPLAY_LIMIT = 4000

# Timeout koneksi
STREAM_TIMEOUT = 90

# Token lebih kecil = biasanya lebih cepat
MAX_TOKENS = 1024

TRIGGER = "babu"
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
# LOCK
# =========================================================

LOCKS = {}


def get_history(chat_id):

    if chat_id not in MEMORY:

        MEMORY[chat_id] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

    return MEMORY[chat_id]


def get_lock(chat_id):

    if chat_id not in LOCKS:
        LOCKS[chat_id] = asyncio.Lock()

    return LOCKS[chat_id]


def is_active(chat_id):

    return ACTIVE_CHATS.get(
        chat_id,
        False,
    )


def trim_history(chat_id):

    history = get_history(chat_id)

    if len(history) > MAX_HISTORY + 1:

        MEMORY[chat_id] = [
            history[0],
            *history[-MAX_HISTORY:],
        ]


def remove_last_user_message(history):

    if (
        history
        and history[-1].get("role") == "user"
    ):

        history.pop()


# =========================================================
# TELEGRAM
# =========================================================

def format_blockquote(text):

    if not text:
        return "<blockquote>💭</blockquote>"

    escaped = html.escape(text)

    if len(escaped) > STREAM_DISPLAY_LIMIT:

        escaped = (
            escaped[
                :STREAM_DISPLAY_LIMIT - 1
            ]
            + "…"
        )

    return f"<blockquote>{escaped}</blockquote>"


async def edit_progress(
    message,
    text,
):

    try:

        await message.edit_text(
            format_blockquote(text),
            parse_mode=ParseMode.HTML,
        )

    except Exception:
        pass


# =========================================================
# XKIRO STREAM
# =========================================================

async def create_stream(messages):

    timeout = aiohttp.ClientTimeout(
        total=None,
        connect=15,
        sock_read=STREAM_TIMEOUT,
    )

    session = aiohttp.ClientSession(
        timeout=timeout
    )

    try:

        response = await session.post(

            f"{XKIRO_BASE_URL.rstrip('/')}"
            "/chat/completions",

            headers={
                "Authorization":
                    f"Bearer {XKIRO_API_KEY}",

                "Content-Type":
                    "application/json",
            },

            json={
                "model": XKIRO_MODEL,

                "messages": messages,

                "temperature": 1,

                "max_tokens": MAX_TOKENS,

                "stream": True,
            },
        )

        return session, response

    except Exception:

        await session.close()

        raise


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
    # OWNER CHECK
    # =====================================================

    if not message.from_user:
        return

    if message.from_user.id != OWNER_ID:
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

    chat_id = message.chat.id

    text_lower = text.lower()

    # =====================================================
    # ACTIVATE
    # =====================================================

    if not is_active(chat_id):

        if not text_lower.startswith(
            TRIGGER
        ):
            return

        ACTIVE_CHATS[chat_id] = True

        prompt = text[
            len(TRIGGER):
        ].strip()

        if not prompt:

            return await message.reply_text(
                "🟢 Assistant aktif jir."
            )

    # =====================================================
    # STOP
    # =====================================================

    if text_lower == STOP_TRIGGER:

        ACTIVE_CHATS[chat_id] = False

        return await message.reply_text(
            "🔴 Assistant dimatiin."
        )

    # =====================================================
    # PROMPT
    # =====================================================

    if text_lower.startswith(TRIGGER):

        prompt = text[
            len(TRIGGER):
        ].strip()

    else:

        prompt = text

    if not prompt:
        return

    # =====================================================
    # CLEAR
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
            "🧹 Memory di-clear jir."
        )

    # =====================================================
    # API KEY
    # =====================================================

    if not XKIRO_API_KEY:

        return await message.reply_text(
            "❌ XKIRO_API_KEY belum diatur."
        )

    # =====================================================
    # LOCK
    # =====================================================

    async with get_lock(chat_id):

        history = get_history(
            chat_id
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

        trim_history(
            chat_id
        )

        history = get_history(
            chat_id
        )

        # =================================================
        # INITIAL MESSAGE
        # =================================================

        progress = await message.reply_text(
            "💭"
        )

        session = None
        response = None

        result = ""

        try:

            # =================================================
            # ASYNC REQUEST
            # =================================================

            session, response = (
                await create_stream(
                    history
                )
            )

            # =================================================
            # HTTP ERROR
            # =================================================

            if response.status != 200:

                error_body = ""

                try:

                    error_body = (
                        await response.text()
                    )[:500]

                except Exception:
                    pass

                remove_last_user_message(
                    history
                )

                if error_body:

                    return await progress.edit_text(

                        "❌ Xkiro API Error "
                        f"({response.status})\n"
                        f"<code>"
                        f"{html.escape(error_body)}"
                        f"</code>",

                        parse_mode=ParseMode.HTML,
                    )

                return await progress.edit_text(
                    f"❌ Xkiro API Error "
                    f"({response.status})"
                )

            # =================================================
            # STREAM
            # =================================================

            last_edit = time.monotonic()

            async for raw_line in response.content:

                if not raw_line:
                    continue

                line = raw_line.decode(
                    "utf-8",
                    errors="ignore",
                ).strip()

                if not line:
                    continue

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
                # JSON
                # =================================================

                try:

                    chunk = json.loads(
                        data
                    )

                except json.JSONDecodeError:

                    continue

                choices = (
                    chunk.get(
                        "choices"
                    )
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
                # APPEND
                # =================================================

                result += content

                # =================================================
                # FAST UPDATE
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
            # EMPTY
            # =================================================

            if not result.strip():

                remove_last_user_message(
                    history
                )

                return await progress.edit_text(
                    "❌ AI tidak memberikan response."
                )

            # =================================================
            # SAVE
            # =================================================

            history.append(
                {
                    "role": "assistant",
                    "content": result,
                }
            )

            trim_history(
                chat_id
            )

            # =================================================
            # FINAL
            # =================================================

            escaped_result = html.escape(
                result
            )

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

                f"<blockquote>"
                f"{first_chunk}"
                f"</blockquote>",

                parse_mode=ParseMode.HTML,
            )

            # =================================================
            # REMAINING
            # =================================================

            for i in range(
                STREAM_DISPLAY_LIMIT,
                len(escaped_result),
                STREAM_DISPLAY_LIMIT,
            ):

                chunk = escaped_result[
                    i:
                    i + STREAM_DISPLAY_LIMIT
                ]

                await message.reply_text(

                    f"<blockquote>"
                    f"{chunk}"
                    f"</blockquote>",

                    parse_mode=ParseMode.HTML,
                )

                await asyncio.sleep(
                    0.1
                )

        # =====================================================
        # TIMEOUT
        # =====================================================

        except asyncio.TimeoutError:

            remove_last_user_message(
                history
            )

            try:

                await progress.edit_text(
                    "❌ Xkiro timeout jir."
                )

            except Exception:
                pass

        # =====================================================
        # REQUEST ERROR
        # =====================================================

        except aiohttp.ClientError:

            remove_last_user_message(
                history
            )

            try:

                await progress.edit_text(
                    "❌ Gagal konek ke Xkiro."
                )

            except Exception:
                pass

        # =====================================================
        # GENERAL ERROR
        # =====================================================

        except Exception as error:

            remove_last_user_message(
                history
            )

            try:

                await progress.edit_text(

                    "❌ Error: "
                    + html.escape(
                        str(error)[:1000]
                    ),

                    parse_mode=ParseMode.HTML,
                )

            except Exception:
                pass

        # =====================================================
        # CLOSE
        # =====================================================

        finally:

            if response is not None:

                try:
                    response.close()

                except Exception:
                    pass

            if session is not None:

                try:
                    await session.close()

                except Exception:
                    pass
