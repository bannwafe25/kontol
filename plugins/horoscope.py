from command import horoskop_cmd
from helpers import CMD

__MODULES__ = "Horoscope"
__CATEGORY__ = "Fun"
__HELP__ = """<blockquote>Command Help <b>Horoscope</b></blockquote>
<blockquote expandable>--**Check Horoscope**--

    ❖ **You can Get detailed horoscope information for a person**
        `{0}horoskop` (zodiac) (today/tomorrow/)</blockquote>
        
<blockquote expandable>--**Available Zodiac Signs**--  

        - Aries  
        - Taurus  
        - Gemini  
        - Cancer  
        - Leo  
        - Virgo  
        - Libra  
        - Scorpio  
        - Sagittarius  
        - Capricorn  
        - Aquarius  
        - Pisces</blockquote>  
<b>   {1}</b>
"""

IS_PRO = True

@CMD.UBOT("horoskop")
async def _(client, message):
    return await horoskop_cmd(client, message)