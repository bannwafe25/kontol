import asyncio

from pyrogram import enums

from config import API_MAELYN
from database import dB
from helpers import Emoji, Tools, animate_proses, task


async def send_action_for_duration(
    message, emo, proses, task_id, chat_id, action, duration, interval=5
):
    client = message._client
    loop = asyncio.get_event_loop()
    end_time = loop.time() + duration

    try:
        while task.is_active(task_id) and loop.time() < end_time:
            try:
                await client.send_chat_action(chat_id=chat_id, action=action)
            except Exception as e:
                await proses.edit(
                    f"{emo.gagal}Terjadi kesalahan saat mengirim aksi: {e}"
                )
                break
            await asyncio.sleep(interval)
    finally:
        await client.send_chat_action(chat_id=chat_id, action=enums.ChatAction.CANCEL)
        task.end_task(task_id)
        return


async def ftype_cmd(client, message):
    emo = Emoji(client)
    await emo.get()
    await message.delete()

    turu = client.get_text(message)
    try:
        turu = int(turu)
        if turu <= 0 or turu > 86400:
            raise ValueError("Durasi tidak valid.")
    except ValueError:
        turu = 3600
    proses_ = await emo.get_costum_text()
    proses = await message.reply(f"{emo.proses}**{proses_[4]}**")
    chat_id = message.chat.id

    try:
        task_id = task.start_task()
    except Exception as e:
        return await proses.edit(f"{emo.gagal}**Failed started task:** {e}")

    prefix = client.get_prefix(client.me.id)
    await proses.edit(
        f"{emo.proses}<i>Task {message.command[0]} running #<code>{task_id}</code>. Type <code>{prefix[0]}cancel {task_id}</code> to stop {message.command[0]}!</i>"
    )
    return await send_action_for_duration(
        message, emo, proses, task_id, chat_id, enums.ChatAction.TYPING, turu
    )


async def fvoice_cmd(client, message):
    emo = Emoji(client)
    await emo.get()
    await message.delete()
    turu = client.get_text(message)

    try:
        turu = int(turu)
        if turu <= 0 or turu > 86400:
            raise ValueError("Durasi tidak valid.")
    except ValueError:
        turu = 3600
    proses_ = await emo.get_costum_text()
    proses = await message.reply(f"{emo.proses}**{proses_[4]}**")
    chat_id = message.chat.id

    try:
        task_id = task.start_task()
    except Exception as e:
        return await proses.edit(f"{emo.gagal}**Failed started task:** {e}")

    prefix = client.get_prefix(client.me.id)
    await proses.edit(
        f"{emo.proses}<i>Task {message.command[0]} running #<code>{task_id}</code>. Type <code>{prefix[0]}cancel {task_id}</code> to stop {message.command[0]}!</i>"
    )
    return await send_action_for_duration(
        message, emo, proses, task_id, chat_id, enums.ChatAction.RECORD_AUDIO, turu
    )


async def fvideo_cmd(client, message):
    emo = Emoji(client)
    await emo.get()
    await message.delete()
    turu = client.get_text(message)

    try:
        turu = int(turu)
        if turu <= 0 or turu > 86400:
            raise ValueError("Durasi tidak valid.")
    except ValueError:
        turu = 3600
    proses_ = await emo.get_costum_text()
    proses = await message.reply(f"{emo.proses}**{proses_[4]}**")
    chat_id = message.chat.id

    try:
        task_id = task.start_task()
    except Exception as e:
        return await proses.edit(f"{emo.gagal}**Failed started task:** {e}")

    prefix = client.get_prefix(client.me.id)
    await proses.edit(
        f"{emo.proses}<i>Task {message.command[0]} running #<code>{task_id}</code>. Type <code>{prefix[0]}cancel {task_id}</code> to stop {message.command[0]}!</i>"
    )
    return await send_action_for_duration(
        message, emo, proses, task_id, chat_id, enums.ChatAction.UPLOAD_VIDEO, turu
    )


async def fstik_cmd(client, message):
    emo = Emoji(client)
    await emo.get()
    await message.delete()
    turu = client.get_text(message)

    try:
        turu = int(turu)
        if turu <= 0 or turu > 86400:
            raise ValueError("Durasi tidak valid.")
    except ValueError:
        turu = 3600
    proses_ = await emo.get_costum_text()
    proses = await message.reply(f"{emo.proses}**{proses_[4]}**")
    chat_id = message.chat.id

    try:
        task_id = task.start_task()
    except Exception as e:
        return await proses.edit(f"{emo.gagal}**Failed started task:** {e}")

    prefix = client.get_prefix(client.me.id)
    await proses.edit(
        f"{emo.proses}<i>Task {message.command[0]} running #<code>{task_id}</code>. Type <code>{prefix[0]}cancel {task_id}</code> to stop {message.command[0]}!</i>"
    )
    return await send_action_for_duration(
        message, emo, proses, task_id, chat_id, enums.ChatAction.CHOOSE_STICKER, turu
    )


async def task_cmd(client, message):
    data = task.get_active_tasks()
    if not data:
        return await message.reply("**No task running!**")
    msg = "<b>List task:\n\n</b>"
    for num, X in enumerate(data, 1):
        msg += f"<b>{num}. <code>{X}</code></b>"
    return await message.reply(msg)
