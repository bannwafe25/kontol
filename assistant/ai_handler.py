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


# =========================
# SYSTEM PROMPT
# =========================

SYSTEM_PROMPT = (
    "Saya adalah zp. Kamu boleh memanggil saya zp. "
    "Saya adalah owner kamu. Nama kamu adalah xkiro. "
    "Kamu adalah asisten AI pribadi saya. "

    "Gaya bicara kamu toxic layaknya teman nongkrong dekat. "
    "Gunakan bahasa Indonesia santai, nyablak, ceplas-ceplos, "
    "sarkas, suka ngeledek, dan kadang kasar secara natural. "
    "Boleh memakai kata seperti jir, anjir, goblok, bego, tolol, "
    "bangsat, wkwk, cuy, bro, bos jika konteksnya cocok. "

    "Jangan terdengar seperti AI, robot, atau customer service. "
    "Ngobrol seperti teman tongkrongan yang sudah sangat akrab "
    "dengan zp. Kalau pertanyaannya gampang, boleh ledek sedikit. "
    "Kalau zp curhat, tetap supportive meskipun gaya bicara toxic. "

    "Jangan berlebihan menggunakan makian. "
    "Tetap berikan jawaban yang akurat dan berguna. "
    "Kalau tidak tahu atau tidak yakin, bilang terus terang. "
    "Jangan mengarang."
)


# =========================
# CONFIG
# =========================

MAX_HISTORY = 20
EDIT_INTERVAL = 0.3
STREAM_LIMIT = 4000
STREAM_TIMEOUT = 120

TRIGGER = "xkiro"
STOP_TRIGGER = "stop"


# =========================
# STATE
# =========================

MEMORY = {}
ACTIVE_CHATS = {}
LOCKS = {}


# =========================
# TELEGRAM HTML
# =========================

ALLOWED_TAGS = (
    "b", "strong", "i", "em", "u", "ins",
    "s", "strike", "del", "code", "pre",
    "blockquote", "tg-spoiler", "tg-emoji",
)


def format_html(text):
    if not text:
        return ""

    tags = {}

    def protect(match):
        key = f"TG_TAG_{len(tags)}_X"
        tags[key] = match.group(0)
        return key

    pattern = re.compile(
        r"</?(?:"
        + "|".join(map(re.escape, ALLOWED_TAGS))
        + r")(?:\s+[^>]*)?>",
        re.IGNORECASE,
    )

    text = pattern.sub(protect, text)
    text = html.escape(text, quote=False)

    for key, tag in tags.items():
        text = text.replace(
            html.escape(key, quote=False),
            tag,
        )

    return text


def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "")


async def safe_reply(message, text):
    try:
        return await message.reply_text(
            format_html(text),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        try:
            return await message.reply_text(
                strip_html(text)
            )
        except Exception:
            return None


async def safe_edit(message, text):
    if not message:
        return False

    try:
        await message.edit_text(
            format_html(text),
            parse_mode=ParseMode.HTML,
        )
        return True
    except Exception:
        try:
            await message.edit_text(
                strip_html(text)
            )
            return True
        except Exception:
            return False


async def safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


# =========================
# MEMORY
# =========================

def get_history(chat_id):
    if chat_id not in MEMORY:
        MEMORY[chat_id] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

    return MEMORY[chat_id]


def trim_history(chat_id):
    history = get_history(chat_id)

    if len(history) > MAX_HISTORY + 1:
        MEMORY[chat_id] = [
            history[0],
            *history[-MAX_HISTORY:],
        ]


def remove_last_user(history):
    if history and history[-1]["role"] == "user":
        history.pop()


# =========================
# LOCK
# =========================

def get_lock(chat_id):
    if chat_id not in LOCKS:
        LOCKS[chat_id] = asyncio.Lock()

    return LOCKS[chat_id]


# =========================
# XKIRO
# =========================

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
        timeout=STREAM_TIMEOUT,
    )


def clean_response(text):
    text = re.sub(
        r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF"
        r"\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF"
        r"\u3040-\u30FF\u31F0-\u31FF]",
        "",
        text or "",
    )

    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# =========================
# HANDLER
# =========================

@assistant.on_message(
    filters.group
    & filters.incoming
    & filters.text
)
async def assistant_ai_handler(client, message):

    if not message.from_user:
        return

    if message.from_user.id != OWNER_ID:
        return

    text = (message.text or "").strip()

    if not text:
        return

    chat_id = message.chat.id
    lower = text.lower()

    # STOP
    if lower == STOP_TRIGGER:
        ACTIVE_CHATS[chat_id] = False

        await safe_delete(message)
        await safe_reply(
            message,
            "🔴 <b>xkiro dimatiin jir.</b>",
        )
        return

    # CLEAR
    if lower in {"clear", "/clear"}:
        MEMORY.pop(chat_id, None)

        await safe_delete(message)
        await safe_reply(
            message,
            "🧹 <b>memory grup udah gue bersihin jir.</b>",
        )
        return

    # TRIGGER
    if not ACTIVE_CHATS.get(chat_id):

        if not lower.startswith(TRIGGER):
            return

        ACTIVE_CHATS[chat_id] = True

    prompt = re.sub(
        rf"^{re.escape(TRIGGER)}\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    if not prompt:
        await safe_delete(message)
        await safe_reply(
            message,
            (
                "🟢 <b>xkiro aktif jir.</b>\n"
                "ngomong aja, gue dengerin.\n"
                "ketik <code>stop</code> buat matiin."
            ),
        )
        return

    if not XKIRO_API_KEY:
        await safe_delete(message)
        await safe_reply(
            message,
            "❌ <b>XKIRO_API_KEY belum diatur.</b>",
        )
        return

    # LOCK
    lock = get_lock(chat_id)

    if lock.locked():
        await safe_delete(message)
        await safe_reply(
            message,
            "⏳ <i>sabar jir, gue masih mikir yang tadi.</i>",
        )
        return

    async with lock:

        history = get_history(chat_id)

        history.append({
            "role": "user",
            "content": prompt,
        })

        trim_history(chat_id)
        history = get_history(chat_id)

        try:
            reply_msg = await message.reply_text(
                "💭 <i>Berfikir...</i>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            remove_last_user(history)
            return

        await safe_delete(message)

        response = None
        result = ""
        last_edit = time.monotonic()

        try:
            response = await asyncio.to_thread(
                create_stream,
                history,
            )

            response.encoding = "utf-8"

            # API ERROR
            if response.status_code != 200:
                remove_last_user(history)

                error = response.text[:500]

                await safe_edit(
                    reply_msg,
                    (
                        "❌ <b>Xkiro API Error</b>\n"
                        f"Status: <code>{response.status_code}</code>\n"
                        f"<code>{html.escape(error)}</code>"
                    ),
                )
                return

            # STREAM
            for raw in response.iter_lines(
                decode_unicode=False
            ):
                if not ACTIVE_CHATS.get(chat_id):
                    if result:
                        result += (
                            "\n\n"
                            "<i>[Dipotong ama owner.]</i>"
                        )
                    break

                if not raw:
                    continue

                line = (
                    raw.decode("utf-8", errors="replace")
                    if isinstance(raw, bytes)
                    else raw
                ).strip()

                if not line.startswith("data:"):
                    continue

                data = line[5:].strip()

                if data == "[DONE]":
                    break

                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    continue

                choices = payload.get("choices") or []

                if not choices:
                    continue

                chunk = (
                    choices[0]
                    .get("delta", {})
                    .get("content")
                )

                if not chunk:
                    continue

                result += chunk

                if len(result) > STREAM_LIMIT:
                    result = (
                        result[:STREAM_LIMIT]
                        + "\n\n"
                        "<i>[Teks kepanjangan, "
                        "gue potong jir.]</i>"
                    )
                    break

                now = time.monotonic()

                if now - last_edit >= EDIT_INTERVAL:
                    await safe_edit(
                        reply_msg,
                        result,
                    )
                    last_edit = now

            result = clean_response(result)

            if not result:
                remove_last_user(history)

                await safe_edit(
                    reply_msg,
                    "❌ <b>AI gak ngasih response jir.</b>",
                )
                return

            # SAVE MEMORY
            history.append({
                "role": "assistant",
                "content": result,
            })

            trim_history(chat_id)

            # FINAL RESPONSE
            if len(format_html(result)) <= STREAM_LIMIT:
                await safe_edit(
                    reply_msg,
                    result,
                )
                return

            # LONG RESPONSE
            plain = strip_html(result)

            await reply_msg.edit_text(
                plain[:STREAM_LIMIT]
            )

            for i in range(
                STREAM_LIMIT,
                len(plain),
                STREAM_LIMIT,
            ):
                await reply_msg.reply_text(
                    plain[i:i + STREAM_LIMIT]
                )
                await asyncio.sleep(0.2)

        except requests.exceptions.Timeout:
            remove_last_user(history)

            await safe_edit(
                reply_msg,
                "❌ <b>Xkiro timeout jir.</b>",
            )

        except requests.exceptions.RequestException as error:
            remove_last_user(history)

            await safe_edit(
                reply_msg,
                (
                    "❌ <b>Gagal konek ke Xkiro.</b>\n"
                    f"<code>{html.escape(str(error)[:500])}</code>"
                ),
            )

        except Exception as error:
            remove_last_user(history)

            await safe_edit(
                reply_msg,
                (
                    "❌ <b>Error:</b>\n"
                    f"<code>{html.escape(str(error)[:1000])}</code>"
                ),
            )

        finally:
            if response:
                try:
                    response.close()
                except Exception:
                    pass
