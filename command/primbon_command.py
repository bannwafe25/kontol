# ===============================================================
#  Copyright (c) 2025 FR RASTA @root404byte
# 
#  File ini adalah bagian dari proyek [NAVY USERBOT].
#  Dilarang menyalin, memodifikasi, atau mendistribusikan kode ini
#  tanpa izin tertulis dari pemilik.
# 
#  Untuk informasi lisensi dan hak cipta, silakan lihat file LICENSE.
# ===============================================================


import asyncio
import os
import re
import shutil

from urllib.parse import quote
from pyrogram.errors import ImageProcessFailed

from helpers import Tools, Emoji, animate_proses
from config import API_BOTCAHX
from .gen_img_command import gen_studio



#nagahari
async def naga_cmd(client, message):
    em = Emoji(client)
    await em.get()
    
    arg = client.get_text(message)

    if not arg:
        return await message.reply(
            f"{em.gagal}**Enter date of birth!**\n**Example:** `{message.text.split()[0]} 14 05 2007`"
        )

    args = arg.strip().split()
    if len(args) != 3 or not all(x.isdigit() for x in args):
        return await message.reply(
            f"{em.gagal}**Invalid format!**\n**Use:** `Date Month Year`\n**Example:** `{message.text.split()[0]} 14 05 2007`"
        )

    tanggal, bulan, tahun = args
    proses = await animate_proses(message, em.proses)
    folder = f"downloads/{client.me.id}/"

    try:
        url = (
            f"https://api.botcahx.eu.org/api/primbon/nagahari?"
            f"tanggal={tanggal}&bulan={bulan}&tahun={tahun}&apikey={API_BOTCAHX}"
        )
        response = await Tools.fetch.get(url)
        data = response.json()

        result = data.get("result", {}).get("message", {})
        tgl_lahir = result.get("tgl_lahir", "-").strip()
        arah = result.get("arah_naga_hari", "-").strip()
        full_catatan = result.get("catatan", "-").strip()

        hari_lahir_raw = result.get("hari_lahir", "-").strip()
        hari_lahir = re.sub(r"\(.*?\);", "", hari_lahir_raw).strip()
        hari_lahir = hari_lahir.splitlines()[-1].strip()

        short_catatan = '.'.join(full_catatan.split('.')[:4]).strip()
        if short_catatan and not short_catatan.endswith('.'):
            short_catatan += '.'

        prompt = f"A majestic and ancient mystical dragon (Naga Hari) embodying the spiritual essence of someone born on {tgl_lahir}. The dragon should reflect traditional Southeast Asian symbolism — with intricate scales, flowing energy patterns, and sacred markings inspired by Javanese or Balinese culture. Surround it with a divine aura, glowing with spiritual power, as if it guards the destiny and soul of the person. The environment should feel timeless and sacred, with clouds, celestial light, and temple motifs. The overall tone must be powerful, divine, and deeply spiritual"
        path_dir, files = await gen_studio(folder, prompt)

        caption = f"""
<blockquote expandable>━━━━━━━━━━━━━━━━━━━
<b>🐉 Naga Hari</b>
━━━━━━━━━━━━━━━━━━━
<b>📆 Tanggal Lahir:</b> {tgl_lahir}
<b>📅 Hari Lahir:</b> {hari_lahir}
━━━━━━━━━━━━━━━━━━━
<b>🧭 Arah Naga:</b> {arah}
━━━━━━━━━━━━━━━━━━━
📝 <b>Notes:</b> <i>{short_catatan}</i>
━━━━━━━━━━━━━━━━━━━
🔮 <b>Paranormal:</b> {client.me.mention}</blockquote>
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

#keberuntungan
async def keberutungan_cmd(client, message):
    em = Emoji(client)
    await em.get()
    
    arg = client.get_text(message)

    if not arg:
        return await message.reply(
            f"{em.gagal}**Enter name and date of birth!**\n**Example:** `{message.text.split()[0]} Rasta 14 05 2007`"
        )

    args = arg.strip().split()
    if len(args) < 4:
        return await message.reply(
            f"{em.gagal}**Invalid format!**\n**Use:** `Name Date Month Year`\n**Example:** `{message.text.split()[0]} Memex 14 05 2007`"
        )

    nama = " ".join(args[:-3])
    tanggal, bulan, tahun = args[-3:]

    if not all(x.isdigit() for x in (tanggal, bulan, tahun)):
        return await message.reply(
            f"{em.gagal}**Incorrect number format! Use the format:** `Name Date Month Year`\n**Example:** `{message.text.split()[0]} Memex 14 05 2007`"
        )

    proses = await animate_proses(message, em.proses)
    folder = f"downloads/{client.me.id}/"    

    try:
        url = f"https://api.botcahx.eu.org/api/primbon/potensikeberuntungan?nama={nama}&tanggal={tanggal}&bulan={bulan}&tahun={tahun}&apikey={API_BOTCAHX}"
        response = await Tools.fetch.get(url)
        data = response.json()
        message_ = data.get("result", {}).get("message", {})

        nama_res = message_.get("nama", "-")
        tgl_lahir = message_.get("tgl_lahir", "-")
      
        result_raw = message_.get("result", "-").strip()
        sentences = re.split(r'(?<=[.。])\s+', result_raw)
        result = " ".join(sentences[:4])

        prompt = f"A realistic and inspiring illustration symbolizing luck and success for {nama_res}, born on {tgl_lahir}. The character is surrounded by a warm golden glow, representing prosperity, positive energy, and a bright future. Include subtle symbolic elements like blooming flowers, rising sun, flowing water, or gentle wind to enhance the feeling of growth and fortune. The overall mood should be uplifting, serene, and visually radiant — a celebration of destiny and hope"
        path_dir, files = await gen_studio(folder, prompt)

        caption = f"""
<blockquote expandable>━━━━━━━━━━━━━━━━━━━       
<b>🍀 Potensi Keberuntungan</b>
━━━━━━━━━━━━━━━━━━━
<b>🧍 Nama:</b> {nama_res}
<b>📆 Tanggal Lahir:</b> {tgl_lahir}
━━━━━━━━━━━━━━━━━━━
📝 <b>Notes:</b> <i>{result}</i>
━━━━━━━━━━━━━━━━━━━

🔮 <b>Paranormal:</b> {client.me.mention}</blockquote>
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


#tarot
async def tarot_cmd(client, message):
    em = Emoji(client)
    await em.get()
    
    arg = client.get_text(message)

    if not arg:
        return await message.reply(
            f"{em.gagal}**Please provide your birth date!**\n**Example:** `{message.text.split()[0]} 14 05 2007`"
        )

    args = arg.strip().split()
    if len(args) != 3 or not all(x.isdigit() for x in args):
        return await message.reply(
            f"{em.gagal}**Invalid format! Use** `Day Month Year`\n"
            f"**Example:** `{message.text.split()[0]} 14 05 2007`"
        )

    tanggal, bulan, tahun = args
    bulan_nama_dict = {
        "01": "Januari", "02": "Februari", "03": "Maret", "04": "April",
        "05": "Mei", "06": "Juni", "07": "Juli", "08": "Agustus",
        "09": "September", "10": "Oktober", "11": "November", "12": "Desember"
    }

    bulan_angka = bulan.zfill(2)
    bulan_nama = bulan_nama_dict.get(bulan_angka)
    if not bulan_nama:
        return await message.reply(f"{em.gagal}**Invalid month number.**")

    proses = await animate_proses(message, em.proses)
    folder = f"downloads/{client.me.id}/"

    async def fetch_tarot(tgl, bln, thn):
        url = (
            f"https://api.botcahx.eu.org/api/primbon/artitarot?"
            f"tanggal={tgl}&bulan={bln}&tahun={thn}&apikey={API_BOTCAHX}"
        )
        return await Tools.fetch.get(url)

    try:
        response = await fetch_tarot(tanggal, bulan_nama, tahun)
        data = response.json()

        if not data.get("result", {}).get("status"):
            response = await fetch_tarot(tanggal, bulan_angka, tahun)
            data = response.json()

        result = data.get("result", {})
        message_ = result.get("message")

        if not result.get("status") or not isinstance(message_, dict):
            return await proses.edit(f"{em.gagal}**Unexpected response format:**\n<code>{data}</code>")

        tgl_lahir = message_.get("tgl_lahir", f"{tanggal} {bulan_nama} {tahun}")
        simbol = message_.get("simbol_tarot", "-")
        arti = message_.get("arti", "-")
        catatan = message_.get("catatan", "-")

        prompt = f"A mystical tarot card illustration for {simbol}, representing: {arti}"
        path_dir, files = await gen_studio(folder, prompt)

        caption = f"""
<blockquote expandable>━━━━━━━━━━━━━━━━━━━       
<b>🔮 Tarot Symbol: {simbol}</b>
<b>📆 Birth Date:</b> {tgl_lahir}
━━━━━━━━━━━━━━━━━━━
<b>📜 Meaning:</b> <i>{arti.strip()}</i>
━━━━━━━━━━━━━━━━━━━

🔮 <b>Paranormal:</b> {client.me.mention}</blockquote>
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
        await proses.edit(f"{em.gagal}**An error occurred:**\n`{e}`")
    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder)


#shio
async def shio_cmd(client, message):
    em = Emoji(client)
    await em.get()
    
    arg = client.get_text(message)

    if not arg:
        return await message.reply(
            f"{em.gagal}**Please provide your birth date! Example:** `{message.text.split()[0]} 14 05 2007`"
        )

    args = arg.strip().split()
    if len(args) != 3 or not all(x.isdigit() for x in args):
        return await message.reply(
            f"{em.gagal}**Invalid format! Use `Day Month Year`**\n"
            f"**Example:** `{message.text.split()[0]} 14 05 2007`"
        )

    tanggal, bulan, tahun = map(int, args)
    proses = await animate_proses(message, em.proses)
    folder = f"downloads/{client.me.id}/"

    try:
        chinese_zodiac = [
            "Goat", "Monkey", "Rooster", "Dog", "Pig", "Rat",
            "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse"
        ]
        shio = chinese_zodiac[tahun % 12]

        url = f"https://api.botcahx.eu.org/api/primbon/shio?shio={shio}&apikey={API_BOTCAHX}"
        response = await Tools.fetch.get(url)

        if response.status_code != 200:
            return await proses.edit(f"{em.gagal}**Failed to fetch data Status Code:** {response.status_code}")

        data = response.json()
        message_ = data.get("result", {}).get("message", {})

        nama = message_.get("nama", "-")
        arti_raw = message_.get("arti", "-").strip()
        catatan = message_.get("catatan", "-")

        import re
        sentences = re.split(r'(?<=[.。])\s+', arti_raw)
        arti = " ".join(sentences[:4])

        prompt = f"A detailed and elegant illustration of the Chinese zodiac sign representing {nama}, incorporating their core traits: {arti}. The artwork should blend traditional Chinese artistic elements — such as ink brush style, red and gold accents, zodiac animal symbolism, and flowing calligraphy. The background may include clouds, lanterns, or celestial motifs to enhance the spiritual and cultural meaning. The overall tone should feel wise, symbolic, and timeless, celebrating the essence of their zodiac identity"
        path_dir, files = await gen_studio(folder, prompt)

        caption = f"""
<blockquote expandable>━━━━━━━━━━━━━━━━━━━        
<b>🐉 Chinese Zodiac: {nama}</b>
━━━━━━━━━━━━━━━━━━━
✨ <b>Traits:</b> {arti}</i>
━━━━━━━━━━━━━━━━━━━

🔮 <b>Paranormal:</b> {client.me.mention}</blockquote>
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
        await proses.edit(f"{em.gagal}**An error occurred:**\n`{e}`")
    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder)


#artinama
async def artinama_cmd(client, message):
    em = Emoji(client)
    await em.get()
    
    arg = client.get_text(message)

    if not arg:
        return await message.reply(
            f"{em.gagal}**Enter name! Example** `{message.text.split()[0]} Budi`"
        )

    proses = await animate_proses(message, em.proses)
    folder = f"downloads/{client.me.id}/"

    try:
        url = f"https://api.botcahx.eu.org/api/primbon/artinama?nama={quote(arg)}&apikey={API_BOTCAHX}"
        response = await Tools.fetch.get(url)

        if response.status_code != 200:
            return await proses.edit(
                f"{em.gagal}**Gagal mengambil data Status Code:** {response.status_code}"
            )

        data = response.json()
        result = data.get("result", {}).get("message")
        if not result:
            return await proses.edit(f"{em.gagal}**Data not found.**")

        nama = result.get("nama", arg)
        arti = result.get("arti", "Tidak ditemukan")

        paragraf = [p.strip() for p in arti.split('.') if p.strip()]
        ringkasan = '. '.join(paragraf[:6]) + ('.' if len(paragraf) > 6 else '.')
        
        prompt = f"Create a dark, mystical illustration inspired by Javanese supernatural folklore. The scene should include eerie shadows, ancient ruins, ghostly figures, or cursed forests typical of Java’s spiritual legends. Integrate the name ‘{nama}’ prominently in the image using an ancient or haunted-looking font, as if the name itself carries a supernatural power. The overall tone should be haunting, mysterious, and spiritually intense"
        path_dir, files = await gen_studio(folder, prompt)

        caption = f"""
<blockquote expandable>━━━━━━━━━━━━━━━━━━━        
<b>🔤 Arti Nama: {nama}</b>
━━━━━━━━━━━━━━━━━━━
📖 <b>Makna:</b> <i>{ringkasan}</i>
━━━━━━━━━━━━━━━━━━━

🔮 <b>Paranormal:</b> {client.me.mention}</blockquote>
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
            

# Weton jawa
async def weton_cmd(client, message):
    em = Emoji(client)
    await em.get()
    
    arg = client.get_text(message)

    if not arg:
        return await message.reply(
            f"{em.gagal} **Please enter date of birth!**\n**Example:** `{message.text.split()[0]} 14 05 2006`"
        )

    try:
        tanggal, bulan, tahun = [x.strip() for x in arg.split()]
        if not (tanggal.isdigit() and bulan.isdigit() and tahun.isdigit()):
            raise ValueError
    except ValueError:
        return await message.reply(
            f"{em.gagal}**Incorrect format!**\n**Use:** `Tanggal Bulan Tahun`\n**Example**: `{message.text.split()[0]} 14 05 2006`"
        )

    proses = await animate_proses(message, em.proses)
    folder = f"downloads/{client.me.id}/"

    try:
        url = f"https://api.botcahx.eu.org/api/primbon/wetonjawa?tanggal={tanggal}&bulan={bulan}&tahun={tahun}&apikey={API_BOTCAHX}"
        response = await Tools.fetch.get(url)
        if response.status_code != 200:
            return await proses.edit(f"{em.gagal}**Failed to fetch Status data:** {response.status_code}")

        data = response.json()
        result = data.get("result", {}).get("message")
        if not result:
            return await proses.edit(f"{em.gagal}**Data not found.**")

        tanggal_lahir = result['tanggal']
        neptu = result['jumlah_neptu']
        watak_hari = result['watak_hari']
        naga_hari = result['naga_hari']
        jam_baik = result['jam_baik']
        watak_kelahiran = result['watak_kelahiran']

        prompt = f"A realistic and detailed illustration of a traditional Javanese person embodying the spiritual traits of their Javanese calendar reading. They possess a neptu value of {neptu}, are born under the day character of {watak_hari}, with the dragon sign {naga_hari}, and reflect the core personality trait of {watak_kelahiran.split(',')[0]}. The scene should be set in a traditional Javanese environment — think batik clothing, wayang shadows, ancient temples, and mystical mist. Capture the ethnic elegance, spiritual depth, and cultural symbolism of Java in a richly atmospheric and respectful way."
        path_dir, files = await gen_studio(folder, prompt)        
        if len(watak_kelahiran) > 100:
            watak_kelahiran = watak_kelahiran[:100] + "..."

        caption = f"""
<blockquote expandable>━━━━━━━━━━━━━━━━━━━
🥠 <b>Perhitungan Weton Jawa:</b>
━━━━━━━━━━━━━━━━━━━
📅 <b>Tanggal:</b> {tanggal_lahir}
🔢 <b>Neptu:</b> {neptu}
🌿 <b>Watak Hari:</b> {watak_hari}
🐉 <b>Naga Hari:</b> {naga_hari}
⏳ <b>Jam Baik:</b> {jam_baik}
🌀 <b>Watak Kelahiran:</b> {watak_kelahiran}
━━━━━━━━━━━━━━━━━━━

🔮 <b>Dukun:</b> {client.me.mention}</blockquote>
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


# Sifat Karakter
async def karakter_cmd(client, message):
    em = Emoji(client)
    await em.get()    
    arg = client.get_text(message)

    if not arg:
        return await message.reply(
            f"{em.gagal}**Please Enter Name and Date of Birth!**\n**Example:** `{message.text.split()[0]} Dani 14 05 2006`"
        )

    try:
        parts = arg.strip().split()
        if len(parts) < 4:
            raise ValueError
        nama = " ".join(parts[:-3])
        tanggal, bulan, tahun = parts[-3:]
        if not (tanggal.isdigit() and bulan.isdigit() and tahun.isdigit()):
            raise ValueError
    except ValueError:
        return await message.reply(
            f"{em.gagal}**Incorrect format!**\n**Use:** `Nama Tanggal Bulan Tahun`\n**Example:** `{message.text.split()[0]} Dani 14 05 2006`"
        )

    proses = await animate_proses(message, em.proses)
    folder = f"downloads/{client.me.id}/"

    try:
        url = f"https://api.botcahx.eu.org/api/primbon/sifatkarakter?nama={nama}&tanggal={tanggal}&bulan={bulan}&tahun={tahun}&apikey={API_BOTCAHX}"
        response = await Tools.fetch.get(url)

        if response.status_code != 200:
            return await proses.edit(
                f"{em.gagal} **Failed to fetch Status data:** (Status Code {response.status_code})"
            )

        data = response.json()
        result = data.get("result", {}).get("message")
        if not result:
            return await proses.edit(f"{em.gagal} **Data not found.**")

        garis_hidup_full = result["garis_hidup"]
        garis_hidup_short = '. '.join(garis_hidup_full.split('. ')[:3]).strip() + '.'

        prompt = (
            f"An artistic portrait of a person named {result['nama']}, born on {result['tgl_lahir']}. "
            f"They possess these traits: {garis_hidup_short} "
            "Style: elegant, semi-realistic, mystical Javanese spiritual background, cinematic lighting, ethereal vibes."
        )

        path_dir, files = await gen_studio(folder, prompt)

        caption = f"""
<blockquote expandable>━━━━━━━━━━━━━━━━━━━
<b>🌞 Karakter Berdasarkan Tanggal Lahir</b>
━━━━━━━━━━━━━━━━━━━
👤 <b>Nama:</b> {result['nama']}
📅 <b>Lahir:</b> {result['tgl_lahir']}
🌀 <b>Garis Hidup:</b> <i>{garis_hidup_short}</i>
━━━━━━━━━━━━━━━━━━━

🔮 <i>Visualisasi ini mencerminkan energi dan sifat unik berdasarkan tanggal lahir.</i>
Dibimbing oleh: {client.me.mention}</blockquote>
"""[:1024]  

        await asyncio.sleep(1)
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
        return await proses.edit(f"{em.gagal}**There is an error:**\n`{e}`")
    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder)


# Ramalan Jodoh
async def jodoh_cmd(client, message):
    em = Emoji(client)
    await em.get()    
    arg = client.get_text(message)

    if not arg:
        return await message.reply(
            f"{em.gagal}**Please Enter Name and Date of Birth!**\n**Example:** `{message.text.split()[0]} Dani 14 05 2006 Dini 12 09 2008`"
        )

    try:
        parts = arg.strip().split()
        if len(parts) < 8:
            raise ValueError

        split_index = len(parts) - 7
        nama1 = " ".join(parts[:split_index])
        tanggal1, bulan1, tahun1 = parts[split_index], parts[split_index + 1], parts[split_index + 2]
        nama2 = " ".join(parts[split_index + 3:-3])
        tanggal2, bulan2, tahun2 = parts[-3], parts[-2], parts[-1]

        if not all(p.isdigit() for p in [tanggal1, bulan1, tahun1, tanggal2, bulan2, tahun2]):
            raise ValueError
    except ValueError:
        return await message.reply(
            f"{em.gagal}**Incorrect format!**\n**Use:** `Nama1 Tgl1 Bln1 Thn1 Nama2 Tgl2 Bln2 Thn2`\n**Example:** `{message.text.split()[0]} Dani 14 05 2006 Dini 12 09 2008`"
        )

    proses = await animate_proses(message, em.proses)
    folder = f"downloads/{client.me.id}/"

    try:
        url = (
            f"https://api.botcahx.eu.org/api/primbon/ramalanjodoh?"
            f"nama1={nama1}&tanggal1={tanggal1}&bulan1={bulan1}&tahun1={tahun1}&"
            f"nama2={nama2}&tanggal2={tanggal2}&bulan2={bulan2}&tahun2={tahun2}&"
            f"apikey={API_BOTCAHX}"
        )
        response = await Tools.fetch.get(url)

        if response.status_code != 200:
            return await proses.edit(f"{em.gagal}**Gagal mengambil data Status:** {response.status_code}")

        data = response.json()
        result = data.get("result", {}).get("message")
        if not result:
            return await proses.edit(f"{em.gagal}**Data not found.**")

        full_explanation = result['result']
        sentences = re.split(r'(?<=[.!?]) +', full_explanation)
        short_explanation = " ".join(sentences[:4])  

        prompt = (
            f"An artistic digital illustration of a Javanese couple named {result['nama_anda']['nama']} and {result['nama_pasangan']['nama']}, "
            "dressed in traditional Javanese clothing, romantic atmosphere, warm sunset, mystical and cultural vibes, realistic style."
        )
        path_dir, files = await gen_studio(folder, prompt)
        
        caption = f"""
<blockquote expandable>━━━━━━━━━━━━━━━━━━━
👨‍❤️‍💋‍👨 <b>Berikut adalah hasil Ramalan Jodoh:</b>
━━━━━━━━━━━━━━━━━━━
👤 <b>Nama Kamu:</b> {result['nama_anda']['nama']}
📅 <b>Tanggal Lahir Kamu:</b> {result['nama_anda']['tgl_lahir']}
💑 <b>Nama Pasangan:</b> {result['nama_pasangan']['nama']}
📆 <b>Tanggal Lahir Pasangan:</b> {result['nama_pasangan']['tgl_lahir']}
━━━━━━━━━━━━━━━━━━━
📖 <b>Penjelasan:</b> <i>{short_explanation}</i>
━━━━━━━━━━━━━━━━━━━

🔮 <b>Paranormal:</b> {client.me.mention}</blockquote>
"""[:1024]

        await asyncio.sleep(1)
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
        return await proses.edit(f"{em.gagal}**There is an error:**\n`{e}`")
    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            

# Ramalan Cinta
async def cinta_cmd(client, message):
    em = Emoji(client)
    await em.get()
    arg = client.get_text(message)

    if not arg:
        return await message.reply(
            f"{em.gagal}**Please Enter Name and Date of Birth!**\n**Example:** `{message.text.split()[0]} Dani 14 05 2006 Dini 12 09 2008`"
        )

    try:
        parts = arg.strip().split()
        if len(parts) < 8:
            raise ValueError

        nama1 = " ".join(parts[:len(parts)-7])
        tanggal1, bulan1, tahun1 = parts[-7], parts[-6], parts[-5]
        nama2 = parts[-4]
        tanggal2, bulan2, tahun2 = parts[-3], parts[-2], parts[-1]

        if not all(p.isdigit() for p in [tanggal1, bulan1, tahun1, tanggal2, bulan2, tahun2]):
            raise ValueError
    except ValueError:
        return await message.reply(
            f"{em.gagal}**Incorrect format!**\n**Use:** `Nama1 Tgl1 Bln1 Thn1 Nama2 Tgl2 Bln2 Thn2`\nContoh: `{message.text.split()[0]} Dani 14 05 2006 Dini 12 09 2008`"
        )

    proses = await animate_proses(message, em.proses)
    folder = f"downloads/{client.me.id}/"    

    try:
        url = (
            f"https://api.botcahx.eu.org/api/primbon/ramalancinta?"
            f"nama1={nama1}&tanggal1={tanggal1}&bulan1={bulan1}&tahun1={tahun1}&"
            f"nama2={nama2}&tanggal2={tanggal2}&bulan2={bulan2}&tahun2={tahun2}&"
            f"apikey={API_BOTCAHX}"
        )
        response = await Tools.fetch.get(url)

        if response.status_code != 200:
            return await proses.edit(f"{em.gagal}**Failed to fetch Status data:** {response.status_code}")

        data = response.json()
        result = data.get("result", {}).get("message")
        if not result:
            return await proses.edit(f"{em.gagal}**Data not found.**")

        prompt = (
            f"A romantic illustration of a couple named {result['nama_anda']['nama']} and {result['nama_pasangan']['nama']}, "
            "set in a traditional Javanese setting with warm, loving atmosphere and cultural background."
        )
        path_dir, files = await gen_studio(folder, prompt)
                
        caption = f"""
<blockquote expandable>━━━━━━━━━━━━━━━━━━━
👨‍❤️‍👨 <b>Berikut adalah hasil Ramalan Cinta:</b>
━━━━━━━━━━━━━━━━━━━
👤 <b>Nama Kamu:</b> {result['nama_anda']['nama']}
📅 <b>Tanggal Lahir Kamu:</b> {result['nama_anda']['tgl_lahir']}
💑 <b>Nama Pasangan:</b> {result['nama_pasangan']['nama']}
📆 <b>Tanggal Lahir Pasangan:</b> {result['nama_pasangan']['tgl_lahir']}
━━━━━━━━━━━━━━━━━━━
✨ <b>Sisi Positif:</b> <i>{result.get('sisi_positif', '-')}</i>
━━━━━━━━━━━━━━━━━━━
📝 <b>Catatan:</b> <i>{result.get('catatan', '-')}</i>
━━━━━━━━━━━━━━━━━━━

🔮 <b>Paranormal:</b> {client.me.mention}</blockquote>
"""[:1024]

        await asyncio.sleep(1)
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
        return await proses.edit(f"{em.gagal}**There is an error:**\n`{e}`")
    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            

# Cocok Pasangan
async def pasangan_cmd(client, message):
    em = Emoji(client)
    await em.get()
    arg = client.get_text(message)

    if not arg or '&' not in arg:
        return await message.reply(f"{em.gagal}**Please enter two names separated by `&`!**\n**Example:** `{message.text.split()[0]} Fajar&Ayas`"
    )

    try:
        nama1, nama2 = [n.strip() for n in arg.split("&", maxsplit=1)]
    except ValueError:
        return await message.reply(f"{em.gagal}**Incorrect format!**\n**Use format:** `Nama1&Nama2`\n**Example:** `{message.text.split()[0]} Fajar&Ayas`"
    )

    proses = await animate_proses(message, em.proses)
    folder = f"downloads/{client.me.id}/"        

    try:
        url = f"https://api.botcahx.eu.org/api/primbon/kecocokanpasangan?cowo={nama1}&cewe={nama2}&apikey={API_BOTCAHX}"
        response = await Tools.fetch.get(url)

        if response.status_code != 200:
            return await proses.edit(f"{em.gagal}**Failed to fetch Status data:** {response.status_code}")

        data = response.json()
        result = data.get("result", {}).get("message")
        if not result:
            return await proses.edit(f"{em.gagal}**Data not found.**")

        prompt = (
            f"Ilustrasi romantis pasangan {result.get('nama_anda', nama1)} dan {result.get('nama_pasangan', nama2)}, "
            f"dengan suasana penuh cinta dan kebahagiaan"
        )
        path_dir, files = await gen_studio(folder, prompt)
        
        caption = f"""
<blockquote expandable>━━━━━━━━━━━━━━━━━━━
<b>💞 Kecocokan Pasangan 💞</b>
━━━━━━━━━━━━━━━━━━━
👤 <b>Nama Kamu:</b> {result.get('nama_anda', nama1)}
💑 <b>Nama Pasangan:</b> {result.get('nama_pasangan', nama2)}
━━━━━━━━━━━━━━━━━━━
✨ <b>Sisi Positif:</b> <i>{result.get('sisi_positif', '-')}</i>
⚠️ <b>Sisi Negatif:</b> <i>{result.get('sisi_negatif', '-')}</i>
━━━━━━━━━━━━━━━━━━━

🔮 <b>Paranormal:</b> {client.me.mention}
━━━━━━━━━━━━━━━━━━━</blockquote>
"""[:1024]

        await asyncio.sleep(1)
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
        return await proses.edit(f"{em.gagal}**There is an error:**\n`{e}`")
    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder)

# Cocok nama
async def cocoknama_cmd(client, message):
    em = Emoji(client)
    await em.get()
    arg = client.get_text(message)

    if not arg or len(arg.split()) < 4:
        return await message.reply(
            f"{em.gagal}**Please enter Name and Date of Birth!**\n**Example:** `{message.text.split()[0]} Dani 14 05 2006`"
        )

    try:
        nama, tanggal, bulan, tahun = arg.split(maxsplit=3)
    except ValueError:
        return await message.reply(
            f"{em.gagal}**Incorrect format!**\n**Use:** `Nama Tanggal Bulan Tahun`\nContoh: `{message.text.split()[0]} Dani 14 05 2006`"
        )

    proses = await animate_proses(message, em.proses)
    folder = f"downloads/genai_cocoknama_{message.id}"

    try:
        url = (
            f"https://api.botcahx.eu.org/api/primbon/kecocokannama?"
            f"nama={nama}&tanggal={tanggal}&bulan={bulan}&tahun={tahun}&apikey={API_BOTCAHX}"
        )
        response = await Tools.fetch.get(url)

        if response.status_code != 200:
            return await proses.edit(f"{em.gagal}**Failed to fetch Status data:** {response.status_code}")

        data = response.json()
        result = data.get("result", {}).get("message")
        if not result:
            return await proses.edit(f"{em.gagal}**Data not found.**")

        prompt = (
            f"Visualisasi takdir dan kepribadian seseorang bernama {result.get('nama', nama)}, "
            f"lahir pada {result.get('tgl_lahir', f'{tanggal}-{bulan}-{tahun}')}, digambarkan dalam gaya mistis, "
            f"dengan nuansa spiritual dan latar horoskop atau bintang."
        )
        path_dir, files = await gen_studio(folder, prompt)
        
        caption = f"""
<blockquote expandable>━━━━━━━━━━━━━━━━━━━
<b>🔤 Kecocokan Nama</b>
━━━━━━━━━━━━━━━━━━━
📌 <b>Nama:</b> {result.get('nama', nama)}
📅 <b>Tanggal Lahir:</b> {result.get('tgl_lahir', f'{tanggal}-{bulan}-{tahun}')}
🔮 <b>Daya Hidup:</b> {result.get('life_path', '-')}
🎯 <b>Destiny:</b> {result.get('destiny', '-')}
🧩 <b>Personality:</b> {result.get('personality', '-')}
📊 <b>Persentase Kecocokan:</b> {result.get('persentase_kecocokan', '-')}
━━━━━━━━━━━━━━━━━━━
📝 <b>Catatan:</b> <i>{result.get('catatan', '-')}</i>
━━━━━━━━━━━━━━━━━━━

🔮 <b>Paranormal:</b> {client.me.mention}</blockquote>
"""[:1024]

        await asyncio.sleep(1)
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
        return await proses.edit(f"{em.gagal}**There is an error:**\n`{e}`")
    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder)


# pekerjaanwetonlahir
async def wetonkerja_cmd(client, message):
    em = Emoji(client)
    await em.get()
    arg = client.get_text(message)

    if not arg:
        return await message.reply(
            f"{em.gagal}**Please Enter Date of Birth!\n**Example:** `{message.text.split()[0]} 14 05 2006`"
        )

    try:
        tanggal, bulan, tahun = arg.strip().split()
    except ValueError:
        return await message.reply(
            f"{em.gagal}**Incorrect format!\n**Use:** `Tanggal Bulan Tahun`\n"
            f"**Example:** `{message.text.split()[0]} 14 05 2006`"
        )

    proses = await animate_proses(message, em.proses)
    folder = f"downloads/genai_wetonkerja_{message.id}"

    try:
        url = f"https://api.botcahx.eu.org/api/primbon/pekerjaanwetonlahir?tanggal={tanggal}&bulan={bulan}&tahun={tahun}&apikey={API_BOTCAHX}"
        response = await Tools.fetch.get(url)

        if response.status_code != 200:
            return await proses.edit(f"{em.gagal}**Failed to fetch Status data:** {response.status_code}")

        data = response.json()
        result = data.get("result", {}).get("message")
        if not result:
            return await proses.edit(f"{em.gagal}**Data not found.**")

        hari = result.get("hari_lahir", "-")
        job = result.get("pekerjaan", "-")
        catatan = result.get("catatan", "-")

        prompt = (
            f"Ilustrasi pekerjaan yang cocok berdasarkan weton Jawa {hari}, "
            f"dengan suasana budaya tradisional, spiritual, dan makna mendalam, menggambarkan pekerjaan: {job}."
        )
        path_dir, files = await gen_studio(folder, prompt)
        
        caption = f"""
<blockquote expandable>━━━━━━━━━━━━━━━━━━━
<b>💼 Pekerjaan Berdasarkan Weton</b>
━━━━━━━━━━━━━━━━━━━
📆 <b>Hari Lahir:</b> {hari}
🔧 <b>Pekerjaan Cocok:</b> {job}
━━━━━━━━━━━━━━━━━━━
📝 <b>Catatan:</b> <i>{catatan}</i>
━━━━━━━━━━━━━━━━━━━

🔮 <b>Paranormal:</b> {client.me.mention}</blockquote>
"""[:1024]

        await asyncio.sleep(1)
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
            

# Arah rezeki
async def rezeki_cmd(client, message):
    em = Emoji(client)
    await em.get()
    arg = client.get_text(message)

    if not arg:
        return await message.reply(
            f"{em.gagal}**Please Enter Date of Birth! Contoh:** `{message.text.split()[0]} 14 05 2006`"
        )

    try:
        tanggal, bulan, tahun = arg.strip().split()
    except ValueError:
        return await message.reply(
            f"{em.gagal}**Incorrect format! Use** `Tanggal Bulan Tahun`\n"
            f"**Example:** `{message.text.split()[0]} 14 05 2006`"
        )

    proses = await animate_proses(message, em.proses)
    folder = f"downloads/genai_arahrezeki_{message.id}"

    try:
        url = f"https://api.botcahx.eu.org/api/primbon/arahrejeki?tanggal={tanggal}&bulan={bulan}&tahun={tahun}&apikey={API_BOTCAHX}"
        response = await Tools.fetch.get(url)

        if response.status_code != 200:
            return await proses.edit(f"{em.gagal}**Failed to fetch Status data:** {response.status_code}")

        data = response.json()
        result = data.get("result", {}).get("message")
        if not result:
            return await proses.edit(f"{em.gagal}**Data not found.**")

        hari = result.get("hari_lahir", "-")
        tgl = result.get("tgl_lahir", f"{tanggal}-{bulan}-{tahun}")
        arah = result.get("arah_rejeki", "-")
        catatan = result.get("catatan", "-")

        prompt = f"A realistic and atmospheric illustration inspired by Javanese spiritual beliefs, depicting the direction of fortune (arah rezeki) for a person born on {hari}. Their fortune flows toward the {arah} direction, represented through symbolic mystical elements like glowing wayang spirits, sacred geometry, and cosmic energy patterns. The scene should evoke deep spirituality with a traditional Javanese backdrop — ancient temples, batik textures, and subtle supernatural auras. The overall tone should feel sacred, mysterious, and rich with cultural symbolism."
        path_dir, files = await gen_studio(folder, prompt)
        
        caption = f"""
<blockquote expandable>━━━━━━━━━━━━━━━━━━━
<b>🧭 Arah Rezeki Berdasarkan Primbon</b>
━━━━━━━━━━━━━━━━━━━
📆 <b>Hari Lahir:</b> {hari}
📅 <b>Tanggal Lahir:</b> {tgl}
🧭 <b>Arah Rezeki:</b> {arah}
━━━━━━━━━━━━━━━━━━━
📝 <b>Catatan:</b> <i>{catatan}</i>
━━━━━━━━━━━━━━━━━━━

🔮 <b>Paranormal:</b> {client.me.mention}</blockquote>
"""[:1024]

        await asyncio.sleep(1)
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

#ArtiMimpi
async def artimimpi_cmd(client, message):
    em = Emoji(client)
    await em.get()
    mimpi = client.get_text(message)

    if not mimpi:
        return await message.reply(
            f"{em.gagal}**Please enter the dream you want to search for!**\n"
            f"**Example:** `{message.text.split()[0]} mandi di laut`"
        )

    proses = await animate_proses(message, em.proses)
    folder = f"downloads/genai_artimimpi_{message.id}"

    try:
        url = f"https://api.botcahx.eu.org/api/primbon/artimimpi?mimpi={mimpi}&apikey={API_BOTCAHX}"
        response = await Tools.fetch.get(url)

        try:
            data = response.json()
        except Exception:
            return await proses.edit(f"{em.gagal}**Failed to parse JSON response from API.**")

        result = data.get("result", {}).get("message")
        if not result:
            return await proses.edit(f"{em.gagal}**Data not found.**")

        if not isinstance(result, dict):
            result = {"mimpi": mimpi, "arti": result, "solusi": "-"}

        mimpi_txt = result.get("mimpi", mimpi)
        arti = result.get("arti", "-")
        arti = ".".join(arti.split(".")[:3]).strip()
        if not arti.endswith("."):
            arti += "."
        solusi = result.get("solusi", "-")
        solusi = ".".join(solusi.split(".")[:3]).strip()
        if not solusi.endswith("."):
            solusi += "."
                
        prompt = f"A dark and mystical illustration of a dream about ‘{mimpi_txt}’, inspired by traditional Javanese spiritual symbolism. The scene should feel mysterious and otherworldly, filled with eerie omens, ancestral spirits, and magical signs drawn from ancient Javanese beliefs. Use shadowy lighting, surreal dreamlike landscapes, and haunting elements that evoke a sense of sacred mystery and subtle fear. The overall atmosphere should be spiritual, symbolic, and deeply rooted in Javanese mysticism."
        path_dir, files = await gen_studio(folder, prompt)

        caption = f"""
<blockquote expandable>━━━━━━━━━━━━━━━━━━━        
<b>🌙 Hasil Arti Mimpi</b>
━━━━━━━━━━━━━━━━━━━
🌟 <b>Mimpi:</b> {mimpi_txt}
🔮 <b>Arti:</b> <i>{arti}</i>
📝 <b>Solusi:</b> <i>{solusi}</i>
━━━━━━━━━━━━━━━━━━━

🔮 <b>Paranormal:</b> {client.me.mention}</blockquote>
"""[:1024]

        await asyncio.sleep(1)
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


# Hari naas
async def naas_cmd(client, message):
    em = Emoji(client)
    await em.get()
    tanggal = client.get_text(message)

    if not tanggal or len(tanggal.split()) != 3:
        return await message.reply(
            f"{em.gagal}**Enter Date of Birth in the correct format!**\n"
            f"**Example:** `{message.text.split()[0]} 14 05 2006`"
        )

    proses = await animate_proses(message, em.proses)
    folder = f"downloads/genai_naas_{message.id}"

    try:
        tgl, bln, thn = tanggal.split()
        url = f"https://api.botcahx.eu.org/api/primbon/harinaas?tanggal={tgl}&bulan={bln}&tahun={thn}&apikey={API_BOTCAHX}"
        response = await Tools.fetch.get(url)

        if response.status_code != 200:
            return await proses.edit(f"{em.gagal}**Failed to fetch Status data:** {response.status_code}")

        data = response.json()
        result = data.get("result", {}).get("message")
        if not result:
            return await proses.edit(f"{em.gagal}**Data not found.**")

        hari = result.get("hari_lahir", "-")
        tgl_lahir = result.get("tgl_lahir", f"{tgl}-{bln}-{thn}")
        naas = result.get("hari_naas", "-")
        catatan = result.get("catatan", "-")
        full_info = result.get("info", "-")

        short_info = '.'.join(full_info.split('.')[:4]).strip()
        if short_info and not short_info.endswith('.'):
            short_info += '.'
            
        prompt = f"A realistic and haunting illustration representing the ill-fated day ‘{naas}’ according to the ancient Javanese primbon. The atmosphere should be dark and heavy, filled with spiritual tension and mystical omens. Incorporate traditional Javanese symbols of misfortune — such as broken offerings, shadowy figures, and ancient curses — set against a backdrop of sacred temples or dense, eerie forests. The tone must feel unsettling, spiritual, and deeply rooted in Javanese mystical beliefs about unlucky days"
        path_dir, files = await gen_studio(folder, prompt)
        caption = f"""
<blockquote expandable>━━━━━━━━━━━━━━━━━━━
<b>🔮 Hasil Perhitungan Hari Naas</b>
━━━━━━━━━━━━━━━━━━━
📅 <b>Hari Lahir:</b> {hari}
📆 <b>Tanggal:</b> {tgl_lahir}
⚠️ <b>Hari Naas:</b> {naas}
━━━━━━━━━━━━━━━━━━━
📝 <b>Catatan:</b> <i>{catatan}</i>
━━━━━━━━━━━━━━━━━━━
ℹ️ <b>Info:</b> <i>{short_info}</i>
━━━━━━━━━━━━━━━━━━━

🔮 <b>Paranormal:</b> {client.me.mention}</blockquote>
"""[:1024]

        await asyncio.sleep(1)
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

