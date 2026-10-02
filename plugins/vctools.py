from command import (cos_cmd, joinvc_cmd, leavevc_cmd, cekos_cmd,
                     startvc_cmd, stopvc_cmd, cleaveos_cmd, vctitle_cmd)
from helpers import CMD

__MODULES__ = "Vctools"
__CATEGORY__ = "Fun"
__HELP__ = """<blockquote>Command Help **VcTools**</blockquote>
<blockquote expandable>--**Basic Commands**--

    **Start voice chat group/channel**
        `{0}startvc` 
    **End voice chat group/channel**
        `{0}stopvc`
    **Join voice chat group/channel**
        `{0}joinvc` (chatid)
    **Leave voice chat group/channel**
        `{0}leavevc` (chatid)</blockquote>

<blockquote expandable>--**On-Stage Commands**--

    **Claim On-Stage Massal**
        `{0}cos` (chatid)
    **Claim Leave On-Stage Massal**
        `{0}cleaveos` (chatid)
    **Check Participants from voice chat**
        `{0}cekos`
    **Edit title voice chat group**
        `{0}vctitle` (title)</blockquote>
<b>   {1}</b>
"""


@CMD.UBOT("startvc")
@CMD.ONLY_GROUP
async def _(client, message):
    return await startvc_cmd(client, message)


@CMD.UBOT("stopvc")
@CMD.ONLY_GROUP
async def _(client, message):
    return await stopvc_cmd(client, message)


@CMD.UBOT("joinvc|jvc")
async def _(client, message):
    return await joinvc_cmd(client, message)


@CMD.UBOT("leavevc|lvc")
async def _(client, message):
    return await leavevc_cmd(client, message)

@CMD.UBOT("cekos")
@CMD.ONLY_GROUP
async def _(client, message):
    return await cekos_cmd(client, message)


@CMD.UBOT("vctitle")
@CMD.ONLY_GROUP
async def _(client, message):
    return await vctitle_cmd(client, message)

@CMD.UBOT("cos")
@CMD.FAKE_NLX
async def _(client, message):
    return await cos_cmd(client, message)

@CMD.UBOT("cleaveos")
@CMD.FAKE_NLX
async def _(client, message):
    return await cleaveos_cmd(client, message)
  
