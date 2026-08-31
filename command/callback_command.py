import re
import time
import os
import asyncio
import traceback
from math import ceil
from gc import get_objects

import requests
import wget
from pyrogram import enums, filters, raw
from pyrogram.errors import (FloodPremiumWait, FloodWait, MediaCaptionTooLong,
                             MessageNotModified)
from pyrogram.helpers import ikb
from pyrogram.raw.types import InputGroupCall
from pyrogram.types import InlineKeyboardButton as Ikb
from pyrogram.types import (InlineKeyboardMarkup, InputMediaAnimation,
                            InputMediaAudio, InputMediaDocument,
                            InputMediaPhoto, InputMediaVideo)
from pyrogram.utils import unpack_inline_message_id
from pytgcalls.exceptions import NoActiveGroupCall, NotInCallError
from pytz import timezone

from clients import bot, navy, session
from config import (API_MAELYN, BOT_NAME, HELPABLE, KYNAN, LOG_SELLER,
                    SUDO_OWNERS, USENAME_OWNER)
from database import dB, state
from helpers import (ButtonUtils, Emoji, Message, Spotify, Tools, gens_font,
                     paginate_modules, paginate_categories, query_fonts, stream, task, youtube, download_thumbnail, EqInlineKeyboardButton)
          
from logs import logger

from .pmpermit_command import LIMIT, flood
from .streaming_command import skip_songs

MESSAGE_DICT = {}
CONVERSATIONS = {}


top_text = """
<b>Inline Help
    Plan: <b>{}</b>
    Prefixes: <code>{}</code>
    Plugins: <code>{}</code>
    {}</b>
<blockquote>{}</blockquote>"""

text_markdown = "**To view markdown format please click on the button below.**"

text_formatting = """
> **Markdown Formatting**
> Anda dapat memformat pesan Anda menggunakan **tebal**, _miring_, --garis bawah--, ~~coret~~, dan banyak lagi.
>
> `<code>kata kode</code>`: Tanda kutip terbalik digunakan buat font monospace. Ditampilkan sebagai: `kata kode`.
>
> `<i>miring</i>`: Garis bawah digunakan buat font miring. Ditampilkan sebagai: __kata miring__.
>
> `<b>tebal</b>`: Asterisk digunakan buat font tebal. Ditampilkan sebagai: **kata tebal**.
>
> `<u>garis bawah</u>`: Buat membuat teks --garis bawah--.
>
> `<strike>coret</strike>`: Tilda digunakan buat strikethrough. Ditampilkan sebagai: ~~coret~~.
>
> `<spoiler>spoiler</spoiler>`: Garis vertikal ganda digunakan buat spoiler. Ditampilkan sebagai: ||spoiler||.
>
> `[hyperlink](contoh)`: Ini adalah pemformatan yang digunakan buat hyperlink.
>
> `<blockquote>teks quote</blockquote>`: Ini adalah pemformatan untuk > teks quote >
>
> `Hallo Disini [Tombol 1|https://link.com]` : Ini adalah pemformatan yang digunakan membuat tombol.
> `Halo Disini [Tombol 1|t.me/kynansupport][Tombol 2|t.me/kontenfilm|same]` : Ini akan membuat tombol berdampingan.
>
> Anda juga bisa membuat tombol callback_data dengan diawal tanda `cb_`
> Jika ingin membuat copy text gunakan Halo Disini `[Click To Copy|copy:1234]`
> Contoh callback `Halo Disini [Tombol 1|data][Tombol 2|data|same]`
>
> Anda juga dapat membuat tombol callback answer dengan diawal tanda `alert:`
> Contoh callback answer`Halo Disini [Tombol 1|alert:Yang klik jelek][Tombol 2|alert:Jangan diklik Tapi boong|same]`
>
> Anda juga dapat membuat teks collapsed dengan button
> Contoh `<blockquote expandable>Aku adalah zpxuserbot yang dikembang oleh @iscrtz dan aku adalah userbot generasi ke 3 setelah KN-Userbot Aku lebih sempurna dari generasi sebelumnya karna aku dibuat dengan memprioritaskan flexibilitas</blockquote> [Owner|https://t.me/iscrtz]`
>
"""

text_fillings = "<blockquote expandable><b>Fillings</b>\n\nAnda juga dapat menyesuaikan isi pesan Anda dengan data kontekstual. Misalnya, Anda bisa menyebut nama pengguna dalam pesan selamat datang, atau menyebutnya dalam filter!\n\n<b>Isian yang didukung:</b>\n\n<code>{first}</code>: Nama depan pengguna.\n<code>{last}</code>: Nama belakang pengguna.\n<code>{fullname}</code>: Nama lengkap pengguna.\n<code>{username}</code>: Nama pengguna pengguna. Jika mereka tidak memiliki satu, akan menyebutkan pengguna tersebut.\n<code>{mention}</code>: Menyebutkan pengguna dengan nama depan mereka.\n<code>{id}</code>: ID pengguna.\n<code>{date}</code>: Tanggal, <code>{day}</code>: hari, <code>{month}</code>: bulan, <code>{year}</code>: tahun, <code>{hour}</code>: jam, <code>{minute}</code>: menit.</blockquote>"


async def callback_alert(_, callback_query):
    uniq = callback_query.data.split("_")[1]
    alert_text = await dB.get_var(uniq, f"{uniq}")
    if len(alert_text) > 200:
        return await callback_query.answer(
            "Alert text is too long, please keep it under 200 characters.",
            show_alert=True,
        )
    if r"\n" in alert_text:
        alert_text = alert_text.replace(r"\n", "\n")
    return await callback_query.answer(text=alert_text, show_alert=True)


async def callback_cancel(_, callback_query):
    data = callback_query.data.split()
    query = data[0]

    if query == "cancel_task":
        taskid = data[1]
        get_id = int(data[2])

        message = [
            obj for obj in get_objects()
            if id(obj) == get_id
        ][0]

        if not message:
            return await callback_query.answer(
                "Message not found",
                True,
            )

        client = message._client

        sudo_users = await dB.get_list_from_var(
            client.me.id,
            "SUDOERS",
        )

        if (
            callback_query.from_user.id not in sudo_users
            and callback_query.from_user.id != client.me.id
        ):
            return await callback_query.answer(
                "GW BUNTUNGIN TANGAN LO YA MEMEK",
                True,
            )

        if not task.is_active(taskid):
            return await callback_query.answer(
                "This task has been completed or canceled.",
                True,
            )

        data_todelete = state.get(
            f"inline_cancel {taskid} {get_id}",
            f"inline_cancel {taskid} {get_id}",
        )

        chat_id = int(data_todelete.get("chat"))
        msgid = int(data_todelete.get("_id"))

        await client.delete_messages(
            chat_id,
            msgid,
        )

        task.end_task(taskid)

        return await message.reply(
            f"**Ended task: #`{taskid}`**"
        )

    elif query == "vctools":
        command = str(data[1])
        uniq = str(data[2])
        chat_id = int(data[3])

        user_id = callback_query.from_user.id
        userbot = session.get_session(user_id)

        data_vctools = state.get(
            uniq,
            uniq,
        )

        if not data_vctools:
            return await callback_query.answer(
                "Data not valid",
                True,
            )

        # =====================================================
        # VC MENU
        # =====================================================

        if command == "menu":
            info_chat = state.get(
                chat_id,
                chat_id,
            )

            title = info_chat.get("title")

            teks = (
                f"<b>Voice Chat Tools\n"
                f"Chat: <code>{title}</code>\n"
                f"ID: <code>{chat_id}</code></b>"
            )

            sub_buttons = InlineKeyboardMarkup(
                [
                    [
                        Ikb(
                            "🎙 Open Mic",
                            callback_data=(
                                f"vctools openmic {uniq} {chat_id}"
                            ),
                            style=enums.ButtonStyle.SUCCESS,
                        ),
                        Ikb(
                            "🔇 Mute Mic",
                            callback_data=(
                                f"vctools mutemic {uniq} {chat_id}"
                            ),
                            style=enums.ButtonStyle.DANGER,
                        ),
                    ],
                    [
                        Ikb(
                            "❌ Leave VC",
                            callback_data=(
                                f"vctools leavevc {uniq} {chat_id}"
                            ),
                            style=enums.ButtonStyle.DANGER,
                        ),
                        Ikb(
                            "👥 Listeners",
                            callback_data=(
                                f"vctools listner {uniq} {chat_id}"
                            ),
                            style=enums.ButtonStyle.PRIMARY,
                        ),
                    ],
                    [
                        Ikb(
                            "✏️ Set Title",
                            callback_data=(
                                f"vctools vctitle {uniq} {chat_id}"
                            ),
                            style=enums.ButtonStyle.PRIMARY,
                        ),
                    ],
                    [
                        Ikb(
                            "⬅️ Back",
                            callback_data=(
                                f"vctools back {uniq} {chat_id}"
                            ),
                            style=enums.ButtonStyle.DANGER,
                        ),
                    ],
                ]
            )

            return await callback_query.edit_message_text(
                teks,
                reply_markup=sub_buttons,
            )

        # =====================================================
        # BACK
        # =====================================================

        elif command == "back":
            data_vctools = state.get(
                uniq,
                uniq,
            )

            targets = data_vctools.get(
                "targets",
                [],
            )

            teks = data_vctools.get(
                "text",
                "",
            )

            all_buttons = []

            for chat in targets:
                info_chat = await userbot.get_chat(chat)

                title = info_chat.title
                target_chat_id = info_chat.id

                all_buttons.append(
                    [
                        Ikb(
                            f"🎙 {title}",
                            callback_data=(
                                f"vctools menu "
                                f"{uniq} "
                                f"{target_chat_id}"
                            ),
                            style=enums.ButtonStyle.PRIMARY,
                        )
                    ]
                )

            return await callback_query.edit_message_text(
                teks,
                reply_markup=InlineKeyboardMarkup(
                    all_buttons
                ),
            )

        # =====================================================
        # OPEN MIC
        # =====================================================

        elif command == "openmic":
            info_chat = state.get(
                chat_id,
                chat_id,
            )
            title = info_chat.get("title")

            group_call = await userbot.get_call(
                chat_id
            )

            if not group_call:
                return await callback_query.answer(
                    f"No active VC in {title}",
                    True,
                )

            try:
                await userbot.group_call.unmute_stream(
                    chat_id
                )

                return await callback_query.answer(
                    f"Mic opened in {title} {chat_id}"
                )

            except (
                NotInCallError,
                NoActiveGroupCall,
            ):
                return await callback_query.answer(
                    f"No active VC in {title}",
                    True,
                )

        # =====================================================
        # MUTE MIC
        # =====================================================

        elif command == "mutemic":
            info_chat = state.get(
                chat_id,
                chat_id,
            )
            title = info_chat.get("title")

            group_call = await userbot.get_call(
                chat_id
            )

            if not group_call:
                return await callback_query.answer(
                    f"No active VC in {title}",
                    True,
                )

            try:
                await userbot.group_call.mute_stream(
                    chat_id
                )

                return await callback_query.answer(
                    f"Mic muted in {title} {chat_id}"
                )

            except (
                NotInCallError,
                NoActiveGroupCall,
            ):
                return await callback_query.answer(
                    f"No active VC in {title}",
                    True,
                )

        # =====================================================
        # LEAVE VC
        # =====================================================

        elif command == "leavevc":
            info_chat = state.get(
                chat_id,
                chat_id,
            )
            title = info_chat.get("title")

            group_call = await userbot.get_call(
                chat_id
            )

            if not group_call:
                return await callback_query.answer(
                    f"No active VC in {title}",
                    True,
                )

            try:
                await userbot.group_call.leave_call(
                    chat_id
                )

                return await callback_query.answer(
                    f"Left VC in {title} {chat_id}"
                )

            except (
                NotInCallError,
                NoActiveGroupCall,
            ):
                return await callback_query.answer(
                    f"No active VC in {title}",
                    True,
                )

        # =====================================================
        # SET TITLE
        # =====================================================

        elif command == "vctitle":
            info_chat = state.get(
                chat_id,
                chat_id,
            )

            title = info_chat.get("title")

            group_call = await userbot.get_call(
                chat_id
            )

            if not group_call:
                return await callback_query.answer(
                    f"No active VC in {title}",
                    True,
                )

            try:
                new_title = await bot.ask(
                    callback_query.message.chat.id,
                    (
                        f"**Send me the new title for VC "
                        f"in {title}**\n\n"
                        f"__You have 2 minutes to send the "
                        f"title, this request will be canceled "
                        f"after 2 minutes.__"
                    ),
                    timeout=120,
                    filters=filters.text,
                )

            except TimeoutError:
                return await callback_query.answer(
                    "Request canceled due to timeout.",
                    True,
                )

            new_title = new_title.text.strip()

            try:
                await userbot.invoke(
                    raw.functions.phone.EditGroupCallTitle(
                        call=InputGroupCall(
                            id=group_call.id,
                            access_hash=group_call.access_hash,
                        ),
                        title=new_title,
                    )
                )

                return await callback_query.answer(
                    f"Changed VC title to "
                    f"'{new_title}' in {title}",
                    True,
                )

            except Exception as e:
                return await callback_query.answer(
                    f"Error: {e}",
                    True,
                )

        # =====================================================
        # LISTENERS
        # =====================================================

        elif command == "listner":
            info_chat = state.get(
                chat_id,
                chat_id,
            )

            title = info_chat.get("title")

            group_call = await userbot.get_call(
                chat_id
            )

            if not group_call:
                return await callback_query.answer(
                    f"No active VC in {title}",
                    True,
                )

            call_title = group_call.title

            userbot.group_call.cache_peer(
                chat_id
            )

            participants = (
                await userbot.group_call.get_participants(
                    chat_id
                )
            )

            mentions = []

            for participant in participants:
                user_id = participant.user_id

                try:
                    user = await userbot.get_users(
                        user_id
                    )

                    mention = user.mention
                    volume = participant.volume

                    status = (
                        "🔇 Muted"
                        if participant.muted
                        else "🔊 Speaking"
                    )

                    mentions.append(
                        f"<b>{mention} | "
                        f"status: <code>{status}</code> | "
                        f"volume: <code>{volume}</code></b>"
                    )

                except Exception:
                    mentions.append(
                        f"{user_id} status Unknown"
                    )

            total_participants = len(
                participants
            )

            if total_participants == 0:
                return await callback_query.answer(
                    f"No participants in {title}",
                    True,
                )

            mentions_text = "\n".join(
                [
                    (
                        f"┣ {mention}"
                        if i < total_participants - 1
                        else f"┖ {mention}"
                    )
                    for i, mention in enumerate(
                        mentions
                    )
                ]
            )

            text = f"""
<b>Voice Chat Listeners:

Chat: <code>{title}</code>.
Total: <code>{total_participants}</code> people.
Title: <code>{call_title}</code>

❒ Participants:
{mentions_text}</b>
"""

            sub_buttons = InlineKeyboardMarkup(
                [
                    [
                        Ikb(
                            "🎙 Open Mic",
                            callback_data=(
                                f"vctools openmic {uniq} {chat_id}"
                            ),
                            style=enums.ButtonStyle.SUCCESS,
                        ),
                        Ikb(
                            "🔇 Mute Mic",
                            callback_data=(
                                f"vctools mutemic {uniq} {chat_id}"
                            ),
                            style=enums.ButtonStyle.DANGER,
                        ),
                    ],
                    [
                        Ikb(
                            "❌ Leave VC",
                            callback_data=(
                                f"vctools leavevc {uniq} {chat_id}"
                            ),
                            style=enums.ButtonStyle.DANGER,
                        ),
                        Ikb(
                            "👥 Listeners",
                            callback_data=(
                                f"vctools listner {uniq} {chat_id}"
                            ),
                            style=enums.ButtonStyle.PRIMARY,
                        ),
                    ],
                    [
                        Ikb(
                            "✏️ Set Title",
                            callback_data=(
                                f"vctools vctitle {uniq} {chat_id}"
                            ),
                            style=enums.ButtonStyle.PRIMARY,
                        ),
                    ],
                    [
                        Ikb(
                            "⬅️ Back",
                            callback_data=(
                                f"vctools back {uniq} {chat_id}"
                            ),
                            style=enums.ButtonStyle.DANGER,
                        ),
                    ],
                ]
            )

            return await callback_query.message.edit_text(
                text,
                reply_markup=sub_buttons,
            )


async def cb_markdown(_, callback_query):
    await callback_query.answer()
    data = callback_query.data.split("_")[1]
    user_id = callback_query.from_user.id
    cekpic = await dB.get_var(user_id, "HELP_LOGO")
    costum_cq = (
        callback_query.edit_message_caption
        if cekpic
        else callback_query.edit_message_text
    )
    full = f"<a href=tg://user?id={callback_query.from_user.id}>{callback_query.from_user.first_name} {callback_query.from_user.last_name or ''}</a>"
    costum_text = "caption" if cekpic else "text"
    prev_page_num = state.get(user_id, "prev_page_num")
    if data == "format":
        # text = f"<blockquote expandable>{text_formatting.strip()}</blockquote>"
        try:
            button = ikb(
                [
                    [
                        ("Formatting", "markdown_format", "callback_data"),
                        ("Fillings", "markdown_fillings", "callback_data"),
                    ],
                    [
                        ("🔙 Back", f"help_back({prev_page_num})"),
                    ],
                ]
            )
            return await costum_cq(
                **{costum_text: text_formatting.strip()},
                reply_markup=button,
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.MARKDOWN,
            )

        except (FloodWait, FloodPremiumWait) as e:
            return await callback_query.answer(f"FloodWait {e}, Please Waiting!!", True)

        except MessageNotModified:
            return
    elif data == "fillings":
        text = f"<blockquote expandable>{text_fillings.strip()}</blockquote>"
        try:
            button = ikb(
                [
                    [
                        ("Formatting", "markdown_format", "callback_data"),
                        ("Fillings", "markdown_fillings", "callback_data"),
                    ],
                    [
                        ("🔙 Back", f"help_back({prev_page_num})"),
                    ],
                ]
            )
            return await costum_cq(
                **{costum_text: text},
                reply_markup=button,
            )
        except (FloodWait, FloodPremiumWait) as e:
            return await callback_query.answer(f"FloodWait {e}, Please Waiting!!", True)

        except MessageNotModified:
            return


async def cb_help(_, callback_query):
    await callback_query.answer()

    data = callback_query.data
    user_id = callback_query.from_user.id

    # =====================================================
    # PLAN
    # =====================================================

    is_bot = await dB.get_var(
        user_id,
        "is_bot",
    )

    is_pro = await dB.get_var(
        user_id,
        "is_bot_pro",
    )

    is_basic = await dB.get_var(
        user_id,
        "is_bot_basic",
    )

    # =====================================================
    # FILTER PLUGIN SESUAI PLAN
    # =====================================================

    if is_bot:

        # -------------------------
        # PRO
        # -------------------------

        if is_pro:
            visible = HELPABLE
            plan = "Pro"

        # -------------------------
        # BASIC
        # -------------------------

        elif is_basic:
            visible = {
                k: v
                for k, v in HELPABLE.items()
                if not v.get("is_pro", False)
            }

            plan = "Basic"

        # -------------------------
        # LITE
        # -------------------------

        else:
            visible = {
                k: v
                for k, v in HELPABLE.items()
                if not v.get("is_pro", False)
                and not v.get("is_basic", False)
            }

            plan = "Lite"

    else:

        user_plan = (
            await dB.get_var(
                user_id,
                "plan",
            )
            or "lite"
        )

        # -------------------------
        # PRO
        # -------------------------

        if user_plan == "is_pro":
            visible = HELPABLE
            plan = "Pro"

        # -------------------------
        # BASIC
        # -------------------------

        elif user_plan == "basic":
            visible = {
                k: v
                for k, v in HELPABLE.items()
                if not v.get("is_pro", False)
            }

            plan = "Basic"

        # -------------------------
        # LITE
        # -------------------------

        else:
            visible = {
                k: v
                for k, v in HELPABLE.items()
                if not v.get("is_pro", False)
                and not v.get("is_basic", False)
            }

            plan = "Lite"

    # =====================================================
    # DATA
    # =====================================================

    prefix = navy.get_prefix(
        user_id
    )

    x_ = next(
        iter(prefix)
    )

    cekpic = await dB.get_var(
        user_id,
        "HELP_LOGO",
    )

    # =====================================================
    # EDIT TEXT / CAPTION
    # =====================================================

    costum_cq = (
        callback_query.edit_message_caption
        if cekpic
        else callback_query.edit_message_text
    )

    costum_text = (
        "caption"
        if cekpic
        else "text"
    )

    # =====================================================
    # CATEGORY PAGE PREV / NEXT
    # =====================================================

    match = re.match(
        r"help_categories_(prev|next)\((\d+)\)",
        data,
    )

    if match:

        page = int(
            match.group(2)
        )

        return await costum_cq(
            **{
                costum_text:
                    top_text.format(
                        plan,
                        " ".join(prefix),
                        len(visible),
                        callback_query
                        .from_user
                        .mention,
                        await dB.get_var(
                            user_id,
                            "text_help",
                        )
                        or (
                            f"**🤖 "
                            f"{BOT_NAME} "
                            f"by "
                            f"{USENAME_OWNER}**"
                        ),
                    )
            },
            reply_markup=InlineKeyboardMarkup(
                paginate_categories(
                    page,
                    visible,
                    "help",
                    is_bot=is_bot,
                )
            ),
        )

    # =====================================================
    # MODULE DETAIL
    # =====================================================

    match = re.match(
        r"help_module\((.+?),(\d+),(\d+)\)",
        data,
    )

    if match:

        module_name = match.group(1).strip()

        category_page = int(
            match.group(2)
        )

        module_page = int(
            match.group(3)
        )

        # -------------------------------------------------
        # CEK MODULE
        # -------------------------------------------------

        if module_name not in visible:

            return await callback_query.answer(
                "Plugin tidak tersedia untuk plan kamu.",
                show_alert=True,
            )

        module_data = visible[
            module_name
        ]

        module = module_data[
            "module"
        ]

        # -------------------------------------------------
        # CATEGORY
        # -------------------------------------------------

        category = getattr(
            module,
            "__CATEGORY__",
            "Other",
        )

        category = str(
            category
        ).strip()

        if not category:
            category = "Other"

        # -------------------------------------------------
        # HELP
        # -------------------------------------------------

        help_text = getattr(
            module,
            "__HELP__",
            "Help untuk plugin ini belum tersedia.",
        )

        try:

            text = help_text.format(
                x_,
                (
                    "<blockquote>"
                    "<b>🤖 "
                    f"{BOT_NAME} "
                    "by "
                    f"{USENAME_OWNER}"
                    "</b>"
                    "</blockquote>"
                ),
            )

        except Exception:

            text = help_text

        # -------------------------------------------------
        # BACK TO MODULE LIST
        # -------------------------------------------------

        buttons = ikb(
            [
                [
                    (
                        "🔙 Back",
                        (
                            f"help_category("
                            f"{category},"
                            f"{category_page},"
                            f"{module_page}"
                            f")"
                        ),
                    )
                ]
            ]
        )

        return await costum_cq(
            **{
                costum_text: text,
            },
            reply_markup=buttons,
        )

    # =====================================================
    # CATEGORY
    # =====================================================

    match = re.match(
        r"help_category\((.+?),(\d+)(?:,(\d+))?\)",
        data,
    )

    if match:

        category = match.group(1).strip()

        category_page = int(
            match.group(2)
        )

        module_page = int(
            match.group(3) or 0
        )

        # -------------------------------------------------
        # CEK CATEGORY
        # -------------------------------------------------

        modules = []

        for item in visible.values():

            module = item.get(
                "module"
            )

            if module is None:
                continue

            if not hasattr(
                module,
                "__MODULES__",
            ):
                continue

            plugin_category = getattr(
                module,
                "__CATEGORY__",
                "Other",
            )

            plugin_category = str(
                plugin_category
            ).strip()

            if not plugin_category:
                plugin_category = "Other"

            if plugin_category == category:

                modules.append(
                    module.__MODULES__
                )

        # -------------------------------------------------
        # CATEGORY KOSONG
        # -------------------------------------------------

        if not modules:

            return await callback_query.answer(
                "Kategori tidak ditemukan atau tidak memiliki plugin.",
                show_alert=True,
            )

        # -------------------------------------------------
        # SORT
        # -------------------------------------------------

        modules = sorted(
            modules,
            key=lambda x: x.lower(),
        )

        # -------------------------------------------------
        # HITUNG PAGE
        # -------------------------------------------------

        per_page = 8

        total_pages = max(
            1,
            ceil(
                len(modules) /
                per_page
            ),
        )

        module_page = max(
            0,
            min(
                module_page,
                total_pages - 1,
            ),
        )

        # -------------------------------------------------
        # KEYBOARD
        #
        # SEMUA LOGIC BUTTON ADA DI button.py
        # -------------------------------------------------

        buttons = paginate_modules(
            category,
            category_page,
            visible,
            "help",
            module_page,
        )

        # -------------------------------------------------
        # TEXT
        # -------------------------------------------------

        category_text = (
            f"<b>📂 {category}</b>\n\n"
            f"Jumlah plugin: "
            f"<code>{len(modules)}</code>\n"
            f"Halaman: "
            f"<code>"
            f"{module_page + 1}/"
            f"{total_pages}"
            f"</code>"
        )

        return await costum_cq(
            **{
                costum_text:
                    category_text,
            },
            reply_markup=InlineKeyboardMarkup(
                buttons
            ),
        )

    # =====================================================
    # BACK TO CATEGORY
    # =====================================================

    match = re.match(
        r"help_back\((\d+)\)",
        data,
    )

    if match:

        page = int(
            match.group(1)
        )

        return await costum_cq(
            **{
                costum_text:
                    top_text.format(
                        plan,
                        " ".join(prefix),
                        len(visible),
                        callback_query
                        .from_user
                        .mention,
                        await dB.get_var(
                            user_id,
                            "text_help",
                        )
                        or (
                            f"**🤖 "
                            f"{BOT_NAME} "
                            f"by "
                            f"{USENAME_OWNER}**"
                        ),
                    )
            },
            reply_markup=InlineKeyboardMarkup(
                paginate_categories(
                    page,
                    visible,
                    "help",
                    is_bot=is_bot,
                )
            ),
        )

    # =====================================================
    # NO OP
    # =====================================================

    if data == "help_noop":
        return await callback_query.answer()

async def del_userbot(_, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in SUDO_OWNERS:
        return await callback_query.answer(
            f"<b>GAUSAH DIPENCET YA ANJING! {callback_query.from_user.first_name} {callback_query.from_user.last_name or ''}",
            True,
        )
    try:
        show = await bot.get_users(callback_query.data.split()[1])
        get_id = show.id
        get_mention = f"<a href=tg://user?id={get_id}>{show.first_name} {show.last_name or ''}</a>"
    except Exception:
        get_id = int(callback_query.data.split()[1])
        get_mention = f"<a href=tg://user?id={get_id}>Userbot</a>"
    X = session.get_session(get_id)
    if X:
        try:
            await X.unblock_user(bot.me.username)
            await bot.send_message(
                X.me.id,
                f"<b>💬 Masa Aktif Anda Telah Habis</b>",
            )
        except Exception:
            pass
        await dB.remove_ubot(X.me.id)
        await dB.rem_expired_date(X.me.id)
        await dB.revoke_token(X.me.id, deleted=True)
        session.remove_session(X.me.id)
        try:
            await X.log_out()
        except Exception:
            pass
        return await bot.send_message(
            LOG_SELLER,
            f"<b> ✅ {get_mention} Deleted on database</b>",
        )


async def tools_acc(_, callback_query):
    data = callback_query.data
    parts = data.split()
    if len(parts) > 1:
        acc_data = parts[1].split("-")
        if len(acc_data) >= 2:
            user_id_acc = acc_data[0]
            count = int(acc_data[1])

            await callback_query.edit_message_text(
                await Message.userbot_detail(count),
                reply_markup=ButtonUtils.userbot_list(
                    user_id_acc,
                    count,
                    session.get_count(),
                ),
            )


async def page_acc(_, callback_query):
    data = callback_query.data.split()
    count = int(data[1])
    return await callback_query.edit_message_text(
        await Message.userbot_list(count),
        reply_markup=ButtonUtils.account_list(count),
    )


async def acc_page(_, callback_query):
    data = callback_query.data
    parts = data.split()
    if len(parts) > 1:
        start_index = int(parts[1])
        await callback_query.edit_message_text(
            await Message.userbot_list(start_index),
            reply_markup=ButtonUtils.account_list(start_index),
        )


async def prevnext_userbot(_, callback_query):
    await callback_query.answer()
    query = callback_query.data.split()
    count = int(query[1])
    if query[0] == "prev_ub":
        count -= 1
    else:
        count += 1
    try:
        count = max(0, min(count, session.get_count() - 1))
        user_id_acc = session.get_list()[count]
        await callback_query.edit_message_text(
            await Message.userbot_detail(count),
            reply_markup=ButtonUtils.userbot_list(
                user_id_acc, count, session.get_count()
            ),
        )
    except Exception as e:
        return f"Error: {e}"


async def tools_userbot(_, callback_query):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    query = callback_query.data.split()
    if user_id not in SUDO_OWNERS:
        return await callback_query.answer(
            f"<b>GAUSAH REWEL YA ANJING! {callback_query.from_user.first_name} {callback_query.from_user.last_name or ''}",
            True,
        )
    query_data = int(query[1])
    logger.info(f"Query data: {query_data}")
    session_list = session.get_list()
    count = session_list[query_data]
    logger.info(f"Userbot count: {count}")
    X = session.get_session(count)
    if X:
        buttons = ButtonUtils.userbot_list(X.me.id, query_data, session.get_count())
        if query[0] == "get_otp":
            async for otp in X.search_messages(777000, limit=1):
                try:
                    if not otp.text:
                        await callback_query.answer("❌ Kode tidak ditemukan", True)
                    else:
                        await callback_query.edit_message_text(
                            otp.text, reply_markup=buttons
                        )
                        return await X.delete_messages(X.me.id, otp.id)
                except Exception as error:
                    return await callback_query.answer(error, True)
        elif query[0] == "get_phone":
            try:
                return await callback_query.edit_message_text(
                    f"<b>📲 Nomer telepon <code>{X.me.id}</code> adalah <code>{X.me.phone_number}</code></b>",
                    reply_markup=buttons,
                )
            except Exception as error:
                return await callback_query.answer(error, True)
        elif query[0] == "get_faktor":
            code = await dB.get_var(X.me.id, "PASSWORD")
            if code == None:
                return await callback_query.answer(
                    "🔐 Kode verifikasi 2 langkah tidak ditemukan", True
                )
            else:
                return await callback_query.edit_message_text(
                    f"<b>🔐 Kode verifikasi 2 langkah pengguna <code>{X.me.id}</code> adalah : <code>{code}</code></b>",
                    reply_markup=buttons,
                )
        elif query[0] == "ub_deak":
            if user_id not in KYNAN:
                return await callback_query.answer(
                    f"<b>GAUSAH REWEL YA ANJING! {callback_query.from_user.first_name} {callback_query.from_user.last_name or ''}",
                    True,
                )
            return await callback_query.edit_message_reply_markup(
                reply_markup=(ButtonUtils.deak(X.me.id, int(query[1])))
            )
        elif query[0] == "deak_akun":
            if user_id not in KYNAN:
                return await callback_query.answer(
                    f"<b>GAUSAH REWEL YA ANJING! {callback_query.from_user.first_name} {callback_query.from_user.last_name or ''}",
                    True,
                )
            session.remove_session(int(query[1]))
            await X.invoke(
                raw.functions.account.DeleteAccount(reason="madarchod hu me")
            )
            return await callback_query.edit_message_text(
                Message.deak(X), reply_markup=buttons
            )
    else:
        return await callback_query.answer("❌ Client tidak ditemukan", True)


async def contact_admins(_, message):
    reply_text = (
        "<b>English:</b> Please write the message you want to convey with the hashtag #ask and please wait for the admin to reply.\n\n"
        "<b>Indonesia:</b> Silahkan tulis pesan yang ingin anda sampaikan dengan hastag #ask dan mohon tunggu sampai admin membalas."
    )
    reply_markup = ikb([[("🔙 Back", "starthome")]])
    return await message.reply(reply_text, reply_markup=reply_markup)


async def closed_user(_, callback_query):

    try:
        split = callback_query.data.split(maxsplit=1)[1]
        data = state.get(split, split)
        if not data:
            return await callback_query.answer("This button not for you fvck!!", True)
        message = next(
            (obj for obj in get_objects() if id(obj) == int(data["idm"])), None
        )
        c = message._client
        if not callback_query.from_user:
            return await callback_query.answer("ANAK ANJING!!", True)
        sudo_users = await dB.get_list_from_var(c.me.id, "SUDOERS")
        if (
            callback_query.from_user.id not in sudo_users
            and callback_query.from_user.id != c.me.id
        ):
            return await callback_query.answer("GW BUNTUNGIN TANGAN LO YA MEMEK", True)
        return await c.delete_messages(int(data["chat"]), int(data["_id"]))
    except Exception:
        return


async def pm_warn(_, callback_query):
    data = callback_query.data.split()
    user_id = callback_query.from_user.id
    query = str(data[1])
    client = int(data[2])
    target = int(data[3])
    uniq = str(data[4])
    try:
        userbot = session.get_session(client)
        if query == "warns":
            Flood = state.get(client, target)
            pm_warns = await dB.get_var(client, "PMLIMIT") or LIMIT
            return await callback_query.answer(
                f"⚠️ You have a chance {Flood}/{pm_warns} ❗\n\nIf you insist on sending messages continuously then you will be ⛔ blocked automatically and we will 📢 report your account as spam",
                True,
            )
        elif query == "block":
            if user_id != client:
                return await callback_query.answer(
                    "This button not for you fvck!!", True
                )
            report_text = (
                "This user spreads fake news, misleads people, thereby inciting aggression "
                "and calling for war between nations. The account contains violent threats "
                "and promotes harmful content. Under platform guidelines, this account "
                "should be suspended. Please review and take appropriate action."
            )

            peer = await userbot.resolve_peer(target)
            await userbot.invoke(
                raw.functions.account.ReportPeer(
                    peer=peer,
                    reason=raw.types.InputReportReasonOther(),
                    message=report_text,
                )
            )
            await userbot.invoke(
                raw.functions.messages.DeleteHistory(peer=peer, max_id=0, revoke=True)
            )
            if flood.get(str(target)):
                del flood[str(target)]
            return await userbot.block_user(target)
        elif query == "approve":
            if user_id != client:
                return await callback_query.answer(
                    "This button not for you fvck!!", True
                )
            await dB.add_to_var(client, "PM_OKE", target)
            state.delete(client, target)
            try:
                if flood.get(str(target)):
                    del flood[str(target)]
                data_todelete = state.get(
                    f"pmpermit_inline {uniq} {target}",
                    f"pmpermit_inline {uniq} {target}",
                )
                chat_id = int(data_todelete.get("chat"))
                msgid = int(data_todelete.get("_id"))
                return await userbot.delete_messages(chat_id, msgid)
            except Exception:
                pass
        elif query == "disapprove":
            if user_id != client:
                return await callback_query.answer(
                    "This button not for you fvck!!", True
                )
            try:
                data_todelete = state.get(
                    f"pmpermit_inline {uniq} {target}",
                    f"pmpermit_inline {uniq} {target}",
                )
                chat_id = int(data_todelete.get("chat"))
                msgid = int(data_todelete.get("_id"))
                return await userbot.delete_messages(chat_id, msgid)
            except Exception:
                pass
    except Exception:
        logger.error(f"ERROR: {traceback.format_exc()}")


async def get_bio(_, callback_query):
    getid = int(callback_query.data.split("_")[1])
    data = state.get(getid, "bio")
    if not data:
        return await callback_query.answer("Bio not found", True)
    return await callback_query.answer(data, True)


async def cb_notes(_, callback_query):
    data = callback_query.data.split("_")
    btn_close = state.get("close_notes", "get_note")
    dia = callback_query.from_user
    type_mapping = {
        "photo": InputMediaPhoto,
        "video": InputMediaVideo,
        "animation": InputMediaAnimation,
        "audio": InputMediaAudio,
        "document": InputMediaDocument,
    }
    try:
        notetag = data[-2].replace("cb_", "")
        gw = data[-1]
        # userbot = session.get_session(gw)
        noteval = await dB.get_var(int(gw), notetag, "notes")
        if not noteval:
            await callback_query.answer("Catatan tidak ditemukan.", True)
            return
        full = (
            f"<a href=tg://user?id={dia.id}>{dia.first_name} {dia.last_name or ''}</a>"
        )
        await dB.add_userdata(
            dia.id,
            dia.first_name,
            dia.last_name,
            dia.username,
            dia.mention,
            full,
            dia.id,
        )
        tks = noteval["result"].get("text")
        note_type = noteval["type"]
        file_id = noteval.get("file_id")
        note, button = ButtonUtils.parse_msg_buttons(tks)
        teks = await Tools.escape_tag(bot, dia.id, note, Tools.parse_words)
        button = await ButtonUtils.create_inline_keyboard(button, int(gw))
        for row in btn_close.inline_keyboard:
            button.inline_keyboard.append(row)
        try:
            if note_type == "text":
                await callback_query.edit_message_text(text=teks, reply_markup=button)

            elif note_type in type_mapping and file_id:
                InputMediaType = type_mapping[note_type]
                media = InputMediaType(media=file_id, caption=teks)
                await callback_query.edit_message_media(
                    media=media, reply_markup=button
                )

            else:
                await callback_query.edit_message_caption(
                    caption=teks, reply_markup=button
                )

        except (FloodWait, FloodPremiumWait) as e:
            return await callback_query.answer(f"FloodWait {e}, Please Waiting!!", True)
        except MessageNotModified:
            pass

    except Exception:
        return await callback_query.answer(
            "Terjadi kesalahan saat memproses catatan.", True
        )


async def get_font(_, callback_query):
    if not callback_query.from_user:
        return await callback_query.answer("ANAK ANJING!!", True)
    if callback_query.from_user.id not in session.get_list():
        return await callback_query.answer("GW BUNTUNGIN TANGAN LO YA MEMEK", True)
    try:
        data = str(callback_query.data.split()[1])
        new = str(callback_query.data.split()[2])
        text = state.get(data, "FONT")
        get_new_font = gens_font(new, text)
        await callback_query.answer("Wait a minute!!", True)
        return await callback_query.edit_message_text(
            f"<b>Result:\n<code>{get_new_font}</code></b>"
        )
    except Exception as error:
        return await callback_query.answer(f"❌ Error: {error}", True)


async def prev_font(_, callback_query):
    if not callback_query.from_user:
        return await callback_query.answer("ANAK ANJING!!", True)
    if callback_query.from_user.id not in session.get_list():
        return await callback_query.answer("GW BUNTUNGIN TANGAN LO YA MEMEK", True)

    try:
        get_id = str(callback_query.data.split()[1])
        current_batch = int(callback_query.data.split()[2])
        prev_batch = current_batch - 1

        if prev_batch < 0:
            prev_batch = len(query_fonts) - 1

        keyboard = ButtonUtils.create_font_keyboard(
            query_fonts[prev_batch], get_id, prev_batch
        )

        buttons = InlineKeyboardMarkup(keyboard)
        return await callback_query.edit_message_reply_markup(reply_markup=buttons)
    except Exception as error:
        return await callback_query.answer(f"❌ Error: {error}", True)


async def next_font(_, callback_query):
    if not callback_query.from_user:
        return await callback_query.answer("ANAK ANJING!!", True)
    if callback_query.from_user.id not in session.get_list():
        return await callback_query.answer("GW BUNTUNGIN TANGAN LO YA MEMEK", True)
    try:
        get_id = str(callback_query.data.split()[1])
        current_batch = int(callback_query.data.split()[2])
        next_batch = current_batch + 1

        if next_batch >= len(query_fonts):
            next_batch = 0

        keyboard = ButtonUtils.create_font_keyboard(
            query_fonts[next_batch], get_id, next_batch
        )

        buttons = InlineKeyboardMarkup(keyboard)
        return await callback_query.edit_message_reply_markup(reply_markup=buttons)
    except Exception as error:
        return await callback_query.answer(f"❌ Error: {error}", True)


async def refresh_cat(_, callback_query):
    if not callback_query.from_user:
        return await callback_query.answer("ANAK ANJING!!", True)
    if callback_query.from_user.id not in session.get_list():
        return await callback_query.answer("GW BUNTUNGIN TANGAN LO YA MEMEK", True)
    uniq = str(callback_query.data.split("_")[2])
    await callback_query.answer("Please wait a minute", True)
    buttons = ikb(
        [
            [("Refresh cat", f"refresh_cat_{uniq}")],
            [("Close", f"close inline_cat {uniq}")],
        ]
    )
    r = requests.get("https://api.thecatapi.com/v1/images/search")
    if r.status_code == 200:
        data = r.json()
        cat_url = data[0]["url"]
        if cat_url.endswith(".gif"):
            await callback_query.edit_message_animation(
                cat_url,
                caption="<blockquote><b>Meow 😽</b></blockquote>",
                reply_markup=buttons,
            )
        else:
            await callback_query.edit_message_media(
                InputMediaPhoto(
                    media=cat_url, caption="<blockquote><b>Meow 😽</b></blockquote>"
                ),
                reply_markup=buttons,
            )
    else:
        await callback_query.edit_message_text("Failed to refresh cat picture 🙀")

async def rest_anime(_, callback_query):
    if not callback_query.from_user:
        return await callback_query.answer("ANAK ANJING!!", True)
    if callback_query.from_user.id not in session.get_list():
        return await callback_query.answer("GW BUNTUNGIN TANGAN LO YA MEMEK", True)
    data = callback_query.data.split("_")
    page = int(data[1])
    uniq = str(data[2])
    berita = state.get(uniq, "anime")
    berita = berita["anime"]
    if not berita:
        await callback_query.answer("Halaman tidak ditemukan.", show_alert=True)
        return
    total_photos = len(berita)
    if page < 0 or page >= total_photos:
        await callback_query.answer("Halaman tidak ditemukan.", show_alert=True)
        return
    buttons = []
    nav_buttons = []
    if page > 0:
        nav_buttons.append(Ikb("⬅️ Prev", callback_data=f"restanime_{page - 1}_{uniq}"))
    if page < total_photos - 1:
        nav_buttons.append(Ikb("➡️ Next", callback_data=f"restanime_{page + 1}_{uniq}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([Ikb("❌ Close", callback_data=f"close inline_anime {uniq}")])
    title = berita[page].get("title", "-")
    thumb = berita[page].get("thumbnail", "-")
    episode = berita[page].get("episode", "-")
    release = berita[page].get("release", "-")
    link = berita[page].get("link", "-")
    caption = f"""
**Title:** `{title}`
**Episode:** {episode}
**Release:** {release}
**Link:** <a href='{link}'>Here</a>
"""
    reply_markup = InlineKeyboardMarkup(buttons)
    return await callback_query.edit_message_media(
        media=InputMediaPhoto(media=thumb, caption=caption),
        reply_markup=reply_markup,
    )

async def news_(_, callback_query):
    if not callback_query.from_user:
        return await callback_query.answer("ANAK ANJING!!", True)
    if callback_query.from_user.id not in session.get_list():
        return await callback_query.answer("GW BUNTUNGIN TANGAN LO YA MEMEK", True)
    data = callback_query.data.split("_")
    page = int(data[1])
    uniq = str(data[2])
    berita = state.get(uniq, "news")
    if not berita:
        await callback_query.answer(
            "Tidak ada berita untuk ditampilkan.", show_alert=True
        )
        return
    total_photos = len(berita)
    if page < 0 or page >= total_photos:
        await callback_query.answer("Halaman tidak ditemukan.", show_alert=True)
        return
    buttons = []
    nav_buttons = []
    buttons.append([Ikb("📮 Link", url=f"{berita[page]['link']}")])
    if page > 0:
        nav_buttons.append(Ikb("⬅️ Prev", callback_data=f"news_{page - 1}_{uniq}"))
    if page < total_photos - 1:
        nav_buttons.append(Ikb("➡️ Next", callback_data=f"news_{page + 1}_{uniq}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([Ikb("❌ Close", callback_data=f"close inline_news {uniq}")])
    title = berita[page]["title"]
    date = berita[page].get("time", "-")
    thumb = berita[page]["image_thumbnail"]
    content = berita[page]["content"]
    clean_content = content[:500]
    judul = f"""
<blockquote expandable>
**Title:** {title}
**Uploaded:** {date}
**Content:** {clean_content}
</blockquote>
"""
    reply_markup = InlineKeyboardMarkup(buttons)
    return await callback_query.edit_message_media(
        media=InputMediaPhoto(media=thumb, caption=judul),
        reply_markup=reply_markup,
    )

async def cine_plax(_, callback_query):
    if not callback_query.from_user:
        return await callback_query.answer("ANAK ANJING!!", True)
    if callback_query.from_user.id not in session.get_list():
        return await callback_query.answer("GW BUNTUNGIN TANGAN LO YA MEMEK", True)
    data = callback_query.data.split("_")
    uniq = str(data[2])
    page = int(data[1])
    type_ = state.get(uniq, "cineplax")
    movies = state.get(uniq, "data_cineplax", [])
    if page * 5 >= len(movies):
        await callback_query.answer("Tidak ada halaman berikutnya.", show_alert=True)
        return

    buttons = []
    for movie in movies[page * 5 : (page + 1) * 5]:
        rating = movie.get("label", "-").split("/")[-1].replace(".png", "")
        if type_ == "soon":
            link = movie["link"].replace("https://21cineplex.com/comingsoon", "", 1)
        else:
            link = movie["link"].replace("https://21cineplex.com/", "", 1)
    if page > 0:
        buttons.append([Ikb("📮 Link", url=link)])
        buttons.append(
            [
                Ikb("⬅️ Prev", callback_data=f"cineplax_{page - 1}_{uniq}"),
                Ikb("➡️ Next", callback_data=f"cineplax_{page + 1}_{uniq}"),
            ]
        )
    buttons.append([Ikb("❌ Close", callback_data=f"close inline_cineplax {uniq}")])
    reply_markup = InlineKeyboardMarkup(buttons)

    caption = f"""
<blockquote>🎬 **Title: {movie['title']}**

**Rating:** {rating}</blockquote>
"""
    await callback_query.edit_message_media(
        media=InputMediaPhoto(
            media=movie["poster"],
            caption=caption,
        ),
        reply_markup=reply_markup,
    )


async def cek_expired_cb(_, cq):
    user_id = int(cq.data.split()[1])
    try:
        expired = await dB.get_expired_date(user_id)
        habis = expired.astimezone(timezone("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M")
        return await cq.answer(f"⏳ Waktu: {habis}", True)
    except Exception:
        return await cq.answer("✅ Sudah tidak aktif", True)


async def closed_bot(_, cq):
    await cq.answer()
    if await dB.get_var(cq.from_user.id, "is_bot"):
        await dB.remove_var(cq.from_user.id, "is_bot")
        await dB.remove_var(cq.from_user.id, "is_bot_pro")
    try:
        return await cq.message.delete()
    except Exception:
        return

async def viewchord(_, callback):
    if not callback.from_user:
        return await callback.answer("ANAK ANJING!!", True)
    if callback.from_user.id not in session.get_list():
        return await callback.answer("GW BUNTUNGIN TANGAN LO YA MEMEK", True)
    try:
        parts = callback.data.split("_", 2)
        if len(parts) != 3:
            return await callback.answer("❌ Callback tidak valid.", show_alert=True)

        _, index_str, uniq = parts
        index = int(index_str)

        data = state.get(uniq, "chord") or []
        if index < 0 or index >= len(data):
            return await callback.answer("❌ Data tidak ditemukan.", show_alert=True)

        song = data[index]
        text = f"""
<blockquote expandable>
<b>🎵 {song['title']}</b>
🎤 {song['artist']}
🔗 <a href=\"{song['link']}\">Open Chord</a>

<code>{song["detail"][:4000]}</code>
</blockquote>
"""

        nav_buttons = [
            ("🎵 {}".format(i + 1), f"viewchord_{i}_{uniq}") for i in range(len(data))
        ]
        nav_layout = [nav_buttons[i : i + 5] for i in range(0, len(nav_buttons), 5)]
        nav_layout.append([("❌ Close", f"close inline_chord {uniq}")])

        await callback.edit_message_text(
            text, reply_markup=ikb(nav_layout), disable_web_page_preview=True
        )
    except MessageNotModified:
        await callback.answer("❌ LU PEA", show_alert=True)
    except Exception:
        await callback.answer("⚠️ Terjadi kesalahan.", show_alert=True)
        print(traceback.format_exc())

async def moddycb(_, callback_query):
    if not callback_query.from_user:
        return await callback_query.answer("ANAK ANJING!!", True)
    if callback_query.from_user.id not in session.get_list():
        return await callback_query.answer("GW BUNTUNGIN TANGAN LO YA MEMEK", True)
    data = callback_query.data.split("_")
    page = int(data[1])
    uniq = str(data[2])
    result = state.get(uniq, uniq)
    if not result:
        await callback_query.answer(
            "Tidak ada halaman untuk ditampilkan.", show_alert=True
        )
        return
    total_result = len(result)
    if page < 0 or page >= total_result:
        await callback_query.answer("Halaman tidak ditemukan.", show_alert=True)
        return
    title = result[page].get("title")
    link = result[page].get("link")
    thumbnail = result[page].get("icon")
    genre = result[page].get("genre")
    rating = result[page]["rating"]
    msg = f"""
**Title:** {title}
**Rating:** {rating.get('value', '-')} | {rating.get('percentage', '-')}%
**Genre:** {genre}
"""
    buttons = []
    nav_buttons = []
    buttons.append([Ikb("📮 Link", url=link)])
    if page > 0:
        nav_buttons.append(Ikb("⬅️ Prev", callback_data=f"moddycb_{page - 1}_{uniq}"))
    if page < total_result - 1:
        nav_buttons.append(Ikb("➡️ Next", callback_data=f"moddycb_{page + 1}_{uniq}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([Ikb("❌ Close", callback_data=f"close inline_apkmoddy {uniq}")])
    reply_markup = InlineKeyboardMarkup(buttons)
    await callback_query.edit_message_media(
        media=InputMediaPhoto(media=thumbnail, caption=msg), reply_markup=reply_markup
    )


async def viewgempa(_, callback):
    if not callback.from_user:
        return await callback.answer("ANAK ANJING!!", True)
    if callback.from_user.id not in session.get_list():
        return await callback.answer("GW BUNTUNGIN TANGAN LO YA MEMEK", True)
    _, page, uniq = callback.data.split("_")
    page = int(page)

    data_result = state.get(uniq, uniq)
    if not data_result:
        return await callback.answer("Data tidak ditemukan!", show_alert=True)

    gempa_list = data_result.get("terkini", {}).get("Infogempa", {}).get("gempa", [])
    if not gempa_list:
        return await callback.answer("Data kosong!", show_alert=True)

    per_page = 5
    start = page * per_page
    end = start + per_page
    sliced = gempa_list[start:end]

    buttons = []
    for idx, item in enumerate(sliced):
        judul = f"{item['Tanggal']} {item['Magnitude']} M - {item['Wilayah'][:20]}"
        callback_data = f"nxtbmkg_{uniq}_{start + idx}"
        buttons.append([("⬇️ " + judul, callback_data)])

    total_pages = (len(gempa_list) + per_page - 1) // per_page
    nav_buttons = [(str(i + 1), f"viewgempa_{i}_{uniq}") for i in range(total_pages)]
    buttons.append(nav_buttons)

    await callback.edit_message_text(
        f"📊 Menampilkan daftar gempa ke {start + 1}–{min(end, len(gempa_list))} dari {len(gempa_list)} total.",
        reply_markup=ikb(buttons),
    )


async def nxtbmkg(_, callback):
    if not callback.from_user:
        return await callback.answer("ANAK ANJING!!", True)
    if callback.from_user.id not in session.get_list():
        return await callback.answer("GW BUNTUNGIN TANGAN LO YA MEMEK", True)
    _, uniq, idx = callback.data.split("_")
    idx = int(idx)

    data_result = state.get(uniq, uniq)
    if not data_result:
        return await callback.answer("Data tidak ditemukan!", show_alert=True)

    gempa_list = data_result.get("terkini", {}).get("Infogempa", {}).get("gempa", [])
    if idx >= len(gempa_list):
        return await callback.answer("Indeks gempa tidak valid!", show_alert=True)

    gempa = gempa_list[idx]

    msg = f"""
<blockquote expandable>
<b>📍 Lokasi:</b> <code>{gempa.get('Wilayah')}</code>
📅 <b>Tanggal:</b> <code>{gempa.get('Tanggal')}</code>
🕒 <b>Jam:</b> <code>{gempa.get('Jam')}</code>
💥 <b>Magnitudo:</b> <code>{gempa.get('Magnitude')}</code>
📏 <b>Kedalaman:</b> <code>{gempa.get('Kedalaman')}</code>
📌 <b>Koordinat:</b> <code>{gempa.get('Coordinates')}</code>
🌊 <b>Potensi:</b> <code>{gempa.get('Potensi')}</code>
😵 <b>Dirasakan:</b> <code>{gempa.get('Dirasakan')}</code>

<i>Sumber: BMKG</i>
</blockquote>
"""
    per_page = 5
    start = idx * per_page
    end = start + per_page
    sliced = gempa_list[start:end]

    buttons = []
    for idx, item in enumerate(sliced):
        judul = f"{item['Tanggal']} {item['Magnitude']} M - {item['Wilayah'][:20]}"
        callback_data = f"nxtbmkg_{uniq}_{start + idx}"
        buttons.append([("⬇️ " + judul, callback_data)])

    total_pages = (len(gempa_list) + per_page - 1) // per_page
    nav_buttons = [(str(i + 1), f"viewgempa_{i}_{uniq}") for i in range(total_pages)]
    buttons.append(nav_buttons)
    try:
        await callback.edit_message_text(msg, reply_markup=ikb(buttons))
    except MessageNotModified:
        await callback.answer("⛔ Sudah di halaman ini", show_alert=True)
    except Exception:
        await callback.answer("⚠️ Terjadi kesalahan.", show_alert=True)
        print(traceback.format_exc())


async def nxt_ytsearch(_, callback_query):
    if not callback_query.from_user:
        return await callback_query.answer(
            "ANAK ANJING!!",
            True,
        )

    if callback_query.from_user.id not in session.get_list():
        return await callback_query.answer(
            "GW BUNTUNGIN TANGAN LO YA MEMEK",
            True,
        )

    await callback_query.answer(
        "Please wait a minute",
        True,
    )

    data = callback_query.data.split("_")

    if len(data) < 3:
        return await callback_query.answer(
            "Invalid callback.",
            show_alert=True,
        )

    page = int(data[1])
    uniq = str(data[2])

    audios = state.get(
        uniq,
        "youtube_search",
    )

    if not audios:
        return await callback_query.answer(
            "Hasil pencarian sudah tidak tersedia.",
            show_alert=True,
        )

    per_page = 5

    total_pages = (
        len(audios) + per_page - 1
    ) // per_page

    if page < 0 or page >= total_pages:
        return await callback_query.answer(
            "Tidak ada halaman berikutnya.",
            show_alert=True,
        )

    sliced = audios[
        page * per_page : (page + 1) * per_page
    ]

    caption = (
        f"<blockquote expandable>"
        f"<b>🎧 Youtube Results "
        f"(Page {page + 1})</b>\n"
    )

    buttons = []

    for idx, audio in enumerate(sliced):
        real_index = (
            page * per_page + idx
        )

        title = audio.get(
            "title",
            "Unknown Title",
        )

        url = audio.get(
            "url",
            "",
        )

        caption += (
            f"\n<b>{idx + 1}. 💽 {title}</b>\n"
            f"🔗 <a href=\"{url}\">Youtube Link</a>\n"
        )

        buttons.append(
            [
                (
                    "⬇️ Download " + title[:20],
                    f"dlytsearch_{uniq}_{real_index}",
                )
            ]
        )

    caption += "</blockquote>"

    nav_buttons = [
        (
            str(i + 1),
            f"nxtytsearch_{i}_{uniq}",
        )
        for i in range(total_pages)
    ]

    buttons.append(nav_buttons)

    buttons.append(
        [
            (
                "❌ Close",
                f"close inline_youtube {uniq}",
            )
        ]
    )

    return await callback_query.edit_message_text(
        caption,
        reply_markup=ikb(buttons),
        disable_web_page_preview=True,
    )


async def dl_ytsearch(_, callback_query):
    if not callback_query.from_user:
        return await callback_query.answer(
            "ANAK ANJING!!",
            True,
        )

    if callback_query.from_user.id not in session.get_list():
        return await callback_query.answer(
            "GW BUNTUNGIN TANGAN LO YA MEMEK",
            True,
        )

    await callback_query.answer(
        "Please wait...",
        True,
    )

    try:
        data = callback_query.data.split("_")

        if len(data) < 3:
            return await callback_query.answer(
                "Invalid callback.",
                show_alert=True,
            )

        uniq = str(data[1])
        index = int(data[2])

        is_video = state.get(
            uniq,
            "as_video",
        )

        logger.info(
            f"Command type: {is_video}"
        )

        audios = state.get(
            uniq,
            "youtube_search",
        )

        if not audios:
            return await callback_query.answer(
                "Search result expired!",
                show_alert=True,
            )

        if index < 0 or index >= len(audios):
            return await callback_query.answer(
                "Track not found!",
                show_alert=True,
            )

        audio = audios[index]

        get_id = state.get(
            uniq,
            "idm_ytsearch",
        )

        if not get_id:
            return await callback_query.answer(
                "Original message not found!",
                show_alert=True,
            )

        objects = get_objects()

        message = next(
            (
                obj
                for obj in objects
                if id(obj) == get_id
            ),
            None,
        )

        if not message:
            return await callback_query.answer(
                "Message expired!",
                show_alert=True,
            )

        client = message._client

        em = Emoji(client)
        await em.get()

        now = time.time()

        proses = await message.reply(
            f"{em.proses}"
            f"**Get detail information...**"
        )

        link = audio["url"]

        logger.info(
            f"Found YouTube link: {link}"
        )

        (
            file_path,
            info,
            title,
            duration,
            views,
            channel,
            url,
            videoid,
            thumb,
            data_ytp,
        ) = await youtube.download(
            link,
            as_video=is_video,
        )

        logger.info(
            f"Downloaded path: {file_path}"
        )

        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        thumbnail = await download_thumbnail(
            thumb,
            f"downloads/thumb_{videoid}.jpg",
        )

        caption = data_ytp.format(
            info,
            title,
            Tools.seconds_to_min(
                int(duration)
            ),
            views,
            channel,
            url,
            client.me.mention,
        )

        try:
            ids = (
                unpack_inline_message_id(
                    callback_query.inline_message_id
                )
            ).id

            await client.delete_messages(
                message.chat.id,
                ids,
            )

        except Exception:
            pass

        if is_video:
            await client.send_video(
                message.chat.id,
                video=file_path,
                thumb=thumbnail,
                file_name=title,
                duration=duration,
                supports_streaming=True,
                caption=caption,
                progress=youtube.progress,
                progress_args=(
                    proses,
                    now,
                    f"{em.proses}"
                    f"<b>Trying to upload...</b>",
                    title,
                ),
                reply_to_message_id=message.id,
            )

        else:
            await client.send_audio(
                message.chat.id,
                audio=file_path,
                thumb=thumbnail,
                file_name=title,
                performer=channel,
                duration=duration,
                caption=caption,
                progress=youtube.progress,
                progress_args=(
                    proses,
                    now,
                    f"{em.proses}"
                    f"<b>Trying to upload...</b>",
                    title,
                ),
                reply_to_message_id=message.id,
            )

        try:
            if os.path.exists(file_path):
                os.remove(file_path)

            if thumbnail and os.path.exists(thumbnail):
                os.remove(thumbnail)

        except Exception:
            pass

        return await proses.delete()

    except Exception:
        logger.error(
            "Error download YouTube:\n"
            f"{traceback.format_exc()}"
        )


async def selected_topic(_, callback_query):
    if not callback_query.from_user:
        return await callback_query.answer("ANAK ANJING!!", True)
    if callback_query.from_user.id not in session.get_list():
        return await callback_query.answer("GW BUNTUNGIN TANGAN LO YA MEMEK", True)
    data = callback_query.data.split("_")
    chat_id = int(data[1])
    tread_id = int(data[2])
    title = str(data[3])
    await dB.set_var(chat_id, "SELECTED_TOPIC", tread_id)
    return await callback_query.answer(f"Changed send topic to {title}.", True)


async def callback_streamings(_, callback_query):
    query = callback_query.data.split()
    chat_id = int(query[1])
    user_id = int(query[2])
    get_id = int(query[3])
    command = str(query[4])
    group_calls = stream.get_active_call(chat_id, user_id)
    client = session.get_session(user_id)
    sudo_users = await dB.get_list_from_var(client.me.id, "SUDOERS")
    if (
        callback_query.from_user.id not in sudo_users
        and callback_query.from_user.id != client.me.id
    ):
        return await callback_query.answer("GW BUNTUNGIN TANGAN LO YA MEMEK", True)
    if not group_calls:
        return await callback_query.answer("No active stream found.", True)
    if command == "pause":
        await client.group_call.pause_stream(chat_id)
        return await callback_query.answer("Stream paused.", True)
    elif command == "resume":
        await client.group_call.resume_stream(chat_id)
        return await callback_query.answer("Stream resumed.", True)
    elif command == "stop":
        await client.group_call.leave_call(chat_id)
        stream.clear_queue(chat_id, client.me.id)
        stream.remove_active_call(chat_id, client.me.id)
        return await callback_query.answer("Stream stopped.", True)
    elif command == "skip":
        queue = stream.get_queue(chat_id, client.me.id)
        if not queue or len(queue) <= 1:
            return await callback_query.answer("No more stream in queue.", True)
        c, m = group_calls
        data_todelete = state.get(
            f"inline_streaming {chat_id} {get_id}",
            f"inline_streaming {chat_id} {get_id}",
        )
        chat_id = int(data_todelete.get("chat"))
        msgid = int(data_todelete.get("_id"))
        await client.delete_messages(chat_id, msgid)
        return await skip_songs(c, m, chat_id, True)

async def waifu_callback(_, callback_query):
    try:
        data = callback_query.data.split()

        if len(data) != 2:
            return await callback_query.answer(
                "❌ Callback tidak valid.",
                show_alert=True,
            )

        owner_id = int(data[1])

        if callback_query.from_user.id != owner_id:
            return await callback_query.answer(
                "❌ Tombol ini bukan untuk kamu.",
                show_alert=True,
            )

        await callback_query.answer("🔄 Mengambil waifu...")

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔄 Refresh",
                        callback_data=f"waifu {owner_id}",
                    ),
                    InlineKeyboardButton(
                        "❌ Close",
                        callback_data=f"waifu_close {owner_id}",
                    ),
                ]
            ]
        )

        await callback_query.message.edit_media(
            InputMediaPhoto(
                media="https://api.deline.web.id/random/loli"
            ),
            reply_markup=keyboard,
        )

    except Exception as error:
        return await callback_query.answer(
            f"❌ {error}",
            show_alert=True,
        )


async def waifu_close(_, callback_query):
    try:
        data = callback_query.data.split()

        if len(data) != 2:
            return await callback_query.answer(
                "❌ Callback tidak valid.",
                show_alert=True,
            )

        owner_id = int(data[1])

        if callback_query.from_user.id != owner_id:
            return await callback_query.answer(
                "❌ Tombol ini bukan untuk kamu.",
                show_alert=True,
            )

        await callback_query.answer("🗑️ Menghapus...")

        return await callback_query.message.delete()

    except Exception:
        return
