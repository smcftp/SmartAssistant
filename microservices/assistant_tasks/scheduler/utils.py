import json
from datetime import datetime, timedelta
import re
import asyncio
from openai import AsyncOpenAI

from aiogram.types import Message

# Настройки проекта
import functions.config as config

# Управление БД для расписания
import microservices.assistant_tasks.scheduler.crud as crud
from microservices.assistant_tasks.scheduler.database_utils import async_session

# Управление расписанием
import microservices.assistant_tasks.scheduler.schedule as schedule

# Импорт отправки сообщения в голосе
from functions.ftt_utils import speak_text_gtts_and_send

client = AsyncOpenAI(
    api_key=config.set.openai_api_key
)

# Извлечение из сообщение планировщика основных компонентов для БД
async def classify_and_extract_task_details(current_datetime: datetime, message_text: str):
    tools = [
        {
            "type": "function",
            "function": {
                "name": "classify_text",
                "description": "Classify and extract task details for scheduling. ",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_text": {
                            "type": "string", 
                            "description": f"""
                                Paraphrase the task description, converting it into a neutral and appropriate form, ensuring that:
                                - The task text MUST does not include any reference to the EXECUTION DATE or TIME INTERVAL.
                                - The resulting text MUST BE is concise, focusing solely on the essence of the task.

                                For example:
                                - Original: "Make an appointment with Oleg for tomorrow." → Result: "Meeting with Oleg.".
                                - Original: "Call the client at 3 pm." → Result: "Call to client.".

                                !!! If task_text is NOT defined in "{message_text}", return only False !!!
                            """
                        },
                        "start_time": {
                            "type": "string",
                            "description": f"""
                                The start time of the task in ISO 8601 format (e.g., 2024-12-01 14:00:00). 
                                !!! If start_time NOT defined in "{message_text}", return only False !!!
                            """
                        },
                        "repeat_interval": {
                            "type": "string",
                            "description": "The repeat interval of the task (e.g., 'daily', 'weekly', or 'NULL' for no repetition)."
                        },
                    },
                    "required": ["task_text", "start_time", "repeat_interval"],
                    "additionalProperties": False,
                },
            }
        }
    ]

    # Формируем промпт
    prompt = (
        f"""
            Current datetime is: {current_datetime.isoformat()}.\n"
            Process the following scheduling request: '{message_text}'.\n"
            Return the task details in this format: task_text, start_time (ISO 8601), and repeat_interval ('daily', 'weekly', or 'NULL').
            If task_text or start_time or both of them NOT defined in "{message_text}", return instead of him (them) only False
        """
    )

    try:
        # Создаём асинхронный запрос к OpenAI
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a scheduling assistant."},
                {"role": "user", "content": prompt}
            ],
            tools=tools,
        )

        # Обрабатываем результат
        result = json.loads(completion.choices[0].message.tool_calls[0].function.arguments)

        # Проверяем каждое поле и обрабатываем отсутствующие данные
        task_text = result.get("task_text", None)
        start_time_raw = result.get("start_time", None)
        repeat_interval = result.get("repeat_interval", None)

        # Если данных нет, устанавливаем значение False
        if not task_text:
            task_text = False
            
        # print(current_datetime, "\n", start_time_raw)

        if datetime.fromisoformat(start_time_raw) == current_datetime:
            start_time_raw = False
        else:
            try:
                start_time_raw = datetime.fromisoformat(start_time_raw)
            except ValueError:
                start_time_raw = False

        # Устанавливаем значение 'NULL' по умолчанию, если repeat_interval отсутствует
        if not repeat_interval:
            repeat_interval = 'NULL'

        # Формируем и возвращаем результат
        return {
            "task_text": task_text,
            "start_time": start_time_raw,
            "repeat_interval": repeat_interval,
        }

    except (KeyError, ValueError, TypeError) as e:
        return f"Ошибка при анализе результата: {e}"
    except Exception as e:
        return f"Общая ошибка: {e}"
      

# Добавление задачи в бд
async def process_user_task(user_id: str, message_text: str, tg_message: Message):
    """
    Обрабатывает сообщение пользователя, классифицирует задачу и добавляет её в планировщик.

    Args:
        user_id (str): Идентификатор пользователя.
        message_text (str): Сообщение пользователя, описывающее задачу.

    Returns:
        dict: Результат добавления задачи или сообщение об ошибке.
    """
    try:
        # Получаем текущую дату и время
        current_datetime = datetime.now()
        chat_id = tg_message.from_user.id

        # Классифицируем и извлекаем детали задачи
        task_details = await classify_and_extract_task_details(current_datetime, message_text)

        # Проверяем, получены ли корректные данные
        task_text = task_details.get("task_text")
        start_time = task_details.get("start_time")
        repeat_interval = task_details.get("repeat_interval")
        print(task_text, start_time, repeat_interval)

        if not task_text:
            text = "Не удалось извлечь текст задачи из вашего сообщения. Пожалуйста уточните задание!"
            await tg_message.answer(text=text)
            await speak_text_gtts_and_send(chat_id=chat_id, text=text)
            return {
                "status": "error",
                "message": "Не удалось извлечь текст задачи из вашего сообщения. Пожалуйста уточните задание!"
            }
        elif not start_time:
            text = "Не удалось извлечь время начала выполения задчи из вашего сообщения. Пожалуйста уточните задание!"
            await tg_message.answer(text=text)
            await speak_text_gtts_and_send(chat_id=chat_id, text=text)
            return {
                "status": "error",
                "message": "Не удалось извлечь время начала выполения задчи из вашего сообщения. Пожалуйста уточните задание!"
            }
        elif not task_text and not start_time:
            text = "Не удалось извлечь текст задачи или время начала выполнения задания из вышего сообщения. Пожалуйста уточните задание!!"
            await tg_message.answer(text=text)
            await speak_text_gtts_and_send(chat_id=chat_id, text=text)
            return {
                "status": "error",
                "message": "Не удалось извлечь текст задачи или время начала выполнения задания из вышего сообщения. Пожалуйста уточните задание!"
            }

        # Добавляем задачу в планировщик
        async with async_session() as session:
            await crud.add_task(
                session,
                telegram_id=user_id,
                text=task_text,
                start_time=start_time,
                repeat_interval=repeat_interval if repeat_interval != "NULL" else None,
            )
        
            task_id = await crud.get_task_id_by_text(session=session, task_text=task_text)
        
        # if repeat_interval == None: 
        #     schedule.add_task_to_scheduler(task_text=task_text, start_time=start_time, repeat_interval=repeat_interval, task_callback=lambda: schedule.execute_once(task_id=task_id))
        # else:
        #     schedule.add_task_to_scheduler(task_text=task_text, start_time=start_time, repeat_interval=repeat_interval, task_callback=lambda: schedule.execute_task(task_id=task_id))
        
        text = "Задача успешно добавлена в планировщик. С чем вам я могу еще помочь?!"
        await tg_message.answer(text=text)
        await speak_text_gtts_and_send(chat_id=chat_id, text=text)
        return {
            "status": "success",
            "message": "Задача успешно добавлена в планировщик.",
            "task_details": {
                "text": task_text,
                "start_time": start_time.isoformat(),
                "repeat_interval": repeat_interval
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка при обработке задачи: {str(e)}"
        }

