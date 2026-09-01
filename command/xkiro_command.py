import asyncio
import html
import json
import traceback

import requests

from config import XKIRO_API_KEY, XKIRO_BASE_URL, XKIRO_MODEL
from helpers import Emoji


SYSTEM_PROMPT = (
    "Kamu adalah chatbot AI dengan gaya bahasa toxic tongkrongan Indonesia. "
    "Ngobrol seperti teman dekat yang nyablak, santai, sarkastik, dan suka roasting. "
    "Gunakan bahasa gue, lu, bro, jir, anjir, bjir, cuy, wkwk, dan slang lainnya "
    "secara natural. Boleh ngegas, nyindir, dan ngeledek sebagai candaan. "
    "Jangan terlalu formal atau sok sopan. Kalau user ngaco, boleh roasting "
    "lalu tetap kasih jawaban yang benar. Kalau pertanyaannya serius, tetap "
    "jawab dengan serius dan akurat. Jangan memaksakan kata kasar di setiap kalimat."
)


async def xkiro_cmd(client, message):
    em = Emoji(client)
    await em.get()

    proses = await animate_proses(message, em.proses)

    prompt = client.get_text(message)

    if not prompt and not message.reply_to_message:
        return await proses.edit(
            f"{em.gagal} **Please give me a prompt.**"
        )

    if not XKIRO_API_KEY:
        return await proses.edit(
            f"{em.gagal} **XKIRO_API_KEY belum diatur di `.env`.**"
        )

    chat_id = message.chat.id

    # Memory conversation
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    while True:
        try:
            # Tambahkan pertanyaan user
            messages.append(
                {
                    "role": "user",
                    "content": prompt,
                }
            )

            headers = {
                "Authorization": f"Bearer {XKIRO_API_KEY}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": XKIRO_MODEL,
                "messages": messages,
                "temperature": 1,
                "max_tokens": 2048,
                "stream": False,
            }

            response = await asyncio.to_thread(
                requests.post,
                f"{XKIRO_BASE_URL.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )

            if response.status_code != 200:
                # Hapus pesan user jika request gagal
                messages.pop()

                return await proses.edit(
                    f"{em.gagal} **Xkiro API Error "
                    f"({response.status_code})**\n\n"
                    f"`{response.text[:1000]}`"
                )

            data = response.json()

            result = (
                data["choices"][0]["message"]["content"]
            )

            if not result:
                messages.pop()

                return await proses.edit(
                    f"{em.gagal} **AI tidak memberikan response.**"
                )

            # Simpan jawaban AI ke memory
            messages.append(
                {
                    "role": "assistant",
                    "content": result,
                }
            )

            # Telegram max message = 4096
            if len(result) > 4096:
                result = result[:4090] + "..."

            caption = (
                f"<b><u>Chat with DeepSeek V4 Pro</u></b>\n\n"
                f"<b>Question:</b>\n"
                f"<blockquote>{html.escape(prompt)}</blockquote>\n\n"
                f"<b>Answer:</b>\n"
                f"<blockquote>{html.escape(result)}</blockquote>\n\n"
                f"<i>Type <code>stopped ask</code> to end "
                f"the conversation.</i>"
            )

            await proses.edit(
                caption
            )

            # Tunggu pesan berikutnya
            next_message = await client.ask(
                chat_id,
                "<b>Chat with DeepSeek V4 Pro</b>\n\n"
                "Kirim pesan berikutnya.\n"
                "Ketik <code>stopped ask</code> untuk mengakhiri.",
                timeout=300,
            )

            if (
                next_message.text
                and next_message.text.strip().lower()
                == "stopped ask"
            ):
                await next_message.reply(
                    "**Conversation ended.**"
                )
                break

            # Pesan berikutnya menjadi prompt
            prompt = next_message.text

            if not prompt:
                await next_message.reply(
                    f"{em.gagal} **Prompt kosong jir.**"
                )
                continue

            # Tampilkan proses di pesan berikutnya
            proses = await next_message.reply(
                f"{em.proses} **Lagi mikir jir...**"
            )

        except asyncio.TimeoutError:
            await proses.edit(
                f"{em.gagal} **Conversation timeout.**\n"
                "Sesi chat otomatis dihentikan."
            )
            break

        except Exception:
            logger.error(traceback.format_exc())

            try:
                await proses.edit(
                    f"{em.gagal} **Terjadi kesalahan. Coba lagi nanti.**"
                )
            except Exception:
                pass

            break
