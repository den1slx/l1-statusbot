import requests
from environs import Env
from requests.exceptions import ReadTimeout, ConnectionError as RequestsConnectionError
import telebot
from telebot.apihelper import ApiTelegramException

from time import sleep
import logging


logger = logging.getLogger('statuslog')


class TelegeramLogsHandler(logging.Handler):
    def __init__(self, tg_bot, admins_ids):
        super().__init__()
        self.admins = admins_ids
        self.tg_bot = tg_bot

    def emit(self, record):
        if record.levelname == 'INFO' or record.levelname == 'DEBUG':
            log_entry = f'{record.process} {record.levelname} {self.format(record)}'
        else:
            log_entry = f'''file: {record.filename} line: {record.lineno}, in {record.module} message:{self.format(record)}'''
        for admin_id in self.admins:
            self.tg_bot.send_message(chat_id=admin_id, text=log_entry)


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


def check_status(devman_token):
    long_polling_url = 'https://dvmn.org/api/long_polling/'
    headers = {
        'Authorization': devman_token,
    }
    params = ''
    logger.info('start check status')
    try:
        lp_response = requests.get(long_polling_url, headers=headers, params=params, timeout=120)
        lp_response.raise_for_status()
    except ReadTimeout:
        logger.debug('ReadTimeout')
    except RequestsConnectionError:
        logger.debug('RequestsConnectionError')
        sleep(5)
    except requests.HTTPError:
        logger.debug('requests.HTTPError')
        sleep(60)
    review = lp_response.json()
    if review['status'] == 'found':
        logger.debug("review['status'] == 'found'")
        notifications = create_notifications(review)
        return notifications
    else:
        logger.debug("review['status'] == 'timeout'")
        params = {'timestamp': review['timestamp_to_request']}


def main():
    # env
    env = Env()
    env.read_env()
    tg_bot_token = env.str('TG_BOT_TOKEN')
    admins_ids = env.list('TG_ADMIN_IDS')
    recipients = env.json('RECIPIENTS')
    # bot
    tg_bot = telebot.TeleBot(tg_bot_token)
    # logger
    logger.setLevel(logging.DEBUG)
    handler = TelegeramLogsHandler(tg_bot, admins_ids)
    logger.addHandler(handler)

    while True:
        for devman_token, chat_ids in recipients.items():
            notifications = check_status(devman_token)
            for chat_id in chat_ids:
                try:
                    tg_bot.send_message(chat_id, f'Рассылка уведомлений')
                    for notification in notifications:
                        tg_bot.send_message(chat_id, notification)

                except ApiTelegramException:
                    logger.error('ApiTelegramException (Wrong timeout)')


if __name__ == '__main__':
    main()

