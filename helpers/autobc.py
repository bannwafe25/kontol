import asyncio
import random
import traceback
from datetime import datetime
from typing import Optional, Tuple 

from pyrogram.errors import FloodPremiumWait, FloodWait, UserBannedInChannel

from clients import bot, session 
from config import BLACKLIST_GCAST
from database import dB
from logs import logger

from .emoji_logs import Emoji


MAX_CONCURRENT_BROADCAST = 5

AUTOBC_STATUS = set() 


async def get_auto_gcast_messages(client):
    entries = await dB.get_var(client.me.id, "AUTO_GCAST") or []
    return [await client.get_messages("me", int(e["message_id"])) for e in entries]


async def safe_send_message(selected_msg, chat_id, watermark=None):
    thread_id = await dB.get_var(chat_id, "SELECTED_TOPIC") or None
    
    try:
        client = selected_msg._client
        
        if watermark:
            text = selected_msg.text
            caption = selected_msg.caption

            if text:
                await client.send_message(
                    chat_id, f"{text}\n\n{watermark}", message_thread_id=thread_id
                )
            elif caption:
                media_types = [
                    ("photo", selected_msg.photo),
                    ("video", selected_msg.video),
                    ("animation", selected_msg.animation),
                    ("audio", selected_msg.audio),
                    ("document", selected_msg.document),
                    ("sticker", selected_msg.sticker),
                ]

                file_id = None
                for media_type, media_obj in media_types:
                    if media_obj:
                        file_id = media_obj.file_id
                        break

                if file_id:
                    await client.send_cached_media(
                        chat_id,
                        file_id,
                        caption=f"{caption}\n\n{watermark}",
                        message_thread_id=thread_id,
                    )
            else:
                media_types = [
                    ("photo", selected_msg.photo),
                    ("video", selected_msg.video),
                    ("animation", selected_msg.animation),
                    ("audio", selected_msg.audio),
                    ("document", selected_msg.document),
                    ("sticker", selected_msg.sticker),
                ]

                file_id = None
                for media_type, media_obj in media_types:
                    if media_obj:
                        file_id = media_obj.file_id
                        break

                if file_id:
                    await client.send_cached_media(
                        chat_id, file_id, caption=watermark, message_thread_id=thread_id
                    )
        else:
            await selected_msg.copy(chat_id, message_thread_id=thread_id)

        await asyncio.sleep(0.1)
        return True

    except (FloodWait, FloodPremiumWait) as e:
        logger.warning(f"FloodWait {client.me.id} {e.value}s on chat {chat_id}") 
        await asyncio.sleep(e.value)
        return await safe_send_message(selected_msg, chat_id, watermark)
    except UserBannedInChannel:
        return "banned" 
    except Exception:
        return False


async def sending_message(client):
    client_id = client.me.id
    try:
        messages = await get_auto_gcast_messages(client)
    except OSError:
        logger.error(f"Koneksi {client_id} putus")
        if client_id in AUTOBC_STATUS:
            AUTOBC_STATUS.discard(client_id) 
        return
        
    if not messages:
        logger.warning(f"Tidak ada pesan AutoBC yang ditemukan untuk {client_id}")
        if client_id in AUTOBC_STATUS:
            AUTOBC_STATUS.discard(client_id) 
        return

    while client_id in AUTOBC_STATUS:
        try:
            em = Emoji(client)
            await em.get()
            
            plan = await dB.get_var(client_id, "plan")
            watermark = None
            if plan != "is_pro":
                watermark = f"<blockquote><b>{em.robot}AutoBC by @{bot.username}</b></blockquote>"
                
            sem = asyncio.Semaphore(MAX_CONCURRENT_BROADCAST)
            delay = await dB.get_var(client_id, "DELAY_GCAST") or 300
            done = await dB.get_var(client_id, "ROUNDS") or 0
            group, failed = 0, 0
            
            blacklist = set(
                await dB.get_list_from_var(client_id, "BLACKLIST_GCAST") or []
            ) | set(BLACKLIST_GCAST or [])

            selected_msg = random.choice(messages)
            
            peer = client._get_my_peer.get(client_id)
            chats = (
                peer.get("group", [])
                if peer and peer.get("group")
                else await client.get_chat_id("group")
            )

            async def send_msg(chat_id):
                nonlocal group, failed
                if chat_id in blacklist:
                    return
                async with sem:
                    result = await safe_send_message(selected_msg, chat_id, watermark)
                    
                if result is True:
                    group += 1
                elif result == "banned":
                    failed += 1
                    logger.warning(f"Akun {client_id} diblokir di chat {chat_id}. Menonaktifkan AutoBC.")
                    await client.send_message(
                        "me",
                        "**⚠️ Akun Anda diblokir di salah satu grup**\nAutoBC telah dinonaktifkan.",
                    )
                    await dB.remove_var(client_id, "AUTOBC")
                    if client_id in AUTOBC_STATUS:
                        AUTOBC_STATUS.discard(client_id) 
                else:
                    failed += 1

            logger.info(f"Running autobc for {client_id}. Target {len(chats)} chats.")
            await asyncio.gather(*(send_msg(chat_id) for chat_id in chats))
            
            done += 1
            await dB.set_var(client_id, "ROUNDS", done)
            await dB.set_var(client_id, "SUCCES_GROUP", group)
            await dB.set_var(client_id, "LAST_TIME", datetime.utcnow().timestamp())
            
            summary = (
                f"<b><i>{em.warn}Autobc Done\n"
                f"{em.sukses}Berhasil : {group} Chat\n"
                f"{em.gagal}Gagal : {failed} Chat\n"
                f"{em.msg}Putaran Ke {done} Delay {delay} detik</i></b>"
            )
            
            try:
                await client.send_message("me", summary)
            except Exception:
                logger.error(f"Gagal mengirim ringkasan ke 'me' untuk {client_id}. Menonaktifkan AutoBC.")
                await dB.remove_var(client_id, "AUTOBC")
                if client_id in AUTOBC_STATUS:
                    AUTOBC_STATUS.discard(client_id) 
                    
            await asyncio.sleep(int(delay)) 
            
        except Exception:
            logger.error(traceback.format_exc())
            
            if client_id in AUTOBC_STATUS:
                AUTOBC_STATUS.discard(client_id) 


async def AutoBC():
    logger.info("✅ AutoBC tasks started")
    while True:
        for user_id in session.get_list():
            client = session.get_session(user_id)
            
            if client:
                client_id = client.me.id
                
                if (
                    await dB.get_var(client_id, "AUTOBC")
                    and client_id not in AUTOBC_STATUS
                ):
                    last_time = await dB.get_var(client_id, "LAST_TIME") or 0
                    delay = await dB.get_var(client_id, "DELAY_GCAST") or 300
                    now = datetime.utcnow().timestamp()
                    delay = int(delay)

                    elapsed = now - last_time
                    if elapsed >= delay:
                        logger.info(f"⏳ AutoBC {client_id} siap dijalankan. Elapsed: {int(elapsed)}s")
                        
                        AUTOBC_STATUS.add(client_id) 
                        asyncio.create_task(sending_message(client))
                    else:
                        #wait_time = delay - int(elapsed)
                        #logger.info(
                            #f"⏳ Menunggu {wait_time} detik sebelum AutoBC {client_id} mulai."
                        #)
                        pass
        await asyncio.sleep(30)
