import asyncio
from datetime import datetime
from typing import Optional, Tuple

from pyrogram.errors import FloodPremiumWait, FloodWait, UserBannedInChannel

from clients import session
from config import BLACKLIST_GCAST
from database import dB
from logs import logger

from .emoji_logs import Emoji
from .tools import Tools

MAX_CONCURRENT_BROADCAST = 5
AUTOFW_STATUS = []


class ForwardResult:
    """Class untuk menyimpan hasil forward message"""

    def __init__(
        self,
        success: bool,
        error_type: Optional[str] = None,
        error_msg: Optional[str] = None,
    ):
        self.success = success
        self.error_type = error_type
        self.error_msg = error_msg


async def safe_forward(client, chat_id, chatids, messageids) -> ForwardResult:
    """Forward message dengan error handling detail"""
    thread_id = await dB.get_var(chat_id, "SELECTED_TOPIC") or None

    try:
        await client.forward_messages(
            chat_id, chatids, message_ids=messageids, message_thread_id=thread_id
        )
        await asyncio.sleep(4)
        return ForwardResult(success=True)

    except (FloodWait, FloodPremiumWait) as e:
        logger.warning(f"FloodWait {client.me.id} {e.value}s on chat {chat_id}")
        await asyncio.sleep(e.value)
        try:
            return await safe_forward(client, chat_id, chatids, messageids)
        except Exception as retry_err:
            return ForwardResult(
                success=False,
                error_type="FloodWaitRetryFailed",
                error_msg=str(retry_err),
            )

    except UserBannedInChannel:
        return ForwardResult(
            success=False,
            error_type="UserBannedInChannel",
            error_msg=f"Banned in chat {chat_id}",
        )

    except Exception as e:
        error_name = type(e).__name__
        return ForwardResult(success=False, error_type=error_name, error_msg=str(e))


async def send_summary_with_retry(
    client, summary: str, max_retries: int = 3
) -> Tuple[bool, Optional[str]]:
    """Kirim summary dengan retry dan return status"""
    for attempt in range(max_retries):
        try:
            await client.send_message("me", summary)
            return True, None

        except FloodWait as e:
            logger.warning(
                f"FloodWait saat kirim summary, attempt {attempt + 1}/{max_retries}"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(e.value)
            else:
                return False, f"FloodWait: {e.value}s"

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(
                f"Gagal kirim summary attempt {attempt + 1}/{max_retries}: {error_msg}"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                return False, error_msg

    return False, "Max retries exceeded"


async def send_forward(client):
    """Main forward loop dengan error tracking detail"""
    while client.me.id in AUTOFW_STATUS:
        em = Emoji(client)
        await em.get()

        delay = await dB.get_var(client.me.id, "DELAY_AUTOFW") or 300
        link = await dB.get_var(client.me.id, "AUTOFW_GCAST_TEXT")

        if not link:
            logger.warning(f"No AUTOFW_GCAST_TEXT found for {client.me.id}")
            return

        logger.info(f"🔁 Running AutoFW for {client.me.id}")
        chatids, messageids = Tools.get_link(link)
        done = await dB.get_var(client.me.id, "ROUNDSFW") or 0
        group, failed = 0, 0

        # Track error details
        error_details = {}

        blacklist = set(
            await dB.get_list_from_var(client.me.id, "BLACKLIST_GCAST") or []
        ) | set(BLACKLIST_GCAST)

        chats = await client.get_chat_id("group")

        for chat_id in chats:
            if chat_id in blacklist:
                continue

            result = await safe_forward(client, chat_id, chatids, messageids)

            if result.success:
                group += 1
            else:
                failed += 1
                error_type = result.error_type or "Unknown"
                if error_type not in error_details:
                    error_details[error_type] = 0
                error_details[error_type] += 1

        done += 1
        await dB.set_var(client.me.id, "ROUNDSFW", done)
        await dB.set_var(client.me.id, "SUCCESFW_GROUP", group)
        await dB.set_var(client.me.id, "LAST_TIME_FW", datetime.utcnow().timestamp())

        summary = (
            f"<b><i>{em.warn}AUTOFW Done\n"
            f"{em.sukses}Berhasil : {group} Chat\n"
            f"{em.gagal}Gagal : {failed} Chat\n"
        )

        if error_details:
            summary += f"\n{em.block}<b>Detail Error:</b>\n"
            for error_type, count in error_details.items():
                summary += f"  • {error_type}: {count}x\n"

        summary += (
            f"\n{em.msg}Putaran Ke-{done}\n{em.uptime} Delay {delay} detik</i></b>"
        )

        # Kirim summary dengan error handling
        send_success, send_error = await send_summary_with_retry(client, summary)

        if not send_success:
            logger.error(
                f"❌ GAGAL kirim summary ke 'me' untuk {client.me.id}: {send_error}"
            )
            error_notif = (
                f"<b>{em.warn}AutoFW Error Report</b>\n\n"
                f"Putaran: {done}\n"
                f"Berhasil: {group} | Gagal: {failed}\n\n"
                f"<b>{em.gagal}Gagal mengirim summary:</b>\n{send_error}\n\n"
                f"AutoFW masih berjalan."
            )
            try:
                await client.send_message("me", error_notif)
            except Exception as e:
                logger.critical(
                    f"‼️ CRITICAL: Tidak bisa kirim pesan apapun ke 'me': {e}"
                )
                await dB.remove_var(client.me.id, "AUTOFW")
                if client.me.id in AUTOFW_STATUS:
                    AUTOFW_STATUS.remove(client.me.id)
                return

        await asyncio.sleep(int(delay))


async def AutoFW():
    logger.info("✅ AutoFW tasks started")
    while True:
        for user_id in session.get_list():
            client = session.get_session(user_id)
            if client:
                if (
                    await dB.get_var(client.me.id, "AUTOFW")
                    and client.me.id not in AUTOFW_STATUS
                ):
                    AUTOFW_STATUS.append(client.me.id)
                    asyncio.create_task(send_forward(client))
        await asyncio.sleep(30)
