import re
from math import ceil
from typing import List, Optional, Tuple
from uuid import uuid4

from pyrogram import enums
from pyrogram.errors import QueryIdInvalid, RPCError
from pyrogram.helpers import ikb, kb
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from clients import session
from database import dB, state
from logs import logger


# =========================================================
# PAGINATION CONFIG
# =========================================================

COLUMN_SIZE = 4
NUM_COLUMNS = 2


# =========================================================
# EQUAL INLINE BUTTON
# =========================================================

class EqInlineKeyboardButton(InlineKeyboardButton):
    def __eq__(self, other):
        if not isinstance(other, InlineKeyboardButton):
            return NotImplemented

        return self.text == other.text

    def __lt__(self, other):
        if not isinstance(other, InlineKeyboardButton):
            return NotImplemented

        return self.text < other.text

    def __gt__(self, other):
        if not isinstance(other, InlineKeyboardButton):
            return NotImplemented

        return self.text > other.text


# =========================================================
# PAGINATE CATEGORIES
# =========================================================

def paginate_categories(
    page_n,
    module_dict,
    prefix,
    is_bot=False,
):
    """
    Menampilkan kategori plugin secara otomatis.

    Sumber kategori:
        __CATEGORY__

    Contoh plugin:

        __MODULES__ = "translate"
        __CATEGORY__ = "Ai"

    Layout:

        📂 Agama       📂 Ai
        📂 Hiburan     📂 Media
        📂 Obrolan     📂 Otomatisasi
        📂 Pembayaran  📂 Pencarian

    Maksimal:
        2 kolom x 4 baris = 8 kategori / halaman
    """

    categories = {}

    # -----------------------------------------------------
    # AMBIL KATEGORI DARI PLUGIN
    # -----------------------------------------------------

    for item in module_dict.values():

        module = item.get("module")

        if module is None:
            continue

        # Plugin harus mempunyai __MODULES__
        if not hasattr(module, "__MODULES__"):
            continue

        # Jika tidak punya kategori -> Other
        category = getattr(
            module,
            "__CATEGORY__",
            "Other",
        )

        # Pastikan string
        category = str(category).strip()

        if not category:
            category = "Other"

        categories.setdefault(
            category,
            0,
        )

        categories[category] += 1

    # -----------------------------------------------------
    # SORT CATEGORY
    # -----------------------------------------------------

    categories = sorted(
        categories.items(),
        key=lambda x: x[0].lower(),
    )

    # -----------------------------------------------------
    # BUAT BUTTON CATEGORY
    # -----------------------------------------------------

    category_buttons = []

    emoji_map = {
        "Admin": "👨‍💼",
        "Agama": "🕌",
        "Ai": "🤖",
        "Auto": "⚙️",
        "Download": "📥",
        "Fun": "😂",
        "Info": "ℹ️",
        "Media": "📸",
        "Stiker": "🔥",
        "System": "💻",
        "Tools": "🛠",
    }

    for category, count in categories:
        emoji = emoji_map.get(category, "📂")

        category_buttons.append(
            EqInlineKeyboardButton(
                f"{emoji} {category}",
                callback_data=(
                    f"{prefix}_category("
                    f"{category},"
                    f"{page_n}"
                    f")"
                ),
                style=enums.ButtonStyle.PRIMARY,
            )
        )
    # -----------------------------------------------------
    # 2 KOLOM
    # -----------------------------------------------------

    pairs = [
        category_buttons[i:i + NUM_COLUMNS]
        for i in range(
            0,
            len(category_buttons),
            NUM_COLUMNS,
        )
    ]

    # -----------------------------------------------------
    # TOTAL PAGE
    # -----------------------------------------------------

    max_num_pages = (
        ceil(len(pairs) / COLUMN_SIZE)
        if pairs
        else 1
    )

    # -----------------------------------------------------
    # NORMALISASI PAGE
    # -----------------------------------------------------

    page_n = max(
        0,
        min(
            page_n,
            max_num_pages - 1,
        ),
    )

    # -----------------------------------------------------
    # CATEGORY PADA PAGE SAAT INI
    # -----------------------------------------------------

    current_page = pairs[
        page_n * COLUMN_SIZE:
        (page_n + 1) * COLUMN_SIZE
    ]

    buttons = list(current_page)

    # -----------------------------------------------------
    # NAVIGATION
    # -----------------------------------------------------

    nav = []

    if page_n > 0:
        nav.append(
            EqInlineKeyboardButton(
                "⬅️",
                callback_data=(
                    f"{prefix}_categories_prev("
                    f"{page_n - 1}"
                    f")"
                ),
                style=enums.ButtonStyle.PRIMARY,
            )
        )

    if max_num_pages > 1:
        nav.append(
            EqInlineKeyboardButton(
                f"{page_n + 1}/{max_num_pages}",
                callback_data="help_noop",
                style=enums.ButtonStyle.PRIMARY,
            )
        )

    if page_n < max_num_pages - 1:
        nav.append(
            EqInlineKeyboardButton(
                "➡️",
                callback_data=(
                    f"{prefix}_categories_next("
                    f"{page_n + 1}"
                    f")"
                ),
                style=enums.ButtonStyle.PRIMARY,
            )
        )

    if nav:
        buttons.append(nav)

    # -----------------------------------------------------
    # CLOSE
    # -----------------------------------------------------

    buttons.append(
        [
            EqInlineKeyboardButton(
                "❌",
                callback_data=(
                    "buttonclose"
                    if is_bot
                    else "close help"
                ),
                style=enums.ButtonStyle.DANGER,
            )
        ]
    )

    return buttons


# =========================================================
# PAGINATE MODULES BY CATEGORY
# =========================================================

def paginate_modules(
    category,
    category_page,
    module_dict,
    prefix,
    module_page=0,
):
    """
    Menampilkan plugin berdasarkan kategori.

    Layout:

        Plugin 1       Plugin 2
        Plugin 3       Plugin 4
        Plugin 5       Plugin 6
        Plugin 7       Plugin 8

    Maksimal:
        2 kolom x 4 baris = 8 plugin / halaman
    """

    modules = []

    # -----------------------------------------------------
    # FILTER KATEGORI
    # -----------------------------------------------------

    for item in module_dict.values():

        module = item.get("module")

        if module is None:
            continue

        if not hasattr(module, "__MODULES__"):
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

        if plugin_category != category:
            continue

        modules.append(
            module.__MODULES__
        )

    # -----------------------------------------------------
    # SORT
    # -----------------------------------------------------

    modules = sorted(
        modules,
        key=lambda x: x.lower(),
    )

    # -----------------------------------------------------
    # PAGINATION
    # -----------------------------------------------------

    per_page = (
        NUM_COLUMNS *
        COLUMN_SIZE
    )

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

    current = modules[
        module_page * per_page:
        (module_page + 1) * per_page
    ]

    buttons = []

    # -----------------------------------------------------
    # PLUGIN BUTTON
    # -----------------------------------------------------

    for i in range(
        0,
        len(current),
        NUM_COLUMNS,
    ):

        row = []

        for name in current[
            i:i + NUM_COLUMNS
        ]:

            row.append(
                EqInlineKeyboardButton(
                    name,
                    callback_data=(
                        f"{prefix}_module("
                        f"{name.lower()},"
                        f"{category_page},"
                        f"{module_page}"
                        f")"
                    ),
                    style=enums.ButtonStyle.SUCCESS,
                )
            )

        buttons.append(row)

    # -----------------------------------------------------
    # NAVIGATION
    # -----------------------------------------------------

    nav = []

    if module_page > 0:

        nav.append(
            EqInlineKeyboardButton(
                "⬅️",
                callback_data=(
                    f"{prefix}_category("
                    f"{category},"
                    f"{category_page},"
                    f"{module_page - 1}"
                    f")"
                ),
                style=enums.ButtonStyle.PRIMARY,
            )
        )

    nav.append(
        EqInlineKeyboardButton(
            f"{module_page + 1}/{total_pages}",
            callback_data="help_noop",
            style=enums.ButtonStyle.PRIMARY,
        )
    )

    if module_page < total_pages - 1:

        nav.append(
            EqInlineKeyboardButton(
                "➡️",
                callback_data=(
                    f"{prefix}_category("
                    f"{category},"
                    f"{category_page},"
                    f"{module_page + 1}"
                    f")"
                ),
                style=enums.ButtonStyle.PRIMARY,
            )
        )

    buttons.append(nav)

    # -----------------------------------------------------
    # BACK CATEGORY
    # -----------------------------------------------------

    buttons.append(
        [
            EqInlineKeyboardButton(
                "🔙 Back Kategori",
                callback_data=(
                    f"{prefix}_back("
                    f"{category_page}"
                    f")"
                ),
                style=enums.ButtonStyle.DANGER,
            )
        ]
    )

    return buttons


# =========================================================
# BUTTON UTILS
# =========================================================

class ButtonUtils:
    """
    Keyboard utilities compatible with
    sepgram / styled Pyrogram.

    Custom emoji IDs are intentionally not used.
    """

    # -----------------------------------------------------
    # REGEX
    # -----------------------------------------------------

    URL_PATTERN = re.compile(
        r"(?:https?://)?(?:www\.)?"
        r"[a-zA-Z0-9.-]+"
        r"(?:\.[a-zA-Z]{2,})+"
        r"(?:[/?]\S+)?"
        r"|tg://\S+"
    )

    BUTTON_PATTERN = re.compile(
        r"\[(.*?)\|(.*?)\]"
    )

    FORMAT_TAGS = {
        "<b>": "**",
        "<i>": "__",
        "<strike>": "~~",
        "<spoiler>": "||",
        "<u>": "--",
    }

    # -----------------------------------------------------
    # BASIC PARSERS
    # -----------------------------------------------------

    @staticmethod
    def is_url(text: str) -> bool:
        return bool(
            ButtonUtils.URL_PATTERN.search(text)
        )

    @staticmethod
    def is_number(text: str) -> bool:
        return text.isdigit()

    @staticmethod
    def is_copy(text: str) -> bool:
        return bool(
            re.search(
                r"copy:",
                text,
            )
        )

    @staticmethod
    def is_alert(text: str) -> bool:
        return bool(
            re.search(
                r"alert:",
                text,
            )
        )

    @staticmethod
    def is_web(text: str) -> bool:
        return bool(
            re.search(
                r"web:",
                text,
            )
        )

    # -----------------------------------------------------
    # CATBOX
    # -----------------------------------------------------

    @staticmethod
    def cek_tg(text):

        tg_pattern = (
            r"https?:\/\/"
            r"files\.catbox\.moe\/\S+"
        )

        match = re.search(
            tg_pattern,
            text,
        )

        if match:

            tg_link = match.group(0)

            non_tg_text = (
                text
                .replace(
                    tg_link,
                    "",
                )
                .strip()
            )

            return (
                tg_link,
                non_tg_text,
            )

        return None, text

    # -----------------------------------------------------
    # MESSAGE BUTTON PARSER
    # -----------------------------------------------------

    @staticmethod
    def parse_msg_buttons(
        texts: str,
    ) -> Tuple[str, List[List]]:

        buttons = []

        for text, url in ButtonUtils.BUTTON_PATTERN.findall(
            texts
        ):

            urls = url.split("|")

            url = urls[0]

            if len(urls) > 1:

                if buttons:

                    buttons[-1].append(
                        [
                            text,
                            url,
                        ]
                    )

                else:

                    buttons.append(
                        [
                            [
                                text,
                                url,
                            ]
                        ]
                    )

            else:

                buttons.append(
                    [
                        [
                            text,
                            url,
                        ]
                    ]
                )

        clean_text = texts

        for match in re.findall(
            r"\[.+?\|.+?\]",
            texts,
        ):

            clean_text = (
                clean_text.replace(
                    match,
                    "",
                )
            )

        return (
            clean_text.strip(),
            buttons,
        )

    # -----------------------------------------------------
    # CREATE INLINE BUTTON
    # -----------------------------------------------------

    @staticmethod
    async def create_button(
        text: str,
        data: str,
        with_suffix: str = "",
    ) -> InlineKeyboardButton:

        data = data.strip()

        # URL
        if ButtonUtils.is_url(data):

            return InlineKeyboardButton(
                text=text,
                url=data,
            )

        # USER ID
        if ButtonUtils.is_number(data):

            return InlineKeyboardButton(
                text=text,
                user_id=int(data),
            )

        # COPY
        if ButtonUtils.is_copy(data):

            return InlineKeyboardButton(
                text=text,
                copy_text=data.replace(
                    "copy:",
                    "",
                    1,
                ),
            )

        # ALERT
        if ButtonUtils.is_alert(data):

            alert_text = data.replace(
                "alert:",
                "",
                1,
            )

            uniq = str(
                uuid4().int
            )[:8]

            await dB.set_var(
                int(uniq),
                int(uniq),
                alert_text,
            )

            return InlineKeyboardButton(
                text=text,
                callback_data=(
                    f"alertcb_{int(uniq)}"
                ),
            )

        # CALLBACK
        callback_data = (
            f"{data}_{with_suffix}"
            if with_suffix
            else data
        )

        return InlineKeyboardButton(
            text=text,
            callback_data=callback_data,
        )

    # -----------------------------------------------------
    # CREATE INLINE KEYBOARD
    # -----------------------------------------------------

    @staticmethod
    async def create_inline_keyboard(
        buttons: List[List],
        suffix: str = "",
    ) -> InlineKeyboardMarkup:

        keyboard = []

        for row in buttons:

            line = []

            for text, data in row:

                line.append(
                    await ButtonUtils.create_button(
                        text,
                        data,
                        suffix,
                    )
                )

            keyboard.append(line)

        return InlineKeyboardMarkup(
            inline_keyboard=keyboard
        )

    # -----------------------------------------------------
    # STYLED REPLY KEYBOARD
    # -----------------------------------------------------

    @staticmethod
    def styled_kb(
        rows=None,
        **kwargs,
    ) -> ReplyKeyboardMarkup:

        if rows is None:
            rows = []

        keyboard = []

        for row in rows:

            line = []

            for button in row:

                if isinstance(
                    button,
                    str,
                ):

                    button = KeyboardButton(
                        text=button
                    )

                elif isinstance(
                    button,
                    dict,
                ):

                    button = KeyboardButton(
                        **button
                    )

                line.append(button)

            keyboard.append(line)

        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            **kwargs,
        )

    # -----------------------------------------------------
    # START MENU
    # -----------------------------------------------------

    @staticmethod
    def start_menu(
        user_id: int,
    ):

        if not session.get_session(
            user_id
        ):

            common_buttons = [

                [
                    {
                        "text":
                            "✨ Mulai Buat Userbot",
                        "style":
                            enums.ButtonStyle.SUCCESS,
                    }
                ],

                [
                    {
                        "text":
                            "❓ Status Akun",
                        "style":
                            enums.ButtonStyle.PRIMARY,
                    }
                ],

                [
                    {
                        "text":
                            "⚡ Plan Lite",
                        "style":
                            enums.ButtonStyle.PRIMARY,
                    },
                    {
                        "text":
                            "🧩 Plan Basic",
                        "style":
                            enums.ButtonStyle.PRIMARY,
                    },
                    {
                        "text":
                            "💎 Plan Pro",
                        "style":
                            enums.ButtonStyle.PRIMARY,
                    },
                ],

                [
                    {
                        "text":
                            "💬 Hubungi Admins",
                        "style":
                            enums.ButtonStyle.PRIMARY,
                    }
                ],

                [
                    {
                        "text":
                            "🔑 Token",
                        "style":
                            enums.ButtonStyle.PRIMARY,
                    }
                ],
            ]

        else:

            common_buttons = [

                [
                    {
                        "text":
                            "❓ Status Akun",
                        "style":
                            enums.ButtonStyle.PRIMARY,
                    }
                ],

                [
                    {
                        "text":
                            "🔑 Token",
                        "style":
                            enums.ButtonStyle.PRIMARY,
                    }
                ],

                [
                    {
                        "text":
                            "🔄 Reset Emoji",
                        "style":
                            enums.ButtonStyle.DANGER,
                    },
                    {
                        "text":
                            "🔄 Reset Prefix",
                        "style":
                            enums.ButtonStyle.DANGER,
                    },
                ],

                [
                    {
                        "text":
                            "🔄 Restart Userbot",
                        "style":
                            enums.ButtonStyle.DANGER,
                    },
                    {
                        "text":
                            "🔄 Reset Text",
                        "style":
                            enums.ButtonStyle.DANGER,
                    },
                ],

                [
                    {
                        "text":
                            "💬 Hubungi Admins",
                        "style":
                            enums.ButtonStyle.PRIMARY,
                    }
                ],
            ]

        return ButtonUtils.styled_kb(
            common_buttons,
            resize_keyboard=True,
            one_time_keyboard=True,
        )

    # -----------------------------------------------------
    # USERBOT LIST
    # -----------------------------------------------------

    @staticmethod
    def userbot_list(
        user_id,
        count,
        total_count,
    ):

        buttons = []

        nav_buttons = []

        if count > 0:

            nav_buttons.append(
                InlineKeyboardButton(
                    "❮",
                    callback_data=(
                        f"prev_ub {count}"
                    ),
                    style=enums.ButtonStyle.PRIMARY,
                )
            )

        page_number = (
            count // 10
        ) * 10

        nav_buttons.append(
            InlineKeyboardButton(
                "Kembali",
                callback_data=(
                    f"bcpg_acc {page_number}"
                ),
                style=enums.ButtonStyle.DANGER,
            )
        )

        if count < total_count - 1:

            nav_buttons.append(
                InlineKeyboardButton(
                    "❯",
                    callback_data=(
                        f"next_ub {count}"
                    ),
                    style=enums.ButtonStyle.PRIMARY,
                )
            )

        buttons.append(nav_buttons)

        buttons.append(
            [
                InlineKeyboardButton(
                    "Get OTP",
                    callback_data=(
                        f"get_otp {count}"
                    ),
                    style=enums.ButtonStyle.PRIMARY,
                )
            ]
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    "Hapus User",
                    callback_data=(
                        f"del_ubot {user_id}"
                    ),
                    style=enums.ButtonStyle.DANGER,
                ),
                InlineKeyboardButton(
                    "Hapus Akun",
                    callback_data=(
                        f"ub_deak {count}"
                    ),
                    style=enums.ButtonStyle.DANGER,
                ),
            ]
        )

        return InlineKeyboardMarkup(
            inline_keyboard=buttons
        )

    # -----------------------------------------------------
    # ACCOUNT LIST
    # -----------------------------------------------------

    @staticmethod
    def account_list(
        start_index=0,
    ):

        user_list = session.get_list()

        total_users = len(
            user_list
        )

        buttons = []

        row = []

        end_index = min(
            start_index + 10,
            total_users,
        )

        for i in range(
            start_index,
            end_index,
        ):

            user_id = user_list[i]

            row.append(
                InlineKeyboardButton(
                    f"{i + 1}",
                    callback_data=(
                        f"tools_acc "
                        f"{user_id}-{i}"
                    ),
                )
            )

            if len(row) == 5:

                buttons.append(row)

                row = []

        if row:
            buttons.append(row)

        nav_buttons = []

        if start_index > 0:

            nav_buttons.append(
                InlineKeyboardButton(
                    "◀️ Prev page",
                    callback_data=(
                        f"acc_page "
                        f"{start_index - 10}"
                    ),
                    style=enums.ButtonStyle.PRIMARY,
                )
            )

        if end_index < total_users:

            nav_buttons.append(
                InlineKeyboardButton(
                    "Next page ▶️",
                    callback_data=(
                        f"acc_page "
                        f"{end_index}"
                    ),
                    style=enums.ButtonStyle.PRIMARY,
                )
            )

        if nav_buttons:
            buttons.append(
                nav_buttons
            )

        buttons.append(
            [
                InlineKeyboardButton(
                    "Tutup",
                    callback_data="buttonclose",
                    style=enums.ButtonStyle.DANGER,
                )
            ]
        )

        return InlineKeyboardMarkup(
            inline_keyboard=buttons
        )

    # -----------------------------------------------------
    # DEACTIVATE
    # -----------------------------------------------------

    @staticmethod
    def deak(
        user_id,
        count,
    ):

        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        "⬅️",
                        callback_data=(
                            f"prev_ub "
                            f"{int(count)}"
                        ),
                    ),
                    InlineKeyboardButton(
                        "Approve",
                        callback_data=(
                            f"deak_akun "
                            f"{int(count)}"
                        ),
                        style=enums.ButtonStyle.DANGER,
                    ),
                ]
            ]
        )

    # -----------------------------------------------------
    # INLINE QUERY
    # -----------------------------------------------------

    @staticmethod
    async def generate_inline_query(
        message,
        chat_id,
        bot_username,
        query,
    ):

        try:

            client = message._client

            results = (
                await client
                .get_inline_bot_results(
                    bot_username,
                    query,
                )
            )

            if (
                results
                and results.results
            ):

                return {
                    "query_id":
                        results.query_id,

                    "result_id":
                        results.results[0].id,

                    "results":
                        results.results,

                    "query":
                        query,
                }

            return None

        except Exception:

            return None

    @staticmethod
    async def send_inline_bot_result(
        message,
        chat_id,
        bot_username,
        query,
        reply_to_message_id: Optional[int] = None,
    ) -> bool:

        client = message._client

        try:

            query_results = (
                await ButtonUtils
                .generate_inline_query(
                    message,
                    chat_id,
                    bot_username,
                    query,
                )
            )

            if not query_results:
                return False

            data = (
                await client
                .send_inline_bot_result(
                    chat_id,
                    query_results[
                        "query_id"
                    ],
                    query_results[
                        "result_id"
                    ],
                    reply_to_message_id=(
                        reply_to_message_id
                    ),
                    message_thread_id=(
                        message.message_thread_id
                        or None
                    ),
                )
            )

            inline_id = {
                "chat": chat_id,
                "_id": data.updates[0].id,
                "me": client.me.id,
                "idm": id(message),
            }

            state.set(
                query,
                query,
                inline_id,
            )

            logger.info(
                f"Inline query '{query}'"
            )

            return True

        except QueryIdInvalid:
            raise

        except RPCError:
            raise

        except Exception:
            raise

    # -----------------------------------------------------
    # BUILD BUTTONS
    # -----------------------------------------------------

    @staticmethod
    def build_buttons(
        data,
        uniq,
        callback,
        closed,
    ):

        buttons = []

        row = []

        for idx, _ in enumerate(data):

            row.append(
                (
                    str(idx + 1),
                    f"{callback}{idx}_{uniq}",
                )
            )

            if len(row) == 5:

                buttons.append(row)

                row = []

        if row:
            buttons.append(row)

        buttons.append(
            [
                (
                    "❌ Close",
                    f"close {closed} {uniq}",
                )
            ]
        )

        return ikb(buttons)

    # -----------------------------------------------------
    # PLUS MINUS
    # -----------------------------------------------------

    @staticmethod
    def plus_minus(
        bulan,
        harga,
        plan,
    ):

        return InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        "⁻1 bulan",
                        callback_data=(
                            f"kurang "
                            f"{bulan} "
                            f"{harga} "
                            f"{plan}"
                        ),
                    ),

                    InlineKeyboardButton(
                        "⁺1 bulan",
                        callback_data=(
                            f"tambah "
                            f"{bulan} "
                            f"{harga} "
                            f"{plan}"
                        ),
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "Konfirmasi",
                        callback_data=(
                            f"confirm "
                            f"{bulan} "
                            f"{harga} "
                            f"{plan}"
                        ),
                        style=enums.ButtonStyle.SUCCESS,
                    )
                ],

                [
                    InlineKeyboardButton(
                        "Batal",
                        callback_data="buttonclose",
                        style=enums.ButtonStyle.DANGER,
                    )
                ],
            ]
        )

    # -----------------------------------------------------
    # CHOOSE PLAN
    # -----------------------------------------------------

    @staticmethod
    def chose_plan():

        return InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        "🧩 Plan Basic",
                        callback_data=(
                            "planusers basic"
                        ),
                        style=enums.ButtonStyle.PRIMARY,
                    ),

                    InlineKeyboardButton(
                        "💎 Plan Pro",
                        callback_data=(
                            "planusers is_pro"
                        ),
                        style=enums.ButtonStyle.PRIMARY,
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "⚡ Plan Lite",
                        callback_data=(
                            "planusers lite"
                        ),
                        style=enums.ButtonStyle.PRIMARY,
                    )
                ],

                [
                    InlineKeyboardButton(
                        "Batal",
                        callback_data="buttonclose",
                        style=enums.ButtonStyle.DANGER,
                    )
                ],
            ]
        )

    # -----------------------------------------------------
    # FONT KEYBOARD
    # -----------------------------------------------------

    @staticmethod
    def create_font_keyboard(
        font_list,
        get_id,
        current_batch,
    ):

        keyboard = []

        for font_dict in font_list:

            for key, value in font_dict.items():

                keyboard.append(
                    InlineKeyboardButton(
                        key,
                        callback_data=(
                            f"get_font "
                            f"{get_id} "
                            f"{value}"
                        ),
                    )
                )

        rows = [
            keyboard[i:i + 2]
            for i in range(
                0,
                len(keyboard),
                2,
            )
        ]

        while len(rows) < 3:
            rows.append([])

        rows.append(
            [
                InlineKeyboardButton(
                    "⬅️",
                    callback_data=(
                        f"prev_font "
                        f"{get_id} "
                        f"{current_batch}"
                    ),
                    style=enums.ButtonStyle.PRIMARY,
                ),

                InlineKeyboardButton(
                    "❌",
                    callback_data=(
                        f"close "
                        f"inline_font "
                        f"{get_id}"
                    ),
                    style=enums.ButtonStyle.DANGER,
                ),

                InlineKeyboardButton(
                    "➡️",
                    callback_data=(
                        f"next_font "
                        f"{get_id} "
                        f"{current_batch}"
                    ),
                    style=enums.ButtonStyle.PRIMARY,
                ),
            ]
        )

        return rows
