from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from database.db import cursor, conn


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


# Define the states
class CleaningOrder(StatesGroup):
    waiting_for_cleaning_type = State()
    waiting_for_area = State()
    waiting_for_window_cleaning = State()
    waiting_for_single_windows = State()
    waiting_for_double_windows = State()
    waiting_for_triple_windows = State()
    waiting_for_date_and_time = State()  # новое состояние для запроса даты и времени
    waiting_for_address = State()


# Handler for setting cleaning type
@dp.message_handler(state=CleaningOrder.waiting_for_cleaning_type)
async def set_cleaning_type(message: types.Message, state: FSMContext):
    if message.text not in ["Генеральная", "После ремонта", "Поддерживающая"]:
        await message.answer("Пожалуйста, выберите тип уборки из предложенных.")
        return
    await state.update_data(cleaning_type=message.text)
    await CleaningOrder.waiting_for_area.set()
    await message.answer("Введите площадь помещения в квадратных метрах:")


# Handler for receiving area
@dp.message_handler(state=CleaningOrder.waiting_for_area)
async def set_area(message: types.Message, state: FSMContext):
    area = message.text
    if not area.isdigit():
        await message.answer("Пожалуйста, введите числовое значение площади.")
        return
    await state.update_data(area=int(area))
    await CleaningOrder.waiting_for_window_cleaning.set()
    await message.answer("Моем окна? Да или Нет")


# Handler for window cleaning decision
@dp.message_handler(state=CleaningOrder.waiting_for_window_cleaning)
async def ask_window_cleaning(message: types.Message, state: FSMContext):
    if message.text.lower() == "да":
        await CleaningOrder.waiting_for_single_windows.set()
        await message.answer("Посмотрите пример одностворчатого окна 👇")
        photo = InputFile("resources/photo/o1.jpg")  # Укажите правильный путь к файлу
        await message.answer_photo(photo=photo, caption="Пример одностворчатого окна")
        await message.answer("Напишите количество одностворчатых окон в ответном сообщении👇")
    elif message.text.lower() == "нет":
        await CleaningOrder.waiting_for_date_and_time.set()
        await message.answer("Введите желаемую дату и время уборки в формате ДД.ММ.ГГГГ ЧЧ:ММ:")


# Handlers for single, double, and triple pane windows
@dp.message_handler(state=CleaningOrder.waiting_for_single_windows)
async def set_single_windows(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите числовое значение для количества одностворчатых окон.")
        return
    await state.update_data(single_windows=int(message.text))
    await CleaningOrder.waiting_for_double_windows.set()
    await message.answer("Посмотрите пример двустворчатого окна 👇")
    photo = InputFile("resources/photo/o2.jpg")  # Укажите правильный путь к файлу
    await message.answer_photo(photo=photo, caption="Пример двустворчатого окна")
    await message.answer("Напишите количество двустворчатых окон в ответном сообщении👇")


@dp.message_handler(state=CleaningOrder.waiting_for_double_windows)
async def set_double_windows(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите числовое значение для количества двустворчатых окон.")
        return
    await state.update_data(double_windows=int(message.text))
    await CleaningOrder.waiting_for_triple_windows.set()
    await message.answer("Посмотрите пример трехстворчатого окна 👇")
    photo = InputFile("resources/photo/o3.jpg")  # Укажите правильный путь к файлу
    await message.answer_photo(photo=photo, caption="Пример трехстворчатого окна")
    await message.answer("Напишите количество трехстворчатых окон в ответном сообщении👇")


@dp.message_handler(state=CleaningOrder.waiting_for_triple_windows)
async def set_triple_windows(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите числовое значение для количества трехстворчатых окон.")
        return
    await state.update_data(triple_windows=int(message.text))
    await CleaningOrder.waiting_for_date_and_time.set()
    await message.answer("Введите желаемую дату и время уборки в формате ДД.ММ.ГГГГ ЧЧ:ММ:")


# Handler for receiving date and time
@dp.message_handler(state=CleaningOrder.waiting_for_date_and_time)
async def set_date_and_time(message: types.Message, state: FSMContext):
    await state.update_data(date_and_time=message.text)
    await CleaningOrder.waiting_for_address.set()
    await message.answer("Введите адрес уборки:")


# Handler for receiving address
@dp.message_handler(state=CleaningOrder.waiting_for_address)
async def set_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    user_data = await state.get_data()
    cleaning_type = user_data['cleaning_type']
    area = user_data['area']
    single_windows = user_data.get('single_windows', 0)
    double_windows = user_data.get('double_windows', 0)
    triple_windows = user_data.get('triple_windows', 0)
    date_and_time = user_data['date_and_time']
    address = user_data['address']
    cost = calculate_cleaning_cost(cleaning_type, area, single_windows, double_windows, triple_windows)

    # Save order in database
    cursor.execute('''
        INSERT INTO orders (user_id, cleaning_type, area, single_windows, double_windows, triple_windows, date_and_time, address, cost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        message.from_user.id, cleaning_type, area, single_windows, double_windows, triple_windows, date_and_time,
        address,
        cost))
    conn.commit()

    await message.answer(
        f"Заказ на уборку сохранён. Тип: {cleaning_type}, Площадь: {area} кв.м, Окна: одностворчатые {single_windows}, двустворчатые {double_windows}, трехстворчатые {triple_windows}, Дата и время: {date_and_time}, Адрес: {address}, Стоимость: {cost} тенге")
    await state.finish()
    # Предлагаем пользователю вернуться к главному меню или выбрать другие опции
    await message.answer(
        "Ваша заявка принята! Наш менеджер скоро с вами свяжется для согласования деталей🤝\n Вы можете перейти в главное меню✔️",
        reply_markup=markup)