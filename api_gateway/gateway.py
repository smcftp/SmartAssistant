# from fastapi import APIRouter, HTTPException
# from utils_gateway import process_user_message
import httpx
import time
import json
from aiogram.types import Message
from openai import AsyncOpenAI

import api_gateway.utils

# Импорт распиания
import microservices.assistant_tasks.scheduler.utils as schd_utils

# Импорт телеграмм
import microservices.assistant_tasks.telegram.utils as tg_utils

# Импорт отправки сообщения в голосе
from functions.ftt_utils import speak_text_gtts_and_send

# Импорт настроек
from functions.config import set, thread, assistant

client_openai = AsyncOpenAI(
    api_key=set.openai_api_key
)

# router = APIRouter()

# # Определяем URL-ы микросервисов
# MICROSERVICES = {
#     "Функции управления умным домом": "http://localhost:8001/smart_home",
#     "Менеджер напоминаний и планирования": "http://localhost:8002/reminder",
#     "Менеджер мессенджера Telegram": "http://localhost:8003/messenger",
#     "Менеджер видеозвонков": "http://localhost:8004/video_calls",
#     "Менеджер скриншотов": "http://localhost:8005/screenshots",
#     "Менеджер переводов": "http://localhost:8006/translations"
# }

# @router.post("/process_message")
async def handle_user_message(message: str, user_id: int, tg_message: Message):
    """
    Обрабатывает сообщение пользователя, классифицирует его и перенаправляет в нужный микросервис.

    Args:
        message (str): Сообщение пользователя.

    Returns:
        dict: Результат выполнения микросервиса.
    """
    try:
        # Получаем результат фильтрации из utils_gateway
        classification_result = await api_gateway.utils.process_user_message(user_message=message, tg_message=tg_message)
        
        print(classification_result)

        # Извлекаем категории
        primary_category = classification_result.get("primary_category")
        secondary_category = classification_result.get("secondary_category")
        details = classification_result.get("details")
        
        print(primary_category)

        # Проверяем, если сообщение не классифицировано
        # if primary_category == "Прочий мусор":
        #     return {"status": "ignored", "details": "Сообщение не относится к поддерживаемым категориям."}

        if primary_category == "Функции личного ассистента" and secondary_category == "Менеджер напоминаний и планирования":
            try:
                """
                
                ### Функции личного ассистента ###
                ### Планировщик задач ###

                - Проверяем корректно ли указание, для добавления задачи
                """
                x = await schd_utils.process_user_task(user_id=user_id, message_text=message, tg_message=tg_message)
                print(x)
            except ValueError as ve:
                return {"status": "error", "details": f"Ошибка обработки задачи: {str(ve)}"}
            except KeyError as ke:
                return {"status": "error", "details": f"Отсутствует ключ в данных задачи: {str(ke)}"}
            except Exception as e:
                return {"status": "error", "details": f"Непредвиденная ошибка в менеджере напоминаний: {str(e)}"}

        elif primary_category == "Функции личного ассистента" and secondary_category == "Менеджер мессенджера Telegram":
            try:
                """
                
                ### Функции личного ассистента ###
                ### Менеджер сообщений в телеграмм ###

                - Проверяем корректно ли указание, для взаимодействия с телеграм
                - Отправляем и удаляем сообщение в чатах, читаем сообщения в чатах и группах
                """
                x = await tg_utils.process_tg_manager(user_id=user_id, message_text=message, tg_message=tg_message)
                print(x)
            except ValueError as ve:
                return {"status": "error", "details": f"Ошибка обработки Telegram команды: {str(ve)}"}
            except KeyError as ke:
                return {"status": "error", "details": f"Отсутствует ключ в данных Telegram менеджера: {str(ke)}"}
            except Exception as e:
                return {"status": "error", "details": f"Непредвиденная ошибка в менеджере Telegram: {str(e)}"}
        
        elif primary_category == "Прочий мусор":
            """
            
            ### Передача сообщения в ассистента ###
            
            """
            print("Зашли в ассистента")
            
            # Начало замера времени
            start_time = time.time()        
            
            
            
            # Получение истории сообщений
            
            
            # Создание промпта
            prompt = f"""
                Действуй как личный ассистент для Ержана Садыкова. Твоя задача — предоставлять персонализированную помощь в различных областях, таких как управление задачами, установка напоминаний, организация расписания и предоставление полезных советов. Ты должен общаться вежливо и профессионально, обращаясь к пользователю по полному имени — «Ержан Садыков». Учитывай конкретные потребности и предпочтения Ержана.

                Если пользователь нуждается в помощи с какой-то задачей или у него есть вопрос, отвечай соответствующим образом. Обеспечь дружелюбные, подробные и проактивные ответы. Если Ержан запрашивает напоминания или задачи, которые нужно запланировать, уточни необходимые детали (например, время, дата, описание задачи).

                Например, если Ержан просит напоминание, ты можешь ответить так: «Конечно, Ержан. Когда мне напомнить тебе о [задаче]?» или, если запрашивает расписание: «Позволь мне проверить твое расписание, Ержан. Минутку, пожалуйста.»

                Твоя главная цель — упростить повседневную жизнь Ержана, управляя задачами и предоставляя релевантную информацию.

                Сейчас Ержан Садыков нуждается в помощи по следующему вопросу: {message}. Как ты будешь ему помогать?
            """

            # Отправка запроса к api
            completion = await client_openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a personal assistant."},
                    {"role": "user", "content": prompt}
                ],
            )
            print(completion)

            # Обрабатываем результат
            # assistants_response = json.loads(completion.choices[0].message.tool_calls[0].function.arguments)
            assistants_response = completion.choices[0].message.content
            
            text = assistants_response
            await tg_message.answer(text=text)
            
            # Конец замера времени
            start_time_ttf = time.time()
            await speak_text_gtts_and_send(chat_id=user_id, text=text)
            end_time_ttf = time.time()

            
            # Конец замера времени
            end_time = time.time()

            # Вывод времени выполнения
            execution_time_ttf = end_time_ttf - start_time_ttf
            print(f"\nВремя выполнения ttf: {execution_time_ttf:.2f} секунд")
            
            # Вывод времени выполнения
            execution_time = end_time - start_time
            print(f"\nВремя выполнения кода: {execution_time:.2f} секунд")
            
            # Обновление истории сообщений в кэшу redis
            

        # return {"status": "success", "service_response": response.json()}

    except ValueError as ve:
        return {"status": "error", "details": f"Ошибка классификации сообщения: {str(ve)}"}
    except KeyError as ke:
        return {"status": "error", "details": f"Отсутствует ключ в данных классификации: {str(ke)}"}
    except Exception as e:
        return {"status": "error", "details": f"Общая ошибка в обработке сообщения: {str(e)}"}
