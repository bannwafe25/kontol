import asyncio
import html
import time

from groq import Groq
from pyrogram.enums import ParseMode

from config import GROQ_API_KEY
from helpers import Emoji


groq = Groq(
    api_key=GROQ_API_KEY
)

MODEL = "openai/gpt-oss-20b"

# Batas pertanyaan user
MAX_PROMPT_LENGTH = 12000

# Batas pesan Telegram
MAX_MESSAGE_LENGTH = 4096

# Interval edit pesan Telegram
EDIT_INTERVAL = 0.7


async def grooq_cmd(client, message):
    em = Emoji(client)
    await em.get()

    if not message.text:
        return

    query = message.text.split(None, 1)

    if len(query) < 2:
        return await message.reply(
            f"{em.gagal} Gunakan:\n"
            "`.ai pertanyaan`"
        )

    prompt = query[1].strip()

    if not prompt:
        return await message.reply(
            f"{em.gagal} Pertanyaan tidak boleh kosong."
        )

    # Batasi input agar request tetap aman
    if len(prompt) > MAX_PROMPT_LENGTH:
        return await message.reply(
            f"{em.gagal} Pertanyaan terlalu panjang.\n"
            f"Maksimal {MAX_PROMPT_LENGTH} karakter."
        )

    progress = await message.edit(
        f"{em.proses} Berpikir..."
    )

    try:
        # Groq Python SDK bersifat synchronous,
        # jadi jalankan request di thread.
        def create_stream():
            return groq.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=1,
                max_completion_tokens=2048,
                top_p=1,
                reasoning_effort="low",
                stream=True,
                stop=None
            )

        stream = await asyncio.to_thread(create_stream)

        result = ""
        last_edit = time.monotonic()

        # Terima response secara streaming
        for chunk in stream:
            if not chunk.choices:
                continue

            content = chunk.choices[0].delta.content

            if not content:
                continue

            result += content

            now = time.monotonic()

            # Edit Telegram secara berkala
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
                        parse_mode=ParseMode.HTML
                    )
                except Exception:
                    # Jangan hentikan proses kalau edit gagal
                    pass

                last_edit = now

        # Kalau AI tidak memberikan response
        if not result:
            result = "Tidak ada respons dari AI."

        # Final output
        display = html.escape(result)

        if len(display) > MAX_MESSAGE_LENGTH:
            display = (
                display[:MAX_MESSAGE_LENGTH - 20]
                + "\n\n…"
            )

        await progress.edit(
            f"{em.sukses}\n\n"
            f"<blockquote>{display}</blockquote>",
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        error = str(e)

        # Tangani error request terlalu besar
        if (
            "413" in error
            or "Request Entity Too Large" in error
            or "request_too_large" in error
        ):
            error = (
                "Request terlalu besar.\n\n"
                "Silakan gunakan pertanyaan yang lebih pendek."
            )

        error = html.escape(error[:3500])

        try:
            await progress.edit(
                f"{em.gagal} Terjadi kesalahan:\n"
                f"<code>{error}</code>",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass