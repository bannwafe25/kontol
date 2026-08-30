import asyncio
import importlib
import traceback
from datetime import datetime
from functools import wraps

from pyrogram import StopPropagation, errors, types
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from config import (AKSES_DEPLOY, API_HASH, API_ID, BOT_ID, BOT_NAME,
                    BOT_TOKEN, HELPABLE, IS_JASA_PRIVATE, LOG_BACKUP, OWNER_ID,
                    SUDO_OWNERS)
from database import dB
from logs import logger
from plugins import _PLUGINS

from .base import BaseClient


class Bot(BaseClient):
    def __init__(self, **kwargs):
        super().__init__(
            name="Bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            device_model=BOT_NAME,
            plugins={"root": "assistant"},
            **kwargs,
        )

    def on_message(self, filters=None, group=-1):
        def decorator(func):
            @wraps(func)
            async def wrapper(client, message):
                try:
                    if asyncio.iscoroutinefunction(func):
                        await func(client, message)
                    else:
                        func(client, message)
                except (errors.FloodWait, errors.FloodPremiumWait) as e:
                    logger.warning(f"FloodWait: Sleeping for {e.value} seconds.")
                    await asyncio.sleep(e.value)
                    await func(client, message)
                except (
                    errors.ChatWriteForbidden,
                    errors.ChatSendMediaForbidden,
                    errors.ChatSendPhotosForbidden,
                    errors.MessageNotModified,
                    errors.MessageIdInvalid,
                ):
                    pass
                except StopPropagation:
                    raise
                except Exception as e:
                    date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    user_id = message.from_user.id if message.from_user else "Unknown"
                    chat_id = message.chat.id if message.chat else "Unknown"
                    chat_username = (
                        f"@{message.chat.username}"
                        if message.chat.username
                        else "Private Group"
                    )
                    command = message.text
                    error_trace = traceback.format_exc()
                    error_message = (
                        f"<b>Error:</b> {type(e).__name__}\n"
                        f"<b>Date:</b> {date_time}\n"
                        f"<b>Chat ID:</b> {chat_id}\n"
                        f"<b>Chat Username:</b> {chat_username}\n"
                        f"<b>User ID:</b> {user_id}\n"
                        f"<b>Command/Text:</b>\n<pre language='python'><code>{command}</code></pre>\n\n"
                        f"<b>Traceback:</b>\n<pre language='python'><code>{error_trace}</code></pre>"
                    )
                    await bot.send_message(LOG_BACKUP, error_message)

            handler = MessageHandler(wrapper, filters)
            self.add_handler(handler, group)
            return func

        return decorator

    def on_callback_query(self, filters=None, group=-1):
        def decorator(function):
            self.add_handler(CallbackQueryHandler(function, filters), group)
            return function

        return decorator

    async def add_reseller(self):
        for user in SUDO_OWNERS:
            if user not in await dB.get_list_from_var(BOT_ID, "SELLER"):
                await dB.add_to_var(BOT_ID, "SELLER", user)
        if OWNER_ID not in await dB.get_list_from_var(BOT_ID, "SELLER"):
            await dB.add_to_var(BOT_ID, "SELLER", OWNER_ID)
        for user in await dB.get_list_from_var(BOT_ID, "SELLER"):
            if user not in AKSES_DEPLOY:
                AKSES_DEPLOY.append(user)
        for u in await dB.get_list_from_var(BOT_ID, "SELLER"):
            if not await dB.get_var(u, "plan"):
                await dB.set_var(u, "plan", "is_pro")

    async def start(self):
        await super().start()
        self.id = self.me.id
        self.fullname = f"{self.me.first_name} {self.me.last_name or ''}"
        self.username = self.me.username
        self.mention = self.me.mention
        user_cmd = [
            types.BotCommand("start", "Start the bot."),
            types.BotCommand("bug", "Report a bug."),
            types.BotCommand("request", "Feature request."),
            types.BotCommand("restart", "Restart your userbot."),
        ]
        await self.set_bot_commands(
            user_cmd, scope=types.BotCommandScopeAllPrivateChats()
        )
        if IS_JASA_PRIVATE:
            owner_cmd = [
                types.BotCommand("addprem", "Berikan akses deploy."),
                types.BotCommand("addseller", "Berikan akses seller."),
                types.BotCommand("unseller", "Hapus akses seller."),
                types.BotCommand("listseller", "Cek daftar seller."),
                types.BotCommand("cekubot", "Lihat pengguna bot."),
            ]
            await self.set_bot_commands(
                user_cmd + owner_cmd,
                scope=types.BotCommandScopeChat(chat_id=OWNER_ID),
            )
        for modul in _PLUGINS:
            imported_module = importlib.import_module(f"plugins.{modul}")
            is_pro_plugin = getattr(imported_module, "IS_PRO", False)
            is_basic_plugin = getattr(imported_module, "IS_BASIC", False)
            module_name = getattr(imported_module, "__MODULES__", "").lower()
            if module_name:
                HELPABLE[module_name] = {
                    "module": imported_module,
                    "is_pro": is_pro_plugin,
                    "is_basic": is_basic_plugin,
                }
        logger.info(f"🔥 {self.username} Bot Started 🔥")


bot = Bot()
