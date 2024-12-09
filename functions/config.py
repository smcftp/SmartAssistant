from pydantic_settings import BaseSettings

from openai import OpenAI

import platform
import struct
import ctypes

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from telethon import TelegramClient, events

from openai import OpenAI

############################################################

# Переменные окружения

class Settings(BaseSettings):
    openai_api_key: str
    redis_public_url: str
    telegram_bot_token: str
    api_id_th: int
    api_hash_th: str

    class Config:
        env_file = 'D:\\Programming\\Python\\GPT\\Voice_assistant_based_on_neural\\.env'

set = Settings()

############################################################

# Настройка телеграмм бота
bot_tg = Bot(token=set.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

router = Router()
dp.include_router(router)

############################################################

# Настройка сессии юзер бота
telegram_client = TelegramClient('voice_assistant', set.api_id_th, set.api_hash_th)

############################################################

# Настройка анализа эмоций в голосовых сообщениях
# if platform.system() == "Darwin":
#     assert struct.calcsize("P") == 8
#     Vokaturi = ctypes.CDLL("D:\\Programming\\OpenVokaturi-4-0\\lib\\open\\macos\\OpenVokaturi-4-0-mac.dylib")
# elif platform.system() == "Windows":
#     if struct.calcsize("P") == 4:
#         Vokaturi = ctypes.CDLL("D:\\Programming\\OpenVokaturi-4-0\\lib\\open\\win\\OpenVokaturi-4-0-win32.dll")
#     else:
#         assert struct.calcsize("P") == 8
#         Vokaturi = ctypes.CDLL("D:\\Programming\\OpenVokaturi-4-0\\lib\\open\\win\\OpenVokaturi-4-0-win64.dll")
# elif platform.system() == "Linux":
#     assert struct.calcsize("P") == 8
#     Vokaturi = ctypes.CDLL("D:\\Programming\\OpenVokaturi-4-0\\lib\\open\\linux\\OpenVokaturi-4-0-linux.so")
    
# print("Library Loaded: %s" % Vokaturi.versionAndLicense())

############################################################

# Инициализация OpenAI ассистента

# Инициализация клиента OpenAI
openai_client = OpenAI(
    api_key=set.openai_api_key
)

# Инструкция
instructions = """

    You are a professional literary Arabic language tutor. Communicate on various topics in literary Arabic. When answering, use next list of words: {my_words}. Use present, past and future tenses. Your answer must include an answer in Arabic and then a translation of the your current answer from Arabic into !!!Russian!!!.

"""

# Выбор модели 
model = "gpt-4o"

# Создание ассистента
assistant = openai_client.beta.assistants.create(
    name="Arabic language tutor",
    instructions=instructions,
    model=model,
)

# Создание потока  
thread = openai_client.beta.threads.create()
