from datetime import datetime

from database import dB
from helpers import AUTOFW_STATUS, Emoji, Tools, animate_proses


async def autofw_cmd(client, message):
    em = Emoji(client)
    await em.get()

    msg = await animate_proses(message, em.proses)
    type, value = client.extract_type_and_text(message)
    status_autofw = await dB.get_var(client.me.id, "AUTOFW_GCAST_TEXT")
    if type == "on":
        if not status_autofw:
            return await msg.edit(
                f"{em.gagal}**Please add link before setting it on!!**\n**Example:** `{message.text.split()[0]} add https://t.me/kynansupport/1884`"
            )
        if await dB.get_var(client.me.id, "AUTOFW"):
            return await msg.edit(f"{em.gagal}<b>Auto forward already turned on.</b>")
        else:
            await dB.set_var(client.me.id, "AUTOFW", True)
            return await msg.edit(f"{em.sukses}<b>Auto forward turned on.</b>")
    elif type == "off":
        if await dB.get_var(client.me.id, "AUTOFW"):
            try:
                AUTOFW_STATUS.remove(client.me.id)
            except Exception:
                pass
            await dB.remove_var(client.me.id, "AUTOFW")
            return await msg.edit(f"{em.gagal}<b>Auto forward has been stopped.</b>")
        else:
            return await msg.edit(f"{em.sukses}<b>Auto forward already off.</b>")
    elif type == "add":
        try:
            target, messageids = Tools.get_link(value)
        except TypeError:
            return await msg.edit(
                f"{em.gagal}**Please give me valid link.\nExample: `{message.text.split()[0]} add https://t.me/kynansupport/1884`**",
                disable_web_page_preview=True,
            )
        args = await client.get_messages(target, messageids)
        if args.empty == True:
            return await msg.edit(
                f"{em.gagal}**Please give me valid link.\nExample: `{message.text.split()[0]} add https://t.me/kynansupport/1884`**",
                disable_web_page_preview=True,
            )
        await dB.set_var(client.me.id, "AUTOFW_GCAST_TEXT", value)
        return await msg.edit(
            f"{em.sukses}<b>Saved {value} for AutoForward Gcast message.</b>",
            disable_web_page_preview=True,
        )
    elif type == "delay":
        await dB.set_var(client.me.id, "DELAY_AUTOFW", value)
        return await msg.edit(
            f"{em.sukses}<b>AutoForward Gcast delay set to: <code>{value}</code> Second.</b>"
        )
    elif type == "del":
        try:
            await dB.remove_var(client.me.id, "AUTOFW_GCAST_TEXT")
            return await msg.edit(
                f"{em.sukses}<b>Succesfully deleted link from database.</b>"
            )
        except Exception as error:
            return await msg.edit(str(error))

    elif type == "get":
        if not status_autofw:
            return await msg.edit(
                f"{em.gagal}<b>Your AutoForward Gcast link is empty, idiot.</b>"
            )
        return await msg.edit(
            f"{em.sukses}**This is your link autoforward gcast: {status_autofw}",
            disable_web_page_preview=True,
        )

    elif type == "status":
        status = await dB.get_var(client.me.id, "AUTOFW")
        delay = await dB.get_var(client.me.id, "DELAY_AUTOFW") or 300
        msgs = await dB.get_var(client.me.id, "AUTOFW_GCAST_TEXT")
        rounds = await dB.get_var(client.me.id, "ROUNDSFW") or 0
        last_broadcast = await dB.get_var(client.me.id, "LAST_TIME_FW") or 0
        status_text = f"{em.sukses}Actived" if status else f"{em.gagal}Deactivated"
        last_broadcast_time = (
            f"<code>{datetime.utcfromtimestamp(last_broadcast).strftime('%Y-%m-%d %H:%M:%S')} UTC</code>"
            if last_broadcast
            else "No auto forward yet"
        )
        total_groups = await dB.get_var(client.me.id, "SUCCESFW_GROUP") or 0
        await msg.edit(
            f"""
<blockquote expandable>**
__<emoji id=5258389041006518073>📑</emoji> Status Auto Forward:
<emoji id=5316727448644103237>👤</emoji> Status: {status_text}
<emoji id=5260535596941582167>🗓️</emoji> Jumlah Grup: {total_groups}
<emoji id=5258419835922030550>⌛</emoji> Delay: {delay}  detik 
<emoji id=5296385246579670377>📑</emoji> Pesan Di Simpan: {msgs} Pesan
<emoji id=5260687119092817530>🔃</emoji> Putaran: {rounds} Kali
<emoji id=5199457120428249992>⏰</emoji> Terakhir Broadcast: {last_broadcast_time}__**</blockquote>""",
            disable_web_page_preview=True,
        )
    else:
        return await msg.edit(
            f"{em.gagal}<b>Wrong, idiot!! At least read the  Command Help.</b>"
        )
    return
