import os
import logging
import sqlite3
from datetime import datetime, timedelta

import openai
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputFile, InlineKeyboardMarkup, \
    InlineKeyboardButton
import asyncio

from aiogram.utils.callback_data import CallbackData

from config import DATABASE_PATH
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import API_TOKEN
from database.db import cursor, conn, create_tables, insert_initial_company_info, create_news_table, insert_sample_news, \
    get_user_info, insert_admins, create_new_washer, insert_washers, insert_orders
from handlers.user import registration_handler

import speech_recognition as sr
from pydub import AudioSegment
import requests
import os


@dp.message_handler(commands=['worker'])
async def worker_panel(message: types.Message):
    cursor.execute("SELECT washer_id FROM washers")
    washers_ids = cursor.fetchall()
    print(washers_ids)
    WASHER_IDS = [washer_id[0] for washer_id in washers_ids]
    # Проверка, является ли отправитель администратором
    if message.from_user.id in WASHER_IDS:
        await message.answer(
            "Добро пожаловать в панель сотрудника!",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Заказы на сегодня")],
                    [KeyboardButton(text="Заказы на завтра")],
                    [KeyboardButton(text="Расписание заказов")],
                    [KeyboardButton(text="История заказов")],
                ],
                resize_keyboard=True,
                selective=True  # Добавим атрибут selective=True
            ))
        # Отобразить меню администратора
    else:
        await message.answer("У вас нет прав доступа к панели сотрудника.")


@dp.message_handler(lambda message: message.text == "Заказы на сегодня")
async def orders_today(message: types.Message):
    washer_telegram_id = message.from_user.id

    cursor.execute('SELECT id FROM washers WHERE washer_id = ?', (washer_telegram_id,))
    washer = cursor.fetchone()
    washer_id = washer[0]
    today = datetime.now().strftime("%d.%m.%Y")
    cursor.execute('SELECT * FROM orders WHERE washer_id = ? AND date_and_time LIKE ?', (washer_id, f"{today} %"))
    orders_today = cursor.fetchall()

    if not orders_today:
        await message.answer("На сегодня нет заказов.")
    else:
        response = "Заказы на сегодня:\n"
        for order in orders_today:
            response += f"ID: {order[0]}, Пользователь: {order[1]}, Дата и время: {order[9]}, Адрес: {order[8]}\n"
        await message.answer(response)


# Обработчик команды для просмотра заказов на завтра
@dp.message_handler(lambda message: message.text == "Заказы на завтра")
async def orders_tomorrow(message: types.Message):
    washer_telegram_id = message.from_user.id
    cursor.execute('SELECT id FROM washers WHERE washer_id = ?', (washer_telegram_id,))
    washer = cursor.fetchone()

    washer_id = washer[0]

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
    cursor.execute('SELECT * FROM orders WHERE washer_id = ? AND date_and_time LIKE ?', (washer_id, f"{tomorrow} %",))
    orders_tomorrow = cursor.fetchall()

    if not orders_tomorrow:
        await message.answer("На завтра нет заказов.")
    else:
        response = "Заказы на завтра:\n"
        for order in orders_tomorrow:
            response += f"ID: {order[0]}, Пользователь: {order[1]}, Дата и время: {order[9]}, Адрес: {order[8]}\n"
        await message.answer(response)


# Обработчик команды для просмотра расписания заказов
@dp.message_handler(lambda message: message.text == "Расписание заказов")
async def schedule(message: types.Message):
    cursor.execute('SELECT * FROM orders ORDER BY date_and_time')
    all_orders = cursor.fetchall()

    if not all_orders:
        await message.answer("Нет заказов в расписании.")
    else:
        response = "Расписание заказов:\n"
        for order in all_orders:
            response += f"ID: {order[0]}, Пользователь: {order[1]}, Дата и время: {order[9]}\n"
        await message.answer(response)


# Обработчик команды для просмотра истории заказов
@dp.message_handler(lambda message: message.text == "История заказов")
async def order_history(message: types.Message):

    now = datetime.now().strftime("%d.%m.%Y")
    cursor.execute('SELECT * FROM orders WHERE date_and_time < ? ORDER BY date_and_time DESC', (f"{now} %",))
    order_history = cursor.fetchall()

    if not order_history:
        await message.answer("Нет истории заказов.")
    else:
        response = "История заказов:\n"
        for order in order_history:
            response += f"ID: {order[0]}, Пользователь: {order[1]}, Дата и время: {order[9]}\n"
        await message.answer(response)