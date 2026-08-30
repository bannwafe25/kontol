import asyncio
import shlex
import subprocess
from typing import Optional

from pyrogram import Client, enums, errors, raw

from database import dB

list_error = []


class BaseClient(Client):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def extract_type_and_text(self, message):
        args = message.text.split(None, 2)
        if len(args) < 2:
            return None, None

        type = args[1]
        msg = (
            message.reply_to_message.text
            if message.reply_to_message
            else args[2] if len(args) > 2 else None
        )
        return type, msg

    async def get_privileges(self, chat_id: int, user_id: int):
        member = await self.get_chat_member(chat_id, user_id)
        privileges = member.privileges
        return privileges

    async def parse_topic(self, chat_id: int):
        data_forum = []
        title = (await self.get_chat(chat_id)).title
        async for topic in self.get_forum_topics(chat_id):
            data_forum.append({"id": topic.id, "title": topic.title})
        return title, data_forum

    async def get_call(self, chat_id: int) -> Optional[raw.types.InputGroupCall]:
        try:
            chat = await self.resolve_peer(chat_id)
        except (errors.PeerIdInvalid, errors.ChannelInvalid):
            return None

        if isinstance(chat, raw.types.InputPeerChannel):
            full_chat = await self.invoke(
                raw.functions.channels.GetFullChannel(
                    channel=raw.types.InputChannel(
                        channel_id=chat.channel_id, access_hash=chat.access_hash
                    )
                )
            )
        else:
            full_chat = await self.invoke(
                raw.functions.messages.GetFullChat(chat_id=chat_id)
            )

        input_call = full_chat.full_chat.call

        if input_call is not None:
            call_details = await self.invoke(
                raw.functions.phone.GetGroupCall(call=input_call, limit=-1)
            )
            call = call_details.call

            if call is not None and call.schedule_date is not None:
                return None

            return call

        return None

    async def admin_list(self, message):
        return [
            member.user.id
            async for member in message._client.get_chat_members(
                message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS
            )
        ]

    async def get_chat_id(self, query):
        chat_types = {
            "global": [
                enums.ChatType.CHANNEL,
                enums.ChatType.GROUP,
                enums.ChatType.SUPERGROUP,
            ],
            "all": [
                enums.ChatType.GROUP,
                enums.ChatType.SUPERGROUP,
                enums.ChatType.PRIVATE,
            ],
            "group": [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP],
            "bot": [enums.ChatType.BOT],
            "usbot": [enums.ChatType.PRIVATE, enums.ChatType.BOT],
            "private": [enums.ChatType.PRIVATE],
            "channel": [enums.ChatType.CHANNEL],
        }

        if query not in chat_types:
            return []

        valid_chat_types = chat_types[query]
        chat_ids = []

        try:
            async for dialog in self.get_dialogs():
                try:
                    chat = dialog.chat
                    if chat and chat.type in valid_chat_types:
                        chat_ids.append(chat.id)
                except Exception:
                    continue
        except Exception:
            pass

        return chat_ids

    def new_arg(self, message):
        if message.reply_to_message and len(message.command) < 3:
            msg = message.reply_to_message.text or message.reply_to_message.caption
            if not msg:
                return ""
            msg = msg.encode().decode("UTF-8")
            msg = msg.replace(" ", "", 2) if msg[2] == " " else msg
            return msg
        elif len(message.command) > 2:
            return " ".join(message.command[2:])
        else:
            return ""

    def extract_type_and_msg(self, message, is_reply_text=False):
        args = message.text.split(None, 2)

        if len(args) < 2:
            return None, None

        type = args[1]

        if is_reply_text:
            msg = (
                message.reply_to_message.text
                if message.reply_to_message
                else args[2] if len(args) > 2 else None
            )
        else:
            msg = (
                message.reply_to_message
                if message.reply_to_message
                else args[2] if len(args) > 2 else None
            )

        return type, msg

    async def get_translate(self):
        data = await dB.get_var(self.me.id, "_translate")
        if data:
            return data
        return "id"

    def get_message(self, message):
        if message.reply_to_message:
            return message.reply_to_message
        elif len(message.command) > 1:
            return " ".join(message.command[1:])
        return ""

    def get_name(self, message):
        if message.reply_to_message:
            if message.reply_to_message.sender_chat:
                return None
            first_name = message.reply_to_message.from_user.first_name or ""
            last_name = message.reply_to_message.from_user.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
            return full_name if full_name else None
        else:
            input_text = message.text.split(None, 1)
            if len(input_text) <= 1:
                first_name = message.from_user.first_name or ""
                last_name = message.from_user.last_name or ""
                full_name = f"{first_name} {last_name}".strip()
                return full_name if full_name else None
            return input_text[1].strip()

    def get_arg(self, message):
        if message.reply_to_message and len(message.command) < 2:
            msg = message.reply_to_message.text or message.reply_to_message.caption
            if not msg:
                return ""
            msg = msg.encode().decode("UTF-8")
            msg = msg.replace(" ", "", 1) if msg[1] == " " else msg
            return msg
        elif len(message.command) > 1:
            return " ".join(message.command[1:])
        else:
            return ""

    def get_text(self, message):
        if message.reply_to_message:
            if len(message.command) < 2:
                text = (
                    message.reply_to_message.text
                    or message.reply_to_message.caption
                    or message.text.split(None, 1)[1]
                )
            else:
                text = (
                    (
                        message.reply_to_message.text
                        or message.reply_to_message.caption
                        or ""
                    )
                    + "\n\n"
                    + message.text.split(None, 1)[1]
                )
        else:
            if len(message.command) < 2:
                text = ""
            else:
                text = message.text.split(None, 1)[1]
        return text

    async def run_cmd(self, cmd):
        args = shlex.split(cmd)
        try:
            process = await asyncio.create_subprocess_exec(
                *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return (
                stdout.decode("utf-8", "replace").strip(),
                stderr.decode("utf-8", "replace").strip(),
                process.returncode,
                process.pid,
            )
        except NotImplementedError:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
            stdout, stderr = process.communicate()
            return (
                stdout.decode("utf-8", "replace").strip(),
                stderr.decode("utf-8", "replace").strip(),
                process.returncode,
                process.pid,
            )
            
    async def extract_userid(self, message, text):
        def is_int(text):
            try:
                int(text)
            except ValueError:
                return False
            return True

        text = text.strip()

        if is_int(text):
            return int(text)

        try:
            entities = message.entities
            app = message._client
            entity = entities[1 if message.text.startswith("/") else 0]
            if entity.type == enums.MessageEntityType.MENTION:
                try:
                    return (await app.get_users(text)).id
                except (errors.UsernameNotOccupied, errors.UsernameInvalid):
                    return None
            if entity.type == enums.MessageEntityType.TEXT_MENTION:
                return entity.user.id
        except (AttributeError, IndexError, ValueError, TypeError):
            return None
                    

    async def extract_user_and_reason(self, message, sender_chat=False):
        args = message.text.strip().split()
        text = message.text
        user = None
        reason = None
        if message.reply_to_message:
            reply = message.reply_to_message
            if not reply.from_user:
                if (
                    reply.sender_chat
                    and reply.sender_chat != message.chat.id
                    and sender_chat
                ):
                    id_ = reply.sender_chat.id
                else:
                    return None, None
            else:
                id_ = reply.from_user.id

            if len(args) < 2:
                reason = None
            else:
                reason = text.split(None, 1)[1]
            return id_, reason

        if len(args) == 2:
            user = text.split(None, 1)[1]
            return await self.extract_userid(message, user), None

        if len(args) > 2:
            user, reason = text.split(None, 2)[1:]
            return await self.extract_userid(message, user), reason

        return user, reason

    async def extract_user(self, message):
        return (await self.extract_user_and_reason(message))[0]
