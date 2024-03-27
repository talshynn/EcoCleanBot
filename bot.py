import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import asyncio

# Установка логгера для вывода ошибок
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token="")
# Создание диспетчера с указанием бота и loop
dp = Dispatcher(bot)

# Глобальные переменные для хранения имени и номера телефона
name = ""
phone_number = ""
birthday = ""

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    # Приветственное сообщение и кнопка "Пройти регистрацию"
    await message.answer("EcoCleanBot - удобный сервис для записи на уборку и химчистку. \nЧтобы продолжить, пройдите регистрацию👇",
                         reply_markup=ReplyKeyboardMarkup(
                             keyboard=[
                                 [KeyboardButton(text="Пройти регистрацию")]
                             ],
                             resize_keyboard=True,
                             selective=True  # Добавим атрибут selective=True
                         ))

# Обработчик для кнопки "Пройти регистрацию"
@dp.message_handler(lambda message: message.text == "Пройти регистрацию")
async def register_start(message: types.Message):
    # Запрос имени
    await message.answer("Введите ваше имя👇",
                         reply_markup=ReplyKeyboardRemove())  # Удаляем клавиатуру

# Обработчик для имени
@dp.message_handler(lambda message: name == "")
async def register_name(message: types.Message):
    global name
    name = message.text
    # Запрос номера телефона
    await message.answer("Для продолжения введите номер телефона в международном формате. Пример: +77007801799",
                         reply_markup=ReplyKeyboardRemove())  # Удаляем клавиатуру

# Обработчик для номера телефона
@dp.message_handler(lambda message: phone_number == "")
async def register_phone(message: types.Message):
    global phone_number
    phone_number = message.text
    # Запрос даты рождения
    await message.answer("Напишите дату вашего рождения в формате ДД.ММ.ГГГГ. Например, 01.01.2000",
                         reply_markup=ReplyKeyboardRemove())  # Удаляем клавиатуру

# Обработчик для даты рождения
@dp.message_handler(lambda message: birthday == "")
async def register_birthday(message: types.Message):
    global birthday
    birthday = message.text
    # Проверка данных и кнопки "Подтверждаю" / "Изменить"
    user_info = f"Ваше имя: {name}\nНомер телефона: {phone_number}\nДата рождения: {birthday}"
    await message.answer(f"Проверьте ваши данные:\n{user_info}",
                         reply_markup=ReplyKeyboardMarkup(
                             keyboard=[
                                 [KeyboardButton(text="Подтверждаю")],
                                 [KeyboardButton(text="Изменить")]
                             ],
                             resize_keyboard=True,
                             selective=True  # Добавим атрибут selective=True
                         ))

# Обработчик для кнопок "Подтверждаю" / "Изменить"
@dp.message_handler(lambda message: message.text in ["Подтверждаю", "Изменить"])
async def register_confirmation(message: types.Message):
    if message.text == "Подтверждаю":
        await message.answer("Регистрация успешно завершена!")
    else:
        # Сброс данных и повторный запрос
        global name, phone_number, birthday
        name = ""
        phone_number = ""
        birthday = ""
        await message.answer("Давайте начнем регистрацию заново!")
        # Приветственное сообщение и кнопка "Пройти регистрацию"
        await message.answer("Чтобы продолжить, пройдите регистрацию👇",
                             reply_markup=ReplyKeyboardMarkup(
                                 keyboard=[
                                     [KeyboardButton(text="Пройти регистрацию")]
                                 ],
                                 resize_keyboard=True,
                                 selective=True  # Добавим атрибут selective=True
                             ))

async def main():
    # Запуск бота
    await dp.start_polling()

if __name__ == '__main__':
    # Запуск асинхронного main-цикла
    asyncio.run(main())
