import traceback

from pyrogram.errors import QueryIdInvalid

from command import (alive_inline, button_inline, get_inline_help,
                     get_inline_note, inline_afk, inline_anime, inline_autobc, inline_bmkg,
                     inline_calculator, inline_cancel, inline_card_info,
                     inline_cat, inline_chord,
                     inline_font, inline_info, inline_news,
                     inline_streaming, inline_youtube,
                     pmpermit_inline, send_inline)
from helpers import CMD
from logs import logger


@CMD.INLINE()
async def _(client, inline_query):
    try:
        text = inline_query.query.strip().lower()
        if not text:
            return
        answers = []
        if text.split()[0] == "help":
            answerss = await get_inline_help(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id, results=answerss, cache_time=0
            )
        elif text.split()[0] == "alive":
            answerss = await alive_inline(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "inline_send":
            tuju = text.split()[1]
            answerss = await send_inline(answers, inline_query, int(tuju))
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "make_button":
            tuju = text.split()[1]
            answerss = await button_inline(answers, inline_query, int(tuju))
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "pmpermit_inline":
            answerss = await pmpermit_inline(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "get_note":
            answerss = await get_inline_note(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "inline_font":
            answerss = await inline_font(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "inline_cat":
            answerss = await inline_cat(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "inline_news":
            answerss = await inline_news(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "inline_anime":
            answerss = await inline_anime(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "inline_info":
            answerss = await inline_info(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "inline_card_info":
            answerss = await inline_card_info(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "inline_chord":
            answerss = await inline_chord(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "inline_afk":
            answerss = await inline_afk(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "inline_bmkg":
            answerss = await inline_bmkg(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "inline_youtube":
            answerss = await inline_youtube(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "inline_autobc":
            answerss = await inline_autobc(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "inline_cancel":
            answerss = await inline_cancel(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] == "inline_streaming":
            answerss = await inline_streaming(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
        elif text.split()[0] in ["calculator", "calc", "kalkulator"]:
            answerss = await inline_calculator(answers, inline_query)
            return await client.answer_inline_query(
                inline_query.id,
                results=answerss,
                cache_time=0,
            )
    except QueryIdInvalid:
        return
    except TypeError:
        return
    except Exception:
        logger.error(f"{traceback.format_exc()}")
