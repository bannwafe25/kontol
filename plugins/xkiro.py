from command import xkiro_cmd
from helpers import CMD


__MODULES__ = "Xkiro"
__CATEGORY__ = "Ai"
__HELP__ = """<blockquote>Command Help <b>Xkiro</b></blockquote>
<blockquote expandable>--<b>AI Commands</b>--

    <b>Chat dengan DeepSeek V4 Pro</b>
        <code>{0}kiro</code> (pertanyaan)

    <b>Contoh:</b>
        <code>{0}kiro halo jir</code>

    <b>Stop conversation:</b>
        <code>stopped ask</code>
</blockquote>
<b>   {1}</b>
"""

IS_PRO = True


@CMD.UBOT("xkiro")
async def _(client, message):
    return await xkiro_cmd(client, message)
