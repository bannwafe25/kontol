import asyncio
import html
import json
import time

import requests
from pyrogram.enums import ParseMode

from config import XKIRO_API_KEY, XKIRO_BASE_URL, XKIRO_MODEL
from helpers import Emoji


MAX_PROMPT_LENGTH = 12000
MAX_MESSAGE_LENGTH = 4096
EDIT_INTERVAL = 0.7


SYSTEM_PROMPT = (
    "Kamu adalah assistant AI dengan gaya bahasa toxic tongkrongan Indonesia. "
    )


def create_stream(prompt):
    return requests.post(
        f"{XKIRO_BASE_URL.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {XKIRO_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": XKIRO_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 1,
            "max_tokens": 2048,
            "stream": True,
        },
        stream=True,
        timeout=120,
    )


async def xkiro_cmd(client, message):
    em = Emoji(client)
    await em.get()

    if not message.text:
        return

    if not XKIRO_API_KEY:
        return await message.reply(
            f"{em.gagal} <b>XKIRO_API_KEY belum diatur.</b>\n\n"
            "Tambahkan API key ke file <code>.env</code>."
        )

    query = message.text.split(None, 1)

    if len(query) < 2:
        return await message.reply(
            f"{em.gagal} <b>Format:</b>\n"
            "<code>.xkiro pertanyaan</code>"
        )

    prompt = query[1].strip()

    if not prompt:
        return await message.reply(
            f"{em.gagal} Pertanyaan tidak boleh kosong."
        )

    if len(prompt) > MAX_PROMPT_LENGTH:
        return await message.reply(
            f"{em.gagal} Pertanyaan terlalu panjang.\n"
            f"Maksimal <b>{MAX_PROMPT_LENGTH}</b> karakter."
        )

    progress = await message.edit(
        f"{em.proses} <b>DeepSeek V4 Pro sedang berpikir...</b>"
    )

    try:
        response = await asyncio.to_thread(
            create_stream,
            prompt,
        )

        if response.status_code != 200:
            error_text = response.text[:2000]

            await progress.edit(
                f"{em.gagal} <b>Xkiro API Error "
                f"({response.status_code})</b>\n\n"
                f"<code>{html.escape(error_text)}</code>",
                parse_mode=ParseMode.HTML,
            )
            return

        result = ""
        last_edit = time.monotonic()

        for line in response.iter_lines(
            decode_unicode=True
        ):
            if not line:
                continue

            if not line.startswith("data: "):
                continue

            data = line[6:]

            if data == "[DONE]":
                break

            try:
                chunk = json.loads(data)

                choices = chunk.get("choices", [])

                if not choices:
                    continue

                delta = choices[0].get("delta", {})
                content = delta.get("content", "")

                if not content:
                    continue

                result += content

                now = time.monotonic()

                if now - last_edit >= EDIT_INTERVAL:
                    display = html.escape(result)

                    if len(display) > MAX_MESSAGE_LENGTH:
                        display = (
                            display[:MAX_MESSAGE_LENGTH - 20]
                            + "\n\n…"
                        )

                    try:
                        await progress.edit(
                            f"{em.sukses}\n\n"
                            f"<blockquote>{display}</blockquote>",
                            parse_mode=ParseMode.HTML,
                        )
                    except Exception:
                        pass

                    last_edit = now

            except json.JSONDecodeError:
                continue

        if not result:
            result = "AI tidak memberikan respons."

        display = html.escape(result)

        if len(display) > MAX_MESSAGE_LENGTH:
            display = (
                display[:MAX_MESSAGE_LENGTH - 20]
                + "\n\n…"
            )

        await progress.edit(
            f"{em.sukses}\n\n"
            f"<blockquote>{display}</blockquote>",
            parse_mode=ParseMode.HTML,
        )

    except requests.exceptions.Timeout:
        await progress.edit(
            f"{em.gagal} <b>Request timeout.</b>\n"
            "Xkiro tidak merespons dalam waktu yang ditentukan."
        )

    except requests.exceptions.RequestException as e:
        error = html.escape(str(e)[:3000])

        try:
            await progress.edit(
                f"{em.gagal} <b>Request error:</b>\n"
                f"<code>{error}</code>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

    except Exception as e:
        error = html.escape(str(e)[:3000])

        try:
            await progress.edit(
                f"{em.gagal} <b>Error:</b>\n"
                f"<code>{error}</code>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
