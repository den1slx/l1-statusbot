import requests
from requests.exceptions import ReadTimeout, ConnectionError as RequestsConnectionError

import json
from time import sleep

from tg_bot_env import bot, devman_token, available_chat_ids, telebot


def create_notifications(response_text):
    notifications = []
    for lesson in response_text['new_attempts']:
        title = lesson['lesson_title']
        url = lesson['lesson_url']

        if lesson['is_negative']:
            status = 'К сожалению в работе есть ошибки'
        else:
            status = 'Преподавателю всё понравилось можно приступать к следующему уроку'

        notification = f'''У вас проверили работу <<{title}>> \n{status} \nСсылка: {url}'''
        notifications.append(notification)
    return notifications


def check_status(chat_id, devman_token):
    long_polling_url = 'https://dvmn.org/api/long_polling/'
    headers = {
        'Authorization': devman_token,
    }
    params = ''
    while True:
        try:
            lp_response = requests.get(long_polling_url, headers=headers, params=params, timeout=120)
        except ReadTimeout:
            continue
        except RequestsConnectionError:
            sleep(5)
            continue
        text = json.loads(lp_response.text)
        if text['status'] == 'found':
            for notification in create_notifications(text):
                bot.send_message(chat_id, notification)
        elif text['status'] == 'timeout':
            params = {'timestamp': f"{text['timestamp_to_request']}"}
        else:
            params = ''


@bot.message_handler(commands=['start'])
def command_menu(message: telebot.types.Message):
    if str(message.chat.id) in available_chat_ids:
        bot.send_message(message.chat.id, f'Здравствуйте {message.from_user.username}. ')
        check_status(message.chat.id, devman_token)
    bot.send_message(message.chat.id, 'Nope')


def start_bot():
    bot.infinity_polling()


def main():
    start_bot()


if __name__ == '__main__':
    main()


