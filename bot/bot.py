import telebot
import logging
from telebot import types
from fuzzywuzzy import fuzz, process
import os
from main import parse_nastolki_ur, parse_znaemigraem, search_game_by_name, insert_games_to_db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = os.getenv("API_TOKEN")

bot = telebot.TeleBot(API_TOKEN)

print("Парсинг данных с сайтов...")
nastolki_ur_data = parse_nastolki_ur()
znaemigraem_data = parse_znaemigraem()
all_games = nastolki_ur_data + znaemigraem_data
insert_games_to_db(all_games)

popular_lines = [
    "Взрывные котята",
    "Колонизаторы",
    "Уно",
    "Манчкин",
    "Монополия",
    "Свинтус"
]

user_states = {}

@bot.message_handler(commands=['start'])
def start(message):
    user_states[message.chat.id] = {'first_time': True}
    send_welcome_message(message.chat.id, first_time=True)

def send_welcome_message(chat_id, first_time=False):
    if first_time:
        bot.send_message(
            chat_id,
            "Привет! Я могу помочь тебе найти настольные игры. "
            "Выбери одну из популярных линеек игр ниже или введи название игры."
        )
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for line in popular_lines:
        keyboard.add(types.KeyboardButton(line))
    keyboard.add(types.KeyboardButton("🔍 Ввести название игры"))

    bot.send_message(chat_id, "Выбери линейку игр или нажми кнопку для ввода:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text in popular_lines)
def handle_popular_line(message):
    line_name = message.text
    bot.send_message(message.chat.id, f"Ищу игры из линейки \"{line_name}\"...")
    results = search_game_by_name(line_name)
    send_search_results(message.chat.id, results)
    send_welcome_message(message.chat.id)

@bot.message_handler(func=lambda message: message.text == "🔍 Ввести название игры")
def handle_custom_input(message):
    bot.send_message(message.chat.id, "Напиши название игры, которую ты ищешь:")

@bot.message_handler(func=lambda message: True)
def search_game(message):

    game_name = message.text

    if not game_name:
        bot.send_message(message.chat.id, 'Пожалуйста, укажи название игры.')
        return

    results = search_game_by_name(game_name)
    send_search_results(message.chat.id, results)
    send_welcome_message(message.chat.id)

def send_search_results(chat_id, results):
    if results:
        response = "📜 === *Результаты поиска* === 📜\n\n"
        for game in results:
            response += (
                f"╔════════════════════════════╗\n"
                f"🎲 *Название*: {game['title']}\n"
                f"💰 *Цена*: {game['price']} руб.\n"
                f"⏳ *Время игры*: {game['time']}\n"
                f"👥 *Игроки*: {game['players']}\n"
                f"🍼 *Возраст*: {game['age']}\n"
                f"🔗 [Ссылка на игру]({game['link']})\n"
                f"╚════════════════════════════╝\n\n"
            )

        cheapest_game = min(results, key=lambda x: x['price'] if x['price'] is not None else float('inf'))
        highest_rated_game = max(results, key=lambda x: x['rating'] if x['rating'] is not None else 0)
        most_popular_game = max(results, key=lambda x: (x['rating'] if x['rating'] is not None else 0) + x['comments_count'])

        response += "🎖️ === *Специальные игры* === 🎖️\n\n"

        response += (
            f"💸 *Самая дешёвая игра*:\n"
            f"🎲 *Название*: {cheapest_game['title']}\n"
            f"💰 *Цена*: {cheapest_game['price']} руб.\n"
            f"🔗 [Ссылка]({cheapest_game['link']})\n"
            f"🟢 *Статус*: Отличный выбор для экономии! 💵\n\n"
        )

        response += (
            f"⭐️ *Самая рейтинговая игра*:\n"
            f"🎲 *Название*: {highest_rated_game['title']}\n"
            f"🌟 *Рейтинг*: {highest_rated_game['rating']} звёзд\n"
            f"🔗 [Ссылка]({highest_rated_game['link']})\n"
            f"✨ *Статус*: Это хит среди игроков! 🏆\n\n"
        )

        response += (
            f"🔥 *Самая популярная игра*:\n"
            f"🎲 *Название*: {most_popular_game['title']}\n"
            f"🗨️ *Отзывы*: {most_popular_game['comments_count']} комментариев\n"
            f"🔗 [Ссылка]({most_popular_game['link']})\n"
            f"❤️ *Статус*: Настоящий любимчик! 🎉\n\n"
        )

        max_length = 4096
        response_parts = [response[i:i + max_length] for i in range(0, len(response), max_length)]

        for part in response_parts:
            bot.send_message(chat_id, part, parse_mode='Markdown')
    else:
        bot.send_message(chat_id, '❌ Игра не найдена на обоих сайтах.')

if __name__ == "__main__":
    bot.polling(none_stop=True)
