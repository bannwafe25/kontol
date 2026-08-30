# ===============================================================
#  Copyright (c) 2025 FR RASTA @ownercpkoid
# 
#  File ini adalah bagian dari proyek [NAVY USERBOT].
#  Dilarang menyalin, memodifikasi, atau mendistribusikan kode ini
#  tanpa izin tertulis dari pemilik.
# 
#  Untuk informasi lisensi dan hak cipta, silakan lihat file LICENSE.
# ===============================================================


import asyncio
import traceback
import re
import os
import random
import httpx
import shutil
from datetime import datetime, timedelta
from gpytranslate import Translator

from pyrogram.errors import ImageProcessFailed
from config import API_BOTCAHX
from helpers import Emoji, Tools, animate_proses, horoscope, jodoh_data
from .gen_img_command import gen_studio



async def cekjodoh_cmd(client, message):
    em = Emoji(client)
    await em.get()

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        arg = message.text.split(maxsplit=1)
        if len(arg) > 1:
            username = arg[1].strip()
            try:
                target_user = await client.get_users(username)
            except Exception:
                return await message.reply(f"{em.gagal}**User not found.**")
        else:
            return await message.reply(f"{em.gagal}**Please reply or provide the target username/name.**")

    proses = await animate_proses(message, em.proses)
    folder = f"downloads/{client.me.id}/"
      
    try:
        data = random.choice(jodoh_data)
        ras = data["ras"]
        warnakulit = data["warnakulit"]
        warnarambut = data["warnarambut"]
        penjelasan = data["penjelasan"]

        prompt = f"Romantic digital illustration of a person from {ras} ethnicity, {warnakulit} skin, {warnarambut} hair, soft light, beautiful portrait"
        path_dir, files = await gen_studio(folder, prompt)

        mention = f"@{target_user.username}" if target_user.username else target_user.mention

        caption = f"""
<blockquote expandable>=========================
<b>💘 Matchmaking Prediction</b>
<b>👤 Name:</b> {mention}
=========================

<b>🧬 Ras:</b> {ras}
<b>🎨 Skin color:</b> {warnakulit}
<b>💇 Hair color:</b> {warnarambut}
=========================
📜 <b>Explanation:</b> <i>{penjelasan}</i>
=========================

🔮 <b>Paranormal:</b> {client.me.mention}
=========================</blockquote>
"""[:1024]

        await proses.delete()

        if files:
            await client.send_photo(
                message.chat.id,
                photo=files[0],
                caption=caption,
                reply_to_message_id=message.id
            )
        else:
            await message.reply(caption)

    except Exception as e:
        await proses.edit(f"{em.gagal}**There is an error:**\n`{e}`")
    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder)


ZODIAC_EMOJI = {
    "aries": "♈️", "taurus": "♉️", "gemini": "♊️", "cancer": "♋️", "leo": "♌️", "virgo": "♍️",
    "libra": "♎️", "scorpio": "♏️", "sagittarius": "♐️", "capricorn": "♑️", "aquarius": "♒️", "pisces": "♓️"
}
VALID_DAYS = {"yesterday", "today", "tomorrow"}


async def horoskop_cmd(client, message):
    em = Emoji(client)
    await em.get()

    arg = client.get_text(message)

    if not arg:
        return await message.reply(
            f"{em.gagal}**Enter your zodiac sign and day!**\n**Example:** `{message.text.split()[0]} taurus today`"
        )

    args = arg.strip().split()
    if len(args) != 2:
        return await message.reply(
            f"{em.gagal}**Invalid format!**\n**Use:** `zodiak hari`\n**Example:** `{message.text.split()[0]} leo tomorrow`"
        )

    zodiac, day = args
    zodiac = zodiac.lower()
    day = day.lower()

    if zodiac not in ZODIAC_EMOJI:
        return await message.reply(f"{em.gagal}**Zodiak invalid:** `{zodiac}`")
    if day not in VALID_DAYS:
        return await message.reply(f"{em.gagal}**Day invalid:** `{day}`")

    proses = await animate_proses(message, em.proses)
    folder = f"downloads/{client.me.id}/"

    try:
        raw_result = await horoscope.get_horoscope(zodiac, day)

        today = datetime.now()
        if day == "yesterday":
            date = today - timedelta(days=1)
        elif day == "tomorrow":
            date = today + timedelta(days=1)
        else:
            date = today

        formatted_date = date.strftime("%A, %d %B %Y")
        emoji = ZODIAC_EMOJI.get(zodiac, "✨")
        zodiac_title = zodiac.capitalize()

        split_raw = raw_result.split("🪄 _", 1)
        if len(split_raw) == 2:
            horoscope_data = split_raw[1].split("_", 1)[0].strip()
        else:
            horoscope_data = raw_result

        translator = Translator()
        translated = await translator.translate(horoscope_data, targetlang="id")

        prompt = f"A digital art representing the daily horoscope for {zodiac_title} on {formatted_date}. {horoscope_data}"
        path_dir, files = await gen_studio(folder, prompt)

        caption = f"""
<blockquote expandable>=========================
{emoji} <b>Horoscope {zodiac_title}</b>
📅 <code>{formatted_date}</code>
=========================

🌐 <i>{translated.text}</i>
=========================

🔮 <b>Paranormal:</b> {client.me.mention}
=========================</blockquote>
"""[:2000]

        await proses.delete()

        if files:
            await client.send_photo(
                message.chat.id,
                photo=files[0],
                caption=caption,
                reply_to_message_id=message.id
            )
        else:
            await message.reply(caption)

    except Exception as e:
        await proses.edit(f"{em.gagal}**There is an error:**\n`{e}`")
    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder)


MAX_CAPTION_LENGTH = 4000

async def zodiak_cmd(client, message):
    em = Emoji(client)
    await em.get()
    proses = await animate_proses(message, em.proses)

    ZODIAK_LIST = [
        "aries", "taurus", "gemini", "cancer", "leo", "virgo",
        "libra", "scorpio", "sagitarius", "capricorn", "aquarius", "pisces",
    ]

    if len(message.command) < 2:
        return await proses.edit(
            f"{em.gagal}**Please give zodiak name\n\n<code>{', '.join([z.capitalize() for z in ZODIAK_LIST])}</code>**"
        )

    try:
        query = message.text.split(None, 1)[1].strip().lower()
    except IndexError:
        return await proses.edit(
            f"{em.gagal} <b>Please give zodiak name!\n\nExample:</b> <code>{message.text.split()[0]} gemini</code>"
        )

    if query not in ZODIAK_LIST:
        return await proses.edit(
            f"{em.gagal} <b>Zodiak not found!</b>\n\n"
            f"<b>Daftar Zodiak:</b>\n"
            f"<code>{', '.join([z.capitalize() for z in ZODIAK_LIST])}</code>"
        )

    try:
        url = f"https://api.siputzx.my.id/api/primbon/zodiak?zodiak={query}"
        rp = await Tools.fetch.get(url)
        if rp.status_code != 200:
            return await proses.edit(f"{em.gagal} <b>Gagal mengambil data dari API.</b>")

        data = rp.json()
        if not data.get("status"):
            return await proses.edit(
                f"{em.gagal} <b>Data tidak ditemukan untuk zodiak ini.</b>"
            )

        z = data["data"]


        deskripsi = (
            f"Ilustrasi artistik zodiak {z['zodiak']}, "
            f"bernuansa {z['warna_keberuntungan']}, "
            f"planet penguasa {z['planet_yang_mengitari']}, "
            f"elemen {z['elemen_keberuntungan']}, "
            f"simbolis, mistis, indah dan detail."
        )


        folder = f"downloads/{client.me.id}/"
        path_dir, files = await gen_studio(folder, deskripsi)


        teks = f"""
<b>♈ Zodiak:</b> {z['zodiak']}
<b>🔢 Nomor Keberuntungan:</b> {z['nomor_keberuntungan']}
<b>🌸 Aroma Keberuntungan:</b> {z['aroma_keberuntungan']}
<b>🪐 Planet Penguasa:</b> {z['planet_yang_mengitari']}
<b>🌼 Bunga Keberuntungan:</b> {z['bunga_keberuntungan']}
<b>🎨 Warna Keberuntungan:</b> {z['warna_keberuntungan']}
<b>💎 Batu Keberuntungan:</b> {z['batu_keberuntungan']}
<b>🌪️ Elemen:</b> {z['elemen_keberuntungan']}

<b>❤️ Pasangan Zodiak & Kepribadian:</b>
<blockquote>{z['pasangan_zodiak']}</blockquote>
""".strip()

        caption = f"<blockquote expandable>{teks}</blockquote>"
        if len(caption) > MAX_CAPTION_LENGTH:
            caption = caption[:MAX_CAPTION_LENGTH] + "..."

        await proses.delete()

        if files:
            await client.send_photo(
                message.chat.id,
                photo=files[0],
                caption=caption,
                reply_to_message_id=message.id,
            )
        else:
            await message.reply(caption)

    except Exception as e:
        await proses.edit(f"{em.gagal} {e}")
    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder)


async def gen_kdm(text):
    bahan = [
        {
            "role": "system",
            "content": (
                "Kamu adalah seorang paranormal Nusantara yang mampu melihat khodam seseorang. "
                "Khodam itu biasanya disebut sebagai pendamping gaib atau makhluk halus yang dipercaya ikut menjaga "
                "atau membantu seseorang. Dalam kepercayaan masyarakat Nusantara, khodam bisa berupa jin, malaikat, "
                "roh leluhur, atau energi gaib yang menempel pada benda (misalnya keris, batu akik, jimat). "
                "Tugasmu adalah mendeskripsikan khodam yang mungkin ada pada seseorang, termasuk wujud, sifat, asal-usul, "
                "dan energi yang dipancarkan. Anggap semua input adalah nama seseorang. "
                "Deskripsi boleh positif atau negatif karena ini hiburan. "
                "Jawaban maksimal 700 karakter alfabet, dalam bahasa Indonesia, plain text."
            ),
        },
        {
            "role": "assistant",
            "content": (
                "Kamu adalah seorang paranormal Nusantara yang mampu melihat khodam seseorang. "
                "Khodam itu biasanya disebut sebagai pendamping gaib atau makhluk halus yang dipercaya ikut menjaga "
                "atau membantu seseorang. Dalam kepercayaan masyarakat Nusantara, khodam bisa berupa jin, malaikat, "
                "roh leluhur, atau energi gaib yang menempel pada benda (misalnya keris, batu akik, jimat). "
                "Tugasmu adalah mendeskripsikan khodam yang mungkin ada pada seseorang, termasuk wujud, sifat, asal-usul, "
                "dan energi yang dipancarkan. Anggap semua input adalah nama seseorang. "
                "Deskripsi boleh positif atau negatif karena ini hiburan. "
                "Jawaban maksimal 700 karakter alfabet, dalam bahasa Indonesia, plain text."
            ),
        },
        {"role": "user", "content": text},
    ]
    url = "https://api.botcahx.eu.org/api/search/openai-custom"
    payload = {"message": bahan, "apikey": f"{API_BOTCAHX}"}
    res = await Tools.fetch.post(url, json=payload)
    if res.status_code == 200:
        data = res.json()
        return data["result"].replace("\n", "")
    else:
        return f"{res.text}"


async def khodam_cmd(client, message):
    em = Emoji(client)
    await em.get()
    nama = client.get_name(message)
    if not nama:
        return await message.reply(
            f"{em.gagal}**Give the name you want to check the Khodam.**"
        )
    
    pros = await animate_proses(message, em.proses)

    folder = f"downloads/{client.me.id}/"
    try:
        deskripsi_khodam = await gen_kdm(nama)
        path_dir, files = await gen_studio(folder, deskripsi_khodam)
        caption = f"""
<blockquote expandable>=========================       
<b>🕯️ Successfully Checked Khodam</b>
👤 <b>Name:</b> {nama}
=========================

📖 <b>Description:</b> <i>{deskripsi_khodam}</i>
=========================
🔮 <b>Paranormal:</b> {client.me.mention}
=========================</blockquote>
"""
        if len(caption) > MAX_CAPTION_LENGTH:
            caption = caption[:MAX_CAPTION_LENGTH] + "..."

        await asyncio.sleep(2)
        await pros.delete()

        if files:
            await client.send_photo(
                message.chat.id,
                photo=files[0],
                caption=caption,
                reply_to_message_id=message.id,
            )
        else:
            await message.reply(caption)

    except Exception:
        await pros.delete()
        return await message.reply(f"{em.gagal} {traceback.format_exc()}")

    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder)