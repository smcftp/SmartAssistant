import asyncio
import schedule
from datetime import datetime, timedelta
import asyncpg

from sqlalchemy.orm import joinedload
from sqlalchemy import text 
from sqlalchemy.future import select

from microservices.assistant_tasks.scheduler.database_utils import async_session, engine, DATABASE_URL
from microservices.assistant_tasks.scheduler.models import Task
import microservices.assistant_tasks.scheduler.crud as crud

from functions.config import bot_tg


# async def run_scheduler():
#     print("Начали прослушку задач")
#     """
#     Асинхронная функция для обработки уведомлений из PostgreSQL.
#     """
#     try:
#         # Устанавливаем соединение с базой через asyncpg
#         conn = await asyncpg.connect(DATABASE_URL.replace("postgresql+asyncpg", "postgresql"))

#         # Определяем callback для обработки уведомлений
#         async def notification_handler(conn, pid, channel, payload):
#             print(f"Получено уведомление из канала {channel}: {payload}")
#             # Обрабатываем задачу
#             await process_task(int(payload))

#         # Подключаем callback
#         await conn.add_listener("task_notifications", notification_handler)
#         print("Подписка на канал task_notifications активна.")

#         # Ждем уведомлений
#         while True:
#             await asyncio.sleep(1)

#     except Exception as e:
#         print(f"Ошибка в процессе работы планировщика: {e}")
#     finally:
#         await conn.close()

async def run_scheduler():
    """
    Асинхронный планировщик задач.
    Проверяет задачи из базы данных и запускает их выполнение, если их время наступило.
    """
    while True:
        try:
            # Получаем текущую дату и время с учетом смещения UTC+3
            current_time = datetime.utcnow() + timedelta(hours=3)

            async with async_session() as session:
                # Получаем все задачи с предзагрузкой связанных пользователей
                tasks = await session.execute(
                    select(Task).options(joinedload(Task.user))
                )
                tasks = tasks.scalars().all()

                # Проверяем задачи на выполнение
                for task in tasks:
                    if task.start_time <= current_time:
                        print(f"Запуск задачи с ID {task.id}, текст: {task.text}")
                        await process_task(task.id)


            # Задержка для снижения нагрузки (например, 60 секунд)
            await asyncio.sleep(60)

        except Exception as e:
            print(f"Ошибка в планировщике: {e}")


async def process_task(task_id: int):
    """
    Выполнение задачи по её ID.
    """
    async with async_session() as session:
        # Получаем задачу с предзагрузкой пользователя
        task_result = await session.execute(
            select(Task).options(joinedload(Task.user)).where(Task.id == task_id)
        )
        task = task_result.scalar_one_or_none()
        
        if task:
            print(f"\n\nВыполняется задача: {task.text}\n\n")
            
            telegram_id = task.user.telegram_id
            
            # Отправляем сообщение пользователю в Telegram
            try:
                await bot_tg.send_message(
                    chat_id=telegram_id,  # Используем связанный telegram_id из модели User
                    text=f"Напоминание: {task.text}\nДата и время: {task.start_time}"
                )
            except Exception as e:
                print(f"Ошибка отправки сообщения: {e}")
            
            # Если задача повторяется, обновляем время
            if task.repeat_interval:
                if task.repeat_interval == "daily":
                    task.start_time += timedelta(days=1)
                elif task.repeat_interval == "weekly":
                    task.start_time += timedelta(weeks=1)
                session.add(task)
            else:
                # Если задача не повторяется, удаляем её
                await session.delete(task)
            
            await session.commit()

