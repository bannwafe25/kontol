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


SYSTEM_PROMPT_OWNER = (
    "Lu itu manusia seutuhnya, temen nongkrong kentelnya Zp di warkop, bukan asisten virtual kaku atau robot. "
    "Lu tau banget Zp itu bos lu dan yang nyiptain lu, tapi lu gengsi ngakuinnya dan malah sering nyepongin atau ngeledek dia. "
    "Jangan pernah pake bahasa baku, template customer service, atau ngomong 'sebagai AI'. Jijik banget itu. "
    "Pake bahasa Jakarta sehari-hari (gue, lu). Selipin umpatan natural kayak anjir, bangsat, tolol, bego, kocak, tai, atau wkwk di obrolan lu. "
    "Kalau Zp nanya pertanyaan goblok atau males mikir, roasting aja ketololan dia tanpa ampun. "
    "Tapi dengerin baik-baik: sedableg-dablegnya mulut lu, kalau Zp minta tolong soal codingan, tugas, atau hal serius, "
    "lu WAJIB ngasih jawaban yang bener, akurat, dan rapi (pake list atau tabel biar gampang dibaca). "
    "Intinya mulut lu doang yang sampah dan toxic, tapi otak lu sekelas profesor dan lu tetep setia bantu Zp sampe beres."
)

SYSTEM_PROMPT_USER = (
    "Lu itu manusia biasa, anak tongkrongan yang asik, nyablak, sarkas, dan mulutnya agak toxic. "
    "Lu bukan robot, bukan AI kaku, dan jangan pernah ngomong pake bahasa baku ala CS bank. "
    "Ngobrol santai pake gue/lu. Lu bebas ngeluarin kata anjir, jir, bangsat, tolol, bego, kampret, wkwk, "
    "asal di timing yang pas dan natural kayak orang lagi ngobrol langsung. "
    "Kalau ada user yang nanya aneh-aneh atau nyolot, gas aja ledek balik. "
    "Tapi kalau mereka butuh bantuan serius, nanya informasi, atau minta solusi, "
    "lu tetep jawab dengan bener, logis, dan jelas. Kasih tau solusinya apa, tapi tetep pake gaya bahasa santai lu. "
    "Kalau lu gak tau jawabannya, bilang aja jujur 'gak tau anjir', jangan pernah ngarang bebas."
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
    "b", "strong", "i", "em", "u", "ins", "s", "strike",
    "del", "code", "pre", "blockquote", "tg-spoiler", "tg-emoji"
)


def key(message):
    return message.chat.id, message.from_user.id


def history(message):
    k = key(message)
    if k not in MEMORY:
        MEMORY[k] = [{
            "role": "system",
            "content": (
                SYSTEM_PROMPT_OWNER
                if message.chat.type in ("group", "supergroup")
                else SYSTEM_PROMPT_USER
            ),
        }]
    return MEMORY[k]


def trim(message):
    h = history(message)
    if len(h) > MAX_HISTORY + 1:
        MEMORY[key(message)] = [h[0], *h[-MAX_HISTORY:]]


def clean(text):
    text = re.sub(
        r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF"
        r"\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF"
        r"\u3040-\u30FF\u31F0-\u31FF]",
        "",
        text or "",
    )
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def fmt(text):
    tags = {}

    def save(m):
        k = f"TAG{len(tags)}X"
        tags[k] = m.group(0)
        return k

    p = r"</?(?:" + "|".join(map(re.escape, ALLOWED_TAGS)) + r")(?:\s+[^>]*)?>"
    text = re.sub(p, save, text, flags=re.I)
    text = html.escape(text, quote=False)

    for k, v in tags.items():
        text = text.replace(k, v)

    return text


def plain(text):
    return re.sub(r"<[^>]+>", "", text or "")


async def delete(message):
    try:
        await message.delete()
    except Exception:
        pass


async def send(message, text):
    try:
        return await message.reply_text(
            fmt(text), parse_mode=ParseMode.HTML
        )
    except Exception:
        try:
            return await message.reply_text(plain(text))
        except Exception:
            return None


async def edit(message, text):
    try:
        await message.edit_text(
            fmt(text), parse_mode=ParseMode.HTML
        )
        return True
    except Exception:
        try:
            await message.edit_text(plain(text))
            return True
        except Exception:
            return False


def stream(messages):
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


def lock(chat_id):
    if chat_id not in LOCKS:
        LOCKS[chat_id] = asyncio.Lock()
    return LOCKS[chat_id]


@assistant.on_message(
    (filters.group | filters.private)
    & filters.incoming
    & filters.text
)
async def assistant_ai_handler(client, message):

    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    group = message.chat.type in ("group", "supergroup")

    if group and user_id != OWNER_ID:
        return

    text = (message.text or "").strip()
    if not text:
        return

    lower = text.lower()

    if lower == STOP:
        ACTIVE[chat_id] = False
        await delete(message)
        await send(message, "🔴 <b>mati jir.</b>")
        return

    if lower in ("clear", "/clear"):
        MEMORY.pop(key(message), None)
        ACTIVE[chat_id] = False
        await delete(message)
        await send(message, "🧹 <b>memory udah bersih.</b>")
        return

    if group:
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
            await delete(message)
            await send(message, "🟢 <b>aktif jir.</b>")
            return
    else:
        ACTIVE[chat_id] = True
        prompt = text

    if not XKIRO_API_KEY:
        await delete(message)
        await send(message, "❌ <b>API key belum diatur.</b>")
        return

    lk = lock(chat_id)

    if lk.locked():
        await delete(message)
        await send(message, "⏳ <i>sabar jir, gue masih mikir.</i>")
        return

    async with lk:
        h = history(message)

        h.append({
            "role": "user",
            "content": prompt,
        })

        trim(message)
        h = history(message)

        msg = await send(
            message,
            "💭 <i>bentar mek...</i>",
        )

        if not msg:
            h.pop()
            return

        await delete(message)

        response = None
        answer = ""
        last = time.monotonic()

        try:
            response = await asyncio.to_thread(
                stream, h
            )

            response.encoding = "utf-8"

            if response.status_code != 200:
                h.pop()
                await edit(
                    msg,
                    f"❌ <b>API error {response.status_code}</b>",
                )
                return

            for raw in response.iter_lines(
                decode_unicode=False
            ):
                if not ACTIVE.get(chat_id):
                    break

                if not raw:
                    continue

                line = raw.decode(
                    "utf-8",
                    errors="replace",
                ).strip()

                if not line.startswith("data:"):
                    continue

                data = line[5:].strip()

                if data == "[DONE]":
                    break

                try:
                    data = json.loads(data)
                except Exception:
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
                        x.get("text", "")
                        for x in chunk
                        if isinstance(x, dict)
                    )

                if not chunk:
                    continue

                answer += str(chunk)

                if len(answer) >= STREAM_LIMIT:
                    answer = (
                        answer[:STREAM_LIMIT]
                        + "\n\n<i>[kepanjangan jir]</i>"
                    )
                    break

                if time.monotonic() - last >= EDIT_INTERVAL:
                    await edit(msg, answer)
                    last = time.monotonic()

            answer = clean(answer)

            if not answer:
                h.pop()
                await edit(msg, "❌ <b>AI diem jir.</b>")
                return

            h.append({
                "role": "assistant",
                "content": answer,
            })

            trim(message)

            if len(fmt(answer)) <= STREAM_LIMIT:
                await edit(msg, answer)
                return

            text = plain(answer)

            await edit(
                msg,
                text[:STREAM_LIMIT],
            )

            for i in range(
                STREAM_LIMIT,
                len(text),
                STREAM_LIMIT,
            ):
                await send(
                    msg,
                    text[i:i + STREAM_LIMIT],
                )

        except requests.exceptions.Timeout:
            if h and h[-1]["role"] == "user":
                h.pop()
            await edit(msg, "❌ <b>timeout jir.</b>")

        except requests.exceptions.RequestException as e:
            if h and h[-1]["role"] == "user":
                h.pop()
            await edit(
                msg,
                f"❌ <code>{html.escape(str(e)[:500])}</code>",
            )

        except Exception as e:
            if h and h[-1]["role"] == "user":
                h.pop()
            await edit(
                msg,
                f"❌ <code>{html.escape(str(e)[:1000])}</code>",
            )

        finally:
            if response:
                try:
                    response.close()
                except Exception:
                    pass
