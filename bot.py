import logging

import openai
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import API_TOKEN
from database.db import create_tables, insert_initial_company_info, create_news_table, insert_sample_news, \
    insert_admins, insert_washers, insert_orders

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Создание клавиатуры с кнопками меню
markup = ReplyKeyboardMarkup(resize_keyboard=True)
markup.add(KeyboardButton("Мой профиль"))
markup.add(KeyboardButton("Цены"))
markup.add(KeyboardButton("Закажите очистку"))
markup.add(KeyboardButton("Оставьте комментарий"))
markup.add(KeyboardButton("Информация о компании"))
markup.add(KeyboardButton("Пример работы"))
markup.add(KeyboardButton("Показать все новости"))
markup.add(KeyboardButton("Начать диалог с OpenAI"))


class CleaningOrder(StatesGroup):
    waiting_for_cleaning_type = State()
    waiting_for_area = State()
    waiting_for_address = State()


# Глобальные переменные для хранения имени и номера телефона
name = ""
phone_number = ""
birthday = ""
registered = False  # Переменная для отслеживания успешной регистрации
cleaning_type = ""
cleaning_standard = ""
area = 0


# Глобальная переменная для хранения статуса диалога с OpenAI
openai_dialog_active = False


@dp.message_handler(lambda message: message.text == "Начать диалог с OpenAI" and not openai_dialog_active)
async def start_openai_dialog(message: types.Message):
    global openai_dialog_active
    openai_dialog_active = True
    await openai_dialog_start(message)


# Обработчик для запуска диалога с OpenAI
async def openai_dialog_start(message: types.Message):
    await message.answer("Вы начали диалог с OpenAI. Задайте ваш вопрос:")
    # Здесь мы не будем регистрировать новый обработчик, так как используем флаг openai_dialog_active


# Обработчик для получения вопроса и отправки запроса в OpenAI
@dp.message_handler(lambda message: openai_dialog_active)
async def process_openai_question(message: types.Message):
    # Отправляем сообщение пользователя в OpenAI для обработки
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo-preview",
        messages=[{"role": "user", "content": message.text}]
    )

    # Отправляем ответ от OpenAI боту пользователю
    await message.answer(response.choices[0].message['content'])

    # Закрываем диалог после ответа
    global openai_dialog_active
    openai_dialog_active = False
    await message.answer("Что вы хотите сделать дальше?", reply_markup=markup)
 


# Запуск бота
if __name__ == '__main__':
    create_tables()  # Создание таблиц в базе данных
    insert_initial_company_info()
    create_news_table()
    insert_sample_news()
    insert_admins()
    insert_washers()
    insert_orders()
    executor.start_polling(dp, skip_updates=True, timeout=30)