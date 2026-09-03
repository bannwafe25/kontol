import asyncio
import html
import json
import time
import traceback

import requests
from pyrogram.enums import ParseMode

from config import XKIRO_API_KEY, XKIRO_BASE_URL, XKIRO_MODEL
from helpers import Emoji


MAX_PROMPT_LENGTH = 12000
MAX_MESSAGE_LENGTH = 4096
EDIT_INTERVAL = 0.7
CONVERSATION_TIMEOUT = 300

SYSTEM_PROMPT = (
    "Kamu adalah assistant AI dengan gaya bahasa tongkrongan toxic "
    "dan mudah dipahami."
)


def create_stream(history):
    return requests.post(
        f"{XKIRO_BASE_URL.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {XKIRO_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        json={
            "model": XKIRO_MODEL,
            "messages": history,
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

    proses = await animate_proses(message, em.proses)

    prompt = client.get_text(message)

    if not prompt:
        return await proses.edit(
            f"{em.gagal} <b>Please give a prompt.</b>"
        )

    if not XKIRO_API_KEY:
        return await proses.edit(
            f"{em.gagal} <b>XKIRO_API_KEY belum diatur.</b>"
        )

    if len(prompt) > MAX_PROMPT_LENGTH:
        return await proses.edit(
            f"{em.gagal} <b>Prompt terlalu panjang.</b>"
        )

    chat_id = message.chat.id

    history = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    while True:
        try:
            history.append({
                "role": "user",
                "content": prompt,
            })

            response = await asyncio.to_thread(
                create_stream,
                history,
            )

            if response.status_code == 200:
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
                        choices = chunk.get(
                            "choices",
                            [],
                        )

                        if not choices:
                            continue

                        content = choices[0].get(
                            "delta",
                            {},
                        ).get("content", "")

                        if not content:
                            continue

                        result += content

                        if (
                            time.monotonic() - last_edit
                            >= EDIT_INTERVAL
                        ):
                            display = html.escape(result)

                            if len(display) > MAX_MESSAGE_LENGTH:
                                display = (
                                    display[
                                        :MAX_MESSAGE_LENGTH - 20
                                    ]
                                    + "\n\n…"
                                )

                            try:
                                await proses.edit(
                                    f"{em.sukses}\n\n"
                                    f"<b>Question:</b>\n"
                                    f"<blockquote>"
                                    f"{html.escape(prompt)}"
                                    f"</blockquote>\n\n"
                                    f"<b>Answer:</b>\n"
                                    f"<blockquote>"
                                    f"{display}"
                                    f"</blockquote>",
                                    parse_mode=ParseMode.HTML,
                                )
                            except Exception:
                                pass

                            last_edit = time.monotonic()

                    except json.JSONDecodeError:
                        continue

                if not result:
                    result = "AI tidak memberikan respons."

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

                try:
                    await proses.edit(
                        f"{em.sukses}\n\n"
                        f"<b>Question:</b>\n"
                        f"<blockquote>"
                        f"{html.escape(prompt)}"
                        f"</blockquote>\n\n"
                        f"<b>Answer:</b>\n"
                        f"<blockquote>"
                        f"{display}"
                        f"</blockquote>\n\n"
                        f"<i>Type <code>.stop</code> "
                        f"to end the conversation.</i>",
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    pass

                next_message = await client.ask(
                    chat_id,
                    f"<b><u>Chat with Xkiro</u></b>\n\n"
                    f"<i>Send your next message...</i>\n\n"
                    f"<i>Type <code>.stop</code> "
                    f"to end the conversation.</i>",
                    timeout=CONVERSATION_TIMEOUT,
                )

                if not next_message:
                    break

                if not next_message.text:
                    continue

                next_prompt = next_message.text.strip()

                if next_prompt.lower() in (
                    ".stop",
                    "stop",
                    "stopped ask",
                ):
                    await next_message.reply(
                        f"{em.sukses} "
                        f"<b>Conversation ended.</b>",
                        parse_mode=ParseMode.HTML,
                    )
                    break

                if len(next_prompt) > MAX_PROMPT_LENGTH:
                    await next_message.reply(
                        f"{em.gagal} "
                        f"<b>Prompt terlalu panjang.</b>",
                        parse_mode=ParseMode.HTML,
                    )
                    continue

                prompt = next_prompt

                proses = await next_message.reply(
                    f"{em.proses} <b>Berpikir...</b>"
                )

            else:
                await proses.edit(
                    f"{em.gagal} "
                    f"<b>Please try again later..</b>"
                )
                break

        except asyncio.TimeoutError:
            try:
                await proses.edit(
                    f"{em.gagal} "
                    f"<b>Conversation timeout.</b>"
                )
            except Exception:
                pass
            break

        except requests.exceptions.Timeout:
            try:
                await proses.edit(
                    f"{em.gagal} "
                    f"<b>Request timeout.</b>"
                )
            except Exception:
                pass
            break

        except requests.exceptions.RequestException:
            logger.error(traceback.format_exc())

            try:
                await proses.edit(
                    f"{em.gagal} "
                    f"<b>Please try again later..</b>"
                )
            except Exception:
                pass

            break

        except Exception:
            logger.error(traceback.format_exc())

            try:
                await proses.edit(
                    f"{em.gagal} "
                    f"<b>Please try again later..</b>"
                )
            except Exception:
                pass

            break
