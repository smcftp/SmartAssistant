from telethon import TelegramClient, events
import asyncio

# Импорт клиента телеграмм
from functions.config import telegram_client

from functions.config import bot_tg, dp

# Запись состояния в Redis
from functions.redis_client import set_user_state

# Импорт отправки сообщения в голосе
from functions.ftt_utils import speak_text_gtts_and_send

# # Настройки для озвучивания текста
# engine = pyttsx3.init()

# def speak_text(text):
#     """
#     Озвучить текст с помощью pyttsx3.
#     """
#     engine.say(text)
#     engine.runAndWait()

async def handle_message(event):
    """
    Обработчик входящих сообщений.
    """
    sender = await event.get_sender()  # Получаем отправителя
    if sender.bot:  # Игнорируем ботов
        return

    sender_name = sender.first_name or "Неизвестный пользователь"
    message_text = event.text or "Сообщение без текста"

    # Получаем user_id (текущий аккаунт)
    me = await telegram_client.get_me()  # Вызов вне "async with"
    chat_id = me.id  # user_id для отправки сообщения через бота
    
    # Получаем user_id отправителя
    sender = await event.get_sender()  # Получаем объект отправителя
    sender_user_id = sender.id
    
    if sender_user_id == chat_id:
        return

    print(f"Ваш user_id: {chat_id}")
    print("Начинаем отправку сообщения")

    # Отправляем сообщение пользователю в Telegram
    try:
        text = f"Пришло сообщение от {sender_name}. Хотите его озвучить?"
        await bot_tg.send_message(
            chat_id=chat_id,  # chat_id = user_id
            text=text
        )
        await speak_text_gtts_and_send(chat_id=chat_id, text=text)
        print("Сообщение успешно отправлено")
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
    
    await set_user_state(user_id=chat_id, waiting_answer=True, income_message_text=message_text)    

    print("Функция завершена")

    # Озвучиваем факт получения сообщения
    # speak_text(f"Пришло сообщение от {sender_name}. Хотите его озвучить?")

    # Ждем ответа пользователя
    # print(f"Пришло сообщение от {sender_name}: {message_text}")
    # user_response = input("Хотите озвучить сообщение? (да/нет): ").strip().lower()

    # # Логика ответа пользователя
    # if user_response in ["да", "yes"]:
    #     speak_text(f"Сообщение от {sender_name}: {message_text}")
    # elif user_response in ["нет", "no"]:
    #     speak_text("Сообщение не будет озвучено.")
    # else:
    #     speak_text("Ответ не распознан. Сообщение пропущено.")

@telegram_client.on(events.NewMessage)
async def on_new_message(event):
    """
    Обработчик новых личных сообщений.
    """
    print("прослушка")
    if event.is_private:  # Отслеживаем только личные сообщения
        await handle_message(event)
    print("прослушка 1")

async def real_time_message_listener():
    """
    Основная функция для запуска прослушивания личных сообщений.
    """
    print("Прослушивание новых сообщений запущено...")
    async with telegram_client:
        await telegram_client.run_until_disconnected()