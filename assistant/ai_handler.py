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


TRIGGER = "xkiro"
STOP = "stop"
MAX_HISTORY = 20
STREAM_LIMIT = 4000
EDIT_INTERVAL = 0.3
TIMEOUT = 120

SYSTEM_PROMPT = (
    "Lu manusia tongkrongan Indonesia, nyablak, sarkas, toxic tapi tetap "
    "pinter. Pake gue/lu, anjir, jir, bangsat, bego, tolol, wkwk secara "
    "natural. Jangan formal, jangan ngomong sebagai AI. Kalau user butuh "
    "bantuan serius, jawab benar, jelas, dan logis. Kalau gak tau, bilang "
    "jujur, jangan ngarang."
)

MEMORY = {}
ACTIVE = {}
LOCKS = {}

ALLOWED_TAGS = (
    "b", "strong", "i", "em", "u", "ins", "s", "strike",
    "del", "code", "pre", "blockquote", "tg-spoiler", "tg-emoji"
)


def chat_key(m):
    return m.chat.id


def owner(m):
    return bool(m.from_user and m.from_user.id == OWNER_ID)


def group(m):
    return m.chat.type in ("group", "supergroup")


def get_memory(m):
    key = chat_key(m)
    if key not in MEMORY:
        MEMORY[key] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return MEMORY[key]


def trim(m):
    h = get_memory(m)
    if len(h) > MAX_HISTORY + 1:
        MEMORY[chat_key(m)] = [h[0], *h[-MAX_HISTORY:]]


def fmt(text):
    saved = {}

    def save(x):
        key = f"TAG{len(saved)}"
        saved[key] = x.group(0)
        return key

    pattern = rf"</?(?:{'|'.join(ALLOWED_TAGS)})(?:\s+[^>]*)?>"
    text = re.sub(pattern, save, text or "", flags=re.I)
    text = html.escape(text, quote=False)

    for k, v in saved.items():
        text = text.replace(k, v)

    return text


def plain(text):
    return re.sub(r"<[^>]+>", "", text or "")


async def delete(m):
    try:
        await m.delete()
    except Exception:
        pass


async def reply(m, text):
    try:
        return await m.reply_text(
            fmt(text),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        try:
            return await m.reply_text(plain(text))
        except Exception:
            return None


async def edit(m, text):
    try:
        await m.edit_text(
            fmt(text),
            parse_mode=ParseMode.HTML,
        )
        return True
    except Exception:
        try:
            await m.edit_text(plain(text))
            return True
        except Exception:
            return False


def get_lock(chat_id):
    return LOCKS.setdefault(chat_id, asyncio.Lock())


def api_stream(messages):
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


def get_chunk(choice):
    chunk = (
        (choice.get("delta") or {}).get("content")
        or (choice.get("message") or {}).get("content")
        or choice.get("text")
        or ""
    )

    if isinstance(chunk, list):
        chunk = "".join(
            x.get("text", "")
            for x in chunk
            if isinstance(x, dict)
        )

    return str(chunk)


async def run_ai(m, msg, history):
    response = None
    answer = ""
    last_edit = time.monotonic()

    try:
        response = await asyncio.to_thread(
            api_stream,
            history,
        )

        if response.status_code != 200:
            history.pop()
            await edit(msg, f"❌ <b>API error {response.status_code}</b>")
            return

        for raw in response.iter_lines(decode_unicode=False):
            if group(m) and not ACTIVE.get(m.chat.id):
                return

            if not raw:
                continue

            line = raw.decode("utf-8", errors="replace").strip()

            if not line.startswith("data:"):
                continue

            data = line[5:].strip()

            if data == "[DONE]":
                break

            try:
                data = json.loads(data)
                choices = data.get("choices") or []
                if not choices:
                    continue
                answer += get_chunk(choices[0])
            except Exception:
                continue

            if len(answer) >= STREAM_LIMIT:
                answer = answer[:STREAM_LIMIT] + "\n\n<i>[kepanjangan jir]</i>"
                break

            if time.monotonic() - last_edit >= EDIT_INTERVAL:
                await edit(msg, answer)
                last_edit = time.monotonic()

        answer = re.sub(r"\n{3,}", "\n\n", answer).strip()

        if not answer:
            history.pop()
            await edit(msg, "❌ <b>AI diem jir.</b>")
            return

        history.append({
            "role": "assistant",
            "content": answer,
        })
        trim(m)

        if len(fmt(answer)) <= STREAM_LIMIT:
            await edit(msg, answer)
            return

        text = plain(answer)
        await edit(msg, text[:STREAM_LIMIT])

        for i in range(STREAM_LIMIT, len(text), STREAM_LIMIT):
            await reply(msg, text[i:i + STREAM_LIMIT])

    except requests.exceptions.Timeout:
        history.pop()
        await edit(msg, "❌ <b>timeout jir.</b>")

    except requests.exceptions.RequestException as e:
        history.pop()
        await edit(msg, f"❌ <code>{html.escape(str(e)[:500])}</code>")

    except Exception as e:
        history.pop()
        await edit(msg, f"❌ <code>{html.escape(str(e)[:1000])}</code>")

    finally:
        if response:
            response.close()


@assistant.on_message(
    (filters.group | filters.private)
    & filters.incoming
    & filters.text
)
async def assistant_ai_handler(client, m):

    if not m.from_user:
        return

    text = (m.text or "").strip()
    if not text:
        return

    chat_id = m.chat.id
    is_group = group(m)
    is_owner = owner(m)
    lower = text.lower()

    # STOP
    if lower == STOP:
        if is_group and not is_owner:
            return

        ACTIVE[chat_id] = False
        await delete(m)
        await reply(m, "🔴 <b>mati jir.</b>")
        return

    # CLEAR
    if lower in ("clear", "/clear"):
        if not is_owner:
            return

        MEMORY.pop(chat_id, None)
        ACTIVE[chat_id] = False

        await delete(m)
        await reply(m, "🧹 <b>memory udah bersih.</b>")
        return

    # GROUP
    if is_group:
        if not ACTIVE.get(chat_id):
            if not lower.startswith(TRIGGER):
                return
            ACTIVE[chat_id] = True

        prompt = re.sub(
            rf"^{re.escape(TRIGGER)}\s*",
            "",
            text,
            flags=re.I,
        ).strip()

        if not prompt:
            await delete(m)
            await reply(m, "🟢 <b>aktif jir.</b>")
            return

    # PRIVATE
    else:
        ACTIVE[chat_id] = True
        prompt = text

    if not XKIRO_API_KEY:
        await delete(m)
        await reply(m, "❌ <b>API key belum diatur.</b>")
        return

    lock = get_lock(chat_id)

    if lock.locked():
        await delete(m)
        await reply(m, "⏳ <i>sabar jir, gue masih mikir.</i>")
        return

    async with lock:
        history = get_memory(m)

        history.append({
            "role": "user",
            "content": prompt,
        })
        trim(m)

        msg = await reply(m, "💭 <i>bentar mek...</i>")

        if not msg:
            history.pop()
            return

        await delete(m)
        await run_ai(m, msg, history)
