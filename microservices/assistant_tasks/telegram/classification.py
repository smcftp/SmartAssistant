import json
from datetime import datetime, timedelta
import asyncio
from openai import AsyncOpenAI

from aiogram.types import Message

import functions.config as config

# Инициализация клиента OpenAI
client = AsyncOpenAI(
    api_key=config.set.openai_api_key
)

# Извлечение из сообщение планировщика основных компонентов для БД
async def classify_and_filter_message_action(current_datetime: datetime, message_text: str):
    """
        Фильтрация:
            1) Написать сообщение -> определение кому написать
            2) Прочитать сообщение -> фильтрация прочитать группу или пользователя -> опредление где читать, сколько читать
            3) Удалить сообщение -> определение где удалять сообщение
    
    """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "message_action_filter",
                "description": "Classify and filter message actions, determining parameters based on the type of action: send, read, or delete.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action_type": {
                            "type": "string",
                            "description": """
                                Classify the action from the message based on its intent. Possible values:
                                - "send": Writing a message to a user or group.
                                - "read": Reading messages from a user or group.
                                - "delete": Deleting messages from a user or group.

                                **Examples of how messages might start for each category**:
                                - "send":
                                    - "Напиши сообщение Ивану..."
                                    - "Отправь Олегу, что встреча перенесена..."
                                    - "Tell John about the meeting..."
                                - "read":
                                    - "Прочитай последние 5 сообщений в группе..."
                                    - "Посмотри, что написал Алекс..."
                                    - "Read the last message from the marketing chat..."
                                - "delete":
                                    - "Удалить сообщение в чате с клиентом..."
                                    - "Очисти историю сообщений в проектной группе..."
                                    - "Delete the last message in the team chat..."
                            """
                        },
                        "recipient": {
                            "type": "string",
                            "description": """
                                Specify the recipient of the action and ensure the recipient's name is converted to its nominative case (for Russian) or its original form (for other languages):
                                - For "send": Indicate the username or group to send the message.
                                - For "read" or "delete": Indicate the chat (group or username) where the action is performed.
                                
                                **Name Normalization**:
                                - If the recipient's name is provided in a declined form (e.g., "Ивану", "Герману"), convert it to its nominative form (e.g., "Иван", "Герман").
                                - For other languages, ensure the name is presented in its original, unaltered form.

                                **Examples**:
                                - Input: "Напиши Герману сообщение."
                                Result: "Герман".
                                - Input: "Прочитай сообщения от Ивана."
                                Result: "Иван".
                                - Input: "Send a message to John."
                                Result: "John".

                                !!! If recipient is NOT defined in "{message_text}", return only False !!!
                            """
                        },
                        "read_count": {
                            "type": "integer",
                            "description": """
                                For "read" action only: The number of messages to read from the specified chat.
                                Default: 1.
                                !!! Return NULL for actions other than "read" !!!
                            """
                        },
                        "message_content": {
                            "type": "string",
                            "description": """
                                For "send" action only: Extract the content of the message to be sent, paraphrase it into a concise and neutral form, and ensure the message is appropriately structured based on the following rules:

                                Instructions:
                                1. **Language Handling**:
                                - If the original message explicitly specifies a language (e.g., "Send the message in German"), ensure the output message is paraphrased and translated into the specified language while preserving its original intent.
                                - If no language is specified, **translate the message into Russian** and paraphrase it.
                                    **Example**:
                                    - Original: "Напиши Герману: встречаемся днем в кафе на немецком."
                                    - Result: "Treffen Sie sich am Nachmittag in einem Café."
                                - If the language is not specified, **translate the message into Russian** and paraphrase it.

                                2. **Paraphrasing**:
                                - Simplify and neutralize the message while preserving its original intent.
                                - Adapt the tone of the message based on its formality (e.g., formal or informal depending on the context or recipient's relationship).
                                - Retain the recipient's name or relevant context if provided.

                                3. **Handling Undefined Messages**:
                                - If the content of the message is not clearly defined in the original text, return NULL.

                                Examples:
                                - Original: "Ask how Andrey is doing." → Result: "Как у тебя дела?"
                                - Original: "Tell John to call me back." → Result: "Позвони мне, пожалуйста."
                                - Original: "Send this message in English: 'Meeting is scheduled.'" → Result: "Meeting is scheduled."
                                - Original: "Напомни Олегу о встрече завтра." → Result: "Олег, не забудь о встрече."
                                - Original: "Check with Maria if the report is ready." → Result: "Мария, отчет готов?"
                                - Original: "Ping Alex with this: 'Can we reschedule?'" → Result: "Алекс, можем перенести встречу?"
                                
                                !!! Return NULL for actions other than "send" !!!
                            """
                        },

                    },
                    "required": ["action_type", "recipient"],
                    "additionalProperties": False,
                },
            }
        }
    ]

    # Формируем промпт
    prompt = (
        f"""
            Current datetime is: {current_datetime.isoformat()}.\n"
            Analyze the following message request: '{message_text}'.\n"
            Determine the action type ("send", "read", or "delete") and extract the necessary parameters:
            - For "send": Extract the recipient and the paraphrased message content to send.
            - For "read": Extract the recipient (group or user), and determine how many messages to read. Default read count is 1 if not specified.
            - For "delete": Extract the recipient (group or user) from where the message(s) will be deleted.
            Return the parameters in this format: action_type, recipient, read_count (NULL for actions other than "read"), and message_content (NULL for actions other than "send").
            If action_type or recipient is NOT defined in "{message_text}", return only False.
        """
    )

    try:
        # Создаём асинхронный запрос к OpenAI
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a messaging assistant that classifies and extracts action details."},
                {"role": "user", "content": prompt}
            ],
            tools=tools,
        )

        # Обрабатываем результат
        result = json.loads(completion.choices[0].message.tool_calls[0].function.arguments)

        # Извлечение параметров
        action_type = result.get("action_type", None)
        recipient = result.get("recipient", None)
        read_count = result.get("read_count", None)
        message_content = result.get("message_content", None)

        # Обработка отсутствующих данных
        if not action_type or not recipient:
            return {"action_type": False, "recipient": False, "read_count": None, "message_content": None}

        # Установить NULL для read_count и message_content, если действие не соответствует "read" или "send"
        if action_type != "read":
            read_count = None
        if action_type != "send":
            message_content = None

        # Возврат результата
        return {
            "action_type": action_type,
            "recipient": recipient,
            "read_count": read_count,
            "message_content": message_content,
        }

    except (KeyError, ValueError, TypeError) as e:
        return f"Ошибка при анализе результата: {e}"
    except Exception as e:
        return f"Общая ошибка: {e}"


# if __name__ == "__main__":
    
#     current_datetime = datetime.now()
#     message_text = "Send a message to John."
    
#     asyncio.run(
        
#         classify_and_filter_message_action(current_datetime=current_datetime, message_text=message_text)
        
#     )
      

