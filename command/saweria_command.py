import asyncio
import os
import traceback
from datetime import datetime
from uuid import uuid4

import config
from clients import bot
from database import dB
from helpers import Emoji, Message, Saweria, Tools, animate_proses

transactions = {}


async def saweria_cmd(client, message):
    em = Emoji(client)
    await em.get()

    proses = await animate_proses(message, em.proses)
    args = ["login", "qris"]
    command = message.command

    if len(command) < 2 or command[1] not in args:
        return await proses.edit(
            f"{em.gagal}**Please give me valid query: `login`, `qris`**"
        )
    if command[1] == "login":
        if not message.reply_to_message:
            return await proses.edit(
                f"{em.gagal}**Usage:** `{message.text.split()[0]} login (reply to message with format: email@.com username)`"
            )
        email, username = Tools.parse_text(message.reply_to_message)
        saweria_userid = await Saweria.get_user_id(username)
        if saweria_userid is None:
            try:
                maelyn_url = "https://api.maelyn.eu/api/payment/saweria/check/account"
                headers = {
                    "x-maelyn-auth": config.API_MAELYN,
                }
                payload = {"username": username}
                response = await Tools.fetch.get(
                    maelyn_url, headers, payload
                )
                if response.status_code != 200:
                    return await proses.edit(f"{em.gagal}**Please try again.**")
                data_response = response.json()
                saweria_userid = data_response["result"].get("userId")
                print(f"Saweria userid: {saweria_userid}")
                if not saweria_userid:
                    return await proses.edit(f"{em.gagal}**Please try again.**")
            except Exception as e:
                print(f"Error: {traceback.format_exc()}")
                return await proses.edit(f"ERROR: {str(e)}")
        data = {
            "saweria_userid": saweria_userid,
            "saweria_email": email,
            "saweria_username": username,
        }
        await dB.set_var(client.me.id, "SAWERIA_ACCOUNT", data)
        return await proses.edit(
            f"{em.sukses}**Successfully logged in to Saweria! Your userId: `{saweria_userid}`**"
        )
    elif command[1] == "qris":
        info = await dB.get_var(client.me.id, "SAWERIA_ACCOUNT")
        if not info:
            return await proses.edit(
                f"{em.gagal}**Please login first using `login` command.**"
            )
        if len(command) < 4:
            return await proses.edit(
                f"{em.gagal}**Usage:** `{message.text.split()[0]} qris 5000 beli kopi`"
            )
        try:
            amount = int(command[2])
        except ValueError:
            return await proses.edit(f"{em.gagal}**Amount must be a number!**")

        desc = " ".join(command[3:])
        uniq = f"{str(uuid4())}"
        saweria_email = info["saweria_email"]
        saweria_userid = info["saweria_userid"]
        url = "https://api.maelyn.eu/api/payment/saweria/create/transaction"
        headers = {
            "Content-Type": "application/json",
            "x-maelyn-auth": config.API_MAELYN,
        }
        payload = {
            "user_id": saweria_userid,
            "amount": amount,
            "name": bot.fullname,
            "email": saweria_email,
            "msg": desc,
        }
        r = await Tools.fetch.post(url, headers=headers, json=payload)
        if r.status_code != 200:
            return await proses.edit(f"**Please try again later...**")
        sdata = r.json()["payment"]
        if not data:
            return await proses.edit(f"**Please try again later...**")
        hasil_amount = hasil_result["amount"]
        hasil_qr = hasil_result["payment_url"]
        hasil_idpayment = hasil_result["id"]
        qris_path = f"qris_{client.me.id}_{hasil_amount}.png"
        Tools.create_qrscan(hasil_qr, str(hasil_amount), qris_path)
        sent = await message.reply_photo(
            qris_path,
            caption=(
                f"""
<b>📃「 Waiting Payment 」</b>

<blockquote expandable><b><i>{em.profil}Item: `{desc}`
{em.net}Price: `{Message.format_rupiah(amount)}`
{em.speed}Total Payment: `{Message.format_rupiah(hasil_amount)}`

Scan QRIS above to pay.</i></b></blockquote>

<blockquote>© Auto Payment @{bot.me.username}</blockquote>
"""
            ),
        )
        if os.path.exists(qris_path):
            os.remove(qris_path)
        await proses.delete()
        transactions[uniq.split("-")[0]] = {
            "expire_time": hasil_expired,
            "message_id": sent.id,
            "done": False,
        }
        while True:
            await asyncio.sleep(1)
            trans = transactions.get(uniq.split("-")[0])
            if not trans or trans["done"]:
                break
            if datetime.now() > trans["expire_time"]:
                if not trans["done"]:
                    await client.send_message(
                        message.chat.id,
                        f"{em.gagal}<b><i>Payment canceled due to timeout.</i></b>",
                    )
                    await client.delete_messages(
                        chat_id=message.chat.id,
                        message_ids=trans["message_id"],
                    )
                    del transactions[uniq.split("-")[0]]
                break
            try:
                url = "https://api.maelyn.eu/api/payment/saweria/check/transaction"
                headers = {
                    "x-maelyn-auth": config.API_MAELYN,
                }
                payload = {"user_id": saweria_userid, "payment_id": hasil_idpayment}
                response = await Tools.fetch.post(url, headers=headers, json=payload)
                is_paid = response.json().get("payment")
                if is_paid and not trans["done"]:
                    if is_paid["status"] == "PAID":
                        trans["done"] = True
                        await message.reply(
                            f"""
<blockquote><b><i>{em.sukses}Payment received!

{em.profil}Item: `{desc}`
{em.net}Price: `{Message.format_rupiah(amount)}`
{em.speed}Total Paid: `{Message.format_rupiah(hasil_amount)}`</i></b></blockquote>
"""
                        )
                        await client.delete_messages(
                            chat_id=message.chat.id,
                            message_ids=transactions[uniq.split("-")[0]]["message_id"],
                        )
                        del transactions[uniq.split("-")[0]]
                        return

            except Exception as e:
                print(f"Error checking payment: {e}")
                if uniq.split("-")[0] in transactions:
                    del transactions[uniq.split("-")[0]]
                await message.reply(f"{em.gagal}**Error occurred:** `{str(e)}`")
                break
