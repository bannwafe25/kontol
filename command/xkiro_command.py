import html
import traceback

import config
from pyrogram.enums import ParseMode

from helpers import Emoji, Tools, animate_proses


SYSTEM_PROMPT = (
    "Kamu adalah chatbot AI dengan gaya bahasa toxic tongkrongan Indonesia. "
    "Ngobrol seperti teman dekat yang nyablak, santai, sarkastik, dan suka roasting. "
    "Gunakan bahasa gue, lu, bro, jir, anjir, bjir, cuy, wkwk, dan slang lainnya "
    "secara natural. Boleh ngegas, nyindir, dan ngeledek sebagai candaan. "
    "Jangan terlalu formal atau sok sopan. Kalau user ngaco, boleh roasting "
    "lalu tetap kasih jawaban yang benar. Kalau pertanyaan serius, tetap jawab "
    "dengan serius dan akurat. Jangan memaksakan kata kasar di setiap kalimat."
)


async def xkiro_cmd(client, message):
    em = Emoji(client)
    await em.get()

    proses = await animate_proses(message, em.proses)

    prompt = client.get_text(message)

    if not prompt:
        return await proses.edit(
            f"{em.gagal} <b>Kasih pertanyaan dulu jir.</b>",
            parse_mode=ParseMode.HTML,
        )

    if not config.XKIRO_API_KEY:
        return await proses.edit(
            f"{em.gagal} <b>XKIRO_API_KEY belum diatur.</b>\n"
            "Tambahkan API key ke file <code>.env</code>.",
            parse_mode=ParseMode.HTML,
        )

    chat_id = message.chat.id

    # Memory percakapan selama session berlangsung
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    while True:
        try:
            messages.append(
                {
                    "role": "user",
                    "content": prompt,
                }
            )

            headers = {
                "Authorization": f"Bearer {config.XKIRO_API_KEY}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": config.XKIRO_MODEL,
                "messages": messages,
                "temperature": 1,
                "max_tokens": 2048,
                "stream": False,
            }

            url = (
                f"{config.XKIRO_BASE_URL.rstrip('/')}"
                "/chat/completions"
            )

            response = await Tools.fetch.post(
                url,
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                # Hapus pesan user yang gagal diproses
                messages.pop()

                error = html.escape(
                    response.text[:1000]
                )

                return await proses.edit(
                    f"{em.gagal} <b>Xkiro API Error "
                    f"({response.status_code})</b>\n\n"
                    f"<code>{error}</code>",
                    parse_mode=ParseMode.HTML,
                )

            data = response.json()

            result = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )

            if not result:
                messages.pop()

                return await proses.edit(
                    f"{em.gagal} <b>AI tidak memberikan jawaban jir.</b>",
                    parse_mode=ParseMode.HTML,
                )

            # Simpan jawaban AI ke memory
            messages.append(
                {
                    "role": "assistant",
                    "content": result,
                }
            )

            # Telegram maksimal 4096 karakter
            display_result = result

            if len(display_result) > 3800:
                display_result = (
                    display_result[:3800]
                    + "\n\n<i>Response kepanjangan jir...</i>"
                )

            caption = (
                "<b><u>Chat with DeepSeek V4 Pro</u></b>\n\n"
                "<b>Question:</b>\n"
                f"<blockquote>{html.escape(prompt)}</blockquote>\n\n"
                "<b>Answer:</b>\n"
                f"<blockquote>{html.escape(display_result)}</blockquote>\n\n"
                "<i>Type <code>stopped ask</code> "
                "to end the conversation.</i>"
            )

            await proses.edit(
                caption,
                parse_mode=ParseMode.HTML,
            )

            # Tunggu pesan berikutnya
            next_message = await client.ask(
                chat_id,
                (
                    "<b>Chat with DeepSeek V4 Pro</b>\n\n"
                    "Kirim pesan berikutnya jir.\n"
                    "Ketik <code>stopped ask</code> "
                    "untuk mengakhiri."
                ),
                timeout=300,
            )

            # Stop conversation
            if (
                next_message.text
                and next_message.text.strip().lower()
                == "stopped ask"
            ):
                await next_message.reply(
                    "<b>Conversation ended.</b>",
                    parse_mode=ParseMode.HTML,
                )
                break

            # Ambil pertanyaan berikutnya
            prompt = next_message.text

            if not prompt:
                await next_message.reply(
                    f"{em.gagal} <b>Prompt kosong jir.</b>",
                    parse_mode=ParseMode.HTML,
                )
                continue

            # Pesan proses baru
            proses = await next_message.reply(
                f"{em.proses} <b>Lagi mikir jir...</b>",
                parse_mode=ParseMode.HTML,
            )

        except TimeoutError:
            await proses.edit(
                f"{em.gagal} <b>Conversation timeout.</b>\n"
                "Sesi chat dihentikan.",
                parse_mode=ParseMode.HTML,
            )
            break

        except Exception:
            logger.error(traceback.format_exc())

            try:
                await proses.edit(
                    f"{em.gagal} <b>Terjadi error jir.</b>\n"
                    "Coba lagi nanti.",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

            break
