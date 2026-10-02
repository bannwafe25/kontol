import traceback

import httpx
from bs4 import BeautifulSoup


class SingleHoroscopeFetcher:
    def __init__(self, html: str):
        self.soup = BeautifulSoup(html, "html.parser")

    def extract_prediction(self) -> str:
        main = self.soup.select_one(".main-horoscope")
        if not main:
            return "⚠️ Ramalan tidak ditemukan dalam halaman."
        lines = main.text.strip().split("\n")
        prediction = next(
            (line.strip() for line in lines if len(line.strip()) > 100),
            "⚠️ Tidak ada teks ramalan yang valid ditemukan.",
        )
        return prediction


class HoroscopeScraper:
    def __init__(self):
        self.base_url = "https://www.horoscope.com/us/horoscopes/general/horoscope-general-daily-{day}.aspx?sign={sign}"
        self.zodiac_slugs = {
            "aries": 1,
            "taurus": 2,
            "gemini": 3,
            "cancer": 4,
            "leo": 5,
            "virgo": 6,
            "libra": 7,
            "scorpio": 8,
            "sagittarius": 9,
            "capricorn": 10,
            "aquarius": 11,
            "pisces": 12,
        }
        self.valid_days = {
            "today": "today",
            "yesterday": "yesterday",
            "tomorrow": "tomorrow",
        }
        self.available_zodiac = list(self.zodiac_slugs.keys())

    async def get_horoscope(self, zodiac: str, day: str = "today") -> str:
        slug = self.zodiac_slugs.get(zodiac.lower())
        if not slug:
            return "⚠️ Zodiak tidak valid. Harap masukkan nama zodiak yang benar."

        day_key = self.valid_days.get(day.lower())
        if not day_key:
            return "⚠️ Hari tidak valid. Gunakan: Today, Yesterday, atau Tomorrow."

        url = self.base_url.format(day=day_key, sign=slug)

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(url)
        except Exception:
            return f"❌ Terjadi kesalahan saat mengambil data:\n<code>{traceback.format_exc()}</code>"

        if response.status_code != 200:
            return (
                f"❌ Gagal mengambil ramalan untuk {zodiac.capitalize()} "
                f"({day.capitalize()}) (Status {response.status_code})."
            )

        fetcher = SingleHoroscopeFetcher(response.text)
        prediction = fetcher.extract_prediction()
        return self.format_response(zodiac, day, prediction)

    def format_response(self, zodiac: str, day: str, text: str) -> str:
        return (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔮 Horoskop *{zodiac.capitalize()}* - {day.capitalize()}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🪄 _{text}_\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 Source: Horoscope.com"
        )


horoscope = HoroscopeScraper()