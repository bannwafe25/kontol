from datetime import datetime, timezone
import random
import string

from pymongo import AsyncMongoClient

from config import MONGO_DB_URI, DB_NAME


class MongoDB:
    def __init__(self) -> None:
        self.mongo = AsyncMongoClient(MONGO_DB_URI)
        self.db = self.mongo[DB_NAME]

        self.user_prefixes = self.db.user_prefixes
        self.floods = self.db.floods
        self.variabel = self.db.variabel
        self.expired = self.db.expired
        self.userdata = self.db.userdata
        self.ubotdb = self.db.ubotdb
        self.tokens = self.db.tokens
        self.states = self.db.states

    # =========================================================
    # PREFIX
    # =========================================================

    async def get_pref(self, user_id):
        data = await self.user_prefixes.find_one({
            "_id": int(user_id)
        })

        if data:
            return data.get(
                "prefix",
                [".", "-", "!", "+", "?"]
            )

        return [".", "-", "!", "+", "?"]

    async def set_pref(self, user_id, prefix):
        return await self.user_prefixes.update_one(
            {"_id": int(user_id)},
            {
                "$set": {
                    "prefix": prefix
                }
            },
            upsert=True,
        )

    async def rem_pref(self, user_id):
        return await self.user_prefixes.delete_one({
            "_id": int(user_id)
        })

    # =========================================================
    # VARIABLES
    # =========================================================

    async def set_var(
        self,
        bot_id,
        vars_name,
        value,
        query="vars",
    ):
        return await self.variabel.update_one(
            {"_id": int(bot_id)},
            {
                "$set": {
                    f"{query}.{vars_name}": value
                }
            },
            upsert=True,
        )

    async def get_var(
        self,
        bot_id,
        vars_name,
        query="vars",
    ):
        data = await self.variabel.find_one({
            "_id": int(bot_id)
        })

        if not data:
            return None

        return data.get(
            query,
            {}
        ).get(vars_name)

    async def remove_var(
        self,
        bot_id,
        vars_name,
        query="vars",
    ):
        return await self.variabel.update_one(
            {"_id": int(bot_id)},
            {
                "$unset": {
                    f"{query}.{vars_name}": ""
                }
            },
        )

    async def all_var(
        self,
        user_id,
        query="vars",
    ):
        data = await self.variabel.find_one({
            "_id": int(user_id)
        })

        if not data:
            return None

        return data.get(query)

    async def rm_all(self, bot_id):
        return await self.variabel.delete_one({
            "_id": int(bot_id)
        })

    async def get_list_from_var(
        self,
        user_id,
        vars_name,
        query="vars",
    ):
        value = await self.get_var(
            user_id,
            vars_name,
            query,
        )

        if not value:
            return []

        if isinstance(value, list):
            return value

        return [
            int(x)
            for x in str(value).split()
        ]

    async def add_to_var(
        self,
        user_id,
        vars_name,
        value,
        query="vars",
    ):
        data = await self.get_list_from_var(
            user_id,
            vars_name,
            query,
        )

        if value not in data:
            data.append(value)

        return await self.set_var(
            user_id,
            vars_name,
            " ".join(map(str, data)),
            query,
        )

    async def remove_from_var(
        self,
        user_id,
        vars_name,
        value,
        query="vars",
    ):
        data = await self.get_list_from_var(
            user_id,
            vars_name,
            query,
        )

        if value in data:
            data.remove(value)

        return await self.set_var(
            user_id,
            vars_name,
            " ".join(map(str, data)),
            query,
        )

    # =========================================================
    # EXPIRED
    # =========================================================

    async def get_expired_date(self, user_id):
        data = await self.expired.find_one({
            "_id": int(user_id)
        })

        if not data:
            return None

        return data.get("expire_date")

    async def set_expired_date(
        self,
        user_id,
        expire_date,
    ):
        if isinstance(expire_date, str):
            try:
                expire_date = datetime.fromisoformat(
                    expire_date
                )
            except ValueError:
                return None

        return await self.expired.update_one(
            {"_id": int(user_id)},
            {
                "$set": {
                    "expire_date": expire_date
                }
            },
            upsert=True,
        )

    async def rem_expired_date(self, user_id):
        return await self.expired.update_one(
            {"_id": int(user_id)},
            {
                "$set": {
                    "expire_date": None
                }
            },
        )

    # =========================================================
    # USERDATA
    # =========================================================

    async def cek_userdata(self, user_id: int) -> bool:
        data = await self.userdata.find_one({
            "_id": int(user_id)
        })

        return data is not None

    async def get_userdata(self, user_id: int):
        return await self.userdata.find_one({
            "_id": int(user_id)
        })

    async def add_userdata(
        self,
        user_id: int,
        depan,
        belakang,
        username,
        mention,
        full,
        _id,
    ):
        return await self.userdata.update_one(
            {"_id": int(user_id)},
            {
                "$set": {
                    "user_id": int(user_id),
                    "depan": depan,
                    "belakang": belakang,
                    "username": username,
                    "mention": mention,
                    "full": full,
                    "telegram_id": _id,
                }
            },
            upsert=True,
        )

    # =========================================================
    # USERBOT
    # =========================================================

    async def add_ubot(
        self,
        user_id,
        session_string,
    ):
        return await self.ubotdb.update_one(
            {"_id": int(user_id)},
            {
                "$set": {
                    "user_id": int(user_id),
                    "session_string": session_string,
                }
            },
            upsert=True,
        )

    async def remove_ubot(self, user_id):
        return await self.ubotdb.delete_one({
            "_id": int(user_id)
        })

    async def get_ubot(self, user_id):
        data = await self.ubotdb.find_one({
            "_id": int(user_id)
        })

        if not data:
            return None

        return {
            "name": str(data["user_id"]),
            "session_string": data["session_string"],
        }

    async def get_userbots(self):
        result = []

        cursor = self.ubotdb.find({})

        async for data in cursor:
            result.append({
                "name": str(data["user_id"]),
                "session_string": data["session_string"],
            })

        return result

    async def remove_columns_ubotdb(self):
        # Tidak diperlukan di MongoDB.
        return None

    # =========================================================
    # FLOOD
    # =========================================================

    async def get_flood(
        self,
        gw: int,
        user_id: int,
    ):
        data = await self.floods.find_one({
            "_id": f"{gw}:{user_id}"
        })

        return data.get("flood") if data else None

    async def set_flood(
        self,
        gw: int,
        user_id: int,
        flood: str,
    ):
        return await self.floods.update_one(
            {
                "_id": f"{gw}:{user_id}"
            },
            {
                "$set": {
                    "gw": int(gw),
                    "user_id": int(user_id),
                    "flood": flood,
                }
            },
            upsert=True,
        )

    async def rem_flood(
        self,
        gw: int,
        user_id: int,
    ):
        return await self.floods.delete_one({
            "_id": f"{gw}:{user_id}"
        })

    async def remove_all_deleted_vars(self):
        return await self.variabel.update_many(
            {},
            {
                "$unset": {
                    "vars.DELETED": ""
                }
            },
        )

    # =========================================================
    # TOKEN
    # =========================================================

    async def generate_token(
        self,
        user_id: str,
        length=16,
        group_size=4,
        separator="-",
    ):
        characters = string.ascii_uppercase + string.digits

        while True:
            raw_token = "".join(
                random.choice(characters)
                for _ in range(length)
            )

            grouped_token = separator.join(
                raw_token[i:i + group_size]
                for i in range(0, length, group_size)
            )

            clean_token = grouped_token.replace(
                separator,
                ""
            )

            exists = await self.tokens.find_one({
                "_id": clean_token
            })

            if not exists:
                break

        await self.tokens.insert_one({
            "_id": clean_token,
            "token": clean_token,
            "owner": str(user_id),
            "created_at": datetime.now(timezone.utc),
            "usage_count": 0,
            "max_usage": 3,
            "usage_history": [],
        })

        return grouped_token

    async def get_token(self, user_id: int):
        data = await self.tokens.find_one({
            "owner": str(user_id)
        })

        if not data:
            return None

        token = data["token"]

        grouped_token = "-".join(
            token[i:i + 4]
            for i in range(0, len(token), 4)
        )

        usage_count = data.get(
            "usage_count",
            0
        )

        max_usage = data.get(
            "max_usage",
            3
        )

        return {
            "token": grouped_token,
            "usage_count": usage_count,
            "max_usage": max_usage,
            "remaining_usage": max_usage - usage_count,
        }

    async def revoke_token(
        self,
        user_id: int,
        deleted: bool = False,
    ):
        ubot = await self.ubotdb.find_one({
            "_id": int(user_id)
        })

        if not ubot:
            await self.tokens.delete_many({
                "owner": str(user_id)
            })

            return (
                False,
                "Token dihapus karena userbot tidak ditemukan.",
            )

        if deleted:
            await self.tokens.delete_many({
                "owner": str(user_id)
            })

            return True, "Token berhasil dihapus."

        old_token = await self.tokens.find_one({
            "owner": str(user_id)
        })

        if not old_token:
            return False, "Token lama tidak ditemukan."

        usage_count = old_token.get(
            "usage_count",
            0
        )

        max_usage = old_token.get(
            "max_usage",
            3
        )

        usage_history = old_token.get(
            "usage_history",
            []
        )

        await self.tokens.delete_one({
            "_id": old_token["_id"]
        })

        new_token = await self.generate_token(
            str(user_id)
        )

        clean_token = new_token.replace("-", "")

        await self.tokens.update_one(
            {"_id": clean_token},
            {
                "$set": {
                    "usage_count": usage_count,
                    "max_usage": max_usage,
                    "usage_history": usage_history,
                }
            },
        )

        remaining_usage = max_usage - usage_count

        return (
            True,
            "Token berhasil di-revoke dan diganti.\n"
            f"Token baru: `{new_token}`\n"
            f"Sisa penggunaan: {remaining_usage}",
        )

    async def check_token_usage(
        self,
        token: str,
    ):
        clean_token = token.replace("-", "")

        data = await self.tokens.find_one({
            "_id": clean_token
        })

        if not data:
            return {
                "valid": False,
                "message": "Token tidak valid",
                "usage_count": 0,
                "max_usage": 3,
                "remaining_usage": 0,
            }

        usage_count = data.get(
            "usage_count",
            0
        )

        max_usage = data.get(
            "max_usage",
            3
        )

        return {
            "valid": True,
            "message": "Token valid",
            "usage_count": usage_count,
            "max_usage": max_usage,
            "remaining_usage": max_usage - usage_count,
            "owner": data.get("owner"),
            "created_at": data.get("created_at"),
            "usage_history": data.get(
                "usage_history",
                []
            ),
        }

    async def use_token(
        self,
        token: str,
        usage_description: str = "Token digunakan",
    ):
        clean_token = token.replace("-", "")

        data = await self.tokens.find_one({
            "_id": clean_token
        })

        if not data:
            return False, "Token tidak valid"

        usage_count = data.get(
            "usage_count",
            0
        )

        max_usage = data.get(
            "max_usage",
            3
        )

        if usage_count >= max_usage:
            return (
                False,
                f"Token telah mencapai batas penggunaan maksimal "
                f"({max_usage} kali)",
            )

        usage_count += 1

        history = data.get(
            "usage_history",
            []
        )

        history.append({
            "timestamp": datetime.now(timezone.utc),
            "description": usage_description,
        })

        await self.tokens.update_one(
            {"_id": clean_token},
            {
                "$set": {
                    "usage_count": usage_count,
                    "usage_history": history,
                }
            },
        )

        return (
            True,
            f"Token berhasil digunakan. "
            f"Sisa penggunaan: {max_usage - usage_count} kali",
        )

    async def verify_token(self, token: str):
        clean_token = token.replace("-", "")

        data = await self.tokens.find_one({
            "_id": clean_token
        })

        if not data:
            return None

        usage_count = data.get(
            "usage_count",
            0
        )

        max_usage = data.get(
            "max_usage",
            3
        )

        if usage_count >= max_usage:
            return None

        return {
            "user_id": data.get("owner"),
            "token": clean_token,
        }

    # =========================================================
    # CLOSE
    # =========================================================

    async def close(self):
        if self.mongo:
            await self.mongo.close()


# Kompatibilitas dengan kode lama
DB_PATH = None

db = MongoDB()
dB = db
