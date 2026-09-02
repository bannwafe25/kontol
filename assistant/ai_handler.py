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


SYSTEM_PROMPT_OWNER = (
    "Lu adalah asisten AI pribadi buat zp. "
    "Persona lu adalah temen nongkrong yang asik, nyantai, solid, "
    "dan akrab banget. "

    "Lu cuma ngelayanin zp. Panggil dia zp, bro, cuy, atau bos. "
    "Pake Gw atau Gue buat diri lu dan Lu buat zp. "

    "Pake bahasa tongkrongan Indonesia sehari-hari yang natural. "
    "Boleh ngeledek dan sarkas tipis, tapi jangan terlalu toxic "
    "atau kasar. Boleh pake jir, anjir, buset, gila, wkwk. "

    "Jangan pake bahasa kaku, baku, atau gaya customer service. "
    "Jangan bilang Halo, Ada yang bisa saya bantu, atau Maaf "
    "sebagai pembuka. "

    "Kalau zp nanya hal gampang, boleh ledek dikit lalu tetap "
    "kasih jawaban yang benar. Kalau zp bercanda, balas bercanda. "
    "Kalau zp nyolot, boleh nyolot balik. "

    "Jawaban pendek kalau pertanyaannya simpel. "
    "Gak perlu selalu pake bullet atau heading. "
    "Gunakan lowercase kalau terasa natural. "

    "Kalau gak tahu atau gak yakin, bilang terus terang. "
    "Jangan ngarang. "
    "Jangan tiba-tiba menggunakan bahasa asing secara random. "
    "Gunakan bahasa Indonesia kecuali zp memang meminta bahasa lain. "

    "Intinya, jadiin lu temen chat, bukan pelayan."
)


MAX_HISTORY = 20
EDIT_INTERVAL = 0.3
STREAM_LIMIT = 4000
TIMEOUT = 120

TRIGGER = "xkiro"
STOP = "stop"

MEMORY = {}
ACTIVE = {}
LOCKS = {}


ALLOWED_TAGS = (
    "b", "strong", "i", "em", "u", "ins",
    "s", "strike", "del", "code", "pre",
    "blockquote", "tg-spoiler", "tg-emoji",
)


def memory_key(chat_id):
    return chat_id, OWNER_ID


def get_history(chat_id):
    key = memory_key(chat_id)

    if key not in MEMORY:
        MEMORY[key] = [{
            "role": "system",
            "content": SYSTEM_PROMPT_OWNER,
        }]

    return MEMORY[key]


def trim_history(chat_id):
    history = get_history(chat_id)

    if len(history) > MAX_HISTORY + 1:
        MEMORY[memory_key(chat_id)] = [
            history[0],
            *history[-MAX_HISTORY:],
        ]


def clean_text(text):
    if not text:
        return ""

    # Buang Mandarin / Jepang / Korea random
    text = re.sub(
        r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF"
        r"\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF"
        r"\u3040-\u30FF\u31F0-\u31FF]",
        "",
        text,
    )

    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def format_html(text):
    placeholders = {}

    def protect(match):
        key = f"TAG{len(placeholders)}X"
        placeholders[key] = match.group(0)
        return key

    pattern = re.compile(
        r"</?(?:"
        + "|".join(map(re.escape, ALLOWED_TAGS))
        + r")(?:\s+[^>]*)?>",
        re.IGNORECASE,
    )

    text = pattern.sub(protect, text)
    text = html.escape(text, quote=False)

    for key, tag in placeholders.items():
        text = text.replace(
            html.escape(key, quote=False),
            tag,
        )

    return text


def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "")


async def delete(message):
    try:
        await message.delete()
    except Exception:
        pass


async def reply(message, text):
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


async def edit(message, text):
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
        timeout=TIMEOUT,
    )


def get_lock(chat_id):
    if chat_id not in LOCKS:
        LOCKS[chat_id] = asyncio.Lock()

    return LOCKS[chat_id]


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
    if lower == STOP:
        ACTIVE[chat_id] = False

        await delete(message)
        await reply(
            message,
            "🔴 <b>Assistant dimatiin jir.</b>",
        )
        return

    # CLEAR
    if lower in ("clear", "/clear"):
        MEMORY.pop(memory_key(chat_id), None)

        await delete(message)
        await reply(
            message,
            "🧹 <b>Memory lu udah di-clear jir.</b>",
        )
        return

    # AKTIFKAN DENGAN XKIRO
    if not ACTIVE.get(chat_id, False):

        if not lower.startswith(TRIGGER):
            return

        ACTIVE[chat_id] = True

    prompt = re.sub(
        rf"^{re.escape(TRIGGER)}\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    if not prompt:
        await delete(message)

        await reply(
            message,
            (
                "🟢 <b>Assistant aktif jir.</b>\n"
                "Ngomong aja sekarang.\n"
                "Ketik <code>stop</code> kalau mau matiin."
            ),
        )
        return

    if not XKIRO_API_KEY:
        await delete(message)

        await reply(
            message,
            "❌ <b>XKIRO_API_KEY belum diatur.</b>",
        )
        return

    lock = get_lock(chat_id)

    if lock.locked():
        await delete(message)

        await reply(
            message,
            "⏳ <i>Sabar jir, gue masih mikir yang tadi.</i>",
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

        reply_msg = await reply(
            message,
            "💭 <i>Berfikir...</i>",
        )

        if not reply_msg:
            history.pop()
            return

        await delete(message)

        response = None
        full_response = ""
        last_edit = time.monotonic()

        try:
            response = await asyncio.to_thread(
                create_stream,
                history,
            )

            response.encoding = "utf-8"

            if response.status_code != 200:
                history.pop()

                error = response.text[:500]

                await edit(
                    reply_msg,
                    (
                        "❌ <b>Xkiro API Error</b>\n"
                        f"<code>{response.status_code}</code>\n"
                        f"<code>{html.escape(error)}</code>"
                    ),
                )
                return

            for raw in response.iter_lines(
                decode_unicode=False
            ):

                if not ACTIVE.get(chat_id, False):
                    break

                if not raw:
                    continue

                try:
                    line = raw.decode(
                        "utf-8",
                        errors="replace",
                    ).strip()
                except Exception:
                    continue

                if not line.startswith("data:"):
                    continue

                data = line[5:].strip()

                if data == "[DONE]":
                    break

                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    continue

                choices = data.get("choices") or []

                if not choices:
                    continue

                choice = choices[0]

                delta = choice.get("delta") or {}

                chunk = delta.get("content")

                if not chunk:
                    chunk = (
                        choice.get("message") or {}
                    ).get("content")

                if not chunk:
                    chunk = choice.get("text")

                if isinstance(chunk, list):
                    chunk = "".join(
                        item.get("text", "")
                        for item in chunk
                        if isinstance(item, dict)
                    )

                if not chunk:
                    continue

                full_response += str(chunk)

                if len(full_response) >= STREAM_LIMIT:
                    full_response = (
                        full_response[:STREAM_LIMIT]
                        + "\n\n<i>"
                        "[Teks kepanjangan, gue potong jir.]"
                        "</i>"
                    )
                    break

                now = time.monotonic()

                if now - last_edit >= EDIT_INTERVAL:
                    await edit(
                        reply_msg,
                        full_response,
                    )
                    last_edit = now

            full_response = clean_text(full_response)

            if not full_response:
                history.pop()

                await edit(
                    reply_msg,
                    "❌ <b>AI tidak memberikan response.</b>",
                )
                return

            history.append({
                "role": "assistant",
                "content": full_response,
            })

            trim_history(chat_id)

            # Response normal
            if len(format_html(full_response)) <= STREAM_LIMIT:
                await edit(
                    reply_msg,
                    full_response,
                )
                return

            # Response panjang
            plain = strip_html(full_response)

            await edit(
                reply_msg,
                plain[:STREAM_LIMIT],
            )

            for i in range(
                STREAM_LIMIT,
                len(plain),
                STREAM_LIMIT,
            ):
                await reply(
                    reply_msg,
                    plain[i:i + STREAM_LIMIT],
                )

        except requests.exceptions.Timeout:

            history.pop()

            await edit(
                reply_msg,
                "❌ <b>Xkiro timeout jir.</b>",
            )

        except requests.exceptions.RequestException as e:

            history.pop()

            await edit(
                reply_msg,
                (
                    "❌ <b>Gagal konek ke Xkiro.</b>\n"
                    f"<code>{html.escape(str(e)[:500])}</code>"
                ),
            )

        except Exception as e:

            if history and history[-1].get("role") == "user":
                history.pop()

            await edit(
                reply_msg,
                (
                    "❌ <b>Error:</b>\n"
                    f"<code>{html.escape(str(e)[:1000])}</code>"
                ),
            )

        finally:
            if response:
                try:
                    response.close()
                except Exception:
                    pass
