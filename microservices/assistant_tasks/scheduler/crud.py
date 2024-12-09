from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from microservices.assistant_tasks.scheduler.models import User, Task


async def get_or_create_user(session: AsyncSession, telegram_id: str):
    result = await session.execute(select(User).filter_by(telegram_id=telegram_id))
    user = result.scalars().first()

    if not user:
        user = User(telegram_id=telegram_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user


async def add_task(session: AsyncSession, telegram_id: str, text: str, start_time, repeat_interval=None):
    user = await get_or_create_user(session, telegram_id)
    task = Task(
        user_id=user.id,
        text=text,
        start_time=start_time,
        repeat_interval=repeat_interval,
    )
    session.add(task)
    await session.commit()
    return task


async def get_all_tasks(session: AsyncSession):
    result = await session.execute(select(Task))
    return result.scalars().all()


async def delete_task(session: AsyncSession, task_id: int):
    result = await session.execute(select(Task).filter_by(id=task_id))
    task = result.scalars().first()
    if task:
        await session.delete(task)
        await session.commit()
        return task
    return None

# Получает ID задачи по её тексту (text)
async def get_task_id_by_text(session: AsyncSession, task_text: str) -> int | None:
    try:
        # Запрос на выбор задачи по тексту
        result = await session.execute(
            select(Task.id).where(Task.text == task_text)
        )
        task_id = result.scalar()  # Получаем первый результат (ID)
        return task_id
    except Exception as e:
        print(f"Ошибка при получении ID задачи: {e}")
        return None

# Получает задачу по её ID
async def get_task_by_id(session: AsyncSession, task_id: int) -> Task | None:
    try:
        # Выполняем запрос к базе данных
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()  # Получаем задачу или None
        return task
    except Exception as e:
        print(f"Ошибка при получении задачи по ID: {e}")
        return None
    
