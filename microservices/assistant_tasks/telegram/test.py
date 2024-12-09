import pytest
from datetime import datetime
import asyncio

from classification import classify_and_filter_message_action  


async def run_tests():
    """
    Функция для последовательного тестирования classify_and_filter_message_action.
    """
    # Текущая дата и время
    current_time = datetime.utcnow()

    # Тестовые данные
    test_cases = [
        # Тесты для "send"
        {
            "input": "Напиши Андрею: Привет, как дела?",
            "expected": {
                "action_type": "send",
                "recipient": "Андрей",
                "read_count": None,
                "message_content": "Привет, как дела?",
            },
        },
        {
            "input": "Напиши smcftp: Привет, как дела? на немецком",
            "expected": {
                "action_type": "send",
                "recipient": "Андрей",
                "read_count": None,
                "message_content": "Привет, как дела?",
            },
        },
        {
            "input": "Напиши smcftp: Привет, как дела? на китайском",
            "expected": {
                "action_type": "send",
                "recipient": "Андрей",
                "read_count": None,
                "message_content": "Привет, как дела?",
            },
        },
        {
            "input": "Напиши smcftp: Привет, как дела? на английском",
            "expected": {
                "action_type": "send",
                "recipient": "Андрей",
                "read_count": None,
                "message_content": "Привет, как дела?",
            },
        },
        {
            "input": "Send this message in English: 'Hello, how are you?'",
            "expected": {
                "action_type": "send",
                "recipient": None,  # Не указан получатель
                "read_count": None,
                "message_content": "Hello, how are you?",
            },
        },
        {
            "input": "Отправь сообщение Ивану: Встреча в 15:00.",
            "expected": {
                "action_type": "send",
                "recipient": "Иван",
                "read_count": None,
                "message_content": "Встреча в 15:00.",
            },
        },
        {
            "input": "Напиши: Позвони мне позже.",
            "expected": {
                "action_type": "send",
                "recipient": None,  # Получатель не указан
                "read_count": None,
                "message_content": "Позвони мне позже.",
            },
        },

        # Тесты для "read"
        {
            "input": "Прочитай последние 5 сообщений из группы 'Работа'.",
            "expected": {
                "action_type": "read",
                "recipient": "Работа",
                "read_count": 5,
                "message_content": None,
            },
        },
        {
            "input": "Прочитай сообщения от Марии.",
            "expected": {
                "action_type": "read",
                "recipient": "Мария",
                "read_count": 1,  # Значение по умолчанию
                "message_content": None,
            },
        },
        {
            "input": "Прочитай 2 сообщения от коллеги.",
            "expected": {
                "action_type": "read",
                "recipient": "коллега",  # Условная обработка
                "read_count": 2,
                "message_content": None,
            },
        },

        # Тесты для "delete"
        {
            "input": "Удалить последнее сообщение из чата с Иваном.",
            "expected": {
                "action_type": "delete",
                "recipient": "Иван",
                "read_count": None,
                "message_content": None,
            },
        },
        {
            "input": "Очисти историю сообщений в чате 'Проект'.",
            "expected": {
                "action_type": "delete",
                "recipient": "Проект",
                "read_count": None,
                "message_content": None,
            },
        },

        # Пограничные случаи
        {
            "input": "Напиши сообщение",
            "expected": {
                "action_type": False,
                "recipient": False,
                "read_count": None,
                "message_content": None,
            },
        },
        {
            "input": "",
            "expected": {
                "action_type": False,
                "recipient": False,
                "read_count": None,
                "message_content": None,
            },
        },
        {
            "input": "Как дела у Андрея?",
            "expected": {
                "action_type": False,
                "recipient": False,
                "read_count": None,
                "message_content": None,
            },
        },
        {
            "input": "Прочитай сообщения от Ивана",
            "expected": {
                "action_type": "read",
                "recipient": "Иван",
                "read_count": 1,  # Значение по умолчанию
                "message_content": None,
            },
        },
        {
            "input": "Удалить сообщения",
            "expected": {
                "action_type": "delete",
                "recipient": None,  # Чат не указан
                "read_count": None,
                "message_content": None,
            },
        },
    ]


    # Последовательное выполнение тестов
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nТест {i}:")
        print(f"Входные данные: {test_case['input']}")

        result = await classify_and_filter_message_action(
            current_datetime=current_time,
            message_text=test_case["input"]
        )

        print(f"Ожидаемый результат: {test_case['expected']}")
        print(f"Фактический результат: {result}")

        # Проверка соответствия
        if result == test_case["expected"]:
            print("✅ Тест пройден!")
        else:
            print("❌ Тест не пройден!")

# Запускаем тесты
if __name__ == "__main__":
    asyncio.run(run_tests())
