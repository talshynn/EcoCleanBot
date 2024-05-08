import os
import logging
import sqlite3
import openai
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,InputFile
import asyncio
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
# Установка логгера для вывода ошибок
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token="")
# Создание диспетчера с указанием бота и loop
# Создание хранилища в памяти
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
# Установка ключа API OpenAI
openai.api_key = ''

# Создание соединения с базой данных SQLite
conn = sqlite3.connect('userdata.db')
cursor = conn.cursor()

# Создание таблицы для хранения данных пользователей, если она ещё не существует
def create_tables():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone_number TEXT,
            birthday TEXT
        )
    ''')
    conn.commit()
    logger.info("Table 'users' created successfully")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    logger.info("Table 'feedbacks' created successfully")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            cleaning_type TEXT,
            cleaning_standard TEXT,
            area INTEGER,
            address TEXT,
            cost INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    logger.info("Table 'orders' created successfully")

# Создание клавиатуры с кнопками меню
markup = ReplyKeyboardMarkup(resize_keyboard=True)
markup.add(KeyboardButton("Мой профиль"))
markup.add(KeyboardButton("Закажите очистку"))
markup.add(KeyboardButton("Оставьте комментарий"))
markup.add(KeyboardButton("Информация о компании"))
markup.add(KeyboardButton("Пример работы"))
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

# Обработчик для кнопок меню
@dp.message_handler(lambda message: registered and message.text in ["Мой профиль", "Закажите очистку", "Оставьте комментарий"])
async def process_menu(message: types.Message):
    if message.text == "Мой профиль":
        # Отображение профиля пользователя
        user_info = await get_user_info(phone_number)
        await message.answer(user_info)
    elif message.text == "Закажите очистку":
        # Обработка заказа очистки
        await order_cleaning(message)
    elif message.text == "Оставьте комментарий":
        # Обработка оставления комментария
        await leave_feedback(message)

# Функция для получения информации о пользователе из базы данных
async def get_user_info(phone_number):
    if registered:
        try:
            # Получаем данные о пользователе из базы данных
            cursor.execute('SELECT name, birthday FROM users WHERE phone_number=?', (phone_number,))
            user_data = cursor.fetchone()
            if user_data:
                name, birthday = user_data
                return f"Имя: {name}\nДата рождения: {birthday}"
            else:
                return "Данные о пользователе не найдены."
        except Exception as e:
            logger.error(f"Произошла ошибка при получении профиля пользователя: {e}")
            return "Произошла ошибка при получении профиля пользователя."
    else:
        return "Сначала пройдите регистрацию!"

# Обработчик для оставления комментария
@dp.message_handler(lambda message: message.text == "Оставьте комментарий")
async def leave_feedback(message: types.Message):
    # Проверяем, зарегистрирован ли пользователь
    if registered:
        await message.answer("Введите ваш комментарий:")
        # Устанавливаем следующий обработчик для получения текста комментария
        dp.register_message_handler(process_feedback, content_types=types.ContentType.TEXT)
    else:
        await message.answer("Сначала пройдите регистрацию!")

# Обработчик для текстового комментария
async def process_feedback(message: types.Message):
    feedback = message.text
    try:
        # Получаем id пользователя, оставившего отзыв
        cursor.execute('SELECT id FROM users WHERE phone_number=?', (phone_number,))
        user_id = cursor.fetchone()[0]  # Получаем первое значение из кортежа
        # Сохраняем отзыв в базу данных
        cursor.execute('INSERT INTO feedbacks (user_id, text) VALUES (?, ?)', (user_id, feedback))
        conn.commit()
        await message.answer("Спасибо за ваш отзыв!")
    except Exception as e:
        logger.error(f"Ошибка при сохранении отзыва: {e}")
        await message.answer("Произошла ошибка при сохранении вашего отзыва. Пожалуйста, попробуйте ещё раз.")
    finally:
        # Удаляем обработчик сообщений о комментарии, чтобы не перехватывать следующие сообщения
        dp.message_handlers.unregister(process_feedback)

def calculate_cleaning_cost(cleaning_type, cleaning_standard, area):
    if cleaning_type == "Генеральная":
        return area * 1500
    elif cleaning_type == "После ремонта":
        return area * 2000
    elif cleaning_type == "Поддерживающая":
        return area * 800
    else:
        return 0

@dp.message_handler(lambda message: message.text == "Закажите очистку", state="*")
async def order_cleaning(message: types.Message):
    await CleaningOrder.waiting_for_cleaning_type.set()
    await message.answer("Выберите тип уборки👇",
                         reply_markup=ReplyKeyboardMarkup(
                             keyboard=[
                                 [KeyboardButton(text="Генеральная")],
                                 [KeyboardButton(text="После ремонта")],
                                 [KeyboardButton(text="Поддерживающая")]
                             ],
                             resize_keyboard=True,
                             selective=True
                         ))

# Handler for receiving cleaning type
@dp.message_handler(state=CleaningOrder.waiting_for_cleaning_type)
async def set_cleaning_type(message: types.Message, state: FSMContext):
    if message.text not in ["Генеральная", "После ремонта", "Поддерживающая"]:
        await message.answer("Пожалуйста, выберите тип уборки из предложенных.")
        return
    await state.update_data(cleaning_type=message.text)
    await CleaningOrder.next()
    await message.answer("Введите площадь помещения в квадратных метрах:")

# Handler for receiving area
@dp.message_handler(state=CleaningOrder.waiting_for_area)
async def set_area(message: types.Message, state: FSMContext):
    area = message.text
    if not area.isdigit():
        await message.answer("Пожалуйста, введите числовое значение площади.")
        return
    await state.update_data(area=int(area))
    await CleaningOrder.next()
    await message.answer("Введите адрес уборки:")

# Handler for receiving address
@dp.message_handler(state=CleaningOrder.waiting_for_address)
async def set_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    user_data = await state.get_data()
    cleaning_type = user_data['cleaning_type']
    area = user_data['area']
    cost = calculate_cleaning_cost(cleaning_type, "standard", area)
    address = user_data['address']

    # Save order in database
    cursor.execute('''
        INSERT INTO orders (user_id, cleaning_type, cleaning_standard, area, address, cost)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (message.from_user.id, cleaning_type, "standard", area, address, cost))
    conn.commit()

    await message.answer(f"Заказ на уборку сохранён. Тип: {cleaning_type}, Площадь: {area} кв.м, Адрес: {address}, Стоимость: {cost}тенге")
     # Предлагаем пользователю вернуться к меню
    await message.answer("Что вы хотите сделать дальше?", reply_markup=markup)
    await state.finish()

@dp.message_handler(lambda message: message.text == "Информация о компании")
async def show_company_info(message: types.Message):
    # Информация о компании
    company_info = """
    🏢 Название компании: EcoClean
    📍 Адрес: г. Нур-Султан, ул. Пушкина, д. 10
    📞 Телефон: +7 777 123 4567
    🕒 Часы работы: Пн-Пт, с 9:00 до 18:00
    🌐 Веб-сайт: www.ecoclean.kz
    📧 Email: info@ecoclean.kz
    """
    await message.answer(company_info, reply_markup=markup)


# Обработчик для кнопки "Фото галерея отеля"
@dp.message_handler(lambda message: message.text == "Пример работы")
async def show_hotel_gallery(message: types.Message):
    global registered  # Объявляем переменную как глобальную
    if registered:
        # Путь к папке с фотографиями отеля
        gallery_path = "img"

        # Получаем список файлов в папке
        photo_files = os.listdir(gallery_path)

        if photo_files:
            # Отправляем фотографии пользователю
            for photo_file in photo_files:
                photo_full_path = os.path.join(gallery_path, photo_file)
                # Отправляем фотографию с использованием InputFile
                with open(photo_full_path, 'rb') as photo:
                    await message.answer_photo(photo=InputFile(photo))
                    await message.answer("Что вы хотите сделать дальше?", reply_markup=markup)
        else:
            await message.answer("Қонақ үй галереясында фотосуреттер жоқ.")
    else:
        await message.answer("Алдымен тіркеуден өтіңіз!")

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

# Обработчик для кнопок "Пройти регистрацию"
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
    executor.start_polling(dp, skip_updates=True)
