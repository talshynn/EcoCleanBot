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

@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    cursor.execute("SELECT admin_id FROM admins")
    admin_ids = cursor.fetchall()
    print(admin_ids)
    ADMIN_IDS = [admin_id[0] for admin_id in admin_ids]
    # Проверка, является ли отправитель администратором
    if message.from_user.id in ADMIN_IDS:
        await message.answer(
            "Добро пожаловать в админ-панель!",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Добавить сотрудника")],
                    [KeyboardButton(text="Просмотреть заказы")],
                    [KeyboardButton(text="Назначить мойщика на заказ")],
                    [KeyboardButton(text="Изменить информацию о компании")],
                    [KeyboardButton(text="Просмотреть отзывы")],
                ],
                resize_keyboard=True,
                selective=True  # Добавим атрибут selective=True
            ))
        # Отобразить меню администратора
    else:
        await message.answer("У вас нет прав доступа к админ-панели.")


@dp.message_handler(lambda message: message.text == "Просмотреть отзывы")
async def view_feedbacks(message: types.Message):
    # Выполнение запроса на выборку отзывов
    cursor.execute('SELECT * FROM feedbacks')
    feedbacks = cursor.fetchall()

    # Проверка, есть ли отзывы в базе данных
    if not feedbacks:
        await message.answer("В базе данных нет отзывов.")
    else:
        # Отправка отзывов пользователю
        response = "Список отзывов:\n"
        for feedback in feedbacks:
            response += f"Отзыв №{feedback[0]}:\n"
            response += f"Пользователь: {feedback[1]}\n"
            response += f"Текст: {feedback[2]}\n\n"

        await message.answer(response)


class EditCompanyInfoState(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()
    waiting_for_phone_number = State()
    waiting_for_email = State()
    waiting_for_working_hours = State()
    waiting_for_website = State()


# Начинаем процесс изменения информации о компании
@dp.message_handler(lambda message: message.text == "Изменить информацию о компании", state='*')
async def edit_company_info_start(message: types.Message):
    await message.answer("Введите название компании:")
    await EditCompanyInfoState.waiting_for_name.set()


# Обработчик для ввода названия компании
@dp.message_handler(state=EditCompanyInfoState.waiting_for_name)
async def process_company_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите адрес компании:")
    await EditCompanyInfoState.waiting_for_address.set()


# Обработчик для ввода адреса компании
@dp.message_handler(state=EditCompanyInfoState.waiting_for_address)
async def process_company_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("Введите номер телефона компании:")
    await EditCompanyInfoState.waiting_for_phone_number.set()


# Обработчик для ввода номера телефона компании
@dp.message_handler(state=EditCompanyInfoState.waiting_for_phone_number)
async def process_company_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("Введите email компании:")
    await EditCompanyInfoState.waiting_for_email.set()


# Обработчик для ввода email компании
@dp.message_handler(state=EditCompanyInfoState.waiting_for_email)
async def process_company_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer("Введите время работы компании:")
    await EditCompanyInfoState.waiting_for_working_hours.set()


@dp.message_handler(state=EditCompanyInfoState.waiting_for_working_hours)
async def process_company_working_hours(message: types.Message, state: FSMContext):
    await state.update_data(working_hours=message.text)
    await message.answer("Введите сайт компании:")
    await EditCompanyInfoState.waiting_for_website.set()


# Обработчик для ввода описания компании и сохранения информации
@dp.message_handler(state=EditCompanyInfoState.waiting_for_website)
async def process_company_website(message: types.Message, state: FSMContext):
    await state.update_data(website=message.text)

    # Получаем все данные из состояния
    data = await state.get_data()
    name = data['name']
    address = data['address']
    phone = data['phone']
    email = data['email']
    working_hours = data['working_hours']
    website = data['website']

    cursor.execute('SELECT COUNT(*) FROM company_info')
    count = cursor.fetchone()[0]

    # Обновляем информацию о компании в базе данных
    try:
        if count == 0:
            # Вставляем новую запись
            cursor.execute('''
                            INSERT INTO company_info (name, address, phone, working_hours, website, email)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (name, address, phone, working_hours, website, email))
        else:
            # Обновляем существующую запись
            cursor.execute('''
                            UPDATE company_info
                            SET name = ?, address = ?, phone = ?, working_hours = ?, website = ?, email = ?
                            WHERE id = 1
                        ''', (name, address, phone, working_hours, website, email))

        conn.commit()
        await message.answer("Информация о компании успешно обновлена.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при обновлении информации о компании: {e}")

    await state.finish()


class AssignWasherState(StatesGroup):
    waiting_for_order_id = State()
    waiting_for_washer_id = State()


order_callback = CallbackData("order", "order_id")
washer_callback = CallbackData("washer", "washer_id")


# Начинаем процесс назначения мойщика через кнопку
@dp.message_handler(lambda message: message.text == "Назначить мойщика на заказ", state='*')
async def assign_washer_start(message: types.Message):
    cursor.execute('SELECT id FROM orders WHERE washer_id IS NULL')
    orders = cursor.fetchall()
    if not orders:
        await message.answer("Нет заказов без назначенного мойщика.")
        return

    keyboard = InlineKeyboardMarkup()
    for order in orders:
        keyboard.add(
            InlineKeyboardButton(text=f"Заказ {order[0]}", callback_data=order_callback.new(order_id=order[0])))

    await message.answer("Выберите заказ для назначения мойщика:", reply_markup=keyboard)
    await AssignWasherState.waiting_for_order_id.set()


# Обработчик выбора заказа
@dp.callback_query_handler(order_callback.filter(), state=AssignWasherState.waiting_for_order_id)
async def assign_washer_order_id(callback_query: types.CallbackQuery, state: FSMContext, callback_data: dict):
    order_id = callback_data['order_id']
    await state.update_data(order_id=order_id)

    cursor.execute('SELECT id, name FROM washers')
    washers = cursor.fetchall()
    if not washers:
        await callback_query.message.answer("Нет доступных мойщиков.")
        return

    keyboard = InlineKeyboardMarkup()
    for washer in washers:
        keyboard.add(InlineKeyboardButton(text=washer[1], callback_data=washer_callback.new(washer_id=washer[0])))

    await callback_query.message.answer("Выберите мойщика:", reply_markup=keyboard)
    await AssignWasherState.waiting_for_washer_id.set()


# Обработчик выбора мойщика
@dp.callback_query_handler(washer_callback.filter(), state=AssignWasherState.waiting_for_washer_id)
async def assign_washer_washer_id(callback_query: types.CallbackQuery, state: FSMContext, callback_data: dict):
    washer_id = callback_data['washer_id']
    data = await state.get_data()
    order_id = data['order_id']

    try:
        cursor.execute('''
            UPDATE orders
            SET washer_id = ?
            WHERE id = ?
        ''', (washer_id, order_id))
        conn.commit()
        await callback_query.message.answer("Мойщик успешно назначен на заказ!")
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка при назначении мойщика: {e}")

    await state.finish()


@dp.message_handler(lambda message: message.text == "Просмотреть заказы")
async def view_orders(message: types.Message):
    cursor.execute("SELECT * FROM orders")
    orders = cursor.fetchall()
    if orders:
        for order in orders:
            order_info = (f"ID Заказа: {order[0]}\n"
                          f"ID Пользователя: {order[1]}\n"
                          f"Тип уборки: {order[2]}\n"
                          f"Стандартная уборка: {order[3]}\n"
                          f"Размер: {order[4]}\n"
                          f"Одностворчатые окна: {order[5]}\n"
                          f"Двустворчатые окна: {order[6]}\n"
                          f"Трехстворчатые окна: {order[7]}\n"
                          f"Адрес: {order[8]}\n"
                          f"Время: {order[9]}\n"
                          f"Цена: {order[10]}\n"
                          f"Назначенный мойщик: {order[11]}\n")
            await message.answer(order_info)
    else:
        await message.answer("No orders found.")


class NewWasherState(StatesGroup):
    waiting_for_name = State()
    waiting_for_id = State()


@dp.message_handler(lambda message: message.text == "Добавить сотрудника")
async def create_washer(message: types.Message):
    # Запрос имени
    await message.answer("Введите имя нового сотрудника:")
    await NewWasherState.waiting_for_name.set()


# Обработчик для имени
@dp.message_handler(state=NewWasherState.waiting_for_name)
async def washer_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    # Запрос номера телефона
    await message.answer("Введите ID сотрудника в телеграмме")
    await NewWasherState.waiting_for_id.set()


# Обработчик для даты рождения
@dp.message_handler(state=NewWasherState.waiting_for_id)
async def adding_washer(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['washer_id'] = message.text
    # Завершение регистрации и добавление пользователя в базу данных
    async with state.proxy() as data:
        name = data['name']
        washer_id = data['washer_id']
        # Добавление пользователя в базу данных
        create_new_washer(name, washer_id)
    # Сброс состояния
    await state.finish()
    # Отправка сообщения об успешной регистрации
    await message.answer("Сотрудник успешно зарегистрирован!")