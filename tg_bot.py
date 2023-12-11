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


def check_status(bot, chat_id, devman_token):
    long_polling_url = 'https://dvmn.org/api/long_polling/'
    headers = {
        'Authorization': devman_token,
    }
    params = ''
    while True:
        logger.info('start check status')
        try:
            lp_response = requests.get(long_polling_url, headers=headers, params=params, timeout=120)
            lp_response.raise_for_status()
        except ReadTimeout:
            logger.debug('ReadTimeout')
            continue
        except RequestsConnectionError:
            logger.debug('RequestsConnectionError')
            sleep(5)
            continue
        except requests.HTTPError:
            logger.debug('requests.HTTPError')
            sleep(60)
            continue
        review = lp_response.json()
        if review['status'] == 'found':
            logger.debug("review['status'] == 'found'")
            for notification in create_notifications(review):
                bot.send_message(chat_id, notification)
            sleep(60)
        elif review['status'] == 'timeout':
            logger.debug("review['status'] == 'timeout'")
            params = {'timestamp': review['timestamp_to_request']}
        else:
            params = ''


def spam(bot, chat_id, spam='spam', timeout=30):
    while True:
        bot.send_message(chat_id, spam)
        sleep(timeout)


def main():
    # env
    env = Env()
    env.read_env()
    devman_token = env.str('DEVMAN_TOKEN')
    tg_bot_token = env.str('TG_BOT_TOKEN')
    available_chat_ids = env.list('TG_CHAT_IDS')
    admins_ids = env.list('TG_ADMIN_IDS')
    # bot
    tg_bot = telebot.TeleBot(tg_bot_token)
    # logger
    logger.setLevel(logging.DEBUG)
    handler = TelegeramLogsHandler(tg_bot, admins_ids)
    logger.addHandler(handler)

    while True:
        try:
            for chat_id in available_chat_ids:
                tg_bot.send_message(chat_id, f'Рассылка уведомлений')
                # spam(tg_bot, chat_id, timeout=0) # debug
                check_status(tg_bot, chat_id, devman_token)
        except ApiTelegramException:
            logger.error('ApiTelegramException (Wrong timeout)')
        # except:
        #     logger.error('unexpected error')
        #     break


if __name__ == '__main__':
    main()

