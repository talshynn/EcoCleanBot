import sqlite3
import logging
import os
import logging
import sqlite3
import openai
from aiogram import executor
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,InputFile
import asyncio
from config import DATABASE_PATH
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

conn = sqlite3.connect(DATABASE_PATH)
cursor = conn.cursor()

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
            single_windows INTEGER,
            double_windows INTEGER,
            triple_windows INTEGER,
            address TEXT,
            date_and_time TEXT,
            cost INTEGER,
            washer_id INTEGER NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
            FOREIGN KEY(washer_id) REFERENCES washers(id)
        )
    ''')
    conn.commit()
    logger.info("Table 'orders' created successfully")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            address TEXT,
            phone TEXT,
            working_hours TEXT,
            website TEXT,
            email TEXT
        )
    ''')
    conn.commit()
    logger.info("Table 'company_info' created successfully")

    cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER
            )
        ''')
    conn.commit()
    logger.info("Table 'washers' created successfully")

    cursor.execute('''
                CREATE TABLE IF NOT EXISTS washers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    washer_id INTEGER
                    create_admin INTEGER
                )
            ''')
    conn.commit()
    logger.info("Table 'admins' created successfully")

def insert_orders():
    cursor.execute('SELECT * FROM orders')
    if cursor.fetchone() is None:
        try:
            # Вчерашний заказ
            cursor.execute('''
                INSERT INTO orders (user_id, cleaning_type, cleaning_standard, area, single_windows, double_windows, triple_windows, address, date_and_time, cost, washer_id)
                VALUES (1, 'Генеральная', NULL, 50, 3, 2, 0, 'Ул. Ленина, 123', '28.05.2024 22:00', 2000, NULL)
            ''')

            # Сегодняшний заказ
            cursor.execute('''
                INSERT INTO orders (user_id, cleaning_type, cleaning_standard, area, single_windows, double_windows, triple_windows, address, date_and_time, cost, washer_id)
                VALUES (1, 'После ремонта', NULL, 80, 1, 4, 1, 'Ул. Пушкина, 456', '29.05.2024 22:30', 3500, NULL)
            ''')

            # Завтрашний заказ
            cursor.execute('''
                INSERT INTO orders (user_id, cleaning_type, cleaning_standard, area, single_windows, double_windows, triple_windows, address, date_and_time, cost, washer_id)
                VALUES (1, 'Поддерживающая', NULL, 30, 2, 1, 0, 'Ул. Гагарина, 789', '31.05.2024 22:00', 1500, NULL)
            ''')

            # Послезавтрашний заказ
            cursor.execute('''
                INSERT INTO orders (user_id, cleaning_type, cleaning_standard, area, single_windows, double_windows, triple_windows, address, date_and_time, cost, washer_id)
                VALUES (1, 'После ремонта', NULL, 60, 0, 3, 1, 'Ул. Чехова, 101', '30.05.2024 11:00', 2800, NULL)
            ''')

            conn.commit()
            logger.info("Initial orders inserted successfully")
        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error during insert: {e}")
        except Exception as e:
            logger.error(f"An error occurred while inserting orders: {e}")
    else:
        logger.info("Orders already exist. Skipping insert.")

def create_news_table():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            image_path TEXT,
            content TEXT,
            published_date DATE
        )
    ''')
    conn.commit()
    logger.info("Table 'news' created successfully")

def insert_sample_news():
    news_items = [
        ("Заголовок новости 1", "Мультиформатная розничная сеть «Лента» завершила тестирование автоматической поломоечной машины Pudu CC1 и приняла решение о ее «трудоустройстве» в одном из московских супермаркетов. Первый робот-уборщик уже приступил к своим обязанностям в «Супер Ленте» на Новочеркасском бульваре", "2023-05-15", "resources/new/new1.jpg"),
        ("Заголовок новости 2", "Содержание новости 2", "2023-05-16", "resources/new/new2.jpg"),
    ]
    cursor.executemany('''
        INSERT INTO news (title, content, published_date, image_path)
        VALUES (?, ?, ?, ?)
    ''', news_items)
    conn.commit()

def insert_admins():
    admins = [
        (1130083020,),
        (797007193,),
        # Добавьте свое айди чтобы смотреть панель админов https://web.telegram.org/k/#@userinfobot
    ]
    try:
        cursor.executemany('''
            INSERT INTO admins (admin_id)
            VALUES (?)
        ''', admins)
        conn.commit()
        logger.info("Successfully inserted admins")
    except sqlite3.IntegrityError as e:
        logger.error(f"Integrity error during insert: {e}")
    except Exception as e:
        logger.error(f"An error occurred while inserting admins info: {e}")


def insert_washers():
    washers = [
        ('Washer 1', 1130083020),
        ('Washer 2', 797007193),
        # Добавьте свое айди чтобы смотреть панель сотрудников https://web.telegram.org/k/#@userinfobot
    ]
    cursor.executemany('''
        INSERT INTO washers (name, washer_id)
        VALUES (?, ?)
    ''', washers)
    conn.commit()


def insert_initial_company_info():
    cursor.execute('SELECT * FROM company_info')
    if cursor.fetchone() is None:
        try:
            cursor.execute('''
                INSERT INTO company_info (name, address, phone, working_hours, website, email)
                VALUES ('EcoClean', 'г. Нур-Султан, ул. Пушкина, д. 10', '+7 777 123 4567', 'Пн-Пт, с 9:00 до 18:00', 'www.ecoclean.kz', 'info@ecoclean.kz')
            ''')
            conn.commit()
            logger.info("Initial company info inserted successfully")
        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error during insert: {e}")
        except Exception as e:
            logger.error(f"An error occurred while inserting company info: {e}")
    else:
        logger.info("Company info already exists. Skipping insert.")


async def get_user_info(phone_number, registered):
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

def create_new_washer(name_state, washer_id_state):
    try:
        cursor.execute('''
            INSERT INTO washers (name, washer_id)
            VALUES (?, ?)
        ''', (name_state, washer_id_state))
        conn.commit()
        logger.info("Successfully inserted washer")
    except sqlite3.IntegrityError as e:
        logger.error(f"Integrity error during insert washer: {e}")
    except Exception as e:
        logger.error(f"An error occurred while inserting washer info: {e}")