import os
import aiohttp
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
import logging
from dotenv import load_dotenv
from cachetools import TTLCache, cached

load_dotenv()
API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

logging.basicConfig(level=logging.INFO)

class Dialog(StatesGroup):
    waiting_for_city = State()

cache = TTLCache(maxsize=100, ttl=300)

# Новая функция для обработки естественного языка
def process_user_message(text):
    # Здесь может быть сложная логика обработки текста
    return text.strip()

async def fetch_openai_response(prompt):
    async with aiohttp.ClientSession() as session:
        response = await session.post(
            "https://api.openai.com/v1/engines/text-davinci-003/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={"prompt": prompt, "max_tokens": 150}
        )
        return await response.json()

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await Dialog.waiting_for_city.set()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Отмена")
    await message.reply("Привет! Введите название города для поиска кофеен.", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text.lower() == 'отмена', state=Dialog.waiting_for_city)
async def cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.reply("Диалог отменен.", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(state=Dialog.waiting_for_city)
async def find_coffee_shops(message: types.Message, state: FSMContext):
    processed_text = process_user_message(message.text)
    if len(processed_text.split()) > 5:
        await message.reply("Введите корректное название города.")
        return
    await state.finish()

    prompt = f"Найдите лучшие кофейни в {processed_text}"
    try:
        reply = await cached_fetch_openai_response(prompt)
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("Показать на карте", url=f"https://www.google.com/maps/search/{processed_text} кофейни"))
        await message.reply(reply, reply_markup=markup)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.reply("Извините, произошла ошибка.")

@cached(cache)
async def cached_fetch_openai_response(prompt):
    return await fetch_openai_response(prompt)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
