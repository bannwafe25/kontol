__MODULES__ = "Xkiro"
__CATEGORY__ = "Ai"
__HELP__ = """<blockquote>Command Help Xkiro</blockquote>
<blockquote expandable>--<b>AI Commands</b>--

    <b>Chat dengan DeepSeek V4 Pro melalui Xkiro</b>
        <code>{0}xkiro</code> (pertanyaan)

    <b>Contoh:</b>
        <code>{0}xkiro jelaskan python</code>
</blockquote>
<b>   {1}</b>
"""

IS_PRO = True

from command import xkiro_cmd
from helpers import CMD


@CMD.UBOT("xkiro")
async def _(client, message):
    return await xkiro_cmd(client, message)
