import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import asyncio

# Установка логгера для вывода ошибок
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token="")
# Создание диспетчера с указанием бота и loop
dp = Dispatcher(bot)

# Создание соединения с базой данных SQLite
conn = sqlite3.connect('userdata.db')
cursor = conn.cursor()

# Создание таблицы для хранения данных пользователей, если она ещё не существует
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone_number TEXT,
        birthday TEXT
    )
''')
conn.commit()

print("Table 'users' created successfully")

cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        text TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
''')
conn.commit()

print("Table 'feedbacks' created successfully")

# Глобальные переменные для хранения имени и номера телефона
name = ""
phone_number = ""
birthday = ""
registered = False  # Переменная для отслеживания успешной регистрации

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
    await message.answer("Для продолжения введите номер телефона в международном формате. Пример: +77055005050",
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
    global name, phone_number, birthday, registered
    if message.text == "Подтверждаю":
        # Сохранение данных пользователя в базе данных
        cursor.execute('''
            INSERT INTO users (name, phone_number, birthday)
            VALUES (?, ?, ?)
        ''', (name, phone_number, birthday))
        conn.commit()
        # Получаем id нового пользователя
        user_id = cursor.lastrowid
        # Создаем клавиатуру с кнопками
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("Мой профиль"))
        markup.add(KeyboardButton("Заказать уборку"))
        markup.add(KeyboardButton("Оставить отзыв"))
        await message.answer("Регистрация успешно завершена! Выберите действие:", reply_markup=markup)
        registered = True
    else:
        # Сброс данных и повторный запрос
        name = ""
        phone_number = ""
        birthday = ""
        await message.answer("Давайте начнем регистрацию заново!")
        await message.answer("Чтобы продолжить, пройдите регистрацию👇",
                             reply_markup=ReplyKeyboardMarkup(
                                 keyboard=[
                                     [KeyboardButton(text="Пройти регистрацию")]
                                 ],
                                 resize_keyboard=True,
                                 selective=True
                             ))

# Обработчик для показа меню после успешной регистрации
@dp.message_handler(lambda message: message.text == "Мой профиль")
async def show_profile(message: types.Message):
    if registered:
        # Создаем клавиатуру с кнопками
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("Мой профиль"))
        markup.add(KeyboardButton("Заказать уборку"))
        markup.add(KeyboardButton("Оставить отзыв"))

        # Отправляем сообщение с клавиатурой
        await message.answer("Выберите действие:", reply_markup=markup)
    else:
        await message.answer("Сначала пройдите регистрацию!")

# Обработчик для показа профиля
@dp.message_handler(lambda message: message.text == "Мой профиль")
async def show_profile(message: types.Message):
    if registered:
        # Получаем данные о пользователе из базы данных
        cursor.execute('SELECT name, birthday FROM users WHERE phone_number=?', (phone_number,))
        user_data = cursor.fetchone()
        if user_data:
            name, birthday = user_data
            await message.answer(f"Имя: {name}\nДата рождения: {birthday}")
        else:
            await message.answer("Данные о пользователе не найдены.")
    else:
        await message.answer("Сначала пройдите регистрацию!")

# Обработчик для заказа уборки
@dp.message_handler(lambda message: message.text == "Заказать уборку")
async def order_cleaning(message: types.Message):
    if registered:
        await message.answer("Выберите тип уборки:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Генеральная")],
                [KeyboardButton(text="После ремонта")],
                [KeyboardButton(text="Поддерживающая")]
            ],
            resize_keyboard=True,
            selective=True
        ))
    else:
        await message.answer("Сначала пройдите регистрацию!")

# Обработчик для оставления отзыва
@dp.message_handler(lambda message: message.text == "Оставить отзыв")
async def leave_feedback(message: types.Message):
    if registered:
        await message.answer("Напишите ваш отзыв:")
        # Добавляем обработчик для следующего сообщения пользователя,
        # в котором будет отзыв
        dp.register_message_handler(save_feedback, content_types=types.ContentType.TEXT)
    else:
        await message.answer("Сначала пройдите регистрацию!")

# Обработчик для сохранения отзыва
async def save_feedback(message: types.Message):
    feedback = message.text
    # Получаем id пользователя, оставившего отзыв
    cursor.execute('SELECT id FROM users WHERE phone_number=?', (phone_number,))
    user_id = cursor.fetchone()[0]  # Получаем первое значение из кортежа
    # Сохраняем отзыв в базу данных
    cursor.execute('INSERT INTO feedbacks (user_id, text) VALUES (?, ?)', (user_id, feedback))
    conn.commit()
    await message.answer("Спасибо за ваш отзыв!")

# Обработчик для завершения работы бота
async def on_shutdown(dp):
    conn.close()

# Запуск асинхронного main-цикла
async def main():
    # Запуск бота
    await dp.start_polling()
    # Регистрация обработчика завершения работы

if __name__ == '__main__':
    # Запуск асинхронного main-цикла
    asyncio.run(main())
