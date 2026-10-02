import os
import traceback

from pyrogram.types import Message

from helpers import CMD, Emoji
from logs import logger

__MODULES__ = "Curi"
__CATEGORY__ = "Tools"
__HELP__ = """<blockquote>Command Help **spy**</blockquote>

<blockquote expandable>    <u>**Copy/Forward message to saved messages**</u>
        `{0}spy` (reply to message)</blockquote>

<b>   {1}</b>
"""
IS_PRO = True

@CMD.UBOT("spy")
async def _(client, message):
    await handle_curi(client, message)


async def handle_curi(client, message: Message):
    """Handle copying messages to saved messages"""
    emo = Emoji(client)
    await emo.get()
    
    # Check if replying to a message
    replied_msg = message.reply_to_message
    if not replied_msg:
        return await message.reply(
            f"<blockquote>{emo.gagal} <b>Please reply to a message to copy it!</b></blockquote>"
        )
    
    try:
        # Delete command message immediately
        await message.delete()
        
        await copy_message_by_type(client, replied_msg, emo)
        
        # Silent confirmation to saved messages
       # await client.send_message(
       #     "me", 
        #    f"<blockquote>{emo.sukses} <b>Message copied successfully!</b></blockquote>"
      #  )
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error in handle_curi: {e} {traceback.format_exc()}")
        await message.edit(
            f"<blockquote>{emo.gagal} <b>Error:</b>\n<code>{error_message}</code></blockquote>"
        )


async def copy_message_by_type(client, replied_msg: Message, emo):
    """Copy message based on its type"""
    caption = replied_msg.caption or None
    
    try:
        # Handle text messages
        if replied_msg.text:
            await replied_msg.copy("me")
            
        # Handle photos
        elif replied_msg.photo:
            file_path = await client.download_media(replied_msg)
            await client.send_photo("me", file_path, caption=caption)
            cleanup_file(file_path)
            
        # Handle videos
        elif replied_msg.video:
            file_path = await client.download_media(replied_msg)
            await client.send_video("me", file_path, caption=caption)
            cleanup_file(file_path)
            
        # Handle audio files
        elif replied_msg.audio:
            file_path = await client.download_media(replied_msg)
            await client.send_audio("me", file_path, caption=caption)
            cleanup_file(file_path)
            
        # Handle voice messages
        elif replied_msg.voice:
            file_path = await client.download_media(replied_msg)
            await client.send_voice("me", file_path, caption=caption)
            cleanup_file(file_path)
            
        # Handle documents
        elif replied_msg.document:
            file_path = await client.download_media(replied_msg)
            await client.send_document("me", file_path, caption=caption)
            cleanup_file(file_path)
            
        # Handle stickers
        elif replied_msg.sticker:
            await replied_msg.copy("me")
            
        # Handle animations (GIFs)
        elif replied_msg.animation:
            file_path = await client.download_media(replied_msg)
            await client.send_animation("me", file_path, caption=caption)
            cleanup_file(file_path)
            
        # Handle video notes (circle videos)
        elif replied_msg.video_note:
            file_path = await client.download_media(replied_msg)
            await client.send_video_note("me", file_path)
            cleanup_file(file_path)
            
        else:
            # For unsupported media types, try to copy directly
            await replied_msg.copy("me")
            
    except Exception as e:
        logger.error(f"Error copying message: {e}")
        raise e


def cleanup_file(file_path: str):
    """Clean up downloaded files"""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning up file {file_path}: {e}")


async def download_and_send_media(client, replied_msg: Message, send_method, caption=None):
    """Generic function to download and send media"""
    try:
        file_path = await client.download_media(replied_msg)
        if caption:
            await send_method("me", file_path, caption=caption)
        else:
            await send_method("me", file_path)
        cleanup_file(file_path)
    except Exception as e:
        logger.error(f"Error in download_and_send_media: {e}")
        raise e
