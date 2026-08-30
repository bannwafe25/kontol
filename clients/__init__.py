import os

if not os.path.exists("downloads"):
    os.makedirs("downloads")

from .active import session
from .base import BaseClient
from .bot import Bot, bot
from .registry import HandlerRegistry, pytgcalls_registry
from .userbot import UserBot, navy

__all__ = [
    "session",
    "BaseClient",
    "UserBot",
    "navy",
    "Bot",
    "bot",
    "HandlerRegistry",
    "pytgcalls_registry",
]
