import asyncio
import schedule
from datetime import datetime
from database_utils import async_session, init_db
from crud import add_task, get_all_tasks


async def remind_task(task_id, text):
    print(f"[{datetime.now()}] Напоминание: {text} (ID задачи: {task_id})")


async def load_tasks_to_scheduler():
    async with async_session() as session:
        tasks = await get_all_tasks(session)
        for task in tasks:
            if task.repeat_interval == "daily":
                schedule.every().day.at(task.start_time.strftime("%H:%M")).do(
                    asyncio.run, remind_task(task.id, task.text)
                )
            elif task.repeat_interval == "weekly":
                schedule.every().week.at(task.start_time.strftime("%H:%M")).do(
                    asyncio.run, remind_task(task.id, task.text)
                )
            elif task.start_time > datetime.now():
                schedule.every().day.at(task.start_time.strftime("%H:%M")).do(
                    asyncio.run, remind_task(task.id, task.text)
                )


async def main():
    await init_db()

    # Пример добавления задачи
    async with async_session() as session:
        await add_task(
            session,
            telegram_id="123456789",
            text="Встреча с клиентом",
            start_time=datetime(2024, 12, 1, 15, 30),
            repeat_interval=None,
        )

    # Загрузка задач в планировщик
    await load_tasks_to_scheduler()

    # Запуск цикла планировщика
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
