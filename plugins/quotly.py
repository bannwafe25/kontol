from command import quote_cmd
from helpers import CMD

__MODULES__ = "Quote"
__CATEGORY__ = "Stiker"
__HELP__ = """<blockquote>Command Help **Quote**</blockquote>
<blockquote expandable>--**Basic Commands**--

    **You can make quote from text random**
        `{0}q` (reply message)</blockquote>
<b>   {1}</b>
"""

IS_BASIC = True


@CMD.UBOT("q")
async def _(client, message):
    return await quote_cmd(client, message)
