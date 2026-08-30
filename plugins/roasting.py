from command import roasting_cmd, stop_roasting_cmd
from helpers import CMD

__MODULES__ = "Roasting"
__CATEGORY__ = "Fun"
__HELP__ = """<blockquote>Command Help for <b>Roasting</b></blockquote>
<blockquote expandable>--**Basic Commands**--

    **You can Roast the target repeatedly with optional delay in seconds**
        `{0}roasting` (username or reply) (delay on second)
    **Roast a random group member**       
        `{0}roasting` 
    **Stop all active roasting processes**
        `{0}stoproasting`</blockquote> 
<b>   {1}</b>
"""

IS_PRO = True

@CMD.UBOT("roasting")
async def _(client, message):
    await roasting_cmd(client, message)

@CMD.UBOT("stoproasting")
async def _(client, message):
    await stop_roasting_cmd(client, message)