from aiogram import types
from aiogram.types import InputFile

from database.db import cursor, conn, get_user_info

import os

import *

# Обработчик для кнопок меню
@dp.message_handler(
    lambda message: registered and message.text in ["Мой профиль", "Закажите очистку", "Оставьте комментарий"])
async def process_menu(message: types.Message):
    if message.text == "Мой профиль":
        # Отображение профиля пользователя
        user_info = await get_user_info(phone_number, registered)
        await message.answer(user_info)
    elif message.text == "Закажите очистку":
        # Обработка заказа очистки
        await order_cleaning(message)
    elif message.text == "Оставьте комментарий":
        # Обработка оставления комментария
        await leave_feedback(message)


# Функция для получения информации о пользователе из базы данных


# Обработчик для оставления комментария
# @dp.message_handler(lambda message: message.text == "Оставьте комментарий")
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


def calculate_cleaning_cost(cleaning_type, area, single_windows, double_windows, triple_windows):
    # Расчет базовой стоимости уборки по типу
    if cleaning_type == "Генеральная":
        base_cost = area * 1500
    elif cleaning_type == "После ремонта":
        base_cost = area * 2000
    elif cleaning_type == "Поддерживающая":
        base_cost = area * 800
    else:
        base_cost = 0

    # Расчет стоимости уборки окон
    window_cost = (single_windows * 300) + (double_windows * 500) + (triple_windows * 700)

    # Возвращаем общую стоимость
    return base_cost + window_cost




@dp.message_handler(lambda message: message.text == "Информация о компании")
async def show_company_info(message: types.Message):
    try:
        cursor.execute('SELECT name, address, phone, working_hours, website, email FROM company_info')
        company_data = cursor.fetchone()
        if company_data:
            name, address, phone, working_hours, website, email = company_data
            company_info = f"""
            🏢 Название компании: {name}
        📍 Адрес: {address} 
        📞 Телефон: {phone}
        🕒 Часы работы: {working_hours}
        🌐 Веб-сайт: {website}
        📧 Email: {email}
            """
            await message.answer(company_info, reply_markup=markup)
        else:
            await message.answer("Информация о компании не найдена.")
    except Exception as e:
        logger.error(f"Произошла ошибка при извлечении информации о компании: {e}")
        await message.answer("Произошла ошибка при извлечении информации о компании.")


@dp.message_handler(lambda message: message.text == "Цены")
async def price_list(message: types.Message):
    cost_info = "Тип уборки: \n\nГенеральная уброка 🧽: 1500 тг за кв.м. \nПосле ремонта 🧼: 2000 тг за кв.м. \nПоддерживающая 🧹: 800 тг за кв.м. \n\nОкна: \n\nОдностворчатое 🪟: 300 тг за кол-во \nДвустворчатое 🪟🪟: 500 тг за кол-во \nТрехстворчатое 🪟🪟🪟: 700 тг за кол-во"
    await message.answer(cost_info, reply_markup=markup)


@dp.message_handler(lambda message: message.text == "Показать все новости")
async def show_all_news(message: types.Message):
    cursor.execute("SELECT title, content, image_path FROM news ORDER BY published_date DESC")
    news_items = cursor.fetchall()
    if news_items:
        for title, content, image_path in news_items:
            news_message = f"{title}\n{content}"
            if os.path.exists(image_path):
                await message.answer_photo(photo=open(image_path, 'rb'), caption=news_message)
            else:
                await message.answer(news_message)
    else:
        await message.answer("На данный момент новостей нет.")


# Обработчик для кнопки "Фото галерея отеля"
@dp.message_handler(lambda message: message.text == "Пример работы")
async def show_hotel_gallery(message: types.Message):
    global registered  # Объявляем переменную как глобальную
    if registered:
        # Путь к папке с фотографиями отеля
        gallery_path = "resources/img"

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
            await message.answer("Фото нет.")
    else:
        await message.answer("Пройти регистрацию")