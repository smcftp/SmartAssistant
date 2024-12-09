from telethon import TelegramClient, events
from rapidfuzz import fuzz, process
import asyncio
import time

from telethon.tl.types import Channel

import api_gateway.utils as gateway_utils

import functions.config as config


async def get_all_chats():
    """
    Получить список всех чатов.
    """
    async with config.telegram_client:
        dialogs = await config.telegram_client.get_dialogs()
        all_chats = [
            {"id": dialog.id, "name": dialog.name}
            for dialog in dialogs
        ]
        print(all_chats)
        return all_chats
    
async def get_private_chats():
    """
    Получить список только личных чатов (диалогов), включая ботов.
    """
    async with config.telegram_client:
        dialogs = await config.telegram_client.get_dialogs()
        private_chats = [
            {"id": dialog.id, "name": dialog.name}
            for dialog in dialogs
            if dialog.is_user  # Проверяем, что это личный чат
        ]
        return private_chats
    
async def get_private_chats_withoiut_bot():
    """
    Получить список только личных чатов с реальными пользователями (исключая ботов).
    """
    async with config.telegram_client:
        dialogs = await config.telegram_client.get_dialogs()
        private_chats = [
            {"id": dialog.id, "name": dialog.name}
            for dialog in dialogs
            if dialog.is_user and not dialog.entity.bot  # Исключаем ботов
        ]
        
        # Печатаем для отладки
        # for chat in private_chats:
        #     print(f"Имя: {chat['name']}, ID: {chat['id']}")
        
        return private_chats

async def get_channels():
    """
    Получить список всех каналов в Telegram.
    """
    async with config.telegram_client:
        dialogs = await config.telegram_client.get_dialogs()
        # Фильтруем только каналы
        channels = [
            {"id": dialog.id, "name": dialog.name}
            for dialog in dialogs
            if getattr(dialog.entity, "broadcast", False)  # Проверяем, что это канал
        ]
        return channels

async def send_message(chat_id: int, message: str) -> bool:
    """
    Отправить сообщение в чат по его ID.

    Args:
        chat_id (int): ID чата, куда нужно отправить сообщение.
        message (str): Текст сообщения.

    Returns:
        bool: True, если сообщение успешно отправлено, иначе False.
    """
    async with config.telegram_client:
        try:
            await config.telegram_client.send_message(chat_id, message)
            print(f"Сообщение отправлено в чат с ID {chat_id}: {message}")
            return True
        except Exception as e:
            print(f"Ошибка при отправке сообщения в чат с ID {chat_id}: {str(e)}")
            return False


async def get_last_messages(chat_id, limit=5):
    """
    Получить последние сообщения из чата по его ID.

    Args:
        chat_id (int): ID чата, из которого нужно получить сообщения.
        limit (int): Количество сообщений для чтения (по умолчанию 5).

    Returns:
        list: Список текстов последних сообщений.
    """
    async with config.telegram_client:
        try:
            messages = await config.telegram_client.get_messages(chat_id, limit=limit)
            return [msg.text for msg in messages if msg.text is not None]
        except Exception as e:
            print(f"Ошибка при получении сообщений из чата с ID {chat_id}: {str(e)}")
            return []


async def find_chat(dialogs, recipient):
    """
    Найти чат по списку диалогов и имени адресата (группы или пользователя).
    
    Args:
        dialogs (list): Список чатов в формате [{"id": ..., "name": ...}, ...].
        recipient (str): Имя чата или группы для поиска.
    
    Returns:
        dict: Найденный чат {"id": ..., "name": ...} или None, если чат не найден.
    """
    # Нормализуем имя адресата
    normalized_recipient = recipient.lower().strip()

    # Шаг 1: Быстрый поиск 100% совпадения
    for dialog in dialogs:
        dialog_name = (dialog["name"]).lower().strip()
        if dialog_name == normalized_recipient:
            return {"id": dialog["id"], "name": dialog["name"]}

    # Шаг 2: Более сложный поиск с семантическим сравнением
    dialog_dict = {dialog["name"]: dialog["id"] for dialog in dialogs}

    # Выполняем фильтрацию с использованием Fuzzy Matching
    results = process.extract(
        query=normalized_recipient,
        choices=dialog_dict.keys(),  # Используем только имена для сравнения
        scorer=fuzz.token_sort_ratio,  # Учитываем перестановку слов
        limit=15  # Возвращаем до 5 лучших совпадений
    )

    # Логируем результаты для отладки
    print("Результаты совпадения:", results)

    # Подготовка данных для классификации
    sequence_to_classify = recipient
    primary_labels = [item[0] for item in results]  # Извлекаем совпавшие имена

    start_time_gpt = time.perf_counter()
    result = await gateway_utils.classify_text_async(sequence_to_classify=sequence_to_classify, candidate_labels=primary_labels)
    end_time_gpt = time.perf_counter()
    execution_time_gpt = end_time_gpt - start_time_gpt
    print(f"Время выполнения classify_text_async: {execution_time_gpt:.6f} секунд")
    print(result)

    # Ищем совпадение по name и создаем новый словарь
    matched_dialogs = next(
        ({"id": dialog_id, "name": name} for name, dialog_id in dialog_dict.items() if name == result),
        None  # Возвращаем None, если совпадение не найдено
    )

    print("Совпавшие чаты:", matched_dialogs)

    # Возвращаем словарь совпадений
    return matched_dialogs
    



# Тестируем

# async def main():
#     start_time_all = time.perf_counter()
#     start_time_1 = time.perf_counter()
#     # dialogs = await get_chats()
#     end_time_1 = time.perf_counter()
    
#     await get_private_chats()
    
#     # from pprint import pprint
#     # pprint(dialogs)
    
#     # recipient = "Андрей хэппи эй ай"
#     # message = "Привет"
    
#     # # Измеряем время выполнения find_chat
#     # start_time = time.perf_counter()
#     # found_chat = await find_chat(dialogs, recipient)
#     # end_time = time.perf_counter()
    
#     # execution_time = end_time - start_time  # Вычисляем время выполнения
#     # execution_time_1 = end_time_1 - start_time_1
    
#     # if found_chat:
#     #     print(f"Найден чат: ID={found_chat['id']}, Name={found_chat['name']}")
#     # else:
#     #     print("Чат не найден")
        
#     # end_time_all = time.perf_counter()
#     # execution_time_all = end_time_all - start_time_all
    
#     # print(f"Время выполнения find_chat: {execution_time:.6f} секунд")
#     # print(f"Время выполнения get_chats: {execution_time_1:.6f} секунд")
#     # print(f"Время выполнения get_chats: {execution_time_all:.6f} секунд")
    
    
#     # await send_message(chat_name=found_chat.name, message=message)
    
# if __name__ == "__main__":
#     asyncio.run(main())