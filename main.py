import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from bot.handlers.start import router as start_router
from bot.middleware.access import AccessMiddleware
from bot.scheduler import poll_chats, sync_all_chats
from bot.handlers.chats import router as chats_router
from bot.handlers.settings import router as settings_router
from bot.handlers.stats import router as stats_router
from avito.messages import AvitoMessages
from bot.middleware.deps import DepsMiddleware
from avito.client import AvitoAPI
from config import AVITO_USER_ID
os.system('cls')


BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_IDS = list(map(int, os.getenv("ALLOWED_USER_IDS", "").split(",")))

async def main():
    session = AiohttpSession(proxy="socks5://127.0.0.1:2080")
    bot = Bot(token=BOT_TOKEN, session=session)
    dp = Dispatcher()

    dp.message.middleware(AccessMiddleware())
    dp.callback_query.middleware(AccessMiddleware())
    dp.include_router(start_router)
    dp.include_router(chats_router)
    dp.include_router(settings_router)
    dp.include_router(stats_router)

    # Инициализация Avito
    api = AvitoAPI(AVITO_USER_ID)
    messages_api = AvitoMessages(api, AVITO_USER_ID)
    
    dp.message.middleware(DepsMiddleware(messages_api))
    dp.callback_query.middleware(DepsMiddleware(messages_api))
    dp["messages_api"] = messages_api


    # Запуск фонового опроса чатов
    admin_id = ALLOWED_USER_IDS[0]  # первый админ
    # Синхронизация чатов при старте
    await sync_all_chats(messages_api)
    asyncio.create_task(poll_chats(bot, messages_api, admin_id))

    await dp.start_polling(bot)



if __name__ == "__main__":
    asyncio.run(main())