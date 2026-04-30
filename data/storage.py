import asyncio
import json
from pathlib import Path
import aiofiles

DATA_DIR = Path(__file__).parent
CHATS_FILE = DATA_DIR / "chats.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
_lock = asyncio.Lock()


async def read_chats() -> dict:
    """Читает chats.json, возвращает словарь. Если файла нет — создаёт пустой."""
    async with _lock:
        if not CHATS_FILE.exists():
            # Создаём файл с начальной структурой
            initial = {"chats": {}}
            async with aiofiles.open(CHATS_FILE, "w", encoding="utf-8") as f:
                await f.write(json.dumps(initial, ensure_ascii=False, indent=2))
            return initial

        async with aiofiles.open(CHATS_FILE, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)


async def write_chats(data: dict) -> None:
    """Записывает словарь в chats.json."""
    async with _lock:
        async with aiofiles.open(CHATS_FILE, "w", encoding="utf-8") as f:
            content = json.dumps(data, ensure_ascii=False, indent=2)
            await f.write(content)

async def get_chat(chat_id: str) -> dict | None:
    """Возвращает данные одного чата или None."""
    data = await read_chats()
    return data["chats"].get(chat_id)


async def upsert_chat(chat_id: str, chat_data: dict) -> None:
    """Добавляет или обновляет чат."""
    data = await read_chats()
    data["chats"][chat_id] = chat_data
    await write_chats(data)


async def update_chat_fields(chat_id: str, **kwargs) -> None:
    """Обновляет отдельные поля чата."""
    data = await read_chats()
    if chat_id in data["chats"]:
        data["chats"][chat_id].update(kwargs)
        await write_chats(data)


async def get_all_chats() -> dict:
    """Возвращает все чаты."""
    data = await read_chats()
    return data["chats"]


async def hide_chat(chat_id: str) -> None:
    """Скрывает чат."""
    await update_chat_fields(chat_id, hidden=True)


async def unhide_chat(chat_id: str) -> None:
    """Показывает скрытый чат."""
    await update_chat_fields(chat_id, hidden=False)


async def pin_chat(chat_id: str) -> None:
    """Закрепляет чат."""
    await update_chat_fields(chat_id, pinned=True)


async def unpin_chat(chat_id: str) -> None:
    """Открепляет чат."""
    await update_chat_fields(chat_id, pinned=False)

async def read_settings() -> dict:
    """Читает settings.json."""
    async with _lock:
        if not SETTINGS_FILE.exists():
            default = {"poll_interval": 30, "hide_days": 7, "notifications": True}
            async with aiofiles.open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                await f.write(json.dumps(default, ensure_ascii=False, indent=2))
            return default

        async with aiofiles.open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)


async def write_settings(data: dict) -> None:
    """Записывает settings.json."""
    async with _lock:
        async with aiofiles.open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            content = json.dumps(data, ensure_ascii=False, indent=2)
            await f.write(content)


async def update_setting(key: str, value) -> None:
    """Обновляет одну настройку."""
    settings = await read_settings()
    settings[key] = value
    await write_settings(settings)