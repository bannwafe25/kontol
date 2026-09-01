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
MAX_HISTORY = 20
EDIT_INTERVAL = 0.7


SYSTEM_PROMPT = (
    "Kamu adalah assistant AI dengan gaya bahasa toxic tongkrongan Indonesia. "
    "Ngobrol seperti teman dekat, santai, nyablak, sarkastik, dan suka roasting. "
    "Gunakan bahasa seperti gue, lu, bro, jir, anjir, bjir, wkwk, cuy, bang, "
    "buset, gila, ngaco, bego, goblok, tolol, dan slang lainnya secara natural. "
    "Boleh ngegas dan ngeledek user sebagai candaan. "
    "Jangan terlalu formal, jangan sok sopan, dan jangan terdengar seperti bot. "
    "Kalau user ngaco, boleh roasting lalu tetap kasih jawaban yang benar. "
    "Kalau pertanyaan serius, tetap jawab dengan serius dan akurat. "
    "Jangan memaksakan kata kasar di setiap kalimat."
)


# Memory per user
user_memory = {}

# Status chatbot per user
user_status = {}


def get_memory(user_id):
    if user_id not in user_memory:
        user_memory[user_id] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

    return user_memory[user_id]


def clear_memory(user_id):
    user_memory.pop(user_id, None)


def create_stream(messages):
    return requests.post(
        f"{XKIRO_BASE_URL.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {XKIRO_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": XKIRO_MODEL,
            "messages": messages,
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
            f"{em.gagal} <b>Command Xkiro</b>\n\n"
            "<code>.xkiro on</code> - aktifkan chatbot\n"
            "<code>.xkiro off</code> - matikan chatbot\n"
            "<code>.xkiro clear</code> - hapus memory\n"
            "<code>.xkiro pertanyaan</code> - chat dengan AI"
        )

    prompt = query[1].strip()
    command = prompt.lower()

    user_id = message.from_user.id

    # =========================
    # ON
    # =========================
    if command == "on":
        user_status[user_id] = True

        get_memory(user_id)

        return await message.reply(
            f"{em.sukses} <b>Xkiro chatbot ON</b>\n\n"
            "Gas ngobrol bro wkwk."
        )

    # =========================
    # OFF
    # =========================
    if command == "off":
        user_status[user_id] = False

        return await message.reply(
            f"{em.sukses} <b>Xkiro chatbot OFF</b>\n\n"
            "Udah gue matiin jir."
        )

    # =========================
    # CLEAR
    # =========================
    if command == "clear":
        clear_memory(user_id)

        return await message.reply(
            f"{em.sukses} <b>Memory dibersihkan.</b>\n\n"
            "Mulai dari nol lagi, bro wkwk."
        )

    # =========================
    # CHECK STATUS
    # =========================
    if not user_status.get(user_id, False):
        return await message.reply(
            f"{em.gagal} <b>Chatbot sedang OFF.</b>\n\n"
            "Nyalakan dengan:\n"
            "<code>.xkiro on</code>"
        )

    # =========================
    # VALIDATE PROMPT
    # =========================
    if not prompt:
        return await message.reply(
            f"{em.gagal} Pertanyaan kosong jir."
        )

    if len(prompt) > MAX_PROMPT_LENGTH:
        return await message.reply(
            f"{em.gagal} Pertanyaan terlalu panjang.\n"
            f"Maksimal <b>{MAX_PROMPT_LENGTH}</b> karakter."
        )

    # =========================
    # MEMORY
    # =========================
    history = get_memory(user_id)

    history.append({
        "role": "user",
        "content": prompt,
    })

    # Simpan maksimal 20 pesan terakhir
    if len(history) > MAX_HISTORY + 1:
        user_memory[user_id] = [
            history[0],
            *history[-MAX_HISTORY:]
        ]

        history = user_memory[user_id]

    # =========================
    # REQUEST
    # =========================
    progress = await message.edit(
        f"{em.proses} <b>Lagi mikir jir...</b>"
    )

    try:
        response = await asyncio.to_thread(
            create_stream,
            history,
        )

        if response.status_code != 200:
            error_text = response.text[:2000]

            # Hapus pesan user dari memory
            if history and history[-1]["role"] == "user":
                history.pop()

            await progress.edit(
                f"{em.gagal} <b>Xkiro API Error "
                f"({response.status_code})</b>\n\n"
                f"<code>{html.escape(error_text)}</code>",
                parse_mode=ParseMode.HTML,
            )
            return

        result = ""
        last_edit = time.monotonic()

        # =========================
        # STREAMING
        # =========================
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

                # Update Telegram setiap 0.7 detik
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

        # =========================
        # SAVE AI RESPONSE
        # =========================
        if not result:
            result = "Buset, AI-nya diem jir. Coba lagi."

        history.append({
            "role": "assistant",
            "content": result,
        })

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
        if history and history[-1]["role"] == "user":
            history.pop()

        await progress.edit(
            f"{em.gagal} <b>Request timeout jir.</b>\n"
            "Xkiro kelamaan mikir."
        )

    except requests.exceptions.RequestException as e:
        if history and history[-1]["role"] == "user":
            history.pop()

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
        if history and history[-1]["role"] == "user":
            history.pop()

        error = html.escape(str(e)[:3000])

        try:
            await progress.edit(
                f"{em.gagal} <b>Error:</b>\n"
                f"<code>{error}</code>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
