import asyncio
from datetime import datetime
from avito.messages import AvitoMessages
from aiogram import Bot
from data.storage import upsert_chat, get_chat, update_chat_fields, get_all_chats, hide_chat, read_settings

def analyze_review(review: dict) -> tuple[str, str, int]:
    """Возвращает (status, text, rating)."""
    score = review.get("score", 0)
    text = review.get("text", "")

    negative_words = [
        "не качественно", "некачественно",
        "контора", "компания",
        "дорого", "дороговато",
        "не приехал", "неприехал",
        "ужас", "кидалово", "обман", "развод", "плохо", "кошмар",
        "не советую", "не рекомендую", "не обращайтесь",
        "зря потратил", "деньги на ветер", "пожалел",
        "сломал", "сломали", "испортил", "испортили",
        "не работает", "неработает", "потек", "потечь",
        "брак", "не починил", "не починили", "не помог", "не помогло",
        "не пришёл", "непришёл", "опоздал",
        "груб", "грубил", "хамил", "нахал",
        "гарантия не",
        "ужасный", "отвратительно", "не доволен", "недоволен",
        "разочарован", "обманул", "обманули",
        "не связывайтесь", "обходите стороной",
        "грязь", "грязно", "наследил", "наследили",
        "безответственный", "пропал", "пропали",
        "игнорирует", "молчит", "не отвечает",
        "мастер никакой", "руки из",
        "лучше бы", "зря", "потратил", "выкинул",
        "дешёвка", "халтура", "халтурщик",
        "не закончил", "недоделал", "бросил",
        "нервы", "вымотал", "настроение испортил",
        "цена завышена", "накрутка",
        "не приехали", "кинул", "кинули",
        "мошенник", "мошенники", "аферист",
        "не советую", "никому не",
    ]

    is_negative = score < 5 or any(word in text.lower() for word in negative_words)

    status = "negative" if is_negative else "positive"
    return status, text, score

async def sync_all_chats(messages_api: AvitoMessages):
    """Вызывается при старте. Добавляет в JSON все чаты, которых там ещё нет."""
    try:
        result = await messages_api.get_chats(unread_only=False, limit=100)
        chats = result.get("chats", [])

        for chat in chats:
            chat_id = chat.get("id")

            # Проверяем, есть ли уже такой чат в JSON
            existing = await get_chat(chat_id)
            if existing is not None:
                # Чат уже есть — обновляем last_activity и last_message
                last_msg = chat.get("last_message", {})
                content = last_msg.get("content", {})
                last_text = content.get("text", "") if content else ""
                await update_chat_fields(
                    chat_id,
                    last_activity=chat.get("updated", ""),
                    last_message=last_text,
                )
                continue

            # Новый чат — сохраняем
            user_name = "Клиент"
            avito_user_id = None
            if chat.get("users"):
                for user in chat["users"]:
                    if user["id"] != messages_api.user_id:
                        user_name = user.get("name", "Клиент")
                        avito_user_id = user["id"]
            
            # Достаём item_id из контекста
            item_id = None
            context = chat.get("context", {})
            if context.get("type") == "item":
                item_id = context.get("value", {}).get("id")

            last_msg = chat.get("last_message", {})
            if last_msg:
                content = last_msg.get("content", {})
                last_text = content.get("text", "") if content else ""
            else:
                last_text = ""

            await upsert_chat(chat_id, {
                "user_name": user_name,
                "avito_user_id": avito_user_id,
                "item_id": item_id,
                "last_activity": chat.get("updated", ""),
                "last_message": last_text,
                "pinned": False,
                "label": None,
                "hidden": False,
                "phone": None,
                "address": None,
                "review_status": None,
                "review_text": None,
                "review_rating": None,
            })

        # Получаем все отзывы продавца
        try:
            all_reviews = await messages_api.api.get_reviews(messages_api.user_id, limit=50, offset=0)
            reviews_list = all_reviews.get("reviews", [])

            all_chats = await get_all_chats()
            for chat_id, chat_data in all_chats.items():
                user_name = chat_data.get("user_name", "").lower()
                if not user_name:
                    continue

                # Ищем отзыв от этого клиента
                found = None
                for review in reviews_list:
                    sender_name = review.get("sender", {}).get("name", "").lower()
                    if sender_name == user_name:
                        found = review
                        break

                if found:
                    status, text, rating = analyze_review(found)
                    await update_chat_fields(
                        chat_id,
                        review_status=status,
                        review_text=text,
                        review_rating=rating,
                    )
        except Exception as e:
            print(f"Ошибка синхронизации отзывов: {e}")

        print(f"Синхронизировано чатов: {len(chats)}")

    except Exception as e:
        print(f"Ошибка синхронизации чатов: {e}")

async def poll_chats(bot, messages_api, admin_id):
    known_chats = set()
    while True:
        try:
            result = await messages_api.get_chats(unread_only=True)
            chats = result.get("chats", [])

            for chat in chats:
                chat_id = chat.get("id")

                if chat_id not in known_chats:
                    known_chats.add(chat_id)

                    user_name = "Клиент"
                    avito_user_id = None
                    if chat.get("users"):
                        for user in chat["users"]:
                            if user["id"] != messages_api.user_id:
                                user_name = user.get("name", "Клиент")
                                avito_user_id = user["id"]

                    last_msg = chat.get("last_message", {})
                    if last_msg:
                        content = last_msg.get("content", {})
                        last_text = content.get("text", "") if content else ""
                    else:
                        last_text = ""

                    text = f"Новое сообщение от {user_name}:\n{last_text}"
                    await bot.send_message(admin_id, text)

                    # Достаём item_id из контекста
                    item_id = None
                    context = chat.get("context", {})
                    if context.get("type") == "item":
                        item_id = context.get("value", {}).get("id")

                    await upsert_chat(chat_id, {
                        "user_name": user_name,
                        "avito_user_id": avito_user_id,
                        "item_id": item_id,
                        "last_activity": chat.get("updated", ""),
                        "last_message": last_text,
                        "pinned": False,
                        "label": None,
                        "hidden": False,
                        "phone": None,
                        "address": None,
                        "review_status": None,
                        "review_text": None,
                        "review_rating": None,
                    })

            # Автоскрытие старых чатов
            all_chats = await get_all_chats()
            now = datetime.now()
            settings = await read_settings()
            hide_days = settings.get("hide_days", 7)

            for chat_id, chat in all_chats.items():
                if chat.get("pinned") or chat.get("hidden"):
                    continue

                last_activity = chat.get("last_activity")
                if not last_activity:
                    continue

                try:
                    if isinstance(last_activity, (int, float)):
                        last_date = datetime.fromtimestamp(last_activity)
                    else:
                        last_date = datetime.fromisoformat(str(last_activity).replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    continue

                if (now - last_date).days >= hide_days:
                    await hide_chat(chat_id)

        except Exception as e:
            print(f"Ошибка опроса: {e}")
        await asyncio.sleep(30)