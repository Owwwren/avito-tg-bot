from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from avito.client import AvitoAPI
from config import AVITO_USER_ID
from datetime import datetime, timedelta

router = Router()


async def _get_api() -> AvitoAPI:
    """Создаёт экземпляр API для статистики."""
    return AvitoAPI(AVITO_USER_ID)


async def _render_stats_menu() -> tuple[str, InlineKeyboardMarkup]:
    """Возвращает текст и клавиатуру меню статистики."""
    text = (
        "╭──────────────────────╮\n"
        "│  📊 СТАТИСТИКА\n"
        "│  ────────────────────\n"
        "│  Выберите раздел:\n"
        "╰──────────────────────╯"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 По объявлениям", callback_data="stats:items")],
        [InlineKeyboardButton(text="📈 Общая сводка", callback_data="stats:summary")],
        [InlineKeyboardButton(text="« Назад в меню", callback_data="menu:main")],
    ])
    return text, kb


@router.message(F.text == "📊 Статистика")
async def show_stats_menu(message: Message):
    text, kb = await _render_stats_menu()
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "stats:back")
async def stats_back(callback: CallbackQuery):
    text, kb = await _render_stats_menu()
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "stats:items")
async def show_items_list(callback: CallbackQuery):
    api = await _get_api()
    try:
        items = await api._request("GET", "/core/v1/items", params={"per_page": 20})
        resources = items.get("resources", [])
    except Exception as e:
        await callback.answer(f"Ошибка загрузки: {e}")
        return
    finally:
        await api.close()

    if not resources:
        await callback.answer("Нет объявлений")
        return

    text = (
        "╭──────────────────────╮\n"
        "│  📋 ПО ОБЪЯВЛЕНИЯМ\n"
        "│  ────────────────────\n"
        "│  Выберите объявление:\n"
        "╰──────────────────────╯"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for item in resources:
        item_id = item.get("id")
        title = item.get("title", "Без названия")[:30]
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"📄 {title}",
                callback_data=f"stats:item:{item_id}"
            )
        ])

    kb.inline_keyboard.append([
        InlineKeyboardButton(text="« Назад", callback_data="stats:back")
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("stats:item:"))
async def show_item_stats(callback: CallbackQuery):
    parts = callback.data.split(":")
    item_id = int(parts[2])
    # Период по умолчанию — неделя, может быть передан 4-м параметром
    period = parts[3] if len(parts) > 3 else "week"

    api = await _get_api()
    try:
        today = datetime.now()
        if period == "today":
            date_from = today.strftime("%Y-%m-%d")
            date_to = date_from
        elif period == "yesterday":
            yesterday = today - timedelta(days=1)
            date_from = yesterday.strftime("%Y-%m-%d")
            date_to = date_from
        elif period == "month":
            date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        else:  # week
            date_from = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")

        stats = await api.get_item_stats([item_id], date_from, date_to)
    except Exception as e:
        await callback.answer(f"Ошибка загрузки: {e}")
        return
    finally:
        await api.close()

    result = stats.get("result", {})
    items = result.get("items", [])

    if not items:
        await callback.answer("Нет данных за выбранный период")
        return

    item_data = items[0]
    stats_list = item_data.get("stats", [])

    total_views = sum(day.get("uniqViews", 0) for day in stats_list)
    total_contacts = sum(day.get("uniqContacts", 0) for day in stats_list)
    total_favorites = sum(day.get("uniqFavorites", 0) for day in stats_list)
    conversion = (total_contacts / total_views * 100) if total_views > 0 else 0

    period_names = {"today": "Сегодня", "yesterday": "Вчера", "week": "7 дней", "month": "30 дней"}
    period_name = period_names.get(period, "7 дней")

    text = (
        "╭──────────────────────╮\n"
        "│  📊 СТАТИСТИКА\n"
        "│  ────────────────────\n"
        f"│  {period_name}:\n"
        "│\n"
        f"│  👁 Просмотры: {total_views}\n"
        f"│  📞 Контакты: {total_contacts}\n"
        f"│  ⭐ Избранное: {total_favorites}\n"
        f"│  📈 Конверсия: {conversion:.1f}%\n"
        "╰──────────────────────╯"
    )

    # Кнопки периода
    periods = [
        ("📅 Сегодня", "today"),
        ("📅 Вчера", "yesterday"),
        ("📅 7 дней", "week"),
        ("📅 30 дней", "month"),
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    # Первый ряд: Сегодня и Вчера
    row1 = []
    for name, p in periods[:2]:
        prefix = "✅ " if period == p else ""
        row1.append(InlineKeyboardButton(text=f"{prefix}{name}", callback_data=f"stats:item:{item_id}:{p}"))
    kb.inline_keyboard.append(row1)

    # Второй ряд: 7 дней и 30 дней
    row2 = []
    for name, p in periods[2:]:
        prefix = "✅ " if period == p else ""
        row2.append(InlineKeyboardButton(text=f"{prefix}{name}", callback_data=f"stats:item:{item_id}:{p}"))
    kb.inline_keyboard.append(row2)

    # Обновить и назад
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"stats:item:{item_id}:{period}"),
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="« К списку", callback_data="stats:items"),
    ])

    try:
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer(f"✅ {period_name}")
    except Exception:
        await callback.answer("🔄 Данные актуальны")

@router.callback_query(F.data.startswith("stats:summary"))
async def show_summary(callback: CallbackQuery):
    parts = callback.data.split(":")
    period = parts[2] if len(parts) > 2 else "week"

    api = await _get_api()
    try:
        items = await api._request("GET", "/core/v1/items", params={"per_page": 100})
        resources = items.get("resources", [])
        item_ids = [item["id"] for item in resources]

        today = datetime.now()
        if period == "today":
            date_from = today.strftime("%Y-%m-%d")
            date_to = date_from
        elif period == "yesterday":
            yesterday = today - timedelta(days=1)
            date_from = yesterday.strftime("%Y-%m-%d")
            date_to = date_from
        elif period == "month":
            date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        else:
            date_from = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")

        try:
            stats = await api.get_item_stats(item_ids, date_from, date_to) if item_ids else {"result": {"items": []}}
        except Exception as e:
            if "429" in str(e):
                await callback.answer("⏳ Слишком много запросов, попробуйте позже")
            else:
                await callback.answer(f"Ошибка загрузки: {e}")
            return
        try:
            spendings = await api.get_spendings(date_from, date_to)
        except Exception as e:
            if "429" in str(e):
                spendings = {"result": {"groupings": []}}
            else:
                raise
    except Exception as e:
        await callback.answer(f"Ошибка загрузки: {e}")
        return
    finally:
        await api.close()

    total_views = 0
    total_contacts = 0

    for item in stats.get("result", {}).get("items", []):
        for day in item.get("stats", []):
            total_views += day.get("uniqViews", 0)
            total_contacts += day.get("uniqContacts", 0)

    conversion = (total_contacts / total_views * 100) if total_views > 0 else 0

    total_spent = 0
    for day in spendings.get("result", {}).get("groupings", []):
        for s in day.get("spendings", []):
            total_spent += s.get("value", 0)

    period_names = {"today": "Сегодня", "yesterday": "Вчера", "week": "7 дней", "month": "30 дней"}
    period_name = period_names.get(period, "7 дней")

    text = (
        "╭──────────────────────╮\n"
        "│  📈 ОБЩАЯ СВОДКА\n"
        "│  ────────────────────\n"
        f"│  {period_name}:\n"
        "│\n"
        f"│  📦 Объявлений: {len(resources)}\n"
        f"│  👁 Просмотры: {total_views}\n"
        f"│  📞 Контакты: {total_contacts}\n"
        f"│  📈 Конверсия: {conversion:.1f}%\n"
        f"│  💰 Расходы: {total_spent:.0f} ₽\n"
        "╰──────────────────────╯"
    )

    periods = [
        ("📅 Сегодня", "today"),
        ("📅 Вчера", "yesterday"),
        ("📅 7 дней", "week"),
        ("📅 30 дней", "month"),
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    row1 = []
    for name, p in periods[:2]:
        prefix = "✅ " if period == p else ""
        row1.append(InlineKeyboardButton(text=f"{prefix}{name}", callback_data=f"stats:summary:{p}"))
    kb.inline_keyboard.append(row1)

    row2 = []
    for name, p in periods[2:]:
        prefix = "✅ " if period == p else ""
        row2.append(InlineKeyboardButton(text=f"{prefix}{name}", callback_data=f"stats:summary:{p}"))
    kb.inline_keyboard.append(row2)

    kb.inline_keyboard.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"stats:summary:{period}"),
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="« Назад", callback_data="stats:back"),
    ])

    try:
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer(f"✅ {period_name}")
    except Exception:
        await callback.answer("🔄 Данные актуальны")
