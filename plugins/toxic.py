from pathlib import Path

from command import alfabet_cmd
from helpers import CMD

__MODULES__ = "Toxic"
__CATEGORY__ = "Fun"
__HELP__ = """<blockquote>Command Help **Toxic**</blockquote>
<blockquote expandable>--**Others Commands**-- 

    **Use alphabet to toxic**
        **`{0}a` | `{0}e` | `{0}i` | `{0}m` | `{0}r` | `{0}v`
        `{0}b` | `{0}f` | `{0}j` | `{0}n` | `{0}s` | `{0}w`
        `{0}c` | `{0}g` | `{0}k` | `{0}o` | `{0}t` | `{0}x`
        `{0}d` | `{0}h` | `{0}l` | `{0}p` | `{0}u` | `{0}z`**</blockquote>
<b>   {1}</b>
"""

IS_BASIC = True

@CMD.UBOT("a|b|c|d|e|f|g|h|i|j|k|l|m|o|p|r|s|t|u|v|w|x|z")
async def _(client, message):
    plugin_name = Path(__file__).stem
    print(plugin_name)
    return await alfabet_cmd(client, message)
