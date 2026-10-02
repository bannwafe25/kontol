import asyncio

from config import DEVS
from helpers import Message

async def alfabet_cmd(client, message):
    if message.reply_to_message and message.reply_to_message.from_user.id in DEVS:
        return await message.reply("**AKUN LO MO ILANG BANGSAT??**")
    command = message.command[0]
    if command == "a":
        await message.reply(
            "**ANAK KONTOL, MUKA KEK JEMBUT MASIH MAEN TELE ?**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "b":
        await message.reply(
            "**BERISIK BET JABLAY TELE**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "c":
        await message.reply(
            "**CALL CALL MULU BANGSAT**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "d":
        await message.reply(
            "**DONGONYA AMPE UBUN UBUN JIRR**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "e":
        await message.reply(
            "**ETDAH BOCAH CAPER BET, MENDING LU NGADUK SEMEN SONO!!**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "f":
        await message.reply(
            "**FANTAT LOE BURIK YA ? SOALNYA MUKA LU KEREMIAN!!**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "g":
        await message.reply(
            "**GOBLOK DIPIARA!! MEMEG NOH LOE PIARA BIAR BANYAK ANAK!!**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "h":
        await message.reply(
            "**HAHAHAHA KOK DIEM ? BINGUNG YA LU BACOT APAAN**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "i":
        await message.reply(
            "**IDIH NAJIS BET PESAN GW DIREP AMA BOCAH KEK LOE**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "j":
        await message.reply(
            "**JADI ORANG GAUSAH BELAGU**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "k":
        await message.reply(
            "**KALO TYPING YANG BENER DEK!! POTRET BOCAH HASIL KONDOM BOCOR YA BEGITU**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "l":
        await message.reply(
            "**LEMES BGT BLM DI KASIH PAP IMUP**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "m":
        await message.reply(
            "**MUKA LU NOH KEK BIJI SAWITT**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "n":
        await message.reply(
            "**NETE DULU SONO BARU NGEBACOT, LAA BOCAH NGETIK KEK ABIS NGELEM**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "o":
        await message.reply(
            "**OPALE MONYE**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "p":
        await message.reply(
            "**PADUKA YANG MULIA ZP**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "r":
        await message.reply(
            "**RAME AMAT YA, KEREN KALI MAH BEGITU? LAA BOCAH BARU LAHIR KEMAREN BANYAK GAYA. TONG TONG!! EMA LO NYESEL KEK NYA LAHIRIN MAKHLUK KE LU!!**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "s":
        await message.reply(
            "**SUARA LU GAUSA DI IMUT IMUTIN BANGSAT MERINDING GUA JING**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "t":
        await message.reply(
            "**TEPOS GAUSAH BELAGU PLERRR**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "u":
        await message.reply(
            "**USU KANDA WELL🤙**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "v":
        await message.reply(
            "**TT NYA DI KONDISIKAN KAK**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "w":
        await message.reply(
            "**OHHH INI ORANG NYA? YANG SUKA NYOLONG ? PENGANGGURAN ? MAKAN DUIT HARAM ? NGENTOT TIAP HARI ? BAHAHAHHA PANTES BET MUKA-MUKA BOCAH PASSOBIS**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "x":
        await message.reply(
            "**DIEM MEMEG, MUKA JERAWATN BANYAK BACOT LU!!**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    elif command == "z":
        await message.reply(
            "**KASIAN BGT UDAH PAKE PP TT DI TONJOLIN TAPI GADA YANG LIRIKK WAHAHAH**",
            reply_to_message_id=Message.ReplyCheck(message),
        )
    return await message.delete()
