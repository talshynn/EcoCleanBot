# handlers/registration_handler.py

import os
import logging
import sqlite3
import openai
from aiogram import executor
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,InputFile
import asyncio

from bot import dp, markup
from config import DATABASE_PATH
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from database.db import cursor, conn

# Глобальные переменные для хранения имени и номера телефона
name = ""
phone_number = ""
birthday = ""
registered = False  # Переменная для отслеживания успешной регистрации


@dp.message_handler(lambda message: message.text == "Авторизоваться")
async def register_start(message: types.Message):
    # Запрос имени
    await message.answer("Введите логин",
                         reply_markup=ReplyKeyboardRemove())  # Удаляем клавиатуру


@dp.message_handler(commands=['user'])
async def user_start(message: types.Message):
    await message.answer("Панель пользователя, Выберите действие:", reply_markup=markup)


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    global name, phone_number, birthday, registered
    name = ""
    phone_number = ""
    birthday = ""
    registered = False
    # Приветственное сообщение и кнопка "Пройти регистрацию"
    await message.answer(
        "EcoCleanBot - удобный сервис для записи на уборку и химчистку. \nЧтобы продолжить, пройдите регистрацию👇",
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