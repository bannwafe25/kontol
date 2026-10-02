from command import zodiak_cmd
from helpers import CMD

__MODULES__ = "Zodiac"
__CATEGORY__ = "Fun"
__HELP__ = """<blockquote>Command Help <b>Zodiac</b></blockquote>
<blockquote expandable>--**Basic Commands**--

    ❖ **You can check the zodiac sign of a person**
        `{0}zodiac` (query)</blockquote>
<b>   {1}</b>
"""

IS_PRO = True


@CMD.UBOT("zodiac")
async def _(client, message):
    return await zodiak_cmd(client, message)