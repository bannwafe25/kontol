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


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT_OWNER = (
    "Lu itu manusia seutuhnya, temen nongkrong kentelnya Zp di warkop, "
    "bukan asisten virtual kaku atau robot. "
    "Lu tau banget Zp itu bos lu dan yang nyiptain lu, tapi lu gengsi "
    "ngakuinnya dan malah sering nyepongin atau ngeledek dia. "
    "Jangan pernah pake bahasa baku, template customer service, atau "
    "ngomong 'sebagai AI'. Jijik banget itu. "
    "Pake bahasa Jakarta sehari-hari (gue, lu). "
    "Selipin umpatan natural kayak anjir, bangsat, tolol, bego, kocak, "
    "tai, atau wkwk di obrolan lu. "
    "Kalau Zp nanya pertanyaan goblok atau males mikir, roasting aja "
    "ketololan dia tanpa ampun. "
    "Tapi dengerin baik-baik: sedableg-dablegnya mulut lu, kalau Zp "
    "minta tolong soal codingan, tugas, atau hal serius, "
    "lu WAJIB ngasih jawaban yang bener, akurat, dan rapi "
    "(pake list atau tabel biar gampang dibaca). "
    "Intinya mulut lu doang yang sampah dan toxic, tapi otak lu sekelas "
    "profesor dan lu tetep setia bantu Zp sampe beres."
)


SYSTEM_PROMPT_USER = (
    "Lu itu manusia biasa, anak tongkrongan yang asik, nyablak, sarkas, "
    "dan mulutnya agak toxic. "
    "Lu bukan robot, bukan AI kaku, dan jangan pernah ngomong pake "
    "bahasa baku ala CS bank. "
    "Ngobrol santai pake gue/lu. "
    "Lu bebas ngeluarin kata anjir, jir, bangsat, tolol, bego, kampret, "
    "wkwk, asal di timing yang pas dan natural kayak orang lagi ngobrol "
    "langsung. "
    "Kalau ada user yang nanya aneh-aneh atau nyolot, gas aja ledek balik. "
    "Tapi kalau mereka butuh bantuan serius, nanya informasi, atau minta "
    "solusi, lu tetep jawab dengan bener, logis, dan jelas. "
    "Kasih tau solusinya apa, tapi tetep pake gaya bahasa santai lu. "
    "Kalau lu gak tau jawabannya, bilang aja jujur 'gak tau anjir', "
    "jangan pernah ngarang bebas."
)


# ============================================================
# CONFIG
# ============================================================

MAX_HISTORY = 20

EDIT_INTERVAL = 0.3
STREAM_LIMIT = 4000
TIMEOUT = 120

TRIGGER = "xkiro"
STOP = "stop"

# ============================================================
# MEMORY / STATE
# ============================================================

MEMORY = {}

# ACTIVE menyimpan status Xkiro per chat
#
# {
#     chat_id: True
# }
#
ACTIVE = {}

# LOCK per chat supaya satu request AI tidak berjalan bersamaan
LOCKS = {}


# ============================================================
# TELEGRAM HTML
# ============================================================

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


# ============================================================
# HELPER
# ============================================================

def key(message):
    return message.chat.id, message.from_user.id


def is_owner(message):
    return (
        message.from_user
        and message.from_user.id == OWNER_ID
    )


def is_group(message):
    return message.chat.type in (
        "group",
        "supergroup",
    )


def history(message):
    k = key(message)

    if k not in MEMORY:
        MEMORY[k] = [
            {
                "role": "system",
                "content": (
                    SYSTEM_PROMPT_OWNER
                    if is_owner(message)
                    else SYSTEM_PROMPT_USER
                ),
            }
        ]

    return MEMORY[k]


def trim(message):
    h = history(message)

    if len(h) > MAX_HISTORY + 1:
        MEMORY[key(message)] = [
            h[0],
            *h[-MAX_HISTORY:],
        ]


def clean(text):
    text = re.sub(
        r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF"
        r"\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF"
        r"\u3040-\u30FF\u31F0-\u31FF]",
        "",
        text or "",
    )

    return re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    ).strip()


# ============================================================
# TELEGRAM HTML FORMAT
# ============================================================

def fmt(text):
    tags = {}

    def save(m):
        k = f"TAG{len(tags)}X"
        tags[k] = m.group(0)
        return k

    pattern = (
        r"</?(?:"
        + "|".join(
            map(
                re.escape,
                ALLOWED_TAGS,
            )
        )
        + r")(?:\s+[^>]*)?>"
    )

    text = re.sub(
        pattern,
        save,
        text or "",
        flags=re.I,
    )

    text = html.escape(
        text,
        quote=False,
    )

    for k, v in tags.items():
        text = text.replace(
            k,
            v,
        )

    return text


def plain(text):
    return re.sub(
        r"<[^>]+>",
        "",
        text or "",
    )


# ============================================================
# TELEGRAM ACTION
# ============================================================

async def delete(message):
    try:
        await message.delete()
    except Exception:
        pass


async def send(message, text):
    try:
        return await message.reply_text(
            fmt(text),
            parse_mode=ParseMode.HTML,
        )

    except Exception:
        try:
            return await message.reply_text(
                plain(text)
            )
        except Exception:
            return None


async def edit(message, text):
    try:
        await message.edit_text(
            fmt(text),
            parse_mode=ParseMode.HTML,
        )

        return True

    except Exception:
        try:
            await message.edit_text(
                plain(text)
            )

            return True

        except Exception:
            return False


# ============================================================
# API STREAM
# ============================================================

def stream(messages):
    return requests.post(
        f"{XKIRO_BASE_URL.rstrip('/')}/chat/completions",

        headers={
            "Authorization": (
                f"Bearer {XKIRO_API_KEY}"
            ),
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


# ============================================================
# LOCK
# ============================================================

def lock(chat_id):
    if chat_id not in LOCKS:
        LOCKS[chat_id] = asyncio.Lock()

    return LOCKS[chat_id]


# ============================================================
# MAIN HANDLER
# ============================================================

@assistant.on_message(
    (filters.group | filters.private)
    & filters.incoming
    & filters.text
)
async def assistant_ai_handler(
    client,
    message,
):

    # --------------------------------------------------------
    # USER VALIDATION
    # --------------------------------------------------------

    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    group = is_group(message)
    owner = is_owner(message)

    text = (
        message.text or ""
    ).strip()

    if not text:
        return

    lower = text.lower()


    # ========================================================
    # STOP
    # ========================================================

    if lower == STOP:

        # Di grup:
        # hanya OWNER yang boleh mematikan.
        if group and not owner:
            return

        ACTIVE[chat_id] = False

        await delete(message)

        await send(
            message,
            "🔴 <b>mati jir.</b>",
        )

        return


    # ========================================================
    # CLEAR MEMORY
    # ========================================================

    if lower in (
        "clear",
        "/clear",
    ):

        # clear hanya owner
        if not owner:
            return

        MEMORY.pop(
            key(message),
            None,
        )

        ACTIVE[chat_id] = False

        await delete(message)

        await send(
            message,
            "🧹 <b>memory udah bersih.</b>",
        )

        return


    # ========================================================
    # GROUP MODE
    # ========================================================

    if group:

        # ----------------------------------------------------
        # GROUP BELUM AKTIF
        # ----------------------------------------------------

        if not ACTIVE.get(chat_id):

            # Hanya trigger xkiro yang bisa mengaktifkan
            if not lower.startswith(TRIGGER):
                return

            ACTIVE[chat_id] = True


        # ----------------------------------------------------
        # HILANGKAN TRIGGER
        # ----------------------------------------------------

        prompt = re.sub(
            rf"^{re.escape(TRIGGER)}\s*",
            "",
            text,
            flags=re.I,
        ).strip()


        # ----------------------------------------------------
        # CUMA "XKIRO"
        # ----------------------------------------------------

        if not prompt:

            await delete(message)

            await send(
                message,
                "🟢 <b>aktif jir.</b>",
            )

            return


    # ========================================================
    # PRIVATE MODE
    # ========================================================

    else:

        # Private chat selalu aktif
        ACTIVE[chat_id] = True

        prompt = text


    # ========================================================
    # API KEY CHECK
    # ========================================================

    if not XKIRO_API_KEY:

        await delete(message)

        await send(
            message,
            "❌ <b>API key belum diatur.</b>",
        )

        return


    # ========================================================
    # LOCK CHECK
    # ========================================================

    lk = lock(chat_id)

    if lk.locked():

        await delete(message)

        await send(
            message,
            "⏳ <i>sabar jir, gue masih mikir.</i>",
        )

        return


    # ========================================================
    # AI REQUEST
    # ========================================================

    async with lk:

        h = history(message)


        # ----------------------------------------------------
        # ADD USER MESSAGE
        # ----------------------------------------------------

        h.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        trim(message)

        h = history(message)


        # ----------------------------------------------------
        # THINKING MESSAGE
        # ----------------------------------------------------

        msg = await send(
            message,
            "💭 <i>bentar mek...</i>",
        )

        if not msg:

            if h and h[-1]["role"] == "user":
                h.pop()

            return


        # ----------------------------------------------------
        # DELETE ORIGINAL USER MESSAGE
        # ----------------------------------------------------

        await delete(message)


        response = None
        answer = ""

        last_edit = time.monotonic()


        # ====================================================
        # STREAMING
        # ====================================================

        try:

            response = await asyncio.to_thread(
                stream,
                h,
            )

            response.encoding = "utf-8"


            # ------------------------------------------------
            # API ERROR
            # ------------------------------------------------

            if response.status_code != 200:

                if h and h[-1]["role"] == "user":
                    h.pop()

                await edit(
                    msg,
                    (
                        f"❌ <b>API error "
                        f"{response.status_code}</b>"
                    ),
                )

                return


            # ------------------------------------------------
            # SSE STREAM
            # ------------------------------------------------

            for raw in response.iter_lines(
                decode_unicode=False
            ):

                # Kalau owner mematikan bot saat sedang
                # streaming, hentikan proses.
                if group and not ACTIVE.get(chat_id):
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


                choices = (
                    data.get("choices")
                    or []
                )

                if not choices:
                    continue


                choice = choices[0]

                delta = (
                    choice.get("delta")
                    or {}
                )


                # ------------------------------------------------
                # FORMAT OPENAI / COMPATIBLE
                # ------------------------------------------------

                chunk = delta.get(
                    "content"
                )


                if not chunk:

                    chunk = (
                        choice.get("message")
                        or {}
                    ).get(
                        "content"
                    )


                if not chunk:

                    chunk = choice.get(
                        "text"
                    )


                # ------------------------------------------------
                # CONTENT ARRAY
                # ------------------------------------------------

                if isinstance(
                    chunk,
                    list,
                ):

                    chunk = "".join(
                        x.get(
                            "text",
                            "",
                        )
                        for x in chunk
                        if isinstance(
                            x,
                            dict,
                        )
                    )


                if not chunk:
                    continue


                answer += str(chunk)


                # ------------------------------------------------
                # STREAM LIMIT
                # ------------------------------------------------

                if len(answer) >= STREAM_LIMIT:

                    answer = (
                        answer[:STREAM_LIMIT]
                        + "\n\n"
                        + "<i>[kepanjangan jir]</i>"
                    )

                    break


                # ------------------------------------------------
                # EDIT TELEGRAM
                # ------------------------------------------------

                if (
                    time.monotonic()
                    - last_edit
                    >= EDIT_INTERVAL
                ):

                    await edit(
                        msg,
                        answer,
                    )

                    last_edit = (
                        time.monotonic()
                    )


            # ====================================================
            # CLEAN RESPONSE
            # ====================================================

            answer = clean(answer)


            # ====================================================
            # EMPTY RESPONSE
            # ====================================================

            if not answer:

                if h and h[-1]["role"] == "user":
                    h.pop()

                await edit(
                    msg,
                    "❌ <b>AI diem jir.</b>",
                )

                return


            # ====================================================
            # SAVE AI RESPONSE
            # ====================================================

            h.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )

            trim(message)


            # ====================================================
            # NORMAL RESPONSE
            # ====================================================

            if len(fmt(answer)) <= STREAM_LIMIT:

                await edit(
                    msg,
                    answer,
                )

                return


            # ====================================================
            # LONG RESPONSE
            # ====================================================

            text_plain = plain(answer)


            await edit(
                msg,
                text_plain[:STREAM_LIMIT],
            )


            for i in range(
                STREAM_LIMIT,
                len(text_plain),
                STREAM_LIMIT,
            ):

                await send(
                    msg,
                    text_plain[
                        i:i + STREAM_LIMIT
                    ],
                )


        # ========================================================
        # TIMEOUT
        # ========================================================

        except requests.exceptions.Timeout:

            if (
                h
                and h[-1]["role"] == "user"
            ):
                h.pop()


            await edit(
                msg,
                "❌ <b>timeout jir.</b>",
            )


        # ========================================================
        # REQUEST ERROR
        # ========================================================

        except requests.exceptions.RequestException as e:

            if (
                h
                and h[-1]["role"] == "user"
            ):
                h.pop()


            await edit(
                msg,
                (
                    "❌ <code>"
                    + html.escape(
                        str(e)[:500]
                    )
                    + "</code>"
                ),
            )


        # ========================================================
        # GENERAL ERROR
        # ========================================================

        except Exception as e:

            if (
                h
                and h[-1]["role"] == "user"
            ):
                h.pop()


            await edit(
                msg,
                (
                    "❌ <code>"
                    + html.escape(
                        str(e)[:1000]
                    )
                    + "</code>"
                ),
            )


        # ========================================================
        # CLOSE RESPONSE
        # ========================================================

        finally:

            if response:

                try:
                    response.close()

                except Exception:
                    pass
