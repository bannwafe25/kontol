import os
import httpx
import base64
import shutil
import traceback
import uuid
import requests
import aiofiles
import aiohttp
import asyncio
import random
import io
import re
from io import BytesIO
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
from pyrogram.types import Message
from helpers import Bing, Emoji, Tools, animate_proses
from logs import logger
from datetime import datetime

from config import API_MAELYN



async def quote_cmd(client: Client, message: Message):
    em = Emoji(client)
    await em.get()

    reply = message.reply_to_message
    if not reply:
        await message.edit_text(
            f"{em.gagal} Silakan *reply* ke pesan yang ingin dijadikan Quotly."
        )
        return

    # Custom background color
    bg_color = "#1b1429"
    if len(message.command) > 1:
        bg_color = message.command[1]

    progress = await message.edit_text(
        f"{em.proses} Sedang merender Quotly..."
    )

    try:
        # 1. Data user target
        user = reply.from_user or reply.sender_chat

        user_id = user.id if user else 1
        first_name = (
            user.first_name
            if hasattr(user, "first_name") and user.first_name
            else (user.title or "User")
        )
        last_name = (
            user.last_name
            if hasattr(user, "last_name") and user.last_name
            else ""
        )
        username = (
            user.username
            if hasattr(user, "username") and user.username
            else ""
        )

        # 2. Foto profil
        avatar_url = (
            f"https://ui-avatars.com/api/?name={first_name.replace(' ', '+')}"
            "&background=random"
        )

        if user and hasattr(user, "photo") and user.photo:
            try:
                photo_bytes = await client.download_media(
                    user.photo.big_file_id,
                    in_memory=True
                )

                if photo_bytes:
                    avatar_url = (
                        "data:image/jpeg;base64,"
                        f"{base64.b64encode(photo_bytes.getvalue()).decode()}"
                    )

            except Exception:
                pass

        text_content = reply.text or reply.caption or ""

        # 3. Data pengirim
        from_data = {
            "id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "photo": {
                "url": avatar_url
            }
        }

        # 4. Reply message
        reply_message_data = None

        if reply.reply_to_message:
            r_msg = reply.reply_to_message
            r_user = r_msg.from_user or r_msg.sender_chat

            r_id = r_user.id if r_user else 123456789

            r_fname = (
                r_user.first_name
                if hasattr(r_user, "first_name") and r_user.first_name
                else (r_user.title or "User")
            )

            r_lname = (
                r_user.last_name
                if hasattr(r_user, "last_name") and r_user.last_name
                else ""
            )

            reply_message_data = {
                "name": f"{r_fname} {r_lname}".strip(),
                "text": r_msg.text or r_msg.caption or "🖼 Media",
                "entities": [],
                "chatId": r_id,
                "from": {
                    "id": r_id,
                    "name": f"{r_fname} {r_lname}".strip(),
                    "photo": {
                        "url": (
                            "https://ui-avatars.com/api/?name="
                            f"{r_fname.replace(' ', '+')}"
                            "&background=random"
                        )
                    }
                }
            }

        message_object = {
            "from": from_data,
            "text": text_content,
            "entities": [],
            "avatar": True
        }

        if reply_message_data:
            message_object["replyMessage"] = reply_message_data

        # 5. Payload
        payload = {
            "backgroundColor": bg_color,
            "width": 512,
            "height": 768,
            "scale": 2,
            "emojiBrand": "apple",
            "messages": [
                message_object
            ]
        }

        # 6. Generate
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }

        async with httpx.AsyncClient(timeout=25.0) as http_client:
            response = await http_client.post(
                "https://quote.yuri.ly/generate.webp",
                json=payload,
                headers=headers
            )

        if response.status_code != 200:
            await progress.edit_text(
                f"{em.gagal} API Error ({response.status_code}):\n"
                f"`{response.text[:100]}`"
            )
            return

        sticker_data = BytesIO(response.content)
        sticker_data.name = "quotly.webp"

        await message.reply_sticker(
            sticker=sticker_data
        )

        await progress.delete()

    except Exception as e:
        await progress.edit_text(
            f"{em.gagal} Terjadi kesalahan:\n`{e}`"
        )

async def gen_studio(folder_name, prompt):
    prompt_clean = re.sub(r"[^\x20-\x7E]", "", prompt.strip())

    try:
        os.makedirs(folder_name, exist_ok=True)

        url = f"https://api.siputzx.my.id/api/ai/flux?prompt={prompt_clean}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200 and response.content_type == "image/png":
                    file_path = os.path.join(folder_name, "flux_1.png")
                    async with aiofiles.open(file_path, "wb") as f:
                        await f.write(await response.read())

                    files = [
                        os.path.join(folder_name, f)
                        for f in os.listdir(folder_name)
                        if f.endswith(".png")
                    ]

                    return folder_name, files
                else:
                    text = await response.text()
                    logger.error(f"Flux API error {response.status}: {text}")
                    return folder_name, []

    except Exception:
        logger.error(f"gen_flux error: {traceback.format_exc()}")
        return folder_name, []

async def brat_cmd(client, message):
    em = Emoji(client)
    await em.get()

    command = message.command[0]
    prompt = client.get_text(message)

    if not prompt:
        return await message.reply(
            f"{em.gagal}**Please reply to a message containing the prompt!**\n"
            f"Example: `{command} aku ganteng`"
        )

    proses = await animate_proses(message, em.proses)

    try:
        url = "https://api.siputzx.my.id/api/m/brat"
        params = {
            "text": prompt,
            "delay": 500
        }

        response = await Tools.fetch.get(url, params=params)

        if response.status_code != 200:
            raise Exception(f"API Error: {response.status_code}")

        # Membaca gambar dari response ke dalam memori
        img_data = BytesIO(response.content)
        
        # Buka gambar menggunakan PIL dan konversi ke RGBA (mendukung transparansi)
        img = Image.open(img_data).convert("RGBA")
        
        # Telegram mewajibkan stiker muat dalam kotak 512x512
        img.thumbnail((512, 512))

        # Menyiapkan file stiker di dalam memori
        sticker = BytesIO()
        sticker.name = "brat_sticker.webp"
        
        # Simpan sebagai format WEBP (format wajib stiker statis Telegram)
        img.save(sticker, "WEBP", quality=100)
        sticker.seek(0)

        # Mengirim langsung sebagai stiker
        await client.send_sticker(
            chat_id=message.chat.id,
            sticker=sticker
        )

        # Menghapus pesan "proses..."
        await proses.delete()

    except Exception as e:
        await proses.edit(f"{em.gagal}**ERROR:**\n`{e}`")

async def maker_img_cmd(client, message):
    em = Emoji(client)
    await em.get()
    if len(message.command) < 2:
        return await message.reply(
            f"{em.gagal}**Please give me command and reply to photo!!\nExample: `{message.text.split()[0]} nude` (reply photo).**"
        )
    proses = await animate_proses(message, em.proses)
    reply = message.reply_to_message
    if message.command[1] == "sertifikat":
        if len(message.command) < 3:
            return await proses.edit(
                f"{em.gagal}**Please give text!!\nExample: `{message.text.split()[0]} sertifikat anak babi`.**"
            )
        text = " ".join(message.command[2:])
        params = {"text": text}
        url = "https://api.siputzx.my.id/api/m/sertifikat-tolol"
        response = await Tools.fetch.post(url, json=params)
        if response.status_code == 200:
            if not response.content:
                return await proses.edit(f"{em.gagal}**Please try again.**")
            file_path = f"sertifikat_{uuid.uuid4().hex}.jpg"
            with open(file_path, "wb") as f:
                f.write(response.content)
            await message.reply_photo(
                file_path, caption=f"{em.sukses}<b>Succesfully generate image.</b>"
            )
            os.remove(file_path)
            return await proses.delete()
        else:
            return await proses.edit(
                f"{em.gagal}<b>Failed to generate image. Please try again later.</b>"
            )
    elif message.command[1] == "xnxx":
        if len(message.command) < 3:
            return await proses.edit(
                f"{em.gagal}**Please give text!!\nExample: `{message.text.split()[0]} xnxx skandal viral`.**"
            )
        text = " ".join(message.command[2:])
        if not message.reply_to_message.media:
            return await proses.edit(f"{em.gagal}**Please reply photo!!**")
        media = await reply.download()
        async with aiofiles.open(media, mode="rb") as file:
            file_data = await file.read()
        url = "https://api.siputzx.my.id/api/canvas/xnxx"
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field("title", text)
            form.add_field(
                "image", file_data, filename="image.jpg", content_type="image/jpeg"
            )

            async with session.post(url, data=form) as response:
                if response.status != 200:
                    return await proses.edit(f"{em.gagal}**Please try again later!!**")
                file_path = f"canvas{uuid.uuid4().hex}.jpg"
                with open(file_path, "wb") as f:
                    f.write(await response.read())
                await proses.delete()
                return await message.reply_photo(file_path)
    else:
        return await proses.edit(
            f"{em.gagal}**Please give me command and reply to photo!!\nExample: `{message.text.split()[0]} nude` (reply photo).**"
        )

