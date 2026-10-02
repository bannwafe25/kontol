import os
import time
import traceback
import urllib.parse
from datetime import timedelta
from itertools import islice
from typing import List
from uuid import uuid4
import asyncio

import yt_dlp
import wget
from pyrogram import enums
from pyrogram.errors import ChatForwardsRestricted
from pyrogram.types import InputMediaAudio, InputMediaPhoto, InputMediaVideo

from clients import bot
from config import API_MAELYN
from database import state
from helpers import (
    ButtonUtils,
    Emoji,
    Spotify,
    Tools,
    YoutubeSearch,
    animate_proses,
    cookies,
    youtube,
)
from logs import logger


def chunk_media_group(media_list: list, chunk_size: int = 4) -> List[list]:
    """Split media list into chunks of specified size"""
    media_chunks = []
    iterator = iter(media_list)
    while chunk := list(islice(iterator, chunk_size)):
        media_chunks.append(chunk)
    return media_chunks


async def spotdl_cmd(client, message, proses, arg):
    em = Emoji(client)
    await em.get()
    await proses.edit(f"{em.proses}**Wait a minute this takes some time...**")
    if arg.split("/")[-2] != "track":
        return await proses.edit(
            f"{em.gagal}**Sorry only track supported!!**\n**Example:** https://open.spotify.com/track/0pmyq5KBXP3agRdxl1SZXx?si=3k3nnok6QtCkMF-XRzBo5w",
            disable_web_page_preview=True,
        )
    now = time.time()
    url = await Spotify.track(arg)
    (
        file_path,
        info,
        title,
        duration,
        views,
        channel,
        url,
        _,
        thumb,
        data_ytp,
    ) = await youtube.download(url.get("file_path"), as_video=False)
    thumbnail = wget.download(thumb)
    caption = data_ytp.format(
        info, title, timedelta(seconds=duration), views, channel, url, client.me.mention
    )
    try:
        await message.reply_audio(
            audio=file_path,
            title=title,
            thumb=thumbnail,
            performer=channel,
            duration=duration,
            caption=caption,
            progress=youtube.progress,
            progress_args=(proses, now, f"<b>Sending request...</b>", f"{title}"),
        )
        return await proses.delete()
    except Exception:
        logger.error(f"Eror download spotify: {traceback.format_exc()}")
        return await proses.edit(f"{em.gagal}**ERROR Please contact developer.*")


async def ytvideo_cmd(client, message, proses, arg):
    try:
        emo = Emoji(client)
        await emo.get()
        await proses.edit(f"{emo.proses}**Wait a minute this takes some time...**")
        now = time.time()
        try:
            yt_search = YoutubeSearch(arg, max_results=1)
            await yt_search.fetch_results()
            link = yt_search.get_link()
            if link is None:
                link = arg
            else:
                link = link
            logger.info(f"Link: {link}")
        except Exception as error:
            return await proses.edit(
                f"{emo.gagal}<b>ERROR:</b><code>{str(error)}</code>"
            )
        try:
            (
                file_name,
                inpoh,
                title,
                duration,
                views,
                channel,
                url,
                _,
                thumb,
                data_ytp,
            ) = await youtube.download(link, as_video=True)

            if isinstance(duration, str):
                duration = duration.replace(".", "")
            duration = int(duration)

        except Exception as error:
            return await proses.edit(
                f"{emo.gagal}<b>ERROR:</b><code>{str(error)}</code>"
            )

        thumbnail = wget.download(thumb)
        kapten = data_ytp.format(
            inpoh,
            title,
            timedelta(seconds=duration),
            views,
            channel,
            url,
            bot.me.mention,
        )
        await client.send_video(
            message.chat.id,
            video=file_name,
            thumb=thumbnail,
            file_name=title,
            duration=duration,
            supports_streaming=True,
            caption=f"{kapten}",
            progress=youtube.progress,
            progress_args=(
                proses,
                now,
                f"{emo.proses}<b>Trying to upload...</b>",
                f"{file_name}",
            ),
            reply_to_message_id=message.id,
        )
        await proses.delete()
        if os.path.exists(thumbnail):
            os.remove(thumbnail)
        if os.path.exists(file_name):
            os.remove(file_name)
    except Exception as er:
        logger.error(f"Error: {traceback.format_exc()}")


async def teledl_cmd(client, message, proses, link):
    em = Emoji(client)
    await em.get()
    chat_id = message.chat.id
    await proses.edit(f"{em.proses}**Wait a minute this takes some time...**")
    logger.info(f"Chat ID: {chat_id}\nLink: {link}")
    if link.startswith(("https", "t.me")):
        if link.endswith("?single"):
            links = link.replace("?single", "")
            logger.info(f"Link Single: {links}")
            parts = links.split("/")
            if len(parts) == 7:
                chat = f"-100{parts[4]}"
                msg_id = int(parts[6])
            else:
                chat = parts[3]
                msg_id = int(parts[4])
            logger.info(f"Chat Single: {chat}")
            logger.info(f"Message ID Single: {msg_id}")
            try:
                await client.copy_media_group(message.chat.id, chat, msg_id)
                return await proses.delete()
            except Exception as e:
                logger.info(f"Chat Single: {chat}")
                logger.info(f"Message ID Single: {msg_id}")
                media_group = []
                mediaa = await client.get_messages(int(chat), int(msg_id))
                medias = await mediaa.get_media_group()
                for msg in medias:
                    if msg.photo:
                        media_group.append(
                            InputMediaPhoto(
                                media=await client.download_media(msg.photo.file_id),
                                caption=msg.caption,
                            )
                        )
                    elif msg.video:
                        media_group.append(
                            InputMediaVideo(
                                media=await client.download_media(msg.video.file_id),
                                caption=msg.caption,
                            )
                        )
                    else:
                        print(f"Skipping message {msg.id}: no media found.")
                if media_group:
                    await client.send_media_group(message.chat.id, media_group)
                    return await proses.delete()

                return await proses.edit(
                    f"><b>{em.gagal} Failed to Copy Message from {chat} {msg_id}: {e}</b>"
                )
        if "?single" in link:
            link = link.replace("?single", "")
        if "/s/" in link:
            user, story_id = Tools.extract_story_link(link)
            story = await client.get_stories(user, story_id)
            await Tools.download_media(story, client, proses, message, True)
            return await proses.delete()
        if "?comment=" in link:
            link_parts = link.split("?comment=")
            msg_id = int(link_parts[0].split("/")[-1])
            tlinket = int(link_parts[1].split("/")[-1])
            chid = str(link.split("/")[-2])
            get_chat = await client.get_discussion_message(chid, msg_id)
            try:
                get_msg = await client.get_messages(get_chat.chat.id, tlinket)
                try:
                    await get_msg.copy(chat_id)
                    return await proses.delete()
                except ChatForwardsRestricted:
                    return await Tools.download_media(get_msg, client, proses, message)
            except Exception as e:
                return await proses.edit(str(e))
        if "t.me/c/" in link:
            print(f"Link private")
            parts = link.split("/")
            if len(parts) == 7:
                get_chat = f"-100{parts[4]}"
                msg_id = int(parts[6])
            else:
                get_chat = f"-100{parts[4]}"
                msg_id = int(parts[5])
            logger.info(f"Chat: {get_chat}")
            logger.info(f"Msg ID: {msg_id}")
            try:
                get_msg = await client.get_messages(get_chat, msg_id)
                try:
                    await get_msg.copy(chat_id)
                    return await proses.delete()
                except ChatForwardsRestricted:
                    return await Tools.download_media(get_msg, client, proses, message)
            except Exception as e:
                return await proses.edit(str(e))
        else:
            parts = link.split("/")
            if len(parts) == 6:
                get_chat = parts[3]
                msg_id = int(parts[5])
            else:
                get_chat = parts[3]
                msg_id = int(parts[4])
            try:
                get_msg = await client.get_messages(get_chat, msg_id)
                await get_msg.copy(chat_id)
                return await proses.delete()
            except ChatForwardsRestricted:
                return await Tools.download_media(get_msg, client, proses, message)
            except Exception as e:
                return await proses.edit(str(e))

    else:
        return await proses.edit(f"{em.gagal}<b>Please give valid link!!</b>")
      
async def instadl_cmd(client, message, proses, arg):
    em = Emoji(client)
    await em.get()

    await proses.edit(f"{em.proses}**Wait a minute, this may take some time...**")

    foto = 0
    video = 0
    errors = []

    api_url = "https://api.maelyn.eu/api/downloader/instagram"

    try:
        if not arg:
            return await proses.edit(f"{em.gagal}**Please provide an Instagram URL.**")

        clean_url = arg.strip().split("?")[0]

        response = await Tools.fetch.get(
            api_url,
            params={"url": clean_url},
            headers={"x-maelyn-auth": API_MAELYN}
        )

        if response.status_code != 200:
            return await proses.edit(
                f"{em.gagal}**Request failed with status code {response.status_code}.**"
            )

        data = response.json()

        if not data.get("success"):
            message_error = data.get("message", "API returned an error or resource not found.")
            return await proses.edit(f"{em.gagal}**{message_error}**")

        metadata = data.get("metadata", {})
        caption = metadata.get("caption") or ""

        if len(caption) > 1024:
            caption = caption[:1021] + "..."

        result = data.get("result", {})
        result_type = result.get("type")

        if result_type == "slide":
            media_items = result.get("items", [])
        elif result_type in ("image", "video"):
            media_items = [result]
        else:
            media_items = []

        if not media_items:
            return await proses.edit(
                f"{em.gagal}**No media found in the Instagram link.**"
            )

        await proses.edit(f"{em.proses}**Preparing media for sending...**")

        media_group = []

        for item in media_items:
            download_url = item.get("url")
            media_type = item.get("type")

            if not download_url or not media_type:
                continue

            if media_type == "image":
                media = await Tools.get_media_data(download_url, "jpg")
                media_group.append(InputMediaPhoto(media=media))
                foto += 1

            elif media_type == "video":
                media = await Tools.get_media_data(download_url, "mp4")
                media_group.append(InputMediaVideo(media=media))
                video += 1

        if not media_group:
            return await proses.edit(
                f"{em.gagal}**Failed to prepare media for sending.**"
            )

        if caption:
            media_group[0].caption = caption

        await proses.delete()

        for index, chunk in enumerate(chunk_media_group(media_group), 1):
            try:
                await client.send_media_group(
                    chat_id=message.chat.id,
                    media=chunk
                )
            except Exception as chunk_error:
                errors.append(f"Chunk {index}: {chunk_error}")

        error_text = ""
        if errors:
            error_text = "\n\n**Errors:**\n" + "\n".join(errors)

        return await message.reply(
            f"{em.sukses}**Successfully sent {len(media_group)} media.**\n"
            f"Photos: `{foto}` | Videos: `{video}`"
            f"{error_text}"
        )

    except Exception as error:
        logger.error(f"instadl: {traceback.format_exc()}")
        return await message.reply(f"{em.gagal}**ERROR:** {error}")


async def ttdl_cmd(client, message, proses, arg):
    em = Emoji(client)
    await em.get()
    await proses.edit(f"{em.proses}**Wait a minute this takes some time...**")

    url = "https://api.maelyn.eu/api/downloader/tiktok/metadata"

    foto, video, audio = 0, 0, 0
    err = ""
    media_group = []
    audio_group = []

    try:
        response = await Tools.fetch.get(
            url,
            params={"url": arg},
            headers={"x-maelyn-auth": API_MAELYN}
        )

        if response.status_code != 200:
            return await proses.edit(
                f"{em.gagal}**Request failed with status code {response.status_code}**"
            )

        data = response.json()

        if not data.get("success"):
            return await proses.edit(f"{em.gagal}**{data.get('message', 'Failed to fetch data')}**")

        metadata = data.get("metadata", {})

        await proses.edit(f"{em.proses}**Preparing media for sending...**")

        # ===== VIDEO =====
        video_data = metadata.get("video")
        if video_data:
            url_video = video_data.get("nwm_url") or video_data.get("url")
            if url_video:
                media_data = await Tools.get_media_data(url_video, "mp4")
                media_group.append(InputMediaVideo(media=media_data))
                video += 1

        # ===== IMAGE =====
        image_data = metadata.get("image_data") or metadata.get("images")
        if image_data:
            image_list = image_data.get("no_watermark_image_list") or image_data
            for uri in image_list:
                media_data = await Tools.get_media_data(uri, "jpg")
                media_group.append(InputMediaPhoto(media=media_data))
                foto += 1

        # ===== AUDIO =====
        music_data = metadata.get("music")
        title_audio = "TikTok Audio"
        if music_data:
            url_audio = music_data.get("url")
            title_audio = music_data.get("title", title_audio)

            if url_audio:
                media_audio = await Tools.get_media_data(url_audio, "mp3")
                audio_group.append(media_audio)
                audio += 1

        if not media_group and not audio_group:
            return await proses.edit(f"{em.gagal}**No media found to send**")

        media_chunks = chunk_media_group(media_group)
        await proses.delete()

        # ===== SEND MEDIA =====
        for i, chunk in enumerate(media_chunks, 1):
            try:
                await client.send_media_group(
                    chat_id=message.chat.id,
                    media=chunk
                )
            except Exception as chunk_error:
                err += f"\n❌ Error sending chunk {i}: {str(chunk_error)}"

        # ===== SEND AUDIO =====
        for i, media_audio in enumerate(audio_group, 1):
            try:
                await client.send_audio(
                    chat_id=message.chat.id,
                    audio=media_audio,
                    title=title_audio,
                )
            except Exception as e:
                err += f"\n❌ Error sending audio {i}: {str(e)}"

        return await message.reply(
            f"{em.sukses}**Successfully sent media**\n"
            f"📸 Photos: `{foto}` | 🎥 Videos: `{video}` | 🎙 Audio: `{audio}`\n{err}"
        )

    except Exception as er:
        logger.error(f"ttdl: {traceback.format_exc()}")
        return await proses.edit(f"{em.gagal}**An error occurred:** `{str(er)}`")
    
    except Exception as er:
        logger.error(f"ttdl: {traceback.format_exc()}")
        return await proses.edit(f"{em.gagal}**An error occurred:** `{str(er)}`")

async def twitter_cmd(client, message, proses, arg):
    em = Emoji(client)
    await em.get()

    await proses.edit(f"{em.proses}**Wait a minute, this may take some time...**")

    foto = 0
    video = 0
    errors = []

    api_url = "https://api.maelyn.eu/api/downloader/twitter"

    try:
        if not arg:
            return await proses.edit(f"{em.gagal}**Please provide a Twitter/X URL.**")

        clean_url = arg.strip().split("?")[0]

        response = await Tools.fetch.get(
            api_url,
            params={"url": clean_url},
            headers={"x-maelyn-auth": API_MAELYN}
        )

        if response.status_code != 200:
            return await proses.edit(
                f"{em.gagal}**Request failed with status code {response.status_code}.**"
            )

        data = response.json()

        if not data.get("success"):
            message_error = data.get("message", "API returned an error or media not found.")
            return await proses.edit(f"{em.gagal}**{message_error}**")

        result = data.get("result", {})
        title = result.get("title") or ""
        medias = result.get("medias", [])

        if not medias:
            return await proses.edit(f"{em.gagal}**No media found in the tweet.**")

        await proses.edit(f"{em.proses}**Preparing media for sending...**")

        media_group = []

        image_exts = ("jpg", "jpeg", "png", "webp")
        video_exts = ("mp4",)

        for item in medias:
            media_url = item.get("url")
            extension = (item.get("extension") or "").lower().replace(".", "")

            if not media_url:
                continue

            if extension in image_exts:
                media = await Tools.get_media_data(media_url, extension)
                media_group.append(InputMediaPhoto(media=media))
                foto += 1

        video_items = [
            item for item in medias
            if (item.get("extension") or "").lower().replace(".", "") in video_exts
            and item.get("url")
        ]

        if video_items:
            best_video = video_items[0]
            media = await Tools.get_media_data(best_video["url"], "mp4")
            media_group.append(InputMediaVideo(media=media))
            video += 1

        if not media_group:
            return await proses.edit(
                f"{em.gagal}**Failed to prepare any media for sending.**"
            )

        if title:
            caption = title[:1021] + "..." if len(title) > 1024 else title
            media_group[0].caption = caption

        await proses.delete()

        for index, chunk in enumerate(chunk_media_group(media_group), 1):
            try:
                await client.send_media_group(
                    chat_id=message.chat.id,
                    media=chunk
                )
            except Exception as chunk_error:
                errors.append(f"Chunk {index}: {chunk_error}")

        error_text = ""
        if errors:
            error_text = "\n\n**Errors:**\n" + "\n".join(errors)

        return await message.reply(
            f"{em.sukses}**Successfully sent {len(media_group)} media.**\n"
            f"Photos: `{foto}` | Videos: `{video}`"
            f"{error_text}"
        )

    except Exception as error:
        logger.error(f"twdl: {traceback.format_exc()}")
        return await proses.edit(f"{em.gagal}**ERROR:** {error}")

async def pindl_cmd(client, message, proses, arg):
    em = Emoji(client)
    await em.get()
    await proses.edit(f"{em.proses}**Wait a minute this takes some time...**")
    data_json = {"url": arg}
    url = "https://api.siputzx.my.id/api/d/pinterest"
    response = await Tools.fetch.post(url, json=data_json)

    if response.status_code != 200:
        return await proses.edit(
            f"{em.gagal}**Failed to download from the provided URL.**"
        )
    data = response.json()
    result = data["data"]["media_urls"][0]
    quality = result["quality"]
    if quality == "original":
        if result["type"] == "image":
            await message.reply_photo(
                result["url"], caption=data["data"]["title"] or ""
            )
        elif result["type"] == "video/mp4":
            await message.reply_video(
                result["video"], caption=data["data"]["title"] or ""
            )
    else:
        await message.reply(f"{em.gagal}**No original link found.**")

    return await proses.delete()


async def thread_cmd(client, message, proses, arg):
    em = Emoji(client)
    await em.get()
    await proses.edit(f"{em.proses}**Wait a minute this takes some time...**")
    foto, video = 0, 0
    err = ""

    try:
        url = f"https://api.maelyn.eu/api/threads?url={arg}&apikey={API_MAELYN}"
        response = await Tools.fetch.get(url)

        if response.status_code != 200:
            return await proses.edit(
                f"{em.gagal}**Request failed with status code {response.status_code}**"
            )

        data = response.json()
        result = data.get("result", {})

        if not result:
            return await proses.edit(f"{em.gagal}**No media found in the tweet.**")

        await proses.edit(f"{em.proses}**Preparing media for sending...**")
        photo_url = result.get("image_urls")
        video_url = result.get("video_urls")
        media_group = []
        if len(photo_url) != 0:
            for item in photo_url:
                media = await Tools.get_media_data(item, "jpg")
                media_group.append(InputMediaPhoto(media=media))
                foto += 1

        if len(video_url) != 0:
            for item in video_url:
                media = await Tools.get_media_data(item["download_url"], "mp4")
                media_group.append(InputMediaVideo(media=media))
                video += 1

        if not media_group:
            return await proses.edit(
                f"{em.gagal}**Failed to prepare any media for sending.**"
            )

        media_chunks = chunk_media_group(media_group)
        await proses.delete()

        for i, chunk in enumerate(media_chunks, 1):
            try:
                await client.send_media_group(chat_id=message.chat.id, media=chunk)
            except Exception as chunk_error:
                err += f"Error sending chunk {i}: {str(chunk_error)}\n"

        return await message.reply(
            f"{em.sukses}**Successfully sent {len(media_group)} media.**\n📸 Photos: `{foto}` | 🎥 Videos: `{video}`\n{err}"
        )

    except Exception as er:
        logger.error(f"twdl: {traceback.format_exc()}")
        return await proses.edit(f"{em.gagal}**ERROR:** {str(er)}")


async def pinterst_search(client, message):
    em = Emoji(client)
    await em.get()
    query = client.get_text(message)
    if not query:
        return await message.reply(
            f"{em.gagal}<b>Please give query\nExample: `{message.text.split()[0]} bh terbang` or `{message.text.split()[0]} garam & madu`</b>"
        )
    proses = await animate_proses(message, em.proses)
    try:
        url = "https://api.siputzx.my.id/api/s/pinterest"
        data_json = {"query": query, "type": ""}
        err = ""
        media_group = []
        foto, video = 0, 0
        response = await Tools.fetch.post(url, json=data_json)
        if response.status_code != 200:
            return await proses.edit(f"{em.gagal}**Please try again later!**")
        data = response.json()["data"]
        for v in data:
            if v["video_url"]:
                media_data = await Tools.get_media_data(v["video_url"], "mp4")
                media_group.append(InputMediaVideo(media=media_data))
                video += 1
            elif v["image_url"]:
                media_data = await Tools.get_media_data(v["image_url"], "jpg")
                media_group.append(InputMediaPhoto(media=media_data))
                foto += 1
        media_chunks = chunk_media_group(media_group)
        if not media_group:
            return await proses.edit(f"{em.gagal}**No media found.**")
        await proses.delete()
        for i, chunk in enumerate(media_chunks, 1):
            try:
                await client.send_media_group(chat_id=message.chat.id, media=chunk)
            except Exception as chunk_error:
                err += f"\n❌ Error sending chunk {i}: {str(chunk_error)}"
        return await message.reply(
            f"{em.sukses}**Successfully sent {len(media_group)} media\n📸 Photos: `{foto}` | 🎥 Videos: `{video}`**\n{err}"
        )
    except Exception as er:
        logger.error(f"ttdl: {traceback.format_exc()}")
        return await message.reply(f"{em.gagal}**An error occurred:** `{str(er)}`")


async def youtube_search(client, message):
    em = Emoji(client)
    await em.get()

    query = client.get_text(message)

    if not query:
        return await message.reply(
            f"{em.gagal}<b>Please give query\n"
            f"Example: `{message.text.split()[0]} bh terbang` "
            f"or `{message.text.split()[0]} garam & madu`</b>"
        )

    proses = await animate_proses(message, em.proses)

    def do_search():
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": True,
            "noplaylist": True,
            "cookiefile": cookies(),
            "extractor_args": {
                "youtubetab": {
                    "skip": ["authcheck"]
                }
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(
                f"ytsearch10:{query}",
                download=False,
            )

    try:
        result = await asyncio.to_thread(do_search)

    except Exception:
        logger.error(
            f"YouTube search error:\n{traceback.format_exc()}"
        )

        return await proses.edit(
            f"{em.gagal}**Please try again later!**"
        )

    entries = result.get("entries", []) if result else []

    if not entries:
        return await proses.edit(
            f"{em.gagal}**No results found!**"
        )

    data = []

    for item in entries:
        if not item:
            continue

        video_id = item.get("id")

        if not video_id:
            continue

        data.append(
            {
                "id": video_id,
                "title": item.get("title") or "Unknown Title",
                "url": (
                    item.get("webpage_url")
                    or f"https://www.youtube.com/watch?v={video_id}"
                ),
                "duration": item.get("duration"),
                "channel": (
                    item.get("channel")
                    or item.get("uploader")
                    or "Unknown"
                ),
                "views": item.get("view_count") or 0,
                "thumbnail": (
                    item.get("thumbnail")
                    or f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                ),
            }
        )

    if not data:
        return await proses.edit(
            f"{em.gagal}**No results found!**"
        )

    uniq = str(uuid4()).split("-")[0]

    state.set(
        uniq,
        "youtube_search",
        data,
    )

    as_video = (
        message.command[0].lower() == "vsong"
    )

    state.set(
        uniq,
        "as_video",
        as_video,
    )

    inline = await ButtonUtils.send_inline_bot_result(
        message,
        message.chat.id,
        bot.me.username,
        f"inline_youtube {uniq}",
    )

    state.set(
        uniq,
        "idm_ytsearch",
        id(message),
    )

    if inline:
        await proses.delete()
    else:
        return await proses.edit(
            f"{em.gagal}**ERROR Please contact developer.**"
        )
