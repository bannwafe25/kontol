from command import help_cmd
from helpers import CMD

__MODULES__ = "Help"
__CATEGORY__ = "System"
__HELP__ = """<blockquote>Command Help **Help**</blockquote>
<blockquote expandable>--**Basic Commands**--

    **You can set inline help media**
        `{0}help media`

    **You can disable inline help media**
        `{0}help disable`

    **View all plugins**
        `{0}help`</blockquote>

<b>   {1}</b>
"""


@CMD.UBOT("help")
async def _(client, message):
    return await help_cmd(client, message)
