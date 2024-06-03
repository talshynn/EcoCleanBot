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



@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice(message: types.Message):
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path

    # Скачивание файла
    file_url = f'https://api.telegram.org/file/bot{API_TOKEN}/{file_path}'
    voice_data = requests.get(file_url)

    # Сохранение голосового сообщения
    with open('voice.ogg', 'wb') as f:
        f.write(voice_data.content)

    # Преобразование OGG в WAV с использованием pydub
    audio = AudioSegment.from_ogg('voice.ogg')
    audio.export('voice.wav', format='wav')

    # Распознавание речи
    recognizer = sr.Recognizer()
    with sr.AudioFile('voice.wav') as source:
        audio_data = recognizer.record(source)
        try:
            recognized_text = recognizer.recognize_google(audio_data, language="ru-RU")
            if recognized_text.lower() == "мой профиль":
                await get_user_info(message)
            elif recognized_text.lower() == "цены":
                await price_list(message)
            elif recognized_text.lower() == "заказать очистку":
                await order_cleaning(message)
            elif recognized_text.lower() == "оставить комментарий":
                await leave_feedback(message)
            elif recognized_text.lower() == "информация о компании":
                await show_company_info(message)
            elif recognized_text.lower() == "пример работы":
                await show_hotel_gallery(message)
            elif recognized_text.lower() == "покажи все новости":
                await show_all_news(message)
            elif recognized_text.lower() == "диалог с OpenAI":
                await start_openai_dialog(message)
            else:
                await message.reply(f"Распознанный текст: {recognized_text}")

        except sr.UnknownValueError:
            await message.reply("Не удалось распознать речь.")
        except sr.RequestError as e:
            await message.reply(f"Ошибка сервиса распознавания речи: {e}")

    # Удаление временных файлов
    os.remove('voice.ogg')
    os.remove('voice.wav')