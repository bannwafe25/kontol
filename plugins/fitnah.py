__MODULES__ = "Fitnah"
__CATEGORY__ = "Fun"
__HELP__ = """<blockquote>Command Help <b>Fitnah</b>️</blockquote>
<blockquote expandable>--**Slander random Reply Message**--

    **You can Slander someone with fake reply in group**
        `{0}fitnah` (username/reply message)</blockquote>
<b>   {1}</b>
"""

IS_PRO = True

from command import fitnah_cmd
from helpers import CMD

@CMD.UBOT("fitnah")
async def _(client, message):
    return await fitnah_cmd(client, message)