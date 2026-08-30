__MODULES__ = "Grooq"
__CATEGORY__ = "Ai"
__HELP__ = """<blockquote>Command Help **Blackbox**</blockquote>
<blockquote expandable>--**Basic Commands**--

    **You can answer question to blackbox ai** 
        `{0}ai` (question)</blockquote>
<b>   {1}</b>
"""

IS_PRO = True

from command import grooq_cmd
from helpers import CMD


@CMD.UBOT("ai")
async def _(client, message):
    return await grooq_cmd(client, message)
