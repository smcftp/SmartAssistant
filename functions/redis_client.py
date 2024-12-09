import redis.asyncio as redis
from functions.config import set

# Инициализация подключения к Redis
redis_client = redis.from_url(set.redis_public_url, decode_responses=True)

async def set_user_state(user_id: int, waiting_answer: bool, income_message_text: str):
    """
    Сохраняет состояние пользователя в Redis с обработкой исключений.
    """
    try:
        # Используем HSET вместо hmset_dict, так как hmset_dict устарел в новых версиях redis-py
        await redis_client.hset(f"user:{user_id}", mapping={"waiting_answer": str(waiting_answer), "income_message_text": income_message_text})
        print(f"Состояние пользователя {user_id} успешно сохранено.")
    except redis.exceptions.ConnectionError as e:
        print(f"Ошибка подключения к Redis: {e}")
    except redis.exceptions.TimeoutError as e:
        print(f"Время ожидания истекло при попытке подключения к Redis: {e}")
    except Exception as e:
        print(f"Неизвестная ошибка при сохранении состояния пользователя {user_id}: {e}")


async def get_user_state(user_id: int):
    """
    Получает состояние пользователя из Redis с обработкой исключений.
    """
    try:
        user_state = await redis_client.hgetall(f"user:{user_id}")
        if user_state:
            return {
                "waiting_answer": user_state.get("waiting_answer", "False") == "True",
                "income_message_text": user_state.get("income_message_text", "")
            }
        else:
            print(f"Состояние пользователя {user_id} не найдено.")
            return None
    except redis.exceptions.ConnectionError as e:
        print(f"Ошибка подключения к Redis: {e}")
    except redis.exceptions.TimeoutError as e:
        print(f"Время ожидания истекло при попытке подключения к Redis: {e}")
    except Exception as e:
        print(f"Неизвестная ошибка при получении состояния пользователя {user_id}: {e}")
    return None


# Новая функция для перезаписи последних 5 сообщений
async def update_message_history(user_id: int, new_message: str):
    """
    Перезаписывает историю последних 5 сообщений ассистента в Redis.
    
    Args:
        user_id (int): Идентификатор пользователя.
        new_message (str): Новое сообщение для добавления в историю.
    """
    try:
        # Добавляем новое сообщение в начало списка
        await redis_client.lpush(f"user:{user_id}:history", new_message)
        
        # Оставляем только последние 5 сообщений
        await redis_client.ltrim(f"user:{user_id}:history", 0, 4)

        print(f"История сообщений для пользователя {user_id} обновлена.")
    except redis.exceptions.ConnectionError as e:
        print(f"Ошибка подключения к Redis: {e}")
    except redis.exceptions.TimeoutError as e:
        print(f"Время ожидания истекло при попытке подключения к Redis: {e}")
    except Exception as e:
        print(f"Неизвестная ошибка при обновлении истории сообщений для пользователя {user_id}: {e}")


async def get_message_history(user_id: int):
    """
    Получает последние 5 сообщений ассистента из Redis.
    
    Args:
        user_id (int): Идентификатор пользователя.
    
    Returns:
        list: Список последних 5 сообщений ассистента.
    """
    try:
        # Получаем последние 5 сообщений из списка
        message_history = await redis_client.lrange(f"user:{user_id}:history", 0, 4)
        
        if message_history:
            return message_history
        else:
            print(f"История сообщений для пользователя {user_id} не найдена.")
            return []
    except redis.exceptions.ConnectionError as e:
        print(f"Ошибка подключения к Redis: {e}")
    except redis.exceptions.TimeoutError as e:
        print(f"Время ожидания истекло при попытке подключения к Redis: {e}")
    except Exception as e:
        print(f"Неизвестная ошибка при получении истории сообщений для пользователя {user_id}: {e}")
    return []