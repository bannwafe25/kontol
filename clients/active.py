import weakref

from logs import logger


class ActiveSessionManager:
    def __init__(self):
        self._active_sessions = weakref.WeakValueDictionary()

    def add_session(self, user_id: int, client_instance):
        self._active_sessions[user_id] = client_instance

    def get_session(self, user_id: int):
        return self._active_sessions.get(user_id)

    def remove_session(self, user_id: int):
        if user_id in self._active_sessions:
            del self._active_sessions[user_id]
            logger.warning(f"🗑️ Removed session for user {user_id}")

    def get_list(self):
        return list(self._active_sessions.keys())

    def get_count(self):
        return len(self._active_sessions)

    def get_client(self):
        for user_id in self.get_list():
            client = self.get_session(user_id)
            if client:
                return client
            return None


session = ActiveSessionManager()
