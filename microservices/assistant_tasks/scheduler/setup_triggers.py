from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text  # Используем text для выполнения SQL-запросов

DATABASE_URL = "postgresql+asyncpg://postgres:GZVqKSkgeJifyNidfPDKJhAHyVowCDql@junction.proxy.rlwy.net:57879/railway"

async def setup_triggers():
    """
    Устанавливаем триггеры и функции для базы данных.
    """
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.connect() as connection:
        # Функция отправки уведомлений
        await connection.execute(text("""
            CREATE OR REPLACE FUNCTION notify_task_ready()
            RETURNS TRIGGER AS $$
            BEGIN
                -- Отправляем уведомление, если задача должна быть выполнена
                IF NEW.start_time <= NOW() THEN
                    PERFORM pg_notify('task_notifications', NEW.id::TEXT);
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        
        # Создание триггера
        await connection.execute(text("""
            CREATE TRIGGER task_ready_trigger
            AFTER INSERT OR UPDATE ON tasks
            FOR EACH ROW
            EXECUTE FUNCTION notify_task_ready();
        """))
    
    await engine.dispose()

# Запуск настройки
if __name__ == "__main__":
    import asyncio
    asyncio.run(setup_triggers())
