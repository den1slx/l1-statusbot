import requests
from environs import Env
from requests.exceptions import ReadTimeout, ConnectionError as RequestsConnectionError
import telebot

from time import sleep


def create_notifications(response_dict):
    notifications = []
    for lesson in response_dict['new_attempts']:
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
            lp_response.raise_for_status()
        except ReadTimeout:
            continue
        except RequestsConnectionError:
            sleep(5)
            continue
        except requests.HTTPError:
            sleep(60)
            continue
        response_dict = lp_response.json()
        if response_dict['status'] == 'found':
            for notification in create_notifications(response_dict):
                bot.send_message(chat_id, notification)

        elif response_dict['status'] == 'timeout':
            params = {'timestamp': response_dict['timestamp_to_request']}
        else:
            params = ''


if __name__ == '__main__':
    env = Env()
    env.read_env()
    devman_token = env.str('DEVMAN_TOKEN')
    tg_bot_token = env.str('TG_BOT_TOKEN')
    available_chat_ids = env.list('TG_CHAT_IDS')
    bot = telebot.TeleBot(tg_bot_token)
    for chat_id in available_chat_ids:
        bot.send_message(chat_id, f'Рассылка уведомлений')
        check_status(chat_id, devman_token)



