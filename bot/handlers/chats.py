import asyncio
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from bot.states import ChatStates
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from data.storage import get_all_chats, get_chat, update_chat_fields, pin_chat, unpin_chat, hide_chat, unhide_chat
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime

router = Router()

def format_date(value) -> str:
    """Превращает дату в читаемый формат. Принимает строку ISO или число (timestamp)."""
    if not value:
        return "—"
    try:
        if isinstance(value, (int, float)):
            # Это timestamp
            dt = datetime.fromtimestamp(value)
        else:
            # Это строка ISO
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y, %H:%M")
    except (ValueError, TypeError):
        return str(value)
    

async def _render_chats():
    """Возвращает (text, keyboard) для списка чатов."""
    chats = await get_all_chats()

    pinned = {}
    active = {}
    hidden = {}
    for chat_id, chat in chats.items():
        if chat.get("hidden"):
            hidden[chat_id] = chat
        elif chat.get("pinned"):
            pinned[chat_id] = chat
        else:
            active[chat_id] = chat

    text = "╭──────────────────────╮\n"
    text += "│  💬 ЧАТЫ\n"
    text += "│  ────────────────────\n"
    text += "│\n"

    if pinned:
        text += "│  📌 ЗАКРЕПЛЁННЫЕ\n"
        for chat_id, chat in pinned.items():
            review = get_review_emoji(chat.get("review_status"))
            label = chat.get("label", "")
            # Берём только эмодзи из метки
            label_emoji = ""
            if label:
                parts = label.split(" ", 1)
                label_emoji = parts[0] + " " if parts else ""
            text += f"│    ▸ {label_emoji}{chat['user_name']} {review}\n"
        text += "│\n"

    if active:
        text += "│  📋 АКТИВНЫЕ\n"
        for chat_id, chat in active.items():
            review = get_review_emoji(chat.get("review_status"))
            label = chat.get("label", "")
            # Берём только эмодзи из метки (первый символ до пробела)
            label_emoji = ""
            if label:
                parts = label.split(" ", 1)
                label_emoji = parts[0] + " " if parts else ""
            text += f"│    ▸ {label_emoji}{chat['user_name']} {review}\n"
        text += "│\n"

    if hidden:
        text += "│  ────────────────────\n"
        text += f"│  🗑 СКРЫТЫЕ: {len(hidden)}\n"

    text += "╰──────────────────────╯"

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for chat_id, chat in pinned.items():
        review = get_review_emoji(chat.get("review_status"))
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{chat['user_name']} {review}".strip(),
                callback_data=f"chat:{chat_id}"
            )
        ])

    for chat_id, chat in active.items():
        review = get_review_emoji(chat.get("review_status"))
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{chat['user_name']} {review}".strip(),
                callback_data=f"chat:{chat_id}"
            )
        ])

    if hidden:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"👁 Показать скрытые ({len(hidden)})",
                callback_data="chats:show_hidden"
            )
        ])

    kb.inline_keyboard.append([
        InlineKeyboardButton(text="« Назад в меню", callback_data="menu:main")
    ])

    return text, kb


@router.message(F.text == "💬 Чаты")
async def show_chats(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await message.delete()
        msg = await message.answer("⚠️ Закончите ввод или нажмите « Назад")
        await asyncio.sleep(2)
        await msg.delete()
        return

    text, kb = await _render_chats()
    await message.answer(text, reply_markup=kb)

def get_review_emoji(status: str | None) -> str:
    """Возвращает эмодзи отзыва."""
    if status is None:
        return "💬"
    if status == "positive":
        return "✅"
    if status == "negative":
        return "❌"
    return "💬"

@router.callback_query(F.data.startswith("unhide:"))
async def unhide_chat_handler(callback: CallbackQuery, state: FSMContext):
    chat_id = callback.data.split(":", 1)[1]
    await unhide_chat(chat_id)
    await callback.answer("Чат показан")
    text, kb = await _render_chats()
    await callback.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data.startswith("chat:"))
async def show_chat_detail(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = callback.data.split(":", 1)[1]
    chat = await get_chat(chat_id)

    if not chat:
        await callback.answer("Чат не найден")
        return

    review = get_review_emoji(chat.get("review_status"))

    # Шапка
    text = "╭──────────────────────╮\n"
    text += f"│  👤 {chat['user_name']}\n"
    if chat.get("label"):
        text += f"│  {chat['label']}\n"
    text += "│  ────────────────────\n"
    text += "│\n"

    # Контакты
    if chat.get("phone") or chat.get("address"):
        text += "│  📋 КОНТАКТЫ\n"
        if chat.get("phone"):
            text += f"│  📱 {chat['phone']}\n"
        if chat.get("address"):
            text += f"│  📍 {chat['address']}\n"
        text += "│\n"
        text += "│  ────────────────────\n"
        text += "│\n"

    # Отзыв
    text += "│  ⭐ ОТЗЫВ\n"
    review_status = chat.get("review_status")
    if review_status:
        status_text = "положительный" if review_status == "positive" else "отрицательный"
        text += f"│  {review} {status_text}\n"
        if chat.get("review_text"):
            text += f'│  "{chat["review_text"]}"\n'
        if chat.get("review_rating"):
            text += f"│  Оценка: {chat['review_rating']}/5\n"
    else:
        text += "│  не оставлен\n"
    text += "│\n"
    text += "│  ────────────────────\n"
    text += "│\n"

    # Последнее сообщение
    text += "│  💬 ПОСЛЕДНЕЕ СООБЩЕНИЕ\n"
    last_msg = chat.get("last_message", "")
    if last_msg:
        if len(last_msg) > 100:
            last_msg = last_msg[:97] + "..."
        text += f'│  "{last_msg}"\n'
    else:
        text += "│  —\n"
    text += f"│  🕐 {format_date(chat.get('last_activity', ''))}\n"

    text += "╰──────────────────────╯"

    # Кнопки
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply:{chat_id}"),
        ],
        [
            InlineKeyboardButton(
                text="📌 Открепить" if chat.get("pinned") else "📌 Закрепить",
                callback_data=f"toggle_pin:{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton(text="🏷 Метка", callback_data=f"label:{chat_id}"),
            InlineKeyboardButton(text="📋 История", callback_data=f"history:{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="✏ Телефон", callback_data=f"edit_phone:{chat_id}"),
            InlineKeyboardButton(text="✏ Адрес", callback_data=f"edit_address:{chat_id}"),
        ],
        [
            InlineKeyboardButton(
                text="👁 Показать" if chat.get("hidden") else "👁 Скрыть",
                callback_data=f"{'unhide' if chat.get('hidden') else 'hide'}:{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton(text="« Назад к чатам", callback_data="chats:list"),
        ],
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("hide:"))
async def hide_chat_handler(callback: CallbackQuery):
    chat_id = callback.data.split(":", 1)[1]
    chat = await get_chat(chat_id)

    if not chat:
        await callback.answer("Чат не найден")
        return

    await hide_chat(chat_id)
    await callback.answer("Чат скрыт")

    # Возвращаемся к списку чатов
    text, kb = await _render_chats()
    await callback.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data == "chats:show_hidden")
async def show_hidden_chats(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    chats = await get_all_chats()

    hidden = {chat_id: chat for chat_id, chat in chats.items() if chat.get("hidden")}

    if not hidden:
        await callback.answer("Нет скрытых чатов")
        return

    text = (
        "╭──────────────────╮\n"
        "│  🗑 СКРЫТЫЕ ЧАТЫ   │\n"
        "╰──────────────────╯\n\n"
    )

    for chat_id, chat in hidden.items():
        review = get_review_emoji(chat.get("review_status"))
        text += f"{chat['user_name']} {review}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for chat_id, chat in hidden.items():
        review = get_review_emoji(chat.get("review_status"))
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{chat['user_name']} {review}".strip(),
                callback_data=f"chat:{chat_id}"
            )
        ])

    kb.inline_keyboard.append([
        InlineKeyboardButton(text="👁 Показать все", callback_data="chats:unhide_all"),
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="« Назад к чатам", callback_data="chats:list"),
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "chats:unhide_all")
async def unhide_all_chats(callback: CallbackQuery):
    chats = await get_all_chats()

    for chat_id, chat in chats.items():
        if chat.get("hidden"):
            await unhide_chat(chat_id)

    await callback.answer("Все чаты показаны")
    text, kb = await _render_chats()
    await callback.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data.startswith("toggle_pin:"))
async def toggle_pin(callback: CallbackQuery, state: FSMContext):
    chat_id = callback.data.split(":", 1)[1]
    chat = await get_chat(chat_id)

    if not chat:
        await callback.answer("Чат не найден")
        return

    if chat.get("pinned"):
        await unpin_chat(chat_id)
        await callback.answer("Чат откреплён")
    else:
        await pin_chat(chat_id)
        await callback.answer("Чат закреплён")

    await show_chat_detail(callback, state=state)

@router.callback_query(F.data == "chats:list")
async def back_to_chats(callback: CallbackQuery):
    # Просто вызываем show_chats через message
    text, kb = await _render_chats()
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "menu:main")
async def back_to_menu(callback: CallbackQuery):
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

    # Удаляем текущее сообщение с Inline-кнопками
    await callback.message.delete()
    # Отправляем новое с ReplyKeyboard
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("edit_phone:"))
async def edit_phone(callback: CallbackQuery, state: FSMContext):
    chat_id = callback.data.split(":", 1)[1]
    chat = await get_chat(chat_id)

    if not chat:
        await callback.answer("Чат не найден")
        return

    # Сохраняем chat_id в состоянии, чтобы знать, чей телефон меняем
    await state.update_data(chat_id=chat_id)
    await state.set_state(ChatStates.waiting_phone)

    current = chat.get("phone", "не указан")
    await callback.message.edit_text(
        f"📱 Введите новый номер телефона для {chat['user_name']}:\n"
        f"Текущий: {current}\n\n"
        f"Для отмены нажмите « Назад",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад к чату", callback_data=f"chat:{chat_id}")]
        ])
    )
    await callback.answer()

@router.message(ChatStates.waiting_phone, F.text)
async def process_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    chat_id = data.get("chat_id")

    phone = message.text.strip() if message.text else ""

    # Проверка — если нажал кнопку меню вместо ввода
    if phone in ["📊 Статистика", "💬 Чаты", "⚙️ Настройки"]:
        await message.delete()
        # Всплывающее уведомление — но для message его нет,
        # поэтому отправляем и сразу удаляем ответ
        msg = await message.answer("⚠️ Закончите ввод или нажмите « Назад")
        await asyncio.sleep(2)
        await msg.delete()
        return

    await update_chat_fields(chat_id, phone=phone)
    await state.clear()

    await message.answer(f"✅ Телефон для чата обновлён: {phone}")

    # Показать обновлённый чат
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Назад к чату", callback_data=f"chat:{chat_id}")]
    ])
    await message.answer("Нажмите для возврата:", reply_markup=kb)

@router.callback_query(F.data.startswith("edit_address:"))
async def edit_address(callback: CallbackQuery, state: FSMContext):
    chat_id = callback.data.split(":", 1)[1]
    chat = await get_chat(chat_id)

    if not chat:
        await callback.answer("Чат не найден")
        return

    await state.update_data(chat_id=chat_id)
    await state.set_state(ChatStates.waiting_address)

    current = chat.get("address", "не указан")
    await callback.message.edit_text(
        f"📍 Введите новый адрес для {chat['user_name']}:\n"
        f"Текущий: {current}\n\n"
        f"Для отмены нажмите « Назад",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад к чату", callback_data=f"chat:{chat_id}")]
        ])
    )
    await callback.answer()


@router.message(ChatStates.waiting_address, F.text)
async def process_address(message: Message, state: FSMContext):
    data = await state.get_data()
    chat_id = data.get("chat_id")

    address = message.text.strip() if message.text else ""

    if address in ["📊 Статистика", "💬 Чаты", "⚙️ Настройки"]:
        await message.delete()
        # Всплывающее уведомление — но для message его нет,
        # поэтому отправляем и сразу удаляем ответ
        msg = await message.answer("⚠️ Закончите ввод или нажмите « Назад")
        await asyncio.sleep(2)
        await msg.delete()
        return

    await update_chat_fields(chat_id, address=address)
    await state.clear()

    await message.answer(f"✅ Адрес для чата обновлён: {address}")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Назад к чату", callback_data=f"chat:{chat_id}")]
    ])
    await message.answer("Нажмите для возврата:", reply_markup=kb)

@router.callback_query(F.data.startswith("label:"))
async def show_labels(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = callback.data.split(":")[1]
    chat = await get_chat(chat_id)

    if not chat:
        await callback.answer("Чат не найден")
        return

    current_label = chat.get("label")

    text = (
        f"╭──────────────────╮\n"
        f"│  🏷 Метка         │\n"
        f"╰──────────────────╯\n\n"
        f"👤 {chat['user_name']}\n\n"
        f"Выберите метку:"
    )

    label_map = {
        "garantiya": "🛡 Гарантия",
        "postoyanniy": "⭐ Постоянный",
        "ozhidanie": "💰 Ожидание оплаты",
    }

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    # Первый ряд: Гарантия и Постоянный
    row1 = []
    for code, name in [("garantiya", "🛡 Гарантия"), ("postoyanniy", "⭐ Постоянный")]:
        prefix = "✅ " if current_label == label_map[code] else ""
        row1.append(InlineKeyboardButton(text=f"{prefix}{name}", callback_data=f"set_label:{chat_id}:{code}"))
    kb.inline_keyboard.append(row1)

    # Второй ряд: Ожидание оплаты
    code = "ozhidanie"
    name = "💰 Ожидание оплаты"
    prefix = "✅ " if current_label == label_map[code] else ""
    kb.inline_keyboard.append([
        InlineKeyboardButton(text=f"{prefix}{name}", callback_data=f"set_label:{chat_id}:{code}")
    ])

    # Третий ряд: Своя метка
    is_custom = current_label is not None and current_label not in label_map.values()
    custom_prefix = "✅ " if is_custom else ""
    kb.inline_keyboard.append([
        InlineKeyboardButton(text=f"{custom_prefix}✏ Своя метка", callback_data=f"custom_label:{chat_id}")
    ])

    # Четвёртый ряд: Без метки
    prefix = "✅ " if current_label is None else ""
    kb.inline_keyboard.append([
        InlineKeyboardButton(text=f"{prefix}❌ Без метки", callback_data=f"set_label:{chat_id}:none")
    ])

    # Назад
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="« Назад к чату", callback_data=f"chat:{chat_id}")
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("set_label:"))
async def set_label(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    chat_id = parts[1]
    code = parts[2]

    label_map = {
        "garantiya": "🛡 Гарантия",
        "postoyanniy": "⭐ Постоянный",
        "ozhidanie": "💰 Ожидание оплаты",
    }

    new_label = None if code == "none" else label_map.get(code)
    await update_chat_fields(chat_id, label=new_label)

    await callback.answer("Метка обновлена")
    await show_labels(callback, state=state)

@router.callback_query(F.data.startswith("history:"))
async def show_history(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.clear()
    messages_api = kwargs.get("messages_api")
    if not messages_api:
        await callback.answer("Ошибка доступа к API")
        return
    chat_id = callback.data.split(":", 1)[1]
    chat = await get_chat(chat_id)

    if not chat:
        await callback.answer("Чат не найден")
        return

    try:
        result = await messages_api.get_messages(chat_id, limit=10)
        msgs = result.get("messages", [])
    except Exception as e:
        await callback.answer(f"Ошибка загрузки сообщений: {e}")
        return

    if not msgs:
        text = (
            f"╭──────────────────╮\n"
            f"│  📋 История       │\n"
            f"╰──────────────────╯\n\n"
            f"👤 {chat['user_name']}\n\n"
            f"Сообщений пока нет."
        )
    else:
        text = (
            f"╭──────────────────╮\n"
            f"│  📋 История       │\n"
            f"╰──────────────────╯\n\n"
            f"👤 {chat['user_name']}\n\n"
        )
        for msg in reversed(msgs):
            direction = "📤" if msg.get("direction") == "out" else "📥"
            msg_text = ""
            if msg.get("content"):
                msg_text = msg["content"].get("text", "")
            dt = format_date(msg.get("created", ""))
            text += f"{direction} {dt}: {msg_text}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply:{chat_id}")],
        [InlineKeyboardButton(text="« Назад к чату", callback_data=f"chat:{chat_id}")],
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("reply:"))
async def start_reply(callback: CallbackQuery, state: FSMContext):
    chat_id = callback.data.split(":", 1)[1]
    chat = await get_chat(chat_id)

    if not chat:
        await callback.answer("Чат не найден")
        return

    await state.update_data(chat_id=chat_id)
    await state.set_state(ChatStates.waiting_reply)

    await callback.message.edit_text(
        f"💬 Ответ для {chat['user_name']}:\n\n"
        f"Введите текст сообщения...\n"
        f"Для отмены нажмите « Назад",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад к чату", callback_data=f"chat:{chat_id}")]
        ])
    )
    await callback.answer()

@router.message(ChatStates.waiting_reply, F.text)
async def process_reply(message: Message, state: FSMContext, **kwargs):
    data = await state.get_data()
    chat_id = data.get("chat_id")
    text = message.text.strip()

    if text in ["📊 Статистика", "💬 Чаты", "⚙️ Настройки"]:
        await message.delete()
        msg = await message.answer("⚠️ Закончите ввод или нажмите « Назад")
        await asyncio.sleep(2)
        await msg.delete()
        return

    messages_api = kwargs.get("messages_api")
    if not messages_api:
        await message.answer("❌ Ошибка доступа к API")
        await state.clear()
        return

    try:
        await messages_api.send_message(chat_id, text)
        await message.answer(f"✅ Сообщение отправлено.")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")

    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Назад к чату", callback_data=f"chat:{chat_id}")]
    ])
    await message.answer("Нажмите для возврата:", reply_markup=kb)

@router.callback_query(F.data.startswith("custom_label:"))
async def custom_label(callback: CallbackQuery, state: FSMContext):
    chat_id = callback.data.split(":", 1)[1]
    chat = await get_chat(chat_id)

    if not chat:
        await callback.answer("Чат не найден")
        return

    await state.update_data(chat_id=chat_id)
    await state.set_state(ChatStates.waiting_custom_label)

    await callback.message.edit_text(
        f"✏ Введите свою метку для {chat['user_name']}:\n\n"
        f"Для отмены нажмите « Назад",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад", callback_data=f"label:{chat_id}")]
        ])
    )
    await callback.answer()

@router.message(ChatStates.waiting_custom_label, F.text)
async def process_custom_label(message: Message, state: FSMContext):
    data = await state.get_data()
    chat_id = data.get("chat_id")

    label_text = message.text.strip()
    # Парсим эмодзи и текст
    import re
    emoji_pattern = re.compile(
        "[\U0001F300-\U0001F9FF"  # эмодзи
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U0001F600-\U0001F64F"
        "\U0001F680-\U0001F6FF"
        "\U00002600-\U000026FF"
        "\U0001F1E0-\U0001F1FF"
        "]+", flags=re.UNICODE
    )

    emojis_found = emoji_pattern.findall(label_text)
    if emojis_found:
        # Берём первое найденное эмодзи
        label_emoji = emojis_found[0]
        # Убираем все эмодзи из текста метки
        label_text_clean = emoji_pattern.sub("", label_text).strip()
    else:
        label_emoji = "🏷"
        label_text_clean = label_text

    if not label_text_clean:
        label_text_clean = label_text  # если одни эмодзи, используем как есть

    # Сохраняем и эмодзи и текст
    full_label = f"{label_emoji} {label_text_clean}".strip()

    if label_text in ["📊 Статистика", "💬 Чаты", "⚙️ Настройки"]:
        await message.delete()
        msg = await message.answer("⚠️ Закончите ввод или нажмите « Назад")
        await asyncio.sleep(2)
        await msg.delete()
        return

    # Ограничим длину метки
    if len(label_text) > 20:
        label_text = label_text[:20]

    await update_chat_fields(chat_id, label=label_text)
    await state.clear()

    await message.answer(f"✅ Метка обновлена: {label_text}")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Назад к чату", callback_data=f"chat:{chat_id}")]
    ])
    await message.answer("Нажмите для возврата:", reply_markup=kb)