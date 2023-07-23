import requests
from requests.exceptions import ReadTimeout, ConnectionError as RequestsConnectionError

import json
import logging
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
    url = 'https://dvmn.org/api/user_reviews/'
    headers = {
        'Authorization': devman_token,
    }
    params = ''
    while True:
        logging.info('start')
        try:
            logging.info('begin try')
            lp_response = requests.get(long_polling_url, headers=headers, params=params, timeout=120)
            logging.info(lp_response)
        except ReadTimeout:
            logging.warning('ReadTimeout')
            continue
        except RequestsConnectionError:
            logging.warning('requests.exceptions.ConnectionError')
            sleep(5)
            continue
        logging.info('end try - except')
        text = json.loads(lp_response.text)
        logging.info(f'json.loads: {text}')
        if text['status'] == 'found':
            for notification in create_notifications(text):
                bot.send_message(chat_id, notification)
        elif text['status'] == 'timeout':
            if not text['request_query'] and params:
                logging.warning(f'not request_query: {text}')
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
    logging.basicConfig(level=logging.INFO, filename="bot_log.log", filemode="w")

    start_bot()


if __name__ == '__main__':
    main()


