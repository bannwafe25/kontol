# ===============================================================
#  Copyright (c) 2025 FR RASTA
# 
#  File ini adalah bagian dari proyek [NAVY USERBOT].
#  Dilarang menyalin, memodifikasi, atau mendistribusikan kode ini
#  tanpa izin tertulis dari pemilik.
# 
#  Untuk informasi lisensi dan hak cipta, silakan lihat file LICENSE.
# ===============================================================


import re
import random
import asyncio
from pyrogram.enums import ChatAction, ChatType
from pyrogram.errors import PeerIdInvalid, RPCError

from clients import bot
from helpers import Emoji, FITNAH_MESSAGES, ROAST_MESSAGES


ACTIVE_ROASTS = {}


async def roasting_cmd(client, message):
    em = Emoji(client)
    await em.get()

    args = message.text.split()[1:]
    target_user = None
    delay = 10  
    target_chat_id = message.chat.id
    target_arg = None
    
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if args:
            target_arg = args[0]
    elif args:
        if args[0].lstrip('-').isdigit():
            target_chat_id = int(args.pop(0))
            if args:
                target_arg = args[0]
        else:
            target_arg = args[0]
            
    if target_user is None and target_arg:
        await client.send_chat_action(target_chat_id, ChatAction.TYPING)
        try:
            target_user = await client.get_users(target_arg.replace("@", ""))
        except (PeerIdInvalid, ValueError):
            return await message.reply(f"{em.gagal}**Username tidak ditemukan atau salah.**")
        except RPCError:
            return await message.reply(f"{em.gagal}**Terjadi kesalahan saat mencari pengguna.**")
    elif target_user is None:
        if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            return await message.reply(f"{em.gagal}**Perintah ini hanya bisa digunakan di grup.**")
            
        await client.send_chat_action(target_chat_id, ChatAction.TYPING)
        try:
            members = [
                member.user async for member in client.get_chat_members(target_chat_id, limit=50)
                if not member.user.is_bot
            ]
            if not members:
                return await message.reply(f"{em.gagal}**Tidak ada member yang bisa dipilih di grup tersebut.**")
            target_user = random.choice(members)
        except RPCError:
            return await message.reply(f"{em.gagal}**Gagal mengambil anggota grup.**")
            
    delay_arg = args[-1] if args and args[-1].isdigit() else None
    if delay_arg:
        delay = int(delay_arg)

    if not target_user or target_user.is_bot:
        return await message.reply(f"{em.gagal}**Target tidak valid atau bot.**")

    roast_key = f"{target_chat_id}:{target_user.id}"
    if roast_key in ACTIVE_ROASTS:
        return await message.reply(f"{em.gagal}**Roasting sudah berjalan untuk user ini.**")

    mention = (
        f"@{target_user.username}"
        if target_user.username else
        f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
    )

    roasting_task = asyncio.create_task(
        _roast_loop(client, target_chat_id, target_user, mention, delay, roast_key)
    )
    ACTIVE_ROASTS[roast_key] = roasting_task

    await message.reply(
        f"{em.proses}**Roasting dimulai untuk {mention} di grup `{target_chat_id}`...**\n"
        f"⏱️ Delay: `{delay}` detik\n\n"
        f"Ketik `stoproasting` untuk menghentikan roasting di grup ini atau `stoproasting [ID grup]` untuk menghentikan dari jarak jauh.",
        disable_web_page_preview=True
    )

async def _roast_loop(client, chat_id, target_user, mention, delay, roast_key):
    try:
        while True:
            await client.send_chat_action(chat_id, ChatAction.TYPING)
            await asyncio.sleep(1)
            roast = random.choice(ROAST_MESSAGES).replace("@user", mention)
            await client.send_message(chat_id, f"🔥 {roast}", disable_web_page_preview=True)
            await asyncio.sleep(delay)
    except asyncio.CancelledError:
        pass
    finally:
        ACTIVE_ROASTS.pop(roast_key, None)

async def stop_roasting_cmd(client, message):
    em = Emoji(client)
    await em.get()

    args = message.text.split()[1:]
    target_chat_id = None
    
    if args and args[0].lstrip('-').isdigit():
        target_chat_id = int(args[0])
    else:
        if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            return await message.reply(f"{em.gagal}**Perintah ini hanya bisa digunakan di grup.**")
        target_chat_id = message.chat.id
    
    keys_to_cancel = [k for k in ACTIVE_ROASTS if k.startswith(f"{target_chat_id}:")]
    
    if not keys_to_cancel:
        return await message.reply(f"{em.gagal}**Tidak ada proses roasting yang sedang berjalan di grup tersebut.**")

    for key in keys_to_cancel:
        task = ACTIVE_ROASTS.get(key)
        if task:
            task.cancel()
    
    await message.reply(f"{em.sukses}**Semua proses roasting di grup `{target_chat_id}` berhasil dihentikan.**")



async def fitnah_cmd(client, message):
    em = Emoji(client)
    await em.get()

    chat = message.chat
    if chat.type != ChatType.SUPERGROUP and chat.type != ChatType.GROUP:
        return await message.reply(f"{em.gagal}**Perintah ini hanya bisa digunakan di grup.**")

    args = message.text.split(None, 1)[1:] if len(message.command) > 1 else []
    target_user = None

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user

    elif args:
        username = extract_username(args[0])
        if not username:
            return await message.reply(f"{em.gagal}**Format mention salah! Contoh:** `.fitnah @username`")
        try:
            target_user = await client.get_users(username)
        except Exception:
            return await message.reply(f"{em.gagal}**Username tidak ditemukan!**")

    else:
        members = []
        try:
            async for member in client.get_chat_members(chat.id, limit=100):
                if not member.user.is_bot:
                    members.append(member.user)
        except Exception:
            return await message.reply(f"{em.gagal}**Gagal mengambil anggota grup.**")
        
        if not members:
            return await message.reply(f"{em.gagal}**Tidak ada member yang bisa dipilih.**")
        target_user = random.choice(members)

    mention = (
        f"@{target_user.username}"
        if target_user.username else
        f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
    )

    fitnah = random.choice(FITNAH_MESSAGES).replace("@user", mention)
    await message.reply(f"🎭 {fitnah}", disable_web_page_preview=True)



RATE_IMAGE = "https://files.catbox.moe/18pdex.jpg"

FEEDBACK_TIPE = {
    "cocok": [
        (90, "Kalian kayak langit dan bintang — gak bisa dipisahkan! 🌌"),
        (85, "Bisa banget nih jadi pasangan sejati! 💑"),
        (75, "Cocok banget, tinggal nunggu restu! 💍"),
        (70, "Kalian bisa saling melengkapi. 🤝"),
        (60, "Lumayan cocok, asal gak banyak drama. 🎭"),
        (50, "Masih bisa diperjuangkan, semangat! 💪"),
        (40, "Cocok kalau mau belajar banyak hal. 📚"),
        (30, "Hubungan ini butuh banyak kompromi. 🔄"),
        (20, "Mungkin lebih baik temenan aja. 👥"),
        (10, "Bercanda, kalian gak cocok! 😜"),
        (0, "Mending mundur sebelum luka lebih dalam. 💔")
    ],
    "kegantengan": [
        (90, "Gantengnya udah level anime protagonist! 🌟"),
        (85, "Ganteng banget, bisa jadi model! 🧑‍🎤"),
        (80, "Ganteng banget, bikin orang senyum sendiri. 😁"),
        (75, "Ganteng natural, gak perlu filter. 📸"),
        (70, "Ganteng dengan sentuhan sempurna. ✨"),
        (60, "Masih ganteng, tapi coba perawatan dikit. 💅"),
        (50, "Ganteng kalau diliat lebih lama. 👀"),
        (40, "Masih oke, asal percaya diri. 💃"),
        (30, "Ganteng, tapi lebih ke kepribadian. 🧠"),
        (20, "Kurang banget, tapi tetep jadi diri sendiri. ✌️"),
        (0, "Gak masalah, inner beauty penting juga. ❤️")
    ],
    "kecantikan": [
        (90, "Secantik senja di pantai — bikin tenang. 🌅"),
        (85, "Cantiknya kayak artis, bikin melongo! 🎬"),
        (80, "Cantik banget, bikin gagal fokus! 😍"),
        (75, "Cantik kalem, bikin adem. 🌿"),
        (70, "Cantiknya natural, tetap keren. 🦋"),
        (60, "Cantik dengan sentuhan yang pas. 💖"),
        (50, "Cantik, cuma butuh lebih banyak percaya diri. 🪞"),
        (40, "Cantik, tapi masih bisa ditingkatkan. 🌸"),
        (30, "Gak masalah, yang penting percaya diri. 💃"),
        (20, "Cantik itu relatif, kamu unik. 🌟"),
        (0, "Gak cantik? Kamu luar biasa dengan caramu sendiri. 💪")
    ],
    "kepintaran": [
        (90, "Pintarnya udah bisa jadi dosen! 🎓"),
        (85, "Cerdas banget, bisa ngajarin orang lain! 📚"),
        (80, "Pinter banget, otak encer! 🧠"),
        (75, "Pinter, tapi jangan lupa istirahat ya. 🛋️"),
        (70, "Kamu pinter banget, tapi kadang suka lupa. 🤔"),
        (60, "Pintar, tapi masih bisa lebih fokus. 👓"),
        (50, "Ada potensi, terus belajar ya! 📖"),
        (40, "Kadang pinter, kadang lupa. 📝"),
        (30, "Masih bisa dikembangkan. 🚀"),
        (20, "Masih butuh banyak latihan. 💼"),
        (0, "Kita semua pernah bodoh sebelum pintar. 😅")
    ],
    "kebadboyan": [
        (90, "Badboy parah, hati-hati semua cewek! 😈"),
        (85, "Kamu punya aura badboy yang luar biasa. 😎"),
        (80, "Badboy banget, tapi tetep menarik. 🔥"),
        (75, "Biarpun badboy, ada sisi lembutnya. 💖"),
        (70, "Setengah badboy, setengah sweetboy. 💕"),
        (60, "Badboy dikit-dikit, tapi tetep lucu. 😂"),
        (50, "Lebih ke nice guy sebenernya. 😊"),
        (40, "Badboy banget sih, tapi masih bisa berubah. ✨"),
        (30, "Kadang badboy, kadang softboy. 🌸"),
        (20, "Badboy, tapi cuma di luar. 🖤"),
        (0, "Too pure to be bad. ✌️")
    ],
    "kehaluan": [
        (90, "Kalian udah level halu yang gak terbendung! 🚀"),
        (85, "Kalian berdua pasti bakal jadi pasangan dalam dunia halu! 💫"),
        (80, "Halu banget, tapi tetep menyenangkan. 🤪"),
        (75, "Sering banget dibawa halu, tapi tetap keren! 😜"),
        (70, "Halu dikit-dikit, tapi masih realistis. ✌️"),
        (60, "Kadang halu, kadang ngelantur. 💬"),
        (50, "Halu itu wajar, asal jangan kebablasan. 🚫"),
        (40, "Halu, tapi jangan kebanyakan. 🤡"),
        (30, "Halu dikit-dikit, gak masalah. 😊"),
        (20, "Halu itu hak setiap orang, tapi jangan sampai kebablasan. 🛑"),
        (0, "Halu itu baik, tapi jangan terlalu jauh. 😬")
    ],
    "kesetiaan": [
        (90, "Setia banget, udah kayak anjing peliharaan! 🐶"),
        (85, "Setia, gak mudah tergoda sama yang lain. ❤️"),
        (80, "Setia banget, jantung cuma untuk satu orang. 💘"),
        (75, "Setia, tapi jangan terlalu terjebak. 🕊️"),
        (70, "Masih setia, tapi jangan suka main hati. 💔"),
        (60, "Setia itu butuh usaha, jangan asal janji. 📅"),
        (50, "Setia, tapi kadang ragu. 🤔"),
        (40, "Setia, tapi ada sedikit keraguan. ⚖️"),
        (30, "Kesetiaan itu masih bisa ditingkatkan. 🔄"),
        (20, "Setia itu tidak selalu mudah. 🛑"),
        (0, "Setia itu proses, jangan cuma janji di mulut. 💬")
    ],
    "kebucinan": [
        (90, "Kalian udah kebucin level dewa! 🤩"),
        (85, "Bucin banget, bahkan bisa jadi inspirasi. 💖"),
        (80, "Bucin, tapi masih bisa kontrol diri. 🧘‍♂️"),
        (75, "Sering bucin, tapi jangan kebablasan. 🛑"),
        (70, "Bucin dikit-dikit, gak apa-apa. 😊"),
        (60, "Kadang bucin, kadang realistis. 🤨"),
        (50, "Bucin itu wajar, asal gak mengganggu. 🕊️"),
        (40, "Bucin sih, tapi perlu batas. ⚖️"),
        (30, "Masih butuh banyak belajar soal cinta. ❤️"),
        (20, "Bucin itu gak selamanya buruk. 💪"),
        (0, "Bucin itu terlalu berlebihan. 😤")
    ],
    "kebodohan": [
        (90, "Kebodohannya udah sampai level expert! 🤪"),
        (85, "Kadang bodoh, tapi tetep lucu. 😜"),
        (80, "Bodoh, tapi tetap menghibur! 😂"),
        (75, "Kadang bodoh, kadang cerdas. 🧠"),
        (70, "Bodoh dikit-dikit, tapi gak masalah. 😅"),
        (60, "Bodoh itu bisa jadi lucu. 🤭"),
        (50, "Bodoh, tapi bukan masalah. 😇"),
        (40, "Bodoh itu bisa jadi pembelajaran. 📖"),
        (30, "Bodoh itu wajar, asal sadar diri. 💡"),
        (20, "Bodoh itu tidak selalu buruk. 😊"),
        (0, "Semua orang pernah bodoh, yang penting belajar! 📚")
    ],
    "keuwuan": [
        (90, "Keuwuanmu gak terbantahkan, gemes banget! 😍"),
        (85, "Keuwuan kamu level dewa, gak ada yang bisa ngalahin! 😘"),
        (80, "Keuwuan kamu ngalahin bintang film! 🎥"),
        (75, "Keuwuan kamu gak bisa diungkapkan dengan kata-kata. 😇"),
        (70, "Keuwuan kamu masih wajar, tetap imut. 🥰"),
        (60, "Keuwuan kamu unik, beda dari yang lain. 💖"),
        (50, "Keuwuan dikit-dikit, tapi masih oke. 😊"),
        (40, "Keuwuan kamu ada, tapi belum cukup untuk jadi perhatian. 👀"),
        (30, "Keuwuan kamu lucu, tapi perlu lebih banyak pengembangan. 🤭"),
        (20, "Keuwuan itu relatif, tapi kamu unik. 💞"),
        (0, "Keuwuan itu tidak selalu terlihat. 💫")
    ]
}

def make_love_bar(progress: int, total: int = 100, length: int = 10) -> str:
    love_count = int((progress / total) * length)
    bar = "❤️" * love_count + "♡" * (length - love_count)
    return f"[{bar}]"


async def rate_cmd(client, message):
    em = Emoji(client)
    await em.get()

    args = message.text.split(None, 2)[1:]
    if not args and not message.reply_to_message:
        return await message.reply(
            f"{em.gagal}**Format salah!**\nContoh: `.rate cocok seberapa cocok aku dan dia?`\n\nJenis yang tersedia: cocok, kegantengan, kecantikan, kepintaran, kebadboyan, kehaluan, kesetiaan, kebucinan, kebodohan, keuwuan."
        )

    tipe = args[0].lower() if args else None
    pertanyaan = " ".join(args[1:]) if len(args) > 1 else None

    if tipe not in FEEDBACK_TIPE:
        return await message.reply(f"{em.gagal}**Jenis rate `{tipe}` tidak tersedia!**")

    if not message.reply_to_message and not pertanyaan:
        return await message.reply(
            f"{em.gagal} Kamu harus membalas pesan seseorang atau menuliskan target setelah jenis rate.\n\nContoh: `.rate cocok @username` atau balas pesan lalu ketik `.rate cocok`"
    )
    
    user = None
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        if user.username:
            target = f"@{user.username}"
        else:
            target = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    else:
        target = pertanyaan or "Tidak diketahui"

    rating = random.randint(0, 100)
    feedback = next((f for batas, f in FEEDBACK_TIPE[tipe] if rating >= batas), "Hasil tidak ditemukan.")

    msg = await message.reply(f"{em.proses}**Memberi rate...**")
    for i in range(0, rating + 1, 10 if rating > 20 else 5):
        bar = make_love_bar(i)
        await msg.edit(f"{em.proses}**Rating...:\n{bar} {i}%**")
        await asyncio.sleep(0.5)
                
    caption = f"""
<blockquote>📌 <b>Jenis Rating:</b> <code>{tipe}</code>
👤 <b>Target:</b> {target}
📊 <b>Hasil:</b> <code>{rating}%</code>

💬 <i>{feedback}</i>

🤖 <b>Rate by</b> <i>{bot.me.username}</i></blockquote>"""

    if pertanyaan:
        caption += f"\n\n<blockquote><b>Pertanyaan:</b> <i>{pertanyaan}</i></blockquote>"

    photo = RATE_IMAGE  
    try:
        if user:
            async for p in client.get_chat_photos(user.id, limit=1):
                photo = p.file_id
                break
    except Exception as e:
        print(f"Gagal ambil foto profil: {e}")
        photo = RATE_IMAGE

    await msg.delete()  
    await client.send_photo(
        chat_id=message.chat.id,
        photo=photo,
        caption=caption,
        reply_to_message_id=message.id
    )



HOT = "https://graph.org/file/745ba3ff07c1270958588.mp4"
HORNY = "https://graph.org/file/eaa834a1cbfad29bd1fe4.mp4"
SEMXY = "https://graph.org/file/58da22eb737af2f8963e6.mp4"
LESBIAN = "https://graph.org/file/ff258085cf31f5385db8a.mp4"
GAY = "https://graph.org/file/850290f1f974c5421ce54.mp4"
BIGBALL = "https://i.gifer.com/8ZUg.gif"
LANGD = "https://telegra.ph/file/423414459345bf18310f5.gif"
CUTIE = "https://graph.org/file/24375c6e54609c0e4621c.mp4"


def get_user_info(message):
    if message.reply_to_message:
        user = message.reply_to_message.from_user
    else:
        user = message.from_user
    return user.id, user.first_name


async def cute_cmd(client, message):
    em = Emoji(client)
    await em.get()
    proses_ = await em.get_costum_text()

    user_id, user_name = get_user_info(message)
    mention = f"[{user_name}](tg://user?id={user_id})"
    percentage = random.randint(1, 100)
    caption = f"**🍑 {mention} {percentage}% ᴄᴜᴛɪᴇ ʙᴀʙʏ🥀**"

    prs = await message.reply_text(f"{em.proses}**{proses_[4]}**")
    await client.send_document(
        chat_id=message.chat.id,
        document=CUTIE,
        caption=caption,
        reply_to_message_id=message.reply_to_message.id if message.reply_to_message else None,
    )
    await prs.delete()


async def horny_cmd(client, message):
    em = Emoji(client)
    await em.get()
    proses_ = await em.get_costum_text()

    user_id, user_name = get_user_info(message)
    mention = f"[{user_name}](tg://user?id={user_id})"
    percentage = random.randint(1, 100)
    caption = f"🔥 **{mention} ɪꜱ {percentage}% ʜᴏʀɴʏ!**"

    prs = await message.reply_text(f"{em.proses}**{proses_[4]}**")
    await client.send_document(
        chat_id=message.chat.id,
        document=HORNY,
        caption=caption,
        reply_to_message_id=message.reply_to_message.id if message.reply_to_message else None,
    )
    await prs.delete()


async def hot_cmd(client, message):
    em = Emoji(client)
    await em.get()
    proses_ = await em.get_costum_text()

    user_id, user_name = get_user_info(message)
    mention = f"[{user_name}](tg://user?id={user_id})"
    percentage = random.randint(1, 100)
    caption = f"🔥 **{mention} ɪꜱ {percentage}% ʜᴏᴛ!**"

    prs = await message.reply_text(f"{em.proses}**{proses_[4]}**")
    await client.send_document(
        chat_id=message.chat.id,
        document=HOT,
        caption=caption,
        reply_to_message_id=message.reply_to_message.id if message.reply_to_message else None,
    )
    await prs.delete()


async def sexy_cmd(client, message):
    em = Emoji(client)
    await em.get()
    proses_ = await em.get_costum_text()

    user_id, user_name = get_user_info(message)
    mention = f"[{user_name}](tg://user?id={user_id})"
    percentage = random.randint(1, 100)
    caption = f"🔥 **{mention} ɪꜱ {percentage}% ꜱᴇxʏ!**"

    prs = await message.reply_text(f"{em.proses}**{proses_[4]}**")
    await client.send_document(
        chat_id=message.chat.id,
        document=SEMXY,
        caption=caption,
        reply_to_message_id=message.reply_to_message.id if message.reply_to_message else None,
    )
    await prs.delete()


async def gay_cmd(client, message):
    em = Emoji(client)
    await em.get()
    proses_ = await em.get_costum_text()

    user_id, user_name = get_user_info(message)
    mention = f"[{user_name}](tg://user?id={user_id})"
    percentage = random.randint(1, 100)
    caption = f"🍷 **{mention} ɪꜱ {percentage}% ɢᴀʏ!**"

    prs = await message.reply_text(f"{em.proses}**{proses_[4]}**")
    await client.send_document(
        chat_id=message.chat.id,
        document=GAY,
        caption=caption,
        reply_to_message_id=message.reply_to_message.id if message.reply_to_message else None,
    )
    await prs.delete()


async def lesby_cmd(client, message):
    em = Emoji(client)
    await em.get()
    proses_ = await em.get_costum_text()

    user_id, user_name = get_user_info(message)
    mention = f"[{user_name}](tg://user?id={user_id})"
    percentage = random.randint(1, 100)
    caption = f"💜 **{mention} ɪꜱ {percentage}% ʟᴇꜱʙɪᴀɴ!**"

    prs = await message.reply_text(f"{em.proses}**{proses_[4]}**")
    await client.send_document(
        chat_id=message.chat.id,
        document=LESBIAN,
        caption=caption,
        reply_to_message_id=message.reply_to_message.id if message.reply_to_message else None,
    )
    await prs.delete()


async def boob_cmd(client, message):
    em = Emoji(client)
    await em.get()
    proses_ = await em.get_costum_text()

    user_id, user_name = get_user_info(message)
    mention = f"[{user_name}](tg://user?id={user_id})"
    percentage = random.randint(1, 100)
    caption = f"🍒 {mention}ꜱ ʙᴏᴏʙꜱ ꜱɪᴢᴇ ɪᴢ {percentage}!"

    prs = await message.reply_text(f"{em.proses}**{proses_[4]}**")
    await client.send_document(
        chat_id=message.chat.id,
        document=BIGBALL,
        caption=caption,
        reply_to_message_id=message.reply_to_message.id if message.reply_to_message else None,
    )
    await prs.delete()


async def cock_cmd(client, message):
    em = Emoji(client)
    await em.get()
    proses_ = await em.get_costum_text()

    user_id, user_name = get_user_info(message)
    mention = f"[{user_name}](tg://user?id={user_id})"
    percentage = random.randint(1, 100)
    caption = f"🍆 **{mention} ᴄᴏᴄᴋ ꜱɪᴢᴇ ɪᴢ {percentage}ᴄᴍ**"

    prs = await message.reply_text(f"{em.proses}**{proses_[4]}**")
    await client.send_document(
        chat_id=message.chat.id,
        document=LANGD,
        caption=caption,
        reply_to_message_id=message.reply_to_message.id if message.reply_to_message else None,
    )
    await prs.delete()
