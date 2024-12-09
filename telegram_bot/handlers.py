import logging

from aiogram import Dispatcher, F, types, Router
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

import functions.ftt_utils as ftt_utils
from functions.config import bot_tg, set, dp, router
import api_gateway.gateway as gateway

# class Form(StatesGroup):
#     waiting_for_message = State()
    
# Определяем состояния
class Form(StatesGroup):
    waiting_for_response = State()

@dp.message(Command('start'))
async def command_start_handler(message: Message, state: FSMContext) -> None:
    await message.answer(f"Приветствую тебя {message.from_user.first_name}!")
    # Логируем состояние для проверки
    current_state = await state.get_state()
    print(f"Текущее состояние: {current_state}")
    
    await state.set_state(Form.waiting_for_response)

    # Логируем состояние для проверки
    current_state = await state.get_state()
    print(f"Текущее состояние: {current_state}")

# Обработка голосовых сообщений
@dp.message(F.voice)
async def handle_voice_message(message: Message, state: FSMContext):
    try:
        # Отправка сообщения в amplitude
        user_id = str(message.from_user.id)
        file_id = message.voice.file_id
        
        # Получение пути к файлу
        try:
            file_info = await bot_tg.get_file(file_id=file_id)
            file_path = str(file_info.file_path)
        except Exception as e:
            logging.error(f"Ошибка при получении пути к файлу: {e}") 
            
        # Транскрибация файла
        try:
            transcription = await ftt_utils.process_voice_message(file_path=file_path)
            await message.answer(transcription)
        except Exception as e:
            logging.error(f"Ошибка при получении пути к файлу: {e}") 
            
        # Отправка текста в фильтрации
        await gateway.handle_user_message(message=transcription, user_id=user_id, tg_message=message)
               
        
    except Exception as e:
        logging.error(f"Ошибка в обработчике голосовых сообщений: {e}")
        await message.answer("Произошла ошибка при обработке вашего сообщения.")

# Обработка текстовых сообщений
@dp.message(F.text)
# @router.message(F.text)
async def handle_text_message(message: Message, state: FSMContext) -> None:
    try:
        # Отправка сообщения в amplitude
        user_id = str(message.from_user.id)
        text = message.text
        
        # Отправка текста в фильтрации
        await gateway.handle_user_message(message=text, user_id=user_id, tg_message=message)
        
    except Exception as e:
        logging.error(f"Ошибка в обработчике голосовых сообщений: {e}")
        await message.answer("Произошла ошибка при обработке вашего сообщения.")
    
def register_handlers1(dp: Dispatcher) -> None:
    dp.message.register(command_start_handler, CommandStart())
    dp.message.register(handle_voice_message, lambda message: message.voice is not None)
    dp.message.register(handle_text_message, lambda message: message.text is not None)
