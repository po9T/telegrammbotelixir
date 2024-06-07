import telebot
import sqlite3
import random
import string
import secrets
import subprocess
import asyncio

from telebot import types
# Подключение к базе данных SQLite
conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()

# Создание таблицы для хранения информации о пользователях
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                (id INTEGER PRIMARY KEY, user_id INTEGER, username TEXT, balance INTEGER)''')
conn.commit()

cursor.execute('''CREATE TABLE IF NOT EXISTS promo_codes
                (id INTEGER PRIMARY KEY, code TEXT, amount INTEGER, is_used INTEGER)''')
conn.commit()

# Токен вашего бота
API_TOKEN = '6848583958:AAFQ4KJ4xe-w2_46s3jWcQL8DrFV9QusOvs'
admin_id_1 = 1252952776
admin_id_2 = 1991169681
admins = [admin_id_1, admin_id_2]
# Создание экземпляра бота
bot = telebot.TeleBot(API_TOKEN)

def get_connection():
    return sqlite3.connect('bot_database.db')

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    conn = get_connection()  # Получаем новое подключение к базе данных
    cursor = conn.cursor()

    user_id = message.chat.id
    username = message.from_user.username  # Получаем имя пользователя

    # Проверяем, существует ли пользователь с таким ID
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()

    if result is None:  # Если пользователь не найден, создаем новую запись
        cursor.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)", (user_id, username, 0))
        conn.commit()
        bot.send_message(message.chat.id, f"Добро пожаловать, {username}! Ваш аккаунт был успешно создан.")

        # Создаем клавиатуру с кнопками меню
    keyboard = types.ReplyKeyboardMarkup(row_width=2)
    item1 = types.KeyboardButton("Проверить баланс")
    item2 = types.KeyboardButton("Ввести промокод")
    if user_id in [admin_id_1, admin_id_2]:  # Проверяем, является ли пользователь администратором
        item3 = types.KeyboardButton("Админ-панель")
        keyboard.add(item1, item2, item3)
    else:
        keyboard.add(item1, item2)

        # Отправляем сообщение с клавиатурой
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=keyboard)

    conn.close()  # Закрываем подключение к базе данных
# Обработчик для кнопки "Проверить баланс"
@bot.message_handler(func=lambda message: message.text == 'Проверить баланс')
def handle_check_balance(message):
    conn = get_connection()  # Получаем новое подключение к базе данных
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (message.chat.id,))
    result = cursor.fetchone()
    if result:
        bot.send_message(message.chat.id, f"Ваш текущий баланс: {result[0]} рублей")
    else:
        bot.send_message(message.chat.id, "Аккаунт не найден. Пожалуйста, создайте аккаунт.")
    conn.close()  # Закрываем подключение к базе данных

# Обработчик для кнопки "Ввести промокод"
@bot.message_handler(func=lambda message: message.text == 'Ввести промокод')
def handle_enter_promocode(message):
    msg = bot.send_message(message.chat.id, "Введите промокод:")
    bot.register_next_step_handler(msg, handle_check_promocode)

# Функция обновления баланса пользователя
def update_balance(user_id, amount):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# Функция обработки введенного промокода
def handle_check_promocode(message):
    promo_code = message.text
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT amount FROM promo_codes WHERE code = ? AND is_used = 0", (promo_code,))
    result = cursor.fetchone()
    if result:
        amount = result[0]  # Получаем сумму из результата запроса
        cursor.execute("UPDATE promo_codes SET is_used = 1 WHERE code = ?", (promo_code,))
        conn.commit()
        user_id = message.from_user.id
        update_balance(user_id, amount)  # Обновляем баланс пользователя
        bot.send_message(message.chat.id, f"Промокод {promo_code} успешно использован! Сумма {amount} выдана на ваш баланс.")
    else:
        bot.send_message(message.chat.id, "Неверный промокод или он уже был использован")

# Обработчик для кнопки "Админ-панель"
@bot.message_handler(func=lambda message: message.text == 'Админ-панель')
def handle_admin_panel(message):
    if message.chat.id in admins:
        keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        keyboard.add(telebot.types.KeyboardButton('Создать промокод'))
        keyboard.add(telebot.types.KeyboardButton('Очистить баланс'))
        keyboard.add(telebot.types.KeyboardButton('Получить ID пользователей'))
        keyboard.add(telebot.types.KeyboardButton('Вернуться в начальное меню'))
        bot.send_message(message.chat.id, "Админ-панель", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к админ-панели.")

# Обработчик для команды /create_promo
@bot.message_handler(func=lambda message: message.text == "Создать промокод" and message.chat.id in admins)
def handle_create_promo_code(message):
    bot.send_message(message.chat.id, "Введите сумму для промокода:")
    bot.register_next_step_handler(message, process_promo_amount)

def process_promo_amount(message):
    try:
        promo_amount = float(message.text)
        conn = get_connection()
        cursor = conn.cursor()
        promo_code = generate_unique_promo_code(cursor)  # Генерация уникального промокода

        cursor.execute("INSERT INTO promo_codes (code, amount, is_used) VALUES (?, ?, 0)", (promo_code, promo_amount))
        conn.commit()
        bot.send_message(message.chat.id, f"Новый промокод успешно создан: {promo_code}. Сумма: {promo_amount} рублей.")
        conn.close()
    except ValueError:
        bot.send_message(message.chat.id, "Некорректное значение суммы. Введите числовое значение.")

def generate_unique_promo_code(cursor):
    while True:
        # Генерация случайного промокода
        promo_code = secrets.token_hex(3).upper()
        cursor.execute("SELECT code FROM promo_codes WHERE code = ?", (promo_code,))
        existing = cursor.fetchone()
        if not existing:
            return promo_code

# Обработчик для команды /clear_balance
@bot.message_handler(func=lambda message: message.text == "Очистить баланс" and message.chat.id in admins)
def handle_clear_balance(message):
    bot.send_message(message.chat.id, "Введите ID пользователя, чей баланс нужно очистить:")
    # Регистрируем следующий шаг для ввода ID пользователя
    bot.register_next_step_handler(message, process_user_id_for_clearing)

# Обработчик для обработки введенного ID пользователя для очистки баланса
def process_user_id_for_clearing(message):
    try:
        conn = get_connection()  # Получаем новое подключение к базе данных
        cursor = conn.cursor()
        user_id = int(message.text)
        cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        bot.send_message(message.chat.id, f"Баланс пользователя с ID {user_id} успешно очищен")
    except ValueError:
        bot.send_message(message.chat.id, "Некорректный ID пользователя. Введите числовое значение.")

@bot.message_handler(func=lambda message: message.text == "Получить ID пользователей" and message.chat.id in admins)
def handle_get_user_ids(message):
    conn = get_connection()  # Получаем новое подключение к базе данных
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, balance FROM users")
    users = cursor.fetchall()
    info_message = "Информация о пользователях:\n"
    for user in users:
        user_id = user[0]
        username = user[1]
        balance = user[2]
        info_message += f"Имя: {username}, ID: {user_id}, Баланс: {balance}\n"
    bot.send_message(message.chat.id, info_message)  # Отправляем сообщение с информацией администратору
    conn.close()

@bot.message_handler(func=lambda message: message.text == "Вернуться в начальное меню")
def handle_return_to_main_menu_admin_panel(message):
    if message.chat.id in admins:
        handle_start(message)
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к админ-панели.")

# Запуск прослушивания сообщений
asyncio.run(bot.polling(none_stop=True))