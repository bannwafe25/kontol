import config

from .base import BaseClient


class AssistantClient(BaseClient):
    def __init__(self, **kwargs):
        super().__init__(
            name="assistant",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=config.ASSISTANT_SESSION_STRING,
            in_memory=True,
            app_version="18.01",
            device_model="AI Assistant",
            system_version="Linux",
            sleep_threshold=30,
            **kwargs,
        )


assistant = AssistantClient()
