from command import (naga_cmd, keberutungan_cmd, shio_cmd, tarot_cmd, artinama_cmd,
                     weton_cmd, karakter_cmd, jodoh_cmd, cinta_cmd, pasangan_cmd, 
                     cocoknama_cmd, wetonkerja_cmd, rezeki_cmd, artimimpi_cmd, naas_cmd)
from helpers import CMD

__MODULES__ = "Primbon"
__CATEGORY__ = "Agama"
__HELP__ = """<blockquote><b>Command Help: Primbon</b></blockquote>
<blockquote expandable>--**Basic Commands**--

    **You can get primbon of a person from this command**
        `{0}artinama` (name)
        `{0}cocoknama` (date month year)  
        `{0}pasangan` (name1 name2)  
        `{0}cinta` (name1 date1 month1 years1 name2 date2 month2 years2) 
        `{0}jodoh` (name1 date1 month1 years1 name2 date2 month2 years2)
        `{0}karakter` (name date month years)   
        `{0}wetonjawa` (date month years) 
        `{0}wetonkerja` (date month years)  
        `{0}rezeki` (date month years) 
        `{0}nagahari` (date month years)  
        `{0}keberuntungan` (date month years) 
        `{0}naas` (date month years)
        `{0}artimimpi` (mimpi)  
        `{0}shio` (date month years)  
        `{0}tarot` (date month years)</blockquote>
<b>   {1}</b>
"""

IS_PRO = True

@CMD.UBOT("cocoknama")
async def _(client, message):
    return await cocoknama_cmd(client, message)

@CMD.UBOT("artinama")
async def _(client, message):
    return await artinama_cmd(client, message)

@CMD.UBOT("wetonkerja")
async def _(client, message):
    return await wetonkerja_cmd(client, message)

@CMD.UBOT("rezeki")
async def _(client, message):
    return await rezeki_cmd(client, message)

@CMD.UBOT("artimimpi")
async def _(client, message):
    return await artimimpi_cmd(client, message)

@CMD.UBOT("naas")
async def _(client, message):
    return await naas_cmd(client, message)

@CMD.UBOT("pasangan")
async def _(client, message):
    return await pasangan_cmd(client, message)

@CMD.UBOT("cinta")
async def _(client, message):
    return await cinta_cmd(client, message)

@CMD.UBOT("jodoh")
async def _(client, message):
    return await jodoh_cmd(client, message)

@CMD.UBOT("karakter")
async def _(client, message):
    return await karakter_cmd(client, message)

@CMD.UBOT("wetonjawa")
async def _(client, message):
    return await weton_cmd(client, message)

@CMD.UBOT("shio")
async def _(client, message):
    return await shio_cmd(client, message)

@CMD.UBOT("tarot")
async def _(client, message):
    return await tarot_cmd(client, message)

@CMD.UBOT("keberuntungan")
async def _(client, message):
    return await keberutungan_cmd(client, message)

@CMD.UBOT("nagahari")
async def _(client, message):
    return await naga_cmd(client, message)