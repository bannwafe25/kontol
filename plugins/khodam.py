from command import khodam_cmd
from helpers import CMD

__MODULES__ = "Khodam"
__CATEGORY__ = "Agama"
__HELP__ = """<blockquote>Command Help **Khodam**</blockquote>
<blockquote expandable>--**Basic Commands**--

    **You can check khodam of person**
        `{0}khodam` (reply user/username)</blockquote>
<b>   {1}</b>
"""

IS_PRO = True


@CMD.UBOT("khodam|kodam|wapak")
async def _(client, message):
    return await khodam_cmd(client, message)
