from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    # Клавиатура главного меню
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Статистика"),
                KeyboardButton(text="💬 Чаты"),
                KeyboardButton(text="⚙️ Настройки"),
            ]
        ],
        resize_keyboard=True,
    )

    # Пока заглушка для сводки, позже будем подтягивать реальные данные
    text = (
    "╭─────────────────────╮\n"
    "│  📊 СВОДКА ЗА СЕГОДНЯ\n"
    "│  ────────────────────\n"
    "│  👁 Просмотры: —\n"
    "│  📞 Контакты: —\n"
    "│  💰 Расходы: —\n"
    "│  ────────────────────\n"
    "│  💬 Чаты: — (новых: —)\n"
    "│  ⭐ Отзывы: — (✅ / ❌)\n"
    "╰─────────────────────╯"
)

    await message.answer(text, reply_markup=kb)