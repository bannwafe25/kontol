import asyncio
import html
import json
import re
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
    "dan mudah dipahami. "
    "Gunakan bahasa Indonesia santai dan natural. "
    "Gunakan Markdown sederhana jika perlu."
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


def markdown_to_telegram(text):
    """Convert Markdown sederhana ke Telegram HTML."""

    if not text:
        return ""

    # Perbaiki UTF-8 mojibake jika terjadi.
    try:
        if "Ã" in text or "ð" in text or "â" in text:
            fixed = text.encode("latin1").decode("utf-8")
            text = fixed
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    # Escape HTML terlebih dahulu.
    text = html.escape(text, quote=False)

    # Code block
    text = re.sub(
        r"```(?:\w+)?\n?(.*?)```",
        lambda m: f"<pre>{m.group(1).strip()}</pre>",
        text,
        flags=re.DOTALL,
    )

    # Inline code
    text = re.sub(
        r"`([^`\n]+)`",
        r"<code>\1</code>",
        text,
    )

    # Bold
    text = re.sub(
        r"\*\*(.+?)\*\*",
        r"<b>\1</b>",
        text,
        flags=re.DOTALL,
    )

    text = re.sub(
        r"__(.+?)__",
        r"<b>\1</b>",
        text,
        flags=re.DOTALL,
    )

    # Italic
    text = re.sub(
        r"(?<!\*)\*([^*\n]+)\*(?!\*)",
        r"<i>\1</i>",
    )

    # Strikethrough
    text = re.sub(
        r"~~(.+?)~~",
        r"<s>\1</s>",
        text,
        flags=re.DOTALL,
    )

    # Markdown heading
    text = re.sub(
        r"(?m)^#{1,6}\s+(.+)$",
        r"<b>\1</b>",
        text,
    )

    # Horizontal separator
    text = re.sub(
        r"(?m)^\s*([-*_])(?:\s*\1){2,}\s*$",
        "",
        text,
    )

    # Bullet list
    text = re.sub(
        r"(?m)^\s*[-*+]\s+",
        "• ",
        text,
    )

    # Numbered list tetap rapi
    text = re.sub(
        r"(?m)^\s*(\d+)[.)]\s+",
        r"\1. ",
        text,
    )

    return text.strip()


def format_answer(prompt, answer, em):
    question = html.escape(prompt, quote=False)
    answer = markdown_to_telegram(answer)

    return (
        f"{em.sukses}\n\n"
        f"<b>Question:</b>\n"
        f"<blockquote>{question}</blockquote>\n\n"
        f"<b>Answer:</b>\n"
        f"<blockquote>{answer}</blockquote>"
    )


def limit_message(text):
    if len(text) <= MAX_MESSAGE_LENGTH:
        return text

    return text[:MAX_MESSAGE_LENGTH - 20] + "\n\n…"


async def xkiro_cmd(client, message):
    em = Emoji(client)
    await em.get()

    prompt = client.get_text(message)

    if not prompt:
        return await message.reply(
            f"{em.gagal} <b>Please give a prompt.</b>",
            parse_mode=ParseMode.HTML,
        )

    if not XKIRO_API_KEY:
        return await message.reply(
            f"{em.gagal} <b>XKIRO_API_KEY belum diatur.</b>",
            parse_mode=ParseMode.HTML,
        )

    if len(prompt) > MAX_PROMPT_LENGTH:
        return await message.reply(
            f"{em.gagal} <b>Prompt terlalu panjang.</b>",
            parse_mode=ParseMode.HTML,
        )

    chat_id = message.chat.id

    history = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    proses = await message.reply(
        f"{em.proses} <b>Berpikir...</b>",
        parse_mode=ParseMode.HTML,
    )

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

            if response.status_code != 200:
                error = html.escape(
                    response.text[:2000],
                    quote=False,
                )

                await proses.edit(
                    f"{em.gagal} "
                    f"<b>Xkiro API Error "
                    f"({response.status_code})</b>\n\n"
                    f"<code>{error}</code>",
                    parse_mode=ParseMode.HTML,
                )
                break

            result = ""
            last_edit = time.monotonic()

            # Paksa decode UTF-8.
            response.encoding = "utf-8"

            for line in response.iter_lines(
                decode_unicode=True
            ):
                if not line:
                    continue

                if not line.startswith("data:"):
                    continue

                data = line[5:].strip()

                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices", [])

                if not choices:
                    continue

                content = (
                    choices[0]
                    .get("delta", {})
                    .get("content", "")
                )

                if not content:
                    continue

                result += content

                if (
                    time.monotonic() - last_edit
                    >= EDIT_INTERVAL
                ):
                    display = limit_message(
                        markdown_to_telegram(result)
                    )

                    try:
                        await proses.edit(
                            format_answer(
                                prompt,
                                display,
                                em,
                            ),
                            parse_mode=ParseMode.HTML,
                        )
                    except Exception:
                        pass

                    last_edit = time.monotonic()

            if not result:
                result = "AI tidak memberikan respons."

            history.append({
                "role": "assistant",
                "content": result,
            })

            display = limit_message(
                markdown_to_telegram(result)
            )

            try:
                await proses.edit(
                    format_answer(
                        prompt,
                        display,
                        em,
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

            # Tunggu pesan berikutnya tanpa prompt terlihat.
            next_message = await client.ask(
                chat_id,
                "",
                timeout=CONVERSATION_TIMEOUT,
            )

            if not next_message:
                break

            if not next_message.text:
                continue

            next_prompt = next_message.text.strip()

            if not next_prompt:
                continue

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
                f"{em.proses} <b>Berpikir...</b>",
                parse_mode=ParseMode.HTML,
            )

        except asyncio.TimeoutError:
            try:
                await proses.edit(
                    f"{em.gagal} "
                    f"<b>Conversation timeout.</b>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
            break

        except requests.exceptions.Timeout:
            try:
                await proses.edit(
                    f"{em.gagal} "
                    f"<b>Request timeout.</b>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
            break

        except requests.exceptions.RequestException:
            print(traceback.format_exc())

            try:
                await proses.edit(
                    f"{em.gagal} "
                    f"<b>Please try again later..</b>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

            break

        except Exception:
            print(traceback.format_exc())

            try:
                await proses.edit(
                    f"{em.gagal} "
                    f"<b>Please try again later..</b>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

            break
