from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from data.storage import read_settings, update_setting

router = Router()


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    settings = await read_settings()

    poll = settings.get("poll_interval", 30)
    hide = settings.get("hide_days", 7)
    notif = settings.get("notifications", True)

    hide_text = f"{hide} дней" if hide > 0 else "никогда"
    notif_text = "вкл ✅" if notif else "выкл ❌"

    text = (
        "╭──────────────────────╮\n"
        "│  ⚙️ НАСТРОЙКИ\n"
        "│  ────────────────────\n"
        f"│  ⏱ Частота опроса: {poll} сек\n"
        f"│  🗑 Автоскрытие: {hide_text}\n"
        f"│  🔔 Уведомления: {notif_text}\n"
        "╰──────────────────────╯"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏱ Частота опроса", callback_data="settings:poll")],
        [InlineKeyboardButton(text="🗑 Автоскрытие", callback_data="settings:hide")],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings:notif")],
        [InlineKeyboardButton(text="« Назад в меню", callback_data="menu:main")],
    ])

    await message.answer(text, reply_markup=kb)

@router.callback_query(F.data == "settings:poll")
async def settings_poll(callback: CallbackQuery):
    settings = await read_settings()
    current = settings.get("poll_interval", 30)

    text = (
        "╭──────────────────────╮\n"
        "│  ⏱ ЧАСТОТА ОПРОСА\n"
        "│  ────────────────────\n"
        f"│  Текущая: {current} сек\n"
        "╰──────────────────────╯"
    )

    intervals = [15, 30, 60, 120]
    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for interval in intervals:
        prefix = "✅ " if current == interval else ""
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{prefix}{interval} сек",
                callback_data=f"set_poll:{interval}"
            )
        ])

    kb.inline_keyboard.append([
        InlineKeyboardButton(text="« Назад", callback_data="settings:back")
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("set_poll:"))
async def set_poll(callback: CallbackQuery):
    interval = int(callback.data.split(":")[1])
    await update_setting("poll_interval", interval)
    await callback.answer(f"Установлено: {interval} сек")
    await settings_poll(callback)

@router.callback_query(F.data == "settings:back")
async def settings_back(callback: CallbackQuery):
    settings = await read_settings()

    poll = settings.get("poll_interval", 30)
    hide = settings.get("hide_days", 7)
    notif = settings.get("notifications", True)

    hide_text = f"{hide} дней" if hide > 0 else "никогда"
    notif_text = "вкл ✅" if notif else "выкл ❌"

    text = (
        "╭──────────────────────╮\n"
        "│  ⚙️ НАСТРОЙКИ\n"
        "│  ────────────────────\n"
        f"│  ⏱ Частота опроса: {poll} сек\n"
        f"│  🗑 Автоскрытие: {hide_text}\n"
        f"│  🔔 Уведомления: {notif_text}\n"
        "╰──────────────────────╯"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏱ Частота опроса", callback_data="settings:poll")],
        [InlineKeyboardButton(text="🗑 Автоскрытие", callback_data="settings:hide")],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings:notif")],
        [InlineKeyboardButton(text="« Назад в меню", callback_data="menu:main")],
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "settings:hide")
async def settings_hide(callback: CallbackQuery):
    settings = await read_settings()
    current = settings.get("hide_days", 7)

    hide_text = f"{current} дней" if current > 0 else "никогда"

    text = (
        "╭──────────────────────╮\n"
        "│  🗑 АВТОСКРЫТИЕ\n"
        "│  ────────────────────\n"
        f"│  Текущее: {hide_text}\n"
        "╰──────────────────────╯"
    )

    days_options = [(1, "1 день"), (3, "3 дня"), (7, "7 дней"), (14, "14 дней"), (0, "Никогда")]
    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for days, name in days_options:
        prefix = "✅ " if current == days else ""
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"{prefix}{name}", callback_data=f"set_hide:{days}")
        ])

    kb.inline_keyboard.append([
        InlineKeyboardButton(text="« Назад", callback_data="settings:back")
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("set_hide:"))
async def set_hide(callback: CallbackQuery):
    days = int(callback.data.split(":")[1])
    await update_setting("hide_days", days)
    await callback.answer(f"Установлено: {days} дней" if days > 0 else "Никогда")
    await settings_hide(callback)


@router.callback_query(F.data == "settings:notif")
async def settings_notif(callback: CallbackQuery):
    settings = await read_settings()
    current = settings.get("notifications", True)

    text = (
        "╭──────────────────────╮\n"
        "│  🔔 УВЕДОМЛЕНИЯ\n"
        "│  ────────────────────\n"
        f"│  Сейчас: {'вкл ✅' if current else 'выкл ❌'}\n"
        "╰──────────────────────╯"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Включить" if not current else "✅ Включить",
                callback_data="set_notif:1"
            ),
            InlineKeyboardButton(
                text="❌ Выключить" if current else "❌ Выключить",
                callback_data="set_notif:0"
            ),
        ],
        [InlineKeyboardButton(text="« Назад", callback_data="settings:back")],
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("set_notif:"))
async def set_notif(callback: CallbackQuery):
    value = callback.data.split(":")[1] == "1"
    await update_setting("notifications", value)
    await callback.answer(f"{'Включены' if value else 'Выключены'}")
    await settings_notif(callback)