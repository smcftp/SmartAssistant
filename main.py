import asyncio
import logging
import sys
from telegram_bot.handlers import register_handlers1, dp

import functions.config as config

from microservices.assistant_tasks.scheduler.schedule import run_scheduler
from microservices.assistant_tasks.telegram.incoming_message_handler import real_time_message_listener

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout)

async def main() -> None:
    """
    Асинхронная основная функция для запуска планировщика задач и Telegram-бота.
    """
    try:
        # Запуск планировщика задач как отдельной фоновой задачи
        asyncio.create_task(run_scheduler())
        
        # Запуск прослушивания входящих сообщений в телеграмм
        # asyncio.create_task(real_time_message_listener())
        
        # Запуск Telegram-бота
        register_handlers1(dp)
        await dp.start_polling(config.bot_tg)
    except Exception as e:
        logging.error(f"Ошибка в основной функции: {e}")

if __name__ == "__main__":
    asyncio.run(main())
