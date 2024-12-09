from datetime import datetime, timedelta

from aiogram.types import Message

# Импорт управления юзер ботом telethon
import microservices.assistant_tasks.telegram.classification as classification
import microservices.assistant_tasks.telegram.bot as telegram_bot

# Импорт отправки сообщения в голосе
from functions.ftt_utils import speak_text_gtts_and_send


def parse_command(command):
    """
    Простейший парсер для обработки текстовых команд.
    """
    if "напиши" in command:
        parts = command.split(":")
        chat_name = parts[0].replace("напиши", "").strip()
        message = parts[1].strip()
        return {"action": "send_message", "params": {"chat_name": chat_name, "message": message}}

    if "что писал" in command:
        chat_name = command.replace("что писал", "").strip()
        return {"action": "read_last_messages", "params": {"chat_name": chat_name, "limit": 5}}

    return {"action": "unknown", "params": {}}

async def process_tg_manager(user_id: str, message_text: str, tg_message: Message):
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

        try:
            # Классифицируем и извлекаем детали задачи
            task_details = await classification.classify_and_filter_message_action(
                current_datetime=current_datetime, message_text=message_text
            )
        except AttributeError as ae:
            return {
                "status": "error",
                "message": f"Ошибка классификации сообщения: {str(ae)}"
            }
        except KeyError as ke:
            return {
                "status": "error",
                "message": f"Ошибка классификации: отсутствует ключ {str(ke)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Неожиданная ошибка классификации: {str(e)}"
            }

        # Проверяем, получены ли корректные данные
        try:
            action_type = str(task_details.get("action_type"))  # Тип действия: "send", "read", "delete"
            recipient = str(task_details.get("recipient"))  # Адресат: пользователь или группа
            read_count = str(task_details.get("read_count"))  # Количество сообщений (только для "read")
            message_content = str(task_details.get("message_content"))  # Сообщение (только для "send")
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка извлечения деталей задачи: {str(e)}"
            }

        # Проверка отсутствующих данных
        missing_fields = []
        if action_type == "False":
            missing_fields.append("тип действия")
        if recipient == "False":
            missing_fields.append("адресат")
        if action_type == "read" and read_count == "None":
            missing_fields.append("количество сообщений для чтения")
        if action_type == "send" and message_content == "None":
            missing_fields.append("текст сообщения для отправки")

        # Если есть пропущенные данные, отправляем пользователю сообщение с деталями
        if missing_fields:
            missing_fields_text = ", ".join(missing_fields)
            text = f"Не удалось извлечь следующие данные из вашего сообщения: {missing_fields_text}. \nПожалуйста, уточните ваше задание!"
            await tg_message.answer(text=text)
            await speak_text_gtts_and_send(chat_id=chat_id, text=text)
            
            return {
                "status": "error",
                "message": f"Не удалось извлечь следующие данные: {missing_fields_text}. Пожалуйста, уточните ваше задание!"
            }

        # Взаимодействуем с Telegram
        try:
            if action_type == "send":
                print(f"\nОтправляем сообщение\n")
                try:
                    dialogs = await telegram_bot.get_private_chats_withoiut_bot()
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Ошибка при получении приватных чатов: {str(e)}"
                    }

                try:
                    chat_inf = await telegram_bot.find_chat(dialogs=dialogs, recipient=recipient)
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Ошибка при поиске чата для адресата '{recipient}': {str(e)}"
                    }
                
                if chat_inf != None:
                    #  Чат для отправки сообщения найден
                    try:
                        sent_res = await telegram_bot.send_message(chat_id=int(chat_inf["id"]), message=message_content)
                    except Exception as e:
                        return {
                            "status": "error",
                            "message": f"Ошибка при отправке сообщения в чат '{chat_inf}': {str(e)}"
                        }
                else:
                    # Чат для отправки сообщений не найден
                    await tg_message.answer(f"Чат с именнем '{recipient}' не найден, пожалуйста повторите попытку")
                    return {
                        "status": "error",
                        "message": f"Ошибка при поиске чата для адресата '{recipient}': {str(e)}, пожалуйста повторите попутку."
                    }

                if sent_res:
                    text = f"Сообщение для {chat_inf['name']} отправлено успешно!"
                    await tg_message.answer(text=text)
                    await speak_text_gtts_and_send(chat_id=chat_id, text=text)
                else:
                    text = f"Сообщение не отправлено, повторите попытку!"
                    await tg_message.answer(text=text)
                    await speak_text_gtts_and_send(chat_id=chat_id, text=text)

            elif action_type == "read":
                print(f"\nЧитаем сообщение\n")
                try:
                    dialogs = await telegram_bot.get_all_chats()
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Ошибка при получении всех чатов: {str(e)}"
                    }

                try:
                    chat_inf = await telegram_bot.find_chat(dialogs=dialogs, recipient=recipient)
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Ошибка при поиске чата для адресата '{recipient}': {str(e)}"
                    }
                    
                if chat_inf != None:
                    # Чат для чтения сообщения найден
                    try:
                        read_messages = await telegram_bot.get_last_messages(chat_id=int(chat_inf["id"]), limit=int(read_count))
                    except Exception as e:
                        return {
                            "status": "error",
                            "message": f"Ошибка при чтении сообщений из чата '{chat_inf['name']}': {str(e)}"
                        }
                else:
                    # Чат для чтения сообщений не найден
                    await tg_message.answer(f"Чат с именнем '{recipient}' не найден, пожалуйста повторите попытку")
                    return {
                        "status": "error",
                        "message": f"Ошибка при поиске чата для адресата '{recipient}': {str(e)}, пожалуйста повторите попутку."
                    }

                if read_messages:
                    text = f"Последние {read_count} сообщение(я) из {chat_inf['name']} следующие: {read_messages}"
                    await tg_message.answer(text=text)
                    await speak_text_gtts_and_send(chat_id=chat_id, text=text)
                else:
                    text = f"Сообщение не прочитано, повторите попытку!"
                    await tg_message.answer(text=text)
                    await speak_text_gtts_and_send(chat_id=chat_id, text=text)

            elif action_type == "delete":
                print(f"\Удаляем сообщение\n")
                # Логика удаления сообщения будет добавлена здесь
                pass
        except AttributeError as ae:
            return {
                "status": "error",
                "message": f"Ошибка в API Telegram: {str(ae)}"
            }
        except KeyError as ke:
            return {
                "status": "error",
                "message": f"Ошибка взаимодействия с Telegram: отсутствует ключ {str(ke)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка при взаимодействии с Telegram: {str(e)}"
            }

        # Если все необходимые данные получены, сообщаем об успехе
        text = "Задание менеджера telegram успешно выполнена. С чем я могу еще помочь?"
        await tg_message.answer(text=text)
        await speak_text_gtts_and_send(chat_id=chat_id, text=text)
        return {
            "status": "success",
            "message": "Задача успешно добавлена в планировщик.",
            "task_details": {
                "action_type": action_type,
                "recipient": recipient,
                "read_count": read_count,
                "message_content": message_content,
            }
        }

    except Exception as e:
        # Общая обработка исключений
        return {
            "status": "error",
            "message": f"Ошибка при обработке задачи: {str(e)}"
        }
