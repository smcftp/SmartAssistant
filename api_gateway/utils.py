from openai import AsyncOpenAI
import json

from aiogram.types import Message

# Импорт инструментов для работы с Redis
from functions.redis_client import set_user_state, get_user_state

# Параметры настроек
from functions.config import set

# Импорт отправки сообщения в голосе
from functions.ftt_utils import speak_text_gtts_and_send

# Инициализация клиента OpenAI
client = AsyncOpenAI(
    api_key=set.openai_api_key
)

async def classify_text_async(sequence_to_classify: str, candidate_labels: list[str]) -> str:
    """
    Асинхронно классифицирует текст в одну из заданных категорий с использованием OpenAI.

    Args:
        sequence_to_classify (str): Текст для классификации.
        candidate_labels (list): Список категорий для классификации.
        client: Асинхронный экземпляр OpenAI клиента.

    Returns:
        str: Категория, к которой относится текст, или сообщение об ошибке.
    """
    # Определение инструмента для функции классификации
    tools = [
        {
            "type": "function",
            "function": {
                "name": "classify_text",
                "description": "Classify the input text into predefined categories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "The category the input text belongs to.",
                        }
                    },
                    "required": ["category"],
                    "additionalProperties": False,
                },
            }
        }
    ]

    # Формируем промпт для модели
    prompt = (
        f"Classify the following text: '{sequence_to_classify}' into one of the following categories: "
        f"{', '.join(candidate_labels)}. "
        "Respond with the category that best describes the text."
    )

    try:
        model = "gpt-3.5-turbo"
        # model="gpt-4o-mini"
        
        # Создаём асинхронный запрос к OpenAI
        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a text classifier."},
                {"role": "user", "content": prompt}
            ],
            tools=tools,
        )

        # Получаем категорию из результатов вызова функции
        category = str(json.loads(completion.choices[0].message.tool_calls[0].function.arguments)["category"])
        return category
    except (KeyError, ValueError, TypeError) as e:
        return f"Ошибка при анализе результата: {e}"
    except Exception as e:
        return f"Общая ошибка: {e}"


# Класификация сообщений
async def process_user_message(user_message: str,  tg_message: Message):
    """
    Обрабатывает входящее сообщение от пользователя и классифицирует его на основе меток.

    Args:
        user_message (str): Сообщение от пользователя.

    Returns:
        dict: Результат классификации и дальнейшей обработки.
    """

    # Получаем текущее состояние пользователя из Redis
    user_id = str(tg_message.from_user.id)
    user_state = await get_user_state(user_id)
    if user_state:
        waiting_answer = user_state["waiting_answer"]
        income_message_text = user_state["income_message_text"]
    else:
        waiting_answer = False
        income_message_text = ""

    if waiting_answer == False:
        """
            Контекст обычного входящего сообщения
            Нет дополнительных контекстов
        """
        
        # Первая классификация
        primary_labels = ["Функции управления умным домом", "Функции личного ассистента", "Другое"]
        # primary_labels = ["Функции управления умным домом", "Функции личного ассистента"]
        primary_classification = await classify_text_async(sequence_to_classify=user_message, candidate_labels=primary_labels)
        print(f"\nprimary_classification = {primary_classification}\n")

        # Проверяем результат первой классификации
        # primary_category = str(primary_classification.get("category", "Прочий мусор"))
        # print(primary_category)
        if primary_classification == "Другое":
            print("Отправляем другое")
        
            return {
                "primary_category": "Прочий мусор",
                "secondary_category": "None",
                "details": f"Cообщение не относится к поддерживаемым категориям."
            }

        if primary_classification == "Функции управления умным домом":
            return {"category": "Функции управления умным домом", "details": "Функция умного дома пока не реализована."}

        # Если категория "Функции личного ассистента", проводим вторичную классификацию
        if primary_classification == "Функции личного ассистента":
            secondary_labels = [
                "Менеджер напоминаний и планирования",
                "Менеджер мессенджера Telegram",
                "Менеджер видеозвонков",
                "Менеджер скриншотов",
                "Менеджер переводов"
            ]
            
            secondary_classification = await classify_text_async(sequence_to_classify=user_message, candidate_labels=secondary_labels)
            print(f"\nsecondary_classification = {secondary_classification}\n")

            # secondary_category = secondary_classification.get("category", "Неопределено")
            # print(secondary_category)

            return {
                "primary_category": "Функции личного ассистента",
                "secondary_category": secondary_classification,
                "details": f"Сообщение классифицировано как: {secondary_classification}"
            }

        # Если ничего не подошло, возвращаем сообщение об ошибке
        return {"category": "Неопределено", "details": "Не удалось классифицировать сообщение."}
    
    elif waiting_answer == True:
        """
        Контекст ожидания ответа пользователя на вопрос:
        "Зачитать ли сообщение?"
        """
        try:
            # Изменения состояния прослушивания ответа
            await set_user_state(user_id=user_id, waiting_answer=False, income_message_text="")

            # Класификация ответа
            # primary_labels = ["Да, зачитать сообщение, которое пришло", "Нет, не зачитывать сообщение, которое пришло", "Прочее"]
            primary_labels = ["Зачитать сообщение", "Не зачитывать сообщение", "Прочее"]

            primary_classification = await classify_text_async(sequence_to_classify=user_message, candidate_labels=primary_labels)
            
            print(f"primary_classification = {primary_classification}")  # Вывод классификации для отладки

            # Проверка и обработка результата классификации
            if primary_classification == "Зачитать сообщение":
                text = f"Вам написали следующее сообщение: {income_message_text}"
                await tg_message.answer(text=text)
                await speak_text_gtts_and_send(chat_id=user_id, text=text)
                return {"category": "Прочий мусор", "details": "Сообщение не относится к поддерживаемым категориям."}
            
            elif primary_classification == "Не зачитывать сообщение":
                text = "Хорошо. Сообщение не будет озвучено. С чем вам помочь еще?"
                await tg_message.answer(text=text)
                await speak_text_gtts_and_send(chat_id=user_id, text=text)
                return {"category": "Прочий мусор", "details": "Сообщение не относится к поддерживаемым категориям."}
            
            else:
                # Обработка случая, когда классификация не совпала с ожидаемыми метками
                text = "Извините, не могу понять ваш ответ."
                await tg_message.answer(text=text)
                await speak_text_gtts_and_send(chat_id=user_id, text=text)
                return {"category": "Неопределено", "details": "Ответ не распознан."}

        except Exception as e:
            # Обработка всех возможных ошибок
            print(f"Произошла ошибка при обработке ответа пользователя: {e}")
            await tg_message.answer("Произошла ошибка при обработке вашего ответа. Попробуйте снова.")
            return {"category": "Ошибка", "details": f"Ошибка: {e}"}

        
        
