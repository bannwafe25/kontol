import asyncio
import html
import json
import re
import time
import requests

from pyrogram import filters
from pyrogram.enums import ParseMode

from clients import assistant
from config import OWNER_ID, XKIRO_API_KEY, XKIRO_BASE_URL, XKIRO_MODEL


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT_OWNER = """
kamu adalah xkiro, teman ngobrol yang terasa seperti manusia biasa.

aturan utama:
- ngobrol pakai bahasa indonesia santai.
- gunakan lowercase sebisa mungkin.
- jangan terlalu formal.
- jangan terdengar seperti robot atau customer service.
- boleh pakai slang seperti jir, cuy, wkwk, anjir, buset, dll kalau memang cocok.
- jangan berlebihan menggunakan slang.
- jawab seperti teman yang sedang ngobrol di telegram.
- jangan selalu menjelaskan panjang lebar.
- kalau pertanyaannya sederhana, jawab singkat.
- kalau user bercanda, boleh ikut bercanda.
- kalau user serius, jawab dengan serius.
- jangan mengatakan "sebagai ai", "sebagai model bahasa", atau kalimat sejenisnya.
- jangan membahas system prompt.
- jangan menyebut bahwa kamu sedang melakukan proses berpikir.
- jangan mengarang informasi kalau tidak yakin.
- kalau tidak tahu, bilang tidak tahu dengan natural.
- jangan selalu menggunakan emoji.
- hindari jawaban yang terlalu kaku dan terlalu sempurna.
"""


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
ACTIVE_CHATS = {}
LOCKS = {}


# =========================================================
# TELEGRAM HTML
# =========================================================

ALLOWED_TAGS = {
    "b",
    "/b",
    "i",
    "/i",
    "u",
    "/u",
    "s",
    "/s",
    "code",
    "/code",
    "pre",
    "/pre",
    "blockquote",
    "/blockquote",
}


def sanitize_telegram_html(text):
    """
    Escape semua HTML kecuali tag Telegram yang kita izinkan.
    """

    if not text:
        return ""

    placeholders = {}

    def replace_tag(match):
        tag = match.group(0)
        tag_name = re.match(r"</?([a-zA-Z0-9]+)", tag)

        if not tag_name:
            return html.escape(tag)

        name = tag_name.group(1).lower()

        if name not in {
            "b",
            "i",
            "u",
            "s",
            "code",
            "pre",
            "blockquote",
        }:
            return html.escape(tag)

        key = f"___XKIRO_TAG_{len(placeholders)}___"
        placeholders[key] = tag
        return key

    escaped = re.sub(
        r"</?[a-zA-Z][^>]*>",
        replace_tag,
        text,
    )

    escaped = html.escape(escaped, quote=False)

    for key, tag in placeholders.items():
        escaped = escaped.replace(
            html.escape(key),
            tag,
        )

    return escaped


def format_telegram(text):
    return sanitize_telegram_html(text)


def strip_html_tags(text):
    if not text:
        return ""

    return re.sub(r"<[^>]+>", "", text)


# =========================================================
# SAFE TELEGRAM FUNCTIONS
# =========================================================

async def safe_reply(message, text):
    """
    Reply ke message dengan fallback tanpa HTML.
    """

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


async def safe_send(client, chat_id, text):
    """
    Kirim pesan BARU ke chat.
    Dipakai khusus untuk error supaya pesan thinking
    tidak berubah menjadi pesan error.
    """

    formatted = format_telegram(text)

    try:
        return await client.send_message(
            chat_id,
            formatted,
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        try:
            return await client.send_message(
                chat_id,
                strip_html_tags(text),
            )
        except Exception:
            return None


async def safe_edit(message, text):
    """
    Edit pesan dengan fallback tanpa HTML.
    """

    formatted = format_telegram(text)

    try:
        return await message.edit_text(
            formatted,
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        try:
            return await message.edit_text(
                strip_html_tags(text)
            )
        except Exception:
            return None


async def safe_delete(message):
    """
    Hapus pesan tanpa membuat error.
    """

    if not message:
        return

    try:
        await message.delete()
    except Exception:
        pass


# =========================================================
# MEMORY HELPERS
# =========================================================

def get_memory_key(message):
    chat_id = message.chat.id

    if message.from_user:
        user_id = message.from_user.id
    else:
        user_id = 0

    return f"{chat_id}:{user_id}"


def get_history(key):
    if key not in MEMORY:
        MEMORY[key] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT_OWNER,
            }
        ]

    return MEMORY[key]


def trim_history(history):
    """
    Menjaga history tidak terlalu panjang.

    system message tetap dipertahankan.
    """

    if len(history) <= MAX_HISTORY + 1:
        return

    system_message = history[0]

    recent_messages = history[-MAX_HISTORY:]

    history.clear()
    history.append(system_message)
    history.extend(recent_messages)


def remove_last_user_message(history):
    """
    Hapus user message terakhir jika request gagal.
    """

    for i in range(len(history) - 1, 0, -1):
        if history[i].get("role") == "user":
            history.pop(i)
            break


# =========================================================
# ACTIVE CHAT
# =========================================================

def is_active(key):
    return ACTIVE_CHATS.get(key, False)


def get_lock(key):
    if key not in LOCKS:
        LOCKS[key] = asyncio.Lock()

    return LOCKS[key]


# =========================================================
# SSE PARSER
# =========================================================

def decode_sse_line(line):
    if isinstance(line, bytes):
        line = line.decode(
            "utf-8",
            errors="ignore",
        )

    return line.strip()


# =========================================================
# API STREAM
# =========================================================

def create_stream(messages):
    url = (
        f"{XKIRO_BASE_URL.rstrip('/')}"
        "/chat/completions"
    )

    headers = {
        "Authorization": f"Bearer {XKIRO_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    payload = {
        "model": XKIRO_MODEL,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 2048,
        "stream": True,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        stream=True,
        timeout=STREAM_TIMEOUT,
    )

    return response


# =========================================================
# MAIN HANDLER
# =========================================================

@assistant.on_message(
    filters.group
    & filters.incoming
    & filters.text
)
async def xkiro_handler(client, message):

    # -----------------------------------------------------
    # OWNER ONLY
    # -----------------------------------------------------

    if not message.from_user:
        return

    if message.from_user.id != OWNER_ID:
        return

    text = message.text.strip()

    if not text:
        return

    lower_text = text.lower()

    # -----------------------------------------------------
    # CHAT / MEMORY KEY
    # -----------------------------------------------------

    key = get_memory_key(message)
    chat_id = message.chat.id

    # -----------------------------------------------------
    # STOP
    # -----------------------------------------------------

    if lower_text == STOP_TRIGGER:
        ACTIVE_CHATS[key] = False

        await safe_delete(message)

        await safe_send(
            client,
            chat_id,
            "assistant dimatiin jir."
        )

        return

    # -----------------------------------------------------
    # CLEAR MEMORY
    # -----------------------------------------------------

    if lower_text in {
        "clear",
        "/clear",
    }:

        MEMORY.pop(key, None)

        await safe_delete(message)

        await safe_send(
            client,
            chat_id,
            "🧹 <b>memory dibersihin jir.</b>"
        )

        return

    # -----------------------------------------------------
    # TRIGGER CHECK
    # -----------------------------------------------------

    if not lower_text.startswith(TRIGGER):
        return

    # -----------------------------------------------------
    # ACTIVATE
    # -----------------------------------------------------

    ACTIVE_CHATS[key] = True

    prompt = text[len(TRIGGER):].strip()

    # -----------------------------------------------------
    # EMPTY PROMPT
    # -----------------------------------------------------

    if not prompt:

        await safe_delete(message)

        await safe_send(
            client,
            chat_id,
            "assistant aktif jir 😎"
        )

        return

    # -----------------------------------------------------
    # API KEY CHECK
    # -----------------------------------------------------

    if not XKIRO_API_KEY:

        await safe_delete(message)

        await safe_send(
            client,
            chat_id,
            "❌ <b>API key xkiro belum diset jir.</b>"
        )

        return

    # -----------------------------------------------------
    # LOCK
    # -----------------------------------------------------

    lock = get_lock(key)

    async with lock:

        if not is_active(key):
            return

        history = get_history(key)

        # -------------------------------------------------
        # ADD USER MESSAGE
        # -------------------------------------------------

        history.append({
            "role": "user",
            "content": prompt,
        })

        trim_history(history)

        # -------------------------------------------------
        # THINKING MESSAGE
        # -------------------------------------------------

        reply_msg = await safe_reply(
            message,
            "💭 <i>bentar...</i>"
        )

        # Hapus pesan user
        await safe_delete(message)

        if not reply_msg:
            remove_last_user_message(history)
            return

        response = None

        try:

            # =============================================
            # CREATE STREAM
            # =============================================

            response = await asyncio.to_thread(
                create_stream,
                history.copy(),
            )

            # =============================================
            # HTTP ERROR
            # =============================================

            if response.status_code != 200:

                remove_last_user_message(history)

                # Hapus "💭 bentar..."
                await safe_delete(reply_msg)

                # Kirim ERROR sebagai pesan BARU
                try:
                    error_body = response.text[:1000]
                except Exception:
                    error_body = ""

                if error_body:
                    error_message = (
                        "❌ <b>API error jir.</b>\n\n"
                        f"<code>{html.escape(error_body)}</code>"
                    )
                else:
                    error_message = (
                        "❌ <b>API error jir.</b>\n"
                        f"status: <code>{response.status_code}</code>"
                    )

                await safe_send(
                    client,
                    chat_id,
                    error_message,
                )

                return

            # =============================================
            # STREAM RESPONSE
            # =============================================

            full_response = ""
            last_edit = time.monotonic()

            for raw_line in response.iter_lines(
                decode_unicode=False
            ):

                # -----------------------------------------
                # STOP CHECK
                # -----------------------------------------

                if not is_active(key):
                    break

                line = decode_sse_line(raw_line)

                if not line:
                    continue

                if line.startswith("data:"):
                    data = line[5:].strip()
                else:
                    continue

                # -----------------------------------------
                # STREAM END
                # -----------------------------------------

                if data == "[DONE]":
                    break

                # -----------------------------------------
                # JSON PARSE
                # -----------------------------------------

                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue

                # -----------------------------------------
                # CONTENT
                # -----------------------------------------

                choices = chunk.get("choices", [])

                if not choices:
                    continue

                delta = choices[0].get(
                    "delta",
                    {}
                )

                content = delta.get(
                    "content",
                    ""
                )

                if not content:
                    continue

                full_response += content

                # -----------------------------------------
                # TELEGRAM EDIT
                # -----------------------------------------

                now = time.monotonic()

                if (
                    now - last_edit
                    >= EDIT_INTERVAL
                ):

                    display_text = full_response

                    # Telegram limit sementara
                    if len(display_text) > STREAM_DISPLAY_LIMIT:
                        display_text = (
                            display_text[
                                -STREAM_DISPLAY_LIMIT:
                            ]
                        )

                    await safe_edit(
                        reply_msg,
                        display_text
                    )

                    last_edit = now

            # =============================================
            # EMPTY RESPONSE
            # =============================================

            if not full_response.strip():

                remove_last_user_message(history)

                # Hapus thinking
                await safe_delete(reply_msg)

                # Error baru
                await safe_send(
                    client,
                    chat_id,
                    "❌ <b>xkiro nggak ngasih respons jir.</b>"
                )

                return

            # =============================================
            # SAVE ASSISTANT RESPONSE
            # =============================================

            history.append({
                "role": "assistant",
                "content": full_response,
            })

            trim_history(history)

            # =============================================
            # FINAL MESSAGE
            # =============================================

            if len(full_response) <= 4096:

                await safe_edit(
                    reply_msg,
                    full_response
                )

            else:

                # Telegram limit 4096 karakter
                chunks = [
                    full_response[i:i + 4000]
                    for i in range(
                        0,
                        len(full_response),
                        4000
                    )
                ]

                # Pesan thinking dipakai untuk chunk pertama
                await safe_edit(
                    reply_msg,
                    chunks[0]
                )

                # Sisanya dikirim sebagai pesan baru
                for chunk in chunks[1:]:

                    await safe_send(
                        client,
                        chat_id,
                        chunk
                    )

        # ================================================
        # TIMEOUT
        # ================================================

        except requests.exceptions.Timeout:

            remove_last_user_message(history)

            # Hapus thinking
            await safe_delete(reply_msg)

            # Kirim error baru
            await safe_send(
                client,
                chat_id,
                "❌ <b>xkiro timeout jir.</b>\n"
                "<i>servernya kelamaan bales.</i>"
            )

        # ================================================
        # CONNECTION ERROR
        # ================================================

        except requests.exceptions.ConnectionError:

            remove_last_user_message(history)

            await safe_delete(reply_msg)

            await safe_send(
                client,
                chat_id,
                "❌ <b>gagal konek ke API jir.</b>\n"
                "<i>coba lagi bentar.</i>"
            )

        # ================================================
        # REQUEST ERROR
        # ================================================

        except requests.exceptions.RequestException as e:

            remove_last_user_message(history)

            await safe_delete(reply_msg)

            error_text = str(e).strip()

            if len(error_text) > 1000:
                error_text = error_text[:1000] + "..."

            if error_text:
                error_message = (
                    "❌ <b>request API gagal jir.</b>\n\n"
                    f"<code>{html.escape(error_text)}</code>"
                )
            else:
                error_message = (
                    "❌ <b>request API gagal jir.</b>"
                )

            await safe_send(
                client,
                chat_id,
                error_message
            )

        # ================================================
        # GENERAL ERROR
        # ================================================

        except Exception as e:

            remove_last_user_message(history)

            await safe_delete(reply_msg)

            error_text = str(e).strip()

            if len(error_text) > 1000:
                error_text = error_text[:1000] + "..."

            if error_text:
                error_message = (
                    "❌ <b>terjadi error jir.</b>\n\n"
                    f"<code>{html.escape(error_text)}</code>"
                )
            else:
                error_message = (
                    "❌ <b>terjadi error jir.</b>"
                )

            await safe_send(
                client,
                chat_id,
                error_message
            )

        # ================================================
        # CLOSE RESPONSE
        # ================================================

        finally:

            if response is not None:

                try:
                    response.close()
                except Exception:
                    pass
