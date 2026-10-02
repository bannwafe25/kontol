from command import rate_cmd
from helpers import CMD

__MODULES__ = "Rate"
__CATEGORY__ = "Fun"
__HELP__ = """<blockquote>Command Help <b>Rate</b></blockquote>
<blockquote expandable>--**Basic Commands**--

    **Get a fun rating based on your input**
        `{0}rate` (type) (question)

     **Available Rating Type**
        - cocok   
        - kegantengan  
        - kecantikan 
        - kepintaran 
        - kebadboyan
        - kehaluan   
        - kesetiaan 
        - kebucinan
        - kebodohan
        - keuwuan</blockquote>
<b>   {1}</b>
"""

IS_PRO = True

@CMD.UBOT("rate")
async def _(client, message):
    return await rate_cmd(client, message)