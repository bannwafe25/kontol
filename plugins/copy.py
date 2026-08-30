__MODULES__ = "Copy"
__CATEGORY__ = "Admin"
__HELP__ = """<blockquote>Command Help **Copy**</blockquote>
<blockquote expandable>--**Basic Commands**--

    ❖ **This command can steal or get message**
        `{0}copymsg`.</blockquote>
<b>   {1}</b>
"""


from command import copymsg_cmd, copyall2_cmd, copyall_cmd
from helpers import CMD

IS_BASIC = True

@CMD.UBOT("copyall")
async def _(client, message):
    return await copyall_cmd(client, message)


@CMD.UBOT("copyall2")
async def _(client, message):
    return await copyall2_cmd(client, message)
    
    
@CMD.UBOT("copymsg")
async def _(client, message):
    return await copymsg_cmd(client, message)
