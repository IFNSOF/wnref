import threading
from flask import Flask
import telebot
from telebot import types
import json
import datetime
import os

# ==== НАСТРОЙКИ ====
TOKEN = "8204880484:AAHZKpUgPBl_hJj_ZQ8HaEczn1dg6njuxZo"
ADMIN_ID = 7816374758  # 🔹 замени на свой Telegram ID
CHANNEL_USERNAME = "@wnref"  # 🔹 например @SpinFortunaNews
SUPPORT_LINK = "@winiksona"

bot = telebot.TeleBot(TOKEN)
DATA_FILE = "data.json"
WITHDRAW_FILE = "withdraws.json"

# ==== ИНИЦИАЛИЗАЦИЯ ====
for file in [DATA_FILE, WITHDRAW_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

def load_json(filename):
    with open(filename, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

def is_subscribed(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except:
        return False

# ==== /START ====
@bot.message_handler(commands=["start"])
def start(message):
    user_id = str(message.chat.id)
    args = message.text.split()
    data = load_json(DATA_FILE)

    if user_id not in data:
        data[user_id] = {
            "balance": 0,
            "withdrawn": 0,
            "referrals": 0,
            "joined": str(datetime.date.today()),
            "invited_by": args[1] if len(args) > 1 else None,
            "ref_counted": False
        }
        save_json(DATA_FILE, data)

    if not is_subscribed(message.chat.id):
        send_subscribe_message(message.chat.id)
        return

    if data[user_id].get("invited_by") and not data[user_id].get("ref_counted"):
        ref_id = data[user_id]["invited_by"]
        if ref_id in data and ref_id != user_id:
            data[ref_id]["balance"] += 1000
            data[ref_id]["referrals"] += 1
            data[user_id]["ref_counted"] = True
            save_json(DATA_FILE, data)
            bot.send_message(int(ref_id), "🎉 Новый реферал подписался на канал! +1000 Gram")

    main_menu(message)

def send_subscribe_message(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"),
        types.InlineKeyboardButton("✅ Проверить подписку", callback_data="check_sub")
    )
    bot.send_message(chat_id, "Подпишитесь на канал, чтобы продолжить 👇", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_subscription(call):
    user_id = str(call.message.chat.id)
    data = load_json(DATA_FILE)
    if is_subscribed(call.message.chat.id):
        bot.answer_callback_query(call.id, "✅ Подписка подтверждена!")
        if data[user_id].get("invited_by") and not data[user_id].get("ref_counted"):
            ref_id = data[user_id]["invited_by"]
            if ref_id in data and ref_id != user_id:
                data[ref_id]["balance"] += 1000
                data[ref_id]["referrals"] += 1
                data[user_id]["ref_counted"] = True
                save_json(DATA_FILE, data)
                bot.send_message(int(ref_id), "🎉 Новый реферал подписался на канал! +1000 Gram")
        main_menu(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Вы ещё не подписаны!")

# ==== ГЛАВНОЕ МЕНЮ ====
def main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💰 Заработать", "👤 Профиль")
    markup.row("📊 Статистика", "📢 Канал")
    if message.chat.id == ADMIN_ID:
        markup.row("🛠 Админ панель")
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=markup)

# ==== ЗАРАБОТАТЬ ====
@bot.message_handler(func=lambda m: m.text == "💰 Заработать")
def earn(message):
    ref_link = f"https://t.me/{bot.get_me().username}?start={message.chat.id}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 Открыть ссылку", url=ref_link))
    bot.send_message(message.chat.id, f"Ваша реферальная ссылка:\n{ref_link}\n\n💸 За каждого подписанного — 1000 Gram", reply_markup=markup)

# ==== ПРОФИЛЬ ====
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):
    user_id = str(message.chat.id)
    data = load_json(DATA_FILE)[user_id]
    text = f"""👤 Ваш профиль
ID: {user_id}
Ник: {message.from_user.first_name}
Баланс: {data['balance']} Gram
Выведено: {data['withdrawn']} Gram
Рефералов: {data['referrals']}"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💸 Вывести", "⬅ Назад")
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⬅ Назад")
def back_to_menu(message):
    main_menu(message)

# ==== ВЫВОД ====
@bot.message_handler(func=lambda m: m.text == "💸 Вывести")
def withdraw_request(message):
    msg = bot.send_message(message.chat.id, "Введите сумму для вывода (мин. 500 Gram):")
    bot.register_next_step_handler(msg, process_withdraw)

def process_withdraw(message):
    user_id = str(message.chat.id)
    try:
        amount = int(message.text)
        data = load_json(DATA_FILE)
        if amount < 500:
            bot.send_message(message.chat.id, "❌ Минимальная сумма — 500 Gram")
            return
        if amount > data[user_id]["balance"]:
            bot.send_message(message.chat.id, "❌ Недостаточно средств")
            return

        data[user_id]["balance"] -= amount
        save_json(DATA_FILE, data)

        withdraws = load_json(WITHDRAW_FILE)
        withdraws[user_id] = {"amount": amount, "status": "pending"}
        save_json(WITHDRAW_FILE, withdraws)

        bot.send_message(message.chat.id, "✅ Заявка на вывод отправлена админу.")
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{user_id}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_{user_id}")
        )
        bot.send_message(
            ADMIN_ID,
            f"💸 Заявка на вывод\nПользователь: @{message.from_user.username}\nID: {user_id}\nСумма: {amount}",
            reply_markup=markup
        )
    except:
        bot.send_message(message.chat.id, "Введите корректное число.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("decline_"))
def handle_withdraw_action(call):
    user_id = call.data.split("_")[1]
    withdraws = load_json(WITHDRAW_FILE)
    data = load_json(DATA_FILE)

    if call.data.startswith("decline_"):
        if user_id in withdraws and withdraws[user_id]["status"] == "pending":
            amount = withdraws[user_id]["amount"]
            data[user_id]["balance"] += amount
            withdraws[user_id]["status"] = "declined"
            save_json(DATA_FILE, data)
            save_json(WITHDRAW_FILE, withdraws)
            bot.edit_message_text("❌ Вывод отклонён. Деньги возвращены пользователю.", call.message.chat.id, call.message.id)
            bot.send_message(int(user_id), f"❌ Ваша заявка на {amount} Gram была отклонена. Средства возвращены.")
    elif call.data.startswith("approve_"):
        if user_id in withdraws and withdraws[user_id]["status"] == "pending":
            withdraws[user_id]["status"] = "awaiting_receipt"
            save_json(WITHDRAW_FILE, withdraws)
            msg = bot.send_message(ADMIN_ID, f"Отправьте ссылку на чек для пользователя {user_id}:")
            bot.register_next_step_handler(msg, send_receipt_to_user, user_id)

def send_receipt_to_user(message, user_id):
    receipt_link = message.text
    withdraws = load_json(WITHDRAW_FILE)
    data = load_json(DATA_FILE)
    if user_id in withdraws:
        amount = withdraws[user_id]["amount"]
        withdraws[user_id]["status"] = "approved"
        data[user_id]["withdrawn"] += amount
        save_json(DATA_FILE, data)
        save_json(WITHDRAW_FILE, withdraws)
        bot.send_message(int(user_id), f"✅ Ваш вывод {amount} Gram подтверждён!\nСсылка на чек: {receipt_link}")
        bot.send_message(ADMIN_ID, "✅ Чек успешно отправлен пользователю.")

# ==== СТАТИСТИКА ====
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(message):
    data = load_json(DATA_FILE)
    users = len(data)
    start_date = min([d["joined"] for d in data.values()]) if users else "Сегодня"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔥 Хочу такого же бота", url="https://t.me/твоя_ссылка"))
    text = f"""📊 Статистика
Бот запущен: {start_date}
Всего пользователей: {users}
Техподдержка: {SUPPORT_LINK}"""
    bot.send_message(message.chat.id, text, reply_markup=markup)

# ==== КАНАЛ ====
@bot.message_handler(func=lambda m: m.text == "📢 Канал")
def channel(message):
    bot.send_message(message.chat.id, f"Подписывайтесь на наш канал 👉 {CHANNEL_USERNAME}")

# ==== АДМИН ПАНЕЛЬ ====
@bot.message_handler(func=lambda m: m.text == "🛠 Админ панель" and m.chat.id == ADMIN_ID)
def admin_panel(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📬 Заявки на вывод", "📢 Рассылка")
    markup.row("⬅ Назад")
    bot.send_message(message.chat.id, "Админ панель:", reply_markup=markup)

print("🤖 Bot started...")
bot.infinity_polling(skip_pending=True)

