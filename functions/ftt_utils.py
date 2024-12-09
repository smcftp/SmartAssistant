import whisper

import aiohttp
import asyncio

import soundfile as sf
import numpy as np

import logging
import os
import tempfile

from gtts import gTTS

from openai import AsyncOpenAI

from aiogram.types import InputFile
from aiogram.types import FSInputFile

import io
from io import BytesIO

from functions.config import set, bot_tg

# Инициализация клиента OpenAI
client_openai = AsyncOpenAI(
    api_key=set.openai_api_key
)

TOKEN = set.telegram_bot_token

async def convert_ogg_to_mp3_bytes(audio_data_bytes_io):
    """
    Асинхронно преобразует аудиофайл из BytesIO (формат OGG) в MP3, возвращает результат в BytesIO.

    :param audio_data_bytes_io: BytesIO объект с аудио в формате OGG.
    :return: BytesIO объект с MP3 содержимым.
    """
    try:
        # Проверка, что входной BytesIO объект не пустой
        if not audio_data_bytes_io or not isinstance(audio_data_bytes_io, io.BytesIO):
            raise ValueError("Передан пустой или некорректный BytesIO объект.")

        # Создаем BytesIO для хранения MP3
        mp3_output = io.BytesIO()

        # Команда для вызова ffmpeg
        command = [
            "ffmpeg", "-i", "pipe:0",  # Вход через stdin
            "-vn",  # Указание, что видео дорожка не обрабатывается
            "-ar", "16000",  # Частота дискретизации для Whisper
            "-ac", "1",  # Один аудиоканал для Whisper
            "-b:a", "192k",  # Битрейт аудио
            "-f", "wav",  # Формат выходного аудио
            "pipe:1"  # Вывод в stdout
        ]

        # Асинхронное выполнение команды
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate(input=audio_data_bytes_io.read())

        if process.returncode != 0:
            raise RuntimeError(f"Ошибка ffmpeg: {stderr.decode('utf-8')}")

        mp3_output.write(stdout)
        mp3_output.seek(0)  # Сброс указателя в начало
        return mp3_output
    except ValueError as e:
        raise ValueError(f"Ошибка: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Непредвиденная ошибка при конвертации аудио: {str(e)}")
    
async def bytesio_to_numpy(audio_bytesio):
    """
    Конвертирует аудиоданные из BytesIO в массив NumPy.
    
    :param audio_bytesio: BytesIO объект с аудиоданными.
    :return: NumPy массив с аудиоданными и частота дискретизации.
    """
    try:
        if not audio_bytesio:
            raise ValueError("Передан пустой BytesIO объект.")

        audio_bytesio.seek(0)  # Устанавливаем указатель на начало
        data, samplerate = sf.read(audio_bytesio)  # Используем soundfile для чтения данных
        return data.astype(np.float32), samplerate  # Преобразуем в float32
    except RuntimeError as e:
        raise RuntimeError(f"Ошибка при чтении аудиофайла с использованием soundfile: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Непредвиденная ошибка при преобразовании в NumPy: {str(e)}")



# Использование whisper в виде развернутой локальной модели
# async def process_voice_message(file_path: str):
#     """
#     Асинхронная загрузка, обработка и транскрипция голосового сообщения из Telegram.

#     Args:
#         file_url (str): Ссылка на файл аудио из Telegram API.

#     Returns:
#         str: Распознанный текст или сообщение об ошибке.
#     """
    
#     # Формирование ссылки
#     file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    
#     try:
#         # Шаг 1: Асинхронная загрузка голосового сообщения из Telegram
#         try:
#             async with aiohttp.ClientSession() as session:
#                 async with session.get(file_url) as response:
#                     if response.status != 200:
#                         return "Ошибка: Не удалось загрузить файл с сервера Telegram"
#                     audio_bytes = await response.read()
#                     audio_data_bytes_io = io.BytesIO(audio_bytes)
#         except aiohttp.ClientError as e:
#             return f"Ошибка при загрузке файла: {str(e)}"
#         except Exception as e:
#             return f"Непредвиденная ошибка при загрузке: {str(e)}"
        
#         try:
#             # Step 1: Convert OGG to MP3 in memory
#             mp3_audio = await convert_ogg_to_mp3_bytes(audio_data_bytes_io=audio_data_bytes_io)
#             if not mp3_audio:
#                 raise ValueError("Конвертация аудио завершилась неудачей.")

#             # Step 2: Convert BytesIO to NumPy array
#             audio_data, sample_rate = await bytesio_to_numpy(mp3_audio)

#             # Step 3: Load Whisper model
#             try:
#                 model = whisper.load_model("base")
#             except Exception as e:
#                 raise RuntimeError(f"Ошибка загрузки модели Whisper: {str(e)}")

#             # Step 4: Transcribe audio
#             try:
#                 result = model.transcribe(audio_data, fp16=False)
#             except Exception as e:
#                 raise RuntimeError(f"Ошибка транскрибирования аудио: {str(e)}")

#             return result["text"]
#         except Exception as e:
#             return f"Ошибка обработки аудиофайла: {str(e)}"
        
#     except Exception as e:
#             return f"Ошибка обработки аудиофайла: {str(e)}"


# Транскрибация через whisper api
async def process_voice_message(file_path: str):
    """
    Асинхронная загрузка, обработка и транскрипция голосового сообщения из Telegram.

    Args:
        file_path (str): Путь к файлу аудио на сервере Telegram.

    Returns:
        str: Распознанный текст или сообщение об ошибке.
    """
    # Формирование ссылки на файл
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    try:
        # Шаг 1: Асинхронная загрузка голосового сообщения из Telegram
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    if response.status != 200:
                        return "Ошибка: Не удалось загрузить файл с сервера Telegram"
                    audio_bytes = await response.read()
                    audio_data_bytes_io = io.BytesIO(audio_bytes)
        except aiohttp.ClientError as e:
            return f"Ошибка при загрузке файла: {str(e)}"
        except Exception as e:
            return f"Непредвиденная ошибка при загрузке: {str(e)}"

        # Шаг 2: Сохранение аудиофайла в формате OGG в временное хранилище
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_ogg_file:
                temp_ogg_file.write(audio_data_bytes_io.read())
                temp_ogg_file_path = temp_ogg_file.name  # Путь к временно сохранённому файлу

            # Шаг 3: Транскрипция с использованием Whisper API
            with open(temp_ogg_file_path, "rb") as audio_file:
                transcription = await client_openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )

            # Шаг 4: Удаление временного файла после транскрипции
            os.remove(temp_ogg_file_path)

            return transcription.text
        
        except Exception as e:
            return f"Ошибка при обработке и транскрипции аудиофайла: {str(e)}"

    except Exception as e:
        return f"Общая ошибка обработки аудиофайла: {str(e)}"


# async def send_voice_message(chat_id: int, voice: BytesIO):
#     """Отправка голосового сообщения пользователю.

#     Args:
#         chat_id (int): чат для отправки
#         voice (BytesIO): файл для отправки
#     """
#     try:
#         # Убедимся, что указатель на начало потока
#         voice.seek(0)
        
#         # Отправка голосового сообщения напрямую через BytesIO
#         await bot_tg.send_voice(chat_id=chat_id, voice=voice)
#     except Exception as e:
#         logging.error(f"Ошибка при отправке голосового сообщения: {e}")


# async def speak_text_gtts_and_send(chat_id: int, text: str):
#     """Генерация TTS и отправка голосового сообщения.

#     Args:
#         chat_id (int): Идентификатор чата.
#         text (str): Текст для озвучивания.
#     """
#     # Генерация TTS
#     tts = gTTS(text=text, lang='ru', slow=False)
    
#     # Сохранение в BytesIO
#     audio_buffer = BytesIO()
#     tts.write_to_fp(audio_buffer)
    
#     # Отправка голосового сообщения
#     await send_voice_message(chat_id=chat_id, voice=audio_buffer)

async def send_voice_message(chat_id: int, voice_path: str):
    """Отправка голосового сообщения пользователю.

    Args:
        chat_id (int): чат для отправки
        voice_path (str): путь к MP3 файлу для отправки
    """
    try:
        # Открываем файл для отправки
        voice_file = FSInputFile(voice_path)
        await bot_tg.send_voice(chat_id=chat_id, voice=voice_file)
    except Exception as e:
        logging.error(f"Ошибка при отправке голосового сообщения: {e}")
    finally:
        # Удаляем файл после отправки
        if os.path.exists(voice_path):
            os.remove(voice_path)

async def speak_text_and_save(text: str, filename: str):
    """Генерация TTS и сохранение в MP3 файл.

    Args:
        text (str): Текст для озвучивания.
        filename (str): Путь к файлу для сохранения MP3.
    """
    try:
        # Генерация TTS
        # tts = gTTS(text=text, lang='ru', slow=False)
        
        from pathlib import Path

        speech_file_path = "voice_message.mp3"
        response = await client_openai.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )

        response.stream_to_file(speech_file_path)
        
        # Сохранение в MP3 файл
        # response.save(speech_file_path)
        logging.info(f"Голосовое сообщение сохранено в файл {filename}")
    except Exception as e:
        logging.error(f"Ошибка при сохранении голосового сообщения: {e}")

async def speak_text_gtts_and_send(chat_id: int, text: str):
    """Генерация TTS, сохранение и отправка голосового сообщения.

    Args:
        chat_id (int): Идентификатор чата.
        text (str): Текст для озвучивания.
    """
    # Создание пути для файла
    voice_file_path = "voice_message.mp3"
    
    # Генерация TTS и сохранение в файл
    await speak_text_and_save(text, voice_file_path)
    
    # Отправка голосового сообщения
    await send_voice_message(chat_id, voice_file_path)