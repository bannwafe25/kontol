"""AnimePic fetcher untuk kontol (zpxrobot).

Port ringan dari selfbot/modules/animepic.py — cuma bagian fetch
gambar anime dari multi-API dengan fallback. Tanpa dependensi selfbot.
"""

import asyncio
import random
import re
from urllib.parse import quote


class AnimePicFetcher:
    """Fetch URL gambar anime dari beberapa API dengan fallback berantai."""

    safebooru_tags = [
        "safebooru", "1girl", "1boy", "2boys", "2girls", "genshin_impact",
        "blue_archive", "azur_lane", "honkai_star_rail", "vocaloid",
        "touhou", "miku", "maid", "school_uniform", "swimsuit",
    ]
    konachan_tags = ["konachan", "landscape", "scenery", "sky", "water", "city", "tree", "clouds", "stars"]

    waifu_pics_tags = [
        "waifu", "happy", "neko", "shinobu", "megumin", "bully", "cuddle", "cry", "hug", "awoo", "kiss",
        "lick", "smug", "bonk", "yeet", "wave", "highfive", "handhold", "nom", "bite",
        "glomp", "slap", "kill", "kick", "wink", "poke", "dance", "cringe",
    ]

    waifu_im_tags = [
        "maid", "waifu", "uniform", "kamisato-ayaka", "marin-kitagawa", "mori-calliope",
        "raiden-shogun", "oppai", "selfies", "genshin-impact", "rem", "nami",
    ]

    nekos_best_tags = [
        "husbando", "kitsune", "pat", "baka", "bored", "laugh", "nod", "nope",
        "pout", "shrug", "sleep", "smile", "stare", "think", "thumbsup", "tickle",
    ]

    # (list_attr, method_name)
    _API_REGISTRY = (
        ("safebooru_tags", "_get_from_safebooru"),
        ("konachan_tags", "_get_from_konachan"),
        ("waifu_im_tags", "_get_from_waifu_im"),
        ("waifu_pics_tags", "_get_from_waifu_pics"),
        ("nekos_best_tags", "_get_from_nekos_best"),
    )

    def __init__(self, http):
        self.http = http  # httpx.AsyncClient (self.client.http di plugin)

    @staticmethod
    def _is_valid_url(url: str | None) -> bool:
        return bool(url) and isinstance(url, str) and url.startswith(("http://", "https://"))

    @classmethod
    def _is_valid_non_gif(cls, url: str | None) -> bool:
        if not cls._is_valid_url(url):
            return False
        return not re.search(r"\.gif($|\?)", url, re.I)

    @classmethod
    def _pick_preferred_url(cls, urls: list) -> str | None:
        non_gif = [u for u in urls if cls._is_valid_non_gif(u)]
        return random.choice(non_gif) if non_gif else None

    def parse_query(self, query: str) -> tuple[str, str | None]:
        """Return (query_bersih, tag_asli) — tag asli dipake buat routing API."""
        q = query.strip().lower()
        return q, q

    async def get_image_url(self, tag: str) -> tuple | None:
        """Return (url, None, {}, None) atau None. Routing sesuai tag."""
        for list_attr, func_name in self._API_REGISTRY:
            if tag in getattr(self, list_attr):
                try:
                    fn = getattr(self, func_name)
                    result = await fn(tag)
                    if result:
                        return result
                except Exception:
                    continue
        return await self._fallback_nekos_life(tag)

    async def _fallback_nekos_life(self, tag: str) -> tuple | None:
        try:
            for _ in range(3):
                resp = await self.http.get(
                    f"https://nekos.life/api/v2/img/{quote(tag)}", timeout=10
                )
                if resp.status_code == 200:
                    url = resp.json().get("url")
                    if self._is_valid_non_gif(url):
                        return url, None, {}, None
                await asyncio.sleep(0.2)
        except Exception:
            pass
        return None

    # ── API methods ──────────────────────────────────────────────────────────

    async def _get_from_waifu_pics(self, tag: str) -> tuple | None:
        many = await self.http.post(
            f"https://api.waifu.pics/many/sfw/{tag}", json={}, timeout=10
        )
        if many.status_code == 200:
            files = (many.json() or {}).get("files") or []
            if isinstance(files, list):
                url = self._pick_preferred_url(files)
                if url:
                    return url, None, {}, None

        resp = await self.http.get(f"https://api.waifu.pics/sfw/{tag}", timeout=10)
        if resp.status_code != 200:
            return None
        url = (resp.json() or {}).get("url")
        return (url, None, {}, None) if self._is_valid_url(url) else None

    async def _get_from_waifu_im(self, tag: str) -> tuple | None:
        params = {"included_tags": tag, "many": "false", "is_nsfw": "false"}
        resp = await self.http.get("https://api.waifu.im/search", params=params, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        images = data.get("images") or []
        for img in images:
            url = img.get("url")
            if self._is_valid_non_gif(url):
                return url, None, {}, None
        return None

    async def _get_from_nekos_best(self, tag: str) -> tuple | None:
        end = "husbando" if tag == "husbando" else tag
        resp = await self.http.get(f"https://nekos.best/api/v2/{end}", timeout=10)
        if resp.status_code != 200:
            return None
        results = resp.json().get("results") or []
        for r in results:
            url = r.get("url")
            if self._is_valid_non_gif(url):
                return url, None, {}, None
        return None

    async def _get_from_safebooru(self, tag: str) -> tuple | None:
        t = tag if tag != "safebooru" else random.choice(self.safebooru_tags[1:])
        params = {"tags": f"{quote(t)} rating:general", "limit": 30}
        resp = await self.http.get("https://safebooru.org/index.php", params={"page": "dapi", "s": "post", "q": "index", "json": 1, **params}, timeout=10)
        if resp.status_code != 200:
            return None
        posts = resp.json() or []
        urls = [f"https://safebooru.org/images/{p['directory']}/{p['image']}" for p in posts if p.get("image")]
        urls = [u for u in urls if not re.search(r"\.(gif|mp4|webm)($|\?)", u, re.I)]
        if not urls:
            return None
        return random.choice(urls), None, {}, None

    async def _get_from_konachan(self, tag: str) -> tuple | None:
        t = tag if tag != "konachan" else random.choice(self.konachan_tags[1:])
        params = {"tags": quote(t), "limit": 30}
        resp = await self.http.get("https://konachan.net/post.json", params=params, timeout=10)
        if resp.status_code != 200:
            return None
        posts = resp.json() or []
        urls = [p.get("file_url") or p.get("jpeg_url") for p in posts]
        urls = [u for u in urls if self._is_valid_non_gif(u)]
        if not urls:
            return None
        return random.choice(urls), None, {}, None
