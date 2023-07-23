import telebot
from environs import Env


env = Env()
env.read_env()
devman_token = env.str('DEVMAN_TOKEN')
tg_bot_token = env.str('TG_BOT_TOKEN')
available_chat_ids = env.list('TG_CHAT_IDS')
bot = telebot.TeleBot(tg_bot_token)

bot.set_my_commands([
    telebot.types.BotCommand("/start", "start"),
])

