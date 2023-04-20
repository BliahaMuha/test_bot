import os
import requests
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import StatesGroup, State
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from models import Session, User, init_db
from dotenv import load_dotenv

# Загружаем ключи API из dotenv файла
load_dotenv()

BOT_TOKEN = os.getenv('TOKEN')                  # Токен бота телеграм
YOUR_APPID = os.getenv('YOUR_APPID')            # Токен API погоды сайт https://openweathermap.org
API_KEY = os.getenv("API_KEY")                  # Токен API конвертера валют сайт https://app.currencyapi.com/
bot = Bot(token=BOT_TOKEN)

# Инициируем БД
init_db()

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Добавляем объект хранилища данных в диспетчер
dp = Dispatcher(bot, storage=MemoryStorage())


# Класс для хранения состояния пользователя
class UserState(StatesGroup):
    CHOOSING = State()  # Состояние выбора функции бота
    GUESS_CITY = State()  # Состояние получения погоды
    CONVERT_CURRENCY = State()  # Состояние конвертации валют


# Обработчик команды "/start"
@dp.message_handler(Command('start'))
async def start(message: types.Message):
    telegram_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username
    with Session() as session:
        user = User(telegram_id=telegram_id,
                    first_name=first_name,
                    last_name=last_name,
                    username=username)
        # init_db()
        session.add(user)
        print(user.username)
        session.commit()

    # Отправляем сообщение и предлагаем пользователю выбрать функцию бота
    await message.reply(
        f"Привет, {first_name}! \nВыбери функцию, которую ты хочешь использовать:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [
                    types.KeyboardButton(text="/start"),
                    types.KeyboardButton(text="☀️ Погода"),
                    types.KeyboardButton(text="💰 Конвертер валют")
                ],
                [
                    types.KeyboardButton(text="🐈 Милые котики"),
                    types.KeyboardButton(text="📊 Опрос"),
                    types.KeyboardButton(text="🙅‍♂️ Отменить выбор")
                ]
            ]
        )
    )
    if message == "🙅‍♂️ Отменить выбор":
        await message.answer("Нажми /start чтобы выбрать другую функцию:")
        await UserState.CHOOSING.set()
    # Переходим в состояние CHOOSING, чтобы отслеживать выбор пользователя
    await UserState.CHOOSING.set()


# Обработчик на выбор функции бота
@dp.message_handler(state=UserState.CHOOSING)
async def choice(message: types.Message, state: FSMContext):
    # Проверяем, что пользователь выбрал одну из функций бота
    if message.text == "☀️ Погода":
        # Отправляем сообщение и предлагаем пользователю ввести город
        await message.reply("Чтобы узнать погоду, введите город:")
        # Переходим в состояние GUESS_CITY, чтобы отслеживать город, введенный пользователем
        await UserState.GUESS_CITY.set()

    elif message.text == "💰 Конвертер валют":
        # Отправляем сообщение и предлагаем пользователю ввести сумму и валюту
        await message.reply("Введите сумму,валюту, из которой будем конвертировать, и валюту, в которую будем "
                            "конвертировать, через пробел (например, '100 USD RUB'):")
        # Переходим в состояние CONVERT_CURRENCY, чтобы отслеживать данные, введенные пользователем
        await UserState.CONVERT_CURRENCY.set()

    elif message.text == "🐈 Милые котики":
        # Формируем ссылку на случайную картинку с милыми животными
        response = requests.get('https://api.thecatapi.com/v1/images/search')
        cat_url = response.json()[0]['url']
        await bot.send_photo(chat_id=message.chat.id, photo=cat_url, caption='Котик для вас ❤️')
        await message.answer('Выбери функцию:')
    elif message.text == "📊 Опрос":
        # Отправляем опрос в группу
        telegram_id = message.from_id
        await bot.send_poll(
            chat_id=telegram_id,
            question="Какой ваш любимый цвет?",
            options=["Красный", "Зеленый", "Синий", "Желтый"]
        )
        await message.answer('Выбери функцию:')
    elif message.text == "🙅‍♂️ Отменить выбор":
        await message.answer("Нажми /start чтобы выбрать другую функцию:")
        await state.reset_state(with_data=False) and UserState.CHOOSING.set()
    else:
        # Если пользователь ввел что-то другое, ничего не делаем и продолжаем в состоянии CHOOSING
        await message.reply("Не удалось распознать ваш выбор. Пожалуйста, выберите одну из функций бота.")


# Обработчик на введенный город
@dp.message_handler(state=UserState.GUESS_CITY)
async def guess_city(message: types.Message, state: FSMContext):
    # Получаем город, введенный пользователем
    city = message.text.strip()
    # Проверяем, что город не пустой
    if not city:
        await message.reply("Вы не указали город. Пожалуйста, введите город.")
        return
    # Отправляем запрос на API погоды для получения погоды в указанном городе
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={YOUR_APPID}&units=metric"
    response = requests.get(url)
    data = response.json()

    if data and 'main' in data:
        # Если данные получены успешно, формируем сообщение с погодой и отправляем пользователю
        temperature = data['main']['temp']
        feels_like = data['main']['feels_like']
        description = data['weather'][0]['description']

        message_text = f"Погода в городе {city}:\nТемпература: {temperature:.1f}°C\nОщущается как: {feels_like:.1f}°C\nОписание: {description}"
        await message.reply(message_text)

        # Выходим из состояния GUESS_CITY и переходим в состояние CHOOSING
        await state.finish()
        await message.answer('Выбери функцию:')
        await UserState.CHOOSING.set()
    elif message.text == "🙅‍♂️ Отменить выбор":
        await message.answer("Нажми /start чтобы выбрать другую функцию:")
        await state.reset_state(with_data=False) and UserState.CHOOSING.set()

    else:
        # Если произошла ошибка при получении данных, сообщаем об этом пользователю и продолжаем в состоянии GUESS_CITY
        await message.reply(f"Не удалось получить погоду для города {city}. Пожалуйста, попробуйте еще раз.")


# Обработчик на введенную сумму и валюту
@dp.message_handler(state=UserState.CONVERT_CURRENCY)
async def convert_currency(message: types.Message, state: FSMContext):
    # Получаем сумму и валюту, введенные пользователем
    text = message.text.strip()

    # Проверяем, что данные не пустые
    if not text:
        await message.reply("Вы не указали данные для конвертации. Пожалуйста, введите сумму и валюты.")
        return
    elif message.text == "🙅‍♂️ Отменить выбор":
        await message.answer("Нажми /start чтобы выбрать другую функцию:")
        await state.reset_state(with_data=False) and UserState.CHOOSING.set()
        return
    data = text.split()
    # Проверяем, что введены аргументы
    if len(data) != 3:
        await message.reply("Неверный формат данных для конвертации. Пожалуйста, введите сумму и валюты через пробел.")
        return

    amount = None
    try:
        amount = float(data[0])
    except ValueError:
        await message.reply("Сумма должна быть числом. Пожалуйста, введите корректную сумму.")
        return

    # Получаем коды и названия изначальной и конечной валюты
    currency_from = data[1].upper()
    currency_to = data[2].upper()
    url = f'http://api.currencyapi.com/v3/latest?apikey={API_KEY}&currencies{currency_to}&base_currency={currency_from}'
    response = requests.get(url)
    data = response.json()

    if data is not None:
        rate = data['data'][currency_to]['value']
        # Вычисляем конвертированную сумму
        result = round(amount * rate, 2)

        # Формируем сообщение о конвертации и отправляем пользователю
        message_text = f"{amount} {currency_from} = {result} {currency_to}"
        await message.reply(message_text)

        # Выходим из состояния CONVERT_CURRENCY и переходим в состояние CHOOSING
        await state.finish()
        await message.answer('Выбери функцию:')
        await UserState.CHOOSING.set()

    else:
        if not data or 'error' in data:
            error_message = data['error']
        else:
            error_message = f"Не удалось получить курс для валюты {currency_from}."
        await message.reply(f"{error_message} Пожалуйста, попробуйте еще раз.")


if __name__ == '__main__':
    executor.start_polling(dp)
