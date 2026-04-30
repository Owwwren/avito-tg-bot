from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Any, Callable, Dict, Awaitable
from avito.messages import AvitoMessages


class DepsMiddleware(BaseMiddleware):
    def __init__(self, messages_api: AvitoMessages):
        self.messages_api = messages_api
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        data["messages_api"] = self.messages_api
        return await handler(event, data)