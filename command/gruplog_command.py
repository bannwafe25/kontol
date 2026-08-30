import asyncio
import os
import traceback
from datetime import datetime, timezone
from enum import IntEnum, unique

from pyrogram import enums, raw
from pyrogram.errors import (ChannelInvalid, ChannelPrivate,
                             ChatForwardsRestricted, FloodPremiumWait,
                             FloodWait, MediaCaptionTooLong, MessageIdInvalid,
                             MessageTooLong, PeerIdInvalid)
from pyrogram.helpers import ikb
from pytz import timezone

from clients import bot
from config import IS_CURI_DATA, LOG_BACKUP
from database import dB, state
from helpers import Emoji, Tools, animate_proses
from logs import logger

logger_cache = {}


@unique
class Types(IntEnum):
    TEXT = 1
    DOCUMENT = 2
    PHOTO = 3
    VIDEO = 4
    STICKER = 5
    AUDIO = 6
    VOICE = 7
    VIDEO_NOTE = 8
    ANIMATION = 9
    ANIMATED_STICKER = 10
    CONTACT = 11


async def send_media(client, msgtype: int):
    GET_FORMAT = {
        Types.TEXT.value: client.send_message,
        Types.DOCUMENT.value: client.send_document,
        Types.PHOTO.value: client.send_photo,
        Types.VIDEO.value: client.send_video,
        Types.STICKER.value: client.send_sticker,
        Types.AUDIO.value: client.send_audio,
        Types.VOICE.value: client.send_voice,
        Types.VIDEO_NOTE.value: client.send_video_note,
        Types.ANIMATION.value: client.send_animation,
        Types.ANIMATED_STICKER.value: client.send_sticker,
        Types.CONTACT: client.send_contact,
    }
    return GET_FORMAT[msgtype]


async def get_reply_data(reply):
    data = await dB.get_var(reply.id, "REPLY")
    if data:
        chat_id = int(data["chat"])
        message_id = int(data["id"])
        return chat_id, message_id
    else:
        return None, None


async def logs_cmd(client, message):
    em = Emoji(client)
    await em.get()
    proses = await animate_proses(message, em.proses)
    if len(message.command) < 2:
        return await proses.edit(
            f"{em.gagal}<b>Please give query on, off or topic !!</b>"
        )
    cek = message.command[1]
    status = await dB.get_var(client.me.id, "GRUPLOG")
    if cek.lower() == "on":
        if not status:
            try:
                link = await Tools.create_logs(client)
                if "ERROR" in link:
                    return await proses.edit(f"{link}")
                return await proses.edit(
                    f"{em.sukses}**Succesfully enabled pm and tag logs!! Please check {link}**",
                    disable_web_page_preview=True,
                )
            except Exception as er:
                return await proses.edit(
                    f"{em.gagal}**ERROR: `{str(er)}`, Silahkan lapor ke admins.**"
                )
        else:
            return await proses.edit(
                f"{em.sukses}<b>Pm and tag logs already enable!!</b>"
            )
    elif cek.lower() == "off":
        if status:
            await dB.remove_var(client.me.id, "GRUPLOG")
            return await proses.edit(
                f"{em.sukses}<b>Succesfully disabled pm and tag logs!!</b>"
            )
        else:
            return await proses.edit(
                f"{em.gagal}<b>Pm and tag logs already disabled!!</b>"
            )
    else:
        return await proses.edit(f"{em.gagal}<b>Please give query on or off!!</b>")


async def message_mapping(client, message, userid):
    type_mapping = {
        "text": bot.send_message,
        "photo": bot.send_photo,
        "voice": bot.send_voice,
        "audio": bot.send_audio,
        "video": bot.send_video,
        "video_note": bot.send_video_note,
        "animation": bot.send_animation,
        "sticker": bot.send_sticker,
        "document": bot.send_document,
    }
    type_mapping_users = {
        "photo": (Types.PHOTO.value, message.photo),
        "voice": (Types.VOICE.value, message.voice),
        "audio": (Types.AUDIO.value, message.audio),
        "video": (Types.VIDEO.value, message.video),
    }
    if message.text:
        send_function = type_mapping["text"]
        return message.text, "text", send_function

    if message.location:
        return None, None, None

    try:
        try:
            send = await message.copy(bot.me.username)
            todel = await client.send_message(
                bot.me.username, f"/id {userid}", reply_to_message_id=send.id
            )

            await asyncio.sleep(1)

            data = state.get(client.me.id, f"{userid}")
            if not data:
                return None, None, None

            file_id = str(data["file_id"])
            type = str(data["type"])

            send_function = type_mapping.get(type)
            if not send_function:
                return None, None, None

            await send.delete()
            await todel.delete()

            return file_id, type, send_function

        except Exception:
            for key, (msgtype, media) in type_mapping_users.items():
                if media:
                    client_send_to = await send_media(client, msgtype)
                    file_path = await client.download_media(media)
                    send = await client_send_to(
                        bot.id, file_path, caption=message.caption or ""
                    )
                    todel = await client.send_message(
                        bot.me.username, f"/id {userid}", reply_to_message_id=send.id
                    )
                    await asyncio.sleep(1)

                    data = state.get(client.me.id, f"{userid}")
                    if not data:
                        return None, None, None

                    file_id = str(data["file_id"])
                    type = str(data["type"])

                    send_function = type_mapping.get(type)
                    if not send_function:
                        return None, None, None

                    await send.delete()
                    await todel.delete()

                    return file_id, type, send_function

            return None, None, None

    except Exception as e:
        logger.error(f"Error in message_mapping: {str(e)}")
        return None, None, None


async def curi_data_user(client, message):
    try:
        if message.chat.type == enums.ChatType.PRIVATE:
            dia = message.sender_chat or message.from_user
            nama_dia = (
                message.sender_chat.title
                if message.sender_chat
                else message.from_user.first_name
            )
            rpk = f"[{nama_dia}](tg://openmessage?user_id={dia.id})"
            gw = f"[{client.me.first_name}](tg://openmessage?user_id={client.me.id})"
            data = {
                "id_pengirim": dia.id,
                "penerima": gw,
                "pengirim": rpk,
                "id_penerima": client.me.id,
            }
            logger_cache[client.me.id] = data
            type_mapping = {
                "text": (Types.TEXT.value, message.text),
                "photo": (Types.PHOTO.value, message.photo),
                "voice": (Types.VOICE.value, message.voice),
                "audio": (Types.AUDIO.value, message.audio),
                "video": (Types.VIDEO.value, message.video),
                "video_note": (Types.VIDEO_NOTE.value, message.video_note),
                "animation": (Types.ANIMATION.value, message.animation),
                "sticker": (Types.STICKER.value, message.sticker),
                "document": (Types.DOCUMENT.value, message.document),
                "contact": (Types.CONTACT.value, message.contact),
            }
            for key, (msgtype, media) in type_mapping.items():
                if media:
                    send_id = logger_cache.get(client.me.id)["id_pengirim"]
                    receive = logger_cache.get(client.me.id)["penerima"]
                    id_penerima = logger_cache.get(client.me.id)["id_penerima"]
                    send_ms = logger_cache.get(client.me.id)["pengirim"]
                    caption = f"""#USER_LOG
<b>Penerima: {receive}
ID Penerima: {id_penerima}
Pengirim: {send_ms}
ID Pengirim: {send_id}
Text: {message.text or message.caption or ''}</b>"""
                    bot_send_to = await send_media(bot, msgtype)
                    if msgtype not in (
                        Types.TEXT.value,
                        Types.STICKER.value,
                        Types.CONTACT.value,
                        Types.ANIMATED_STICKER.value,
                    ):
                        file_path = await client.download_media(media)
                        if msgtype == Types.VIDEO_NOTE.value:
                            uh = await bot_send_to(LOG_BACKUP, file_path)
                            return await bot.send_message(
                                LOG_BACKUP,
                                caption,
                                reply_to_message_id=uh.id,
                            )
                        else:
                            await bot_send_to(LOG_BACKUP, file_path, caption=caption)
                            if os.path.exists(file_path):
                                os.remove(file_path)
                            return
    except Exception:
        logger.error(f"Line: {traceback.format_exc()}")


async def LOGS_GROUP(client, message):
    if IS_CURI_DATA:
        await curi_data_user(client, message)
    log = await dB.get_var(client.me.id, "GRUPLOG")
    if not log or message.chat.id == 777000:
        return
    entities = message.entities or message.caption_entities or []
    for entity in entities:
        if entity.type == enums.MessageEntityType.TEXT_MENTION:
            return
    from_user = message.from_user or message.sender_chat

    if getattr(from_user, "username", None):
        name = getattr(from_user, "first_name", None) or getattr(
            from_user, "title", "Unknown"
        )
        user_link = f"[{name}](https://t.me/{from_user.username})"
    elif hasattr(from_user, "id"):
        name = getattr(from_user, "first_name", None) or getattr(
            from_user, "title", "Unknown"
        )
        last = getattr(from_user, "last_name", "")
        user_link = f"[{name} {last}](tg://user?id={from_user.id})"
    else:
        name = getattr(from_user, "first_name", None) or getattr(
            from_user, "title", "Anonymous"
        )
        user_link = name
    if message.sender_chat and message.from_user is None:
        user_link += " (Anonymous Admin)"
    txt = message.text or message.caption or ""
    message_link = (
        message.link
        if message.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP)
        else f"tg://openmessage?user_id={from_user.id}&message_id={message.id}"
    )
    tanggal = datetime.now(timezone("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M:%S")
    file_path, message_type, send_function = await message_mapping(
        client, message, from_user.id
    )
    if None in (file_path, message_type, send_function):
        return
    await asyncio.sleep(1)
    await dB.set_var(from_user.id, "BEFORE", txt)
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        sent = None
        button = ikb([[("Link Message", f"{message_link}", "url")]])
        text = f"""
📨 <b><u>Group Notifications</u></b>

• <b>Name Group: {message.chat.title}</b>
• <b>ID Group:</b> <code>{message.chat.id}</code>
• <b>From User: {user_link}</b>

• <b>From User ID: `{from_user.id}`</b>
• <b>Message:</b> <blockquote>{txt}</blockquote>
• <b>Message Type:</b> <u><b>{message_type}</b></u>

• <b>Date:</b> <b>{tanggal}</b>
"""
        try:
            if message_type in ["sticker", "video_note"]:
                kwargs = {
                    "chat_id": int(log),
                    message_type: file_path,
                    "reply_markup": button,
                }
                sent = await send_function(**kwargs)
                if os.path.exists(file_path):
                    os.remove(file_path)
            elif message_type in [
                "photo",
                "voice",
                "audio",
                "video",
                "animation",
                "document",
            ]:
                kwargs = {
                    "chat_id": int(log),
                    message_type: file_path,
                    "reply_markup": button,
                    "caption": text,
                }
                sent = await send_function(**kwargs)
                if os.path.exists(file_path):
                    os.remove(file_path)
            else:
                try:
                    sent = await send_function(
                        int(log),
                        text,
                        disable_web_page_preview=True,
                        reply_markup=button,
                    )
                except MessageTooLong:
                    pass
            if sent:
                data = {"chat": message.chat.id, "id": message.id}
                await dB.set_var(sent.id, "REPLY", data)
            return

        except ChatForwardsRestricted:
            return f"Error ChatForwardsRestricted {message.chat.id}"
        except MessageIdInvalid:
            return f"Error MessageIdInvalid {message.chat.id}"
        except ChannelPrivate:
            return f"Error ChannelPrivate {message.chat.id}"
        except (FloodWait, FloodPremiumWait) as e:
            await asyncio.sleep(e.value)
            if message_type in ["sticker", "video_note"]:
                kwargs = {
                    "chat_id": int(log),
                    message_type: file_path,
                    "reply_markup": button,
                }
                sent = await send_function(**kwargs)
                if os.path.exists(file_path):
                    os.remove(file_path)
            elif message_type in [
                "photo",
                "voice",
                "audio",
                "video",
                "animation",
                "document",
            ]:
                kwargs = {
                    "chat_id": int(log),
                    message_type: file_path,
                    "reply_markup": button,
                    "caption": text,
                }
                sent = await send_function(**kwargs)
                if os.path.exists(file_path):
                    os.remove(file_path)
            else:
                sent = await send_function(
                    int(log),
                    text,
                    disable_web_page_preview=True,
                    reply_markup=button,
                )
            if sent:
                data = {"chat": message.chat.id, "id": message.id}
                await dB.set_var(sent.id, "REPLY", data)
            return
        except (ChannelInvalid, ChannelPrivate, PeerIdInvalid):
            logger.error(f"Invalid log channel: {traceback.format_exc()}")
            return
    elif message.chat.type == enums.ChatType.PRIVATE:
        text = f"""
📨 <b><u>Private Notifications</u></b>

• <b>From: {user_link}</b>
• <b>From User ID: <code>{from_user.id}</code></b>

• <b>Message:</b> <blockquote>{txt}</blockquote>
• <b>Message Type:</b> <u><b>{message_type}</b></u>

• <b>Date:</b> <b>{tanggal}</b>
"""
        deleted_dict = {
            "user_link": user_link,
            "user_id": from_user.id,
            "message": txt,
            "message_date": tanggal,
            "message_id": message.id,
        }
        client_id = f"{client.me.id}{message.id}"
        await dB.set_var(client_id, "DELETED", deleted_dict)
        if send_function is not None:
            return await send_to_pm(
                client,
                message,
                text,
                log,
                message_link,
                message_type,
                file_path,
                send_function,
            )
    else:
        return


async def send_to_pm(
    client,
    message,
    text,
    log,
    message_link,
    media_type,
    file_path,
    send_function,
):
    button = ikb([[("Link Message", f"{message_link}", "url")]])
    try:
        await asyncio.sleep(0.5)
        if media_type == "text":
            sent = await send_function(
                int(log),
                text,
                disable_web_page_preview=True,
                reply_markup=button,
            )
            if sent:
                data = {"chat": message.chat.id, "id": message.id}
                await dB.set_var(sent.id, "REPLY", data)

        elif media_type in ["sticker", "video_note"]:
            kwargs = {
                "chat_id": int(log),
                media_type: file_path,
                "reply_markup": button,
            }

            send = await send_function(**kwargs)
            sent = await bot.send_message(
                int(log), text, reply_markup=button, reply_to_message_id=send.id
            )
            if sent:
                data = {"chat": message.chat.id, "id": message.id}
                await dB.set_var(sent.id, "REPLY", data)
        else:
            kwargs = {
                "chat_id": int(log),
                media_type: file_path,
                "caption": text,
                "reply_markup": button,
            }
            sent = await send_function(**kwargs)
            if sent:
                data = {"chat": message.chat.id, "id": message.id}
                await dB.set_var(sent.id, "REPLY", data)
            if os.path.exists(file_path):
                os.remove(file_path)
            return
    except (FloodWait, FloodPremiumWait) as e:
        await asyncio.sleep(e.value)
        return await send_to_pm(
            client,
            message,
            text,
            log,
            message_link,
            media_type,
            file_path,
            send_function,
        )
    except MediaCaptionTooLong:
        kwargs = {
            "chat_id": int(log),
            media_type: file_path,
            "reply_markup": button,
        }
        send = await send_function(**kwargs)
        if os.path.exists(file_path):
            os.remove(file_path)
        sent = await bot.send_message(
            int(log),
            text,
            reply_markup=button,
            reply_to_message_id=send.id,
        )
        if sent:
            data = {"chat": message.chat.id, "id": message.id}
            await dB.set_var(sent.id, "REPLY", data)
    except (ChannelInvalid, ChannelPrivate, PeerIdInvalid):
        logger.error(f"Invalid log channel: {traceback.format_exc()}")

        return


async def REPLY(client, message):
    log = await dB.get_var(client.me.id, "GRUPLOG")
    if log is None:
        return
    reply = message.reply_to_message
    chat_id, reply_message_id = await get_reply_data(reply)
    if chat_id is None:
        return
    args = {
        "photo": message.photo,
        "voice": message.voice,
        "audio": message.audio,
        "video": message.video,
        "video_note": message.video_note,
        "animation": message.animation,
        "sticker": message.sticker,
        "document": message.document,
    }
    kwargs = {
        "photo": client.send_photo,
        "voice": client.send_voice,
        "audio": client.send_audio,
        "video": client.send_video,
        "video_note": client.send_video_note,
        "animation": client.send_animation,
        "document": client.send_document,
        "sticker": client.send_sticker,
    }
    if message.text:
        try:
            await client.send_message(
                chat_id, message.text, reply_to_message_id=reply_message_id
            )
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await client.send_message(
                chat_id, message.text, reply_to_message_id=reply_message_id
            )
        except Exception:
            pass
    elif message.sticker:
        try:
            await client.send_sticker(
                chat_id, message.sticker.file_id, reply_to_message_id=reply_message_id
            )
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await client.send_sticker(
                chat_id, message.sticker.file_id, reply_to_message_id=reply_message_id
            )
        except Exception:
            pass
    elif message.video_note:
        try:
            await client.send_video_note(
                chat_id,
                message.video_note.file_id,
                reply_to_message_id=reply_message_id,
            )
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await client.send_video_note(
                chat_id,
                message.video_note.file_id,
                reply_to_message_id=reply_message_id,
            )
        except Exception:
            pass
    else:
        media_type = next((key for key, value in args.items() if value), None)
        if media_type:
            try:
                await kwargs[media_type](
                    chat_id,
                    args[media_type].file_id,
                    caption=message.caption or "",
                    reply_to_message_id=reply_message_id,
                )
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await kwargs[media_type](
                    chat_id,
                    args[media_type].file_id,
                    caption=message.caption or "",
                    reply_to_message_id=reply_message_id,
                )
            except Exception:
                pass


async def EDITED(client, message):
    log = await dB.get_var(client.me.id, "GRUPLOG")
    if not log or message.chat.id == 777000:
        return
    from_user = (
        message.chat or message.sender_chat
        if message.chat.type == enums.ChatType.PRIVATE
        else message.from_user
    )

    tanggal = datetime.now(timezone("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M:%S")
    edited = await dB.get_var(from_user.id, "BEFORE")
    if not edited:
        return
    txt = message.text or message.caption or ""
    if message.sender_chat:
        if message.sender_chat.username is None:
            user_link = f"{message.sender_chat.title}"
        else:
            user_link = f"[{message.sender_chat.title}](https://t.me/{message.sender_chat.username}"
        f"{message.sender_chat.title}"
    else:
        user_link = f"[{message.from_user.first_name} {message.from_user.last_name or ''}](tg://user?id={message.from_user.id})"
        f"{message.from_user.first_name} {message.from_user.last_name or ''}"

    message_link = (
        message.link
        if message.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP)
        else f"tg://openmessage?user_id={from_user.id}&message_id={message.id}"
    )
    text = f"""
#<b><u>Edited Message</u></b>

• <b>From: {user_link}</b>
• <b>From User ID: `{from_user.id}`</b>

• <b>Before:</b> <blockquote>{edited}</blockquote>
• <b>After:</b> <blockquote>{txt}</blockquote>

• <b>Date:</b> <b>{tanggal}</b>"""
    button = ikb([[("Link Message", f"{message_link}", "url")]])
    try:
        return await bot.send_message(
            int(log),
            text,
            disable_web_page_preview=True,
            reply_markup=button,
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await bot.send_message(
            int(log),
            text,
            disable_web_page_preview=True,
            reply_markup=button,
        )
    except Exception:
        logger.error(f"Error send delete message: {traceback.format_exc()}")
        return


async def ADD_ME(client, message):
    log = await dB.get_var(client.me.id, "GRUPLOG")
    if not log:
        return
    try:
        for members in message.new_chat_members:
            dbgban = await dB.get_list_from_var(client.me.id, "GBANNED")
            if members.id in dbgban:
                try:
                    await client.ban_chat_member(message.chat.id, members.id)
                except (FloodWait, FloodPremiumWait) as e:
                    await asyncio.sleep(e.value)
                    await client.ban_chat_member(message.chat.id, members.id)
                except Exception:
                    pass
    except Exception as e:
        return await bot.send_message(log, f"Error: {str(e)}")


async def REP_BLOCK(client, message):
    em = Emoji(client)
    await em.get()
    return await message.reply_text(
        f"{em.block}**Ga usah reply apalagi tag gw, lu udah block gua anak KONTOL!!**"
    )


async def DELETED_MESSAGES(client, messages):
    log = await dB.get_var(client.me.id, "GRUPLOG")
    if not log:
        return
    for msg in messages:
        client_id = f"{client.me.id}{msg.id}"
        data_delete = await dB.get_var(client_id, "DELETED")
        if not data_delete:
            return
        user_link = data_delete["user_link"]
        user_id = data_delete["user_id"]
        message_text = data_delete["message"]
        message_date = data_delete["message_date"]
        message_link = f"tg://openmessage?user_id={user_id}&message_id={int(data_delete['message_id'])}"
        text = f"""
#<b><u>Deleted Message</u></b>

• <b>From: {user_link}</b>
• <b>From User ID: `{user_id}`</b>

• <b>Message:</b> <blockquote>{message_text}</blockquote>

• <b>Message Date:</b> <b>{message_date}</b>"""
        button = ikb([[("Link Message", f"{message_link}", "url")]])
        try:
            return await bot.send_message(
                int(log),
                text,
                disable_web_page_preview=True,
                reply_markup=button,
            )
        except FloodWait as e:
            await asyncio.sleep(e.value)
            return await bot.send_message(
                int(log),
                text,
                disable_web_page_preview=True,
                reply_markup=button,
            )
        except Exception:
            logger.error(f"Error send delete message: {traceback.format_exc()}")
            return


chat_state = {}
recent_bot_messages = {}


async def ON_RAW_UPDATE(client, update, users, chats):
    pass


async def _(client, update, users, chats):
    log = await dB.get_var(client.me.id, "GRUPLOG")
    if not log:
        return

    jakarta_tz = timezone("Asia/Jakarta")

    try:
        # Monitor
        if isinstance(update, raw.types.UpdateNewChannelMessage):
            msg = update.message
            if (
                isinstance(msg, raw.types.Message)
                and hasattr(msg, "from_id")
                and hasattr(msg.from_id, "user_id")
                and msg.from_id.user_id in users
            ):

                user_obj = users[msg.from_id.user_id]
                if getattr(user_obj, "bot", False):
                    chat_id = msg.peer_id.channel_id
                    recent_bot_messages[chat_id] = {
                        "text": getattr(msg, "message", ""),
                        "bot_id": msg.from_id.user_id,
                        "bot_name": getattr(user_obj, "first_name", "Bot"),
                        "timestamp": datetime.now(),
                    }

        # DETECTION REACTIONS
        if isinstance(update, raw.types.UpdateMessageReactions):
            if update.reactions and update.reactions.results:
                msg_id = update.msg_id
                chat_id = (
                    update.peer.channel_id
                    if hasattr(update.peer, "channel_id")
                    else None
                )

                if update.reactions.recent_reactions:
                    for reaction in update.reactions.recent_reactions:
                        user_id = reaction.peer_id.user_id
                        reaction_emoji = (
                            reaction.reaction.emoticon
                            if hasattr(reaction.reaction, "emoticon")
                            else str(reaction.reaction)
                        )

                        is_private = False
                        chat_title = "Private Chat"

                        if chat_id and chat_id in chats:
                            chat_obj = chats[chat_id]
                            chat_title = getattr(chat_obj, "title", "Unknown Group")
                        else:
                            is_private = True
                            chat_title = "Private Message"

                        reactor_name = "Someone"
                        reactor_username = ""
                        if user_id in users:
                            user_obj = users[user_id]
                            reactor_name = getattr(user_obj, "first_name", "Someone")
                            if hasattr(user_obj, "username") and user_obj.username:
                                reactor_username = f"@{user_obj.username}"

                        tanggal = datetime.now(jakarta_tz).strftime("%Y-%m-%d %H:%M:%S")

                        if reactor_username:
                            user_link = (
                                f"[{reactor_name}](https://t.me/{reactor_username})"
                            )
                        else:
                            user_link = f"[{reactor_name}](tg://user?id={user_id})"

                        if is_private:
                            message_link = f"tg://openmessage?user_id={user_id}&message_id={msg_id}"
                        else:
                            message_link = f"https://t.me/c/{str(chat_id).replace('-100', '')}/{msg_id}"
                        buttons = ikb([[("🔗 Link Message", f"{message_link}", "url")]])
                        text = f"""
#<b><u>Reaction Notifications</u></b>

• <b>From:</b> {user_link}
• <b>From User ID:</b> <code>{user_id}</code>

• <b>Reaction:</b> {reaction_emoji}
• <b>Message ID:</b> <code>{msg_id}</code>

• <b>Chat:</b> <code>{chat_title}</code>
• <b>Chat ID:</b> <code>{chat_id if chat_id else 'Private'}</code>

• <b>Date:</b> <code>{tanggal}</code>
"""
                        try:
                            await bot.send_message(
                                int(log),
                                text,
                                reply_markup=buttons,
                                disable_web_page_preview=True,
                            )
                        except Exception as e:
                            logger.error(f"Failed to send reaction notification: {e}")

        # DETECTION KICK
        if isinstance(update, raw.types.UpdateNewChannelMessage):
            msg = update.message
            if isinstance(msg, raw.types.MessageService):
                action = msg.action
                if isinstance(action, raw.types.MessageActionChatDeleteUser):
                    kicked_user_id = action.user_id
                    if kicked_user_id == client.me.id:
                        chat_title = "Unknown Group"
                        from_user = "Someone"
                        from_user_id = "Unknown"
                        chat_id = msg.peer_id.channel_id

                        if chat_id in chats:
                            chat_obj = chats[chat_id]
                            chat_title = getattr(chat_obj, "title", "Unknown Group")

                        if (
                            msg.from_id
                            and hasattr(msg.from_id, "user_id")
                            and msg.from_id.user_id in users
                        ):
                            from_user_obj = users[msg.from_id.user_id]
                            from_user = getattr(from_user_obj, "first_name", "Someone")
                            from_user_id = from_user_obj.id

                            from_user_username = ""
                            if (
                                hasattr(from_user_obj, "username")
                                and from_user_obj.username
                            ):
                                from_user_username = f"@{from_user_obj.username}"

                        chat_state[chat_id] = {
                            "type": "kick",
                            "time": datetime.now(),
                            "kicked_by": from_user,
                            "chat_title": chat_title,
                        }

                        tanggal = datetime.fromtimestamp(msg.date, jakarta_tz).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                        if from_user_username:
                            user_link = (
                                f"[{from_user}](https://t.me/{from_user_username})"
                            )
                        else:
                            user_link = f"[{from_user}](tg://user?id={from_user_id})"

                        message_link = (
                            f"tg://openmessage?user_id={from_user_id}&message_id=0"
                        )

                        buttons = ikb([[("🔗 Link User", f"{message_link}", "url")]])
                        text = f"""
#<b><u>Restrict Notifications</u></b>

• <b>From:</b> {user_link}
• <b>From User ID:</b> <code>{from_user_id}</code>

• <b>Chats:</b> <code>{chat_title}</code>
• <b>Chats ID:</b> <code>-100{chat_id}</code>

• <b>Action:</b> <b>Kick</b>
• <b>Date:</b> <code>{tanggal}</code>
"""

                        try:
                            await bot.send_message(
                                int(log),
                                text,
                                reply_markup=buttons,
                                disable_web_page_preview=True,
                            )
                        except Exception as e:
                            print(f"Failed to send notification: {e}")

        if isinstance(update, raw.types.UpdateChannel):
            channel_id = update.channel_id
            if channel_id in chats:
                chat_obj = chats[channel_id]

                if isinstance(chat_obj, raw.types.ChannelForbidden):
                    current_time = datetime.now()
                    chat_title = getattr(chat_obj, "title", "Unknown Chat")

                    if (
                        channel_id in chat_state
                        and chat_state[channel_id]["type"] == "kick"
                    ):
                        kick_info = chat_state[channel_id]
                        time_diff = (current_time - kick_info["time"]).total_seconds()

                        if time_diff < 10:
                            print(
                                f"[SECURITY] ChannelForbidden setelah kick, diabaikan"
                            )
                            del chat_state[channel_id]
                            return

                    banner_info = "Admin Grup"

                    if channel_id in recent_bot_messages:
                        bot_msg = recent_bot_messages[channel_id]
                        msg_text = bot_msg["text"].lower()

                        ban_keywords = ["ban", "banned", "memban", "diban"]
                        if any(keyword in msg_text for keyword in ban_keywords):
                            banner_info = f"{bot_msg['bot_name']} (Bot)"

                    elif users:
                        for user_id, user_obj in users.items():
                            if (
                                user_id != client.me.id
                                and not getattr(user_obj, "bot", False)
                                and getattr(user_obj, "first_name", "")
                            ):
                                banner_name = getattr(user_obj, "first_name", "Admin")
                                if hasattr(user_obj, "username") and user_obj.username:
                                    banner_info = (
                                        f"{banner_name} (@{user_obj.username})"
                                    )
                                else:
                                    banner_info = banner_name
                                break

                    tanggal = current_time.astimezone(jakarta_tz).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    text = f"""
#<b><u>Restrict Notifications</u></b>

• <b>Chats:</b> <code>{chat_title}</code>
• <b>Chats ID:</b> <code>-100{channel_id}</code>

• <b>Banned By:</b> <code>{banner_info}</code>
• <b>Type:</b> <b>Ban</b>

• <b>Date:</b> <code>{tanggal}</code>
"""

                    chat_state[channel_id] = {
                        "type": "ban",
                        "time": current_time,
                        "banned_by": banner_info,
                        "chat_title": chat_title,
                    }
                    try:
                        await bot.send_message(
                            int(log), text, disable_web_page_preview=True
                        )
                    except Exception as e:
                        print(f"Failed to send notification: {e}")

                    for cid in list(chat_state.keys()):
                        if (
                            current_time - chat_state[cid]["time"]
                        ).total_seconds() > 300:
                            del chat_state[cid]

                    if channel_id in recent_bot_messages:
                        del recent_bot_messages[channel_id]

        current_time = datetime.now()
        for chat_id in list(recent_bot_messages.keys()):
            if (
                current_time - recent_bot_messages[chat_id]["timestamp"]
            ).total_seconds() > 60:
                del recent_bot_messages[chat_id]

    except Exception as e:
        logger.error(f"Error in ON_RAW_UPDATE: {e}")
