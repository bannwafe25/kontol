from command import inline_cmd
from helpers import CMD

__MODULES__ = "Alive"
__CATEGORY__ = "Tools"
__HELP__ = """<blockquote>Command Help **Alive**</blockquote>
<blockquote expandable>--**Basic Commands**--

    **You can set inline alive media**
        `{0}alive media`

    **You can disable inline alive media**
        `{0}alive disable`

    **View status bot**
        `{0}alive`</blockquote>

<b>   {1}</b>
"""


@CMD.UBOT("alive")
async def _(client, message):
    return await inline_cmd(client, message)
