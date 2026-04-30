from avito.client import AvitoAPI
from urllib.parse import quote

class AvitoMessages:
    def __init__(self, api: AvitoAPI, user_id: int):
        self.api = api
        self.user_id = user_id

    async def get_chats(self, unread_only: bool = False, limit: int = 50):
        params = {"unread_only": str(unread_only).lower(), "limit": limit}
        return await self.api._request("GET", f"/messenger/v2/accounts/{self.user_id}/chats", params=params)

    async def get_messages(self, chat_id: str, limit: int = 50):
        chat_id_encoded = quote(chat_id, safe="")
        return await self.api._request("GET", f"/messenger/v3/accounts/{self.user_id}/chats/{chat_id_encoded}/messages", params={"limit": limit})

    async def send_message(self, chat_id: str, text: str):
        await self.api._request("POST", f"/messenger/v2/accounts/{self.user_id}/chats/{chat_id}/messages", json={"message": {"text": text}})