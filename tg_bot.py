import requests
from environs import Env
from requests.exceptions import ReadTimeout, ConnectionError as RequestsConnectionError
import telebot
from telebot.async_telebot import AsyncTeleBot
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientResponseError

import logging
import asyncio


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
            log_entry = f'''file: {record.filename} line:
{record.lineno}, in {record.module} message:{self.format(record)}'''
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


def set_logger_level(logger, level):
    if level == "INFO":
        logger.setLevel(logging.INFO)
    elif level == "WARNING":
        logger.setLevel(logging.WARNING)
    elif level == "ERROR":
        logger.setLevel(logging.ERROR)
    elif level == 'CRITICAL':
        logger.setLevel(logging.CRITICAL)
    else:
        logger.setLevel(logging.DEBUG)


async def async_check_status(devman_token, recipients, params=''):
    async with ClientSession() as session:
        long_polling_url = 'https://dvmn.org/api/long_polling/'
        headers = {
            'Authorization': devman_token,
        }
        logger.info('start check status')
        try:
            async with session.get(
                    url=long_polling_url, headers=headers, params=params, timeout=120, raise_for_status=True
            ) as response:
                review = await response.json()
                logger.debug(f'old params : {params}')
                if review['status'] == 'found':
                    logger.debug("review['status'] == 'found'")
                    notifications = create_notifications(review)
                    params = {'timestamp': review['last_attempt_timestamp']}
                    logger.debug(f'updated params: {params}')
                    return params, notifications, recipients
                else:
                    logger.debug("review['status'] == 'timeout'")
                    params = {'timestamp': review['timestamp_to_request']}
                    logger.debug(f'updated params: {params}')
                    return params, None, recipients
        except ClientResponseError:
            logger.debug('ClientResponseError')
            return None, None, None
        except ReadTimeout:
            logger.debug('ReadTimeout')
            return None, None, None
        except RequestsConnectionError:
            logger.debug('RequestsConnectionError')
            return None, None, None
        except requests.HTTPError:
            logger.debug('requests.HTTPError')
            return None, None, None


async def async_newsletter(async_bot, chat_id, letters):
    for letter in letters:
        await async_bot.send_message(chat_id, letter)


async def main():
    # env
    env = Env()
    env.read_env()
    tg_bot_token = env.str('TG_BOT_TOKEN')
    admins_ids = env.list('TG_ADMIN_IDS', [])
    level = env.str('LOGGING_LEVEL', 'debug').upper()
    recipients = env.json('RECIPIENTS')
    # bot
    tg_bot = telebot.TeleBot(tg_bot_token)
    async_tg_bot = AsyncTeleBot(tg_bot_token)
    # Use one token in TeleBot and AsyncTeleBot is bad ?
    # logger
    set_logger_level(logger, level)
    handler = TelegeramLogsHandler(tg_bot, admins_ids)
    # How do async handler ?
    logger.addHandler(handler)
    # empty token params
    token_params = {token: '' for token in recipients.keys()}
    # tasks
    while True:
        check_status_tasks = []
        for devman_token, chat_ids in recipients.items():
            check_status_tasks.append(
                asyncio.create_task(async_check_status(devman_token, chat_ids, params=token_params[devman_token]))
            )

        check_status_result = await asyncio.gather(*check_status_tasks)

        newsletter_tasks = []
        for params, notification, ids in check_status_result:
            if ids and notification:
                for chat_id in ids:
                    newsletter_tasks.append(
                        asyncio.create_task(async_newsletter(async_tg_bot, chat_id, notification))
                    )
            for task in newsletter_tasks:
                await task

if __name__ == '__main__':
    asyncio.run(main())
