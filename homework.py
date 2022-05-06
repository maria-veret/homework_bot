import logging
import os
import time

import requests
import telegram
from http import HTTPStatus
from dotenv import load_dotenv

import exceptions
import settings

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение отправлено: {message}')
    except telegram.TelegramError as error:
        msg = f'Сообщение не отправленоs: {error}'
        logger.error(msg)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    try:
        timestamp = current_timestamp or int(time.time())
        if not isinstance(timestamp, (float, int)):
            raise TypeError('Ошибка формата даты')
        params = {'from_date': timestamp}
        response = requests.get(settings.ENDPOINT, headers=HEADERS,
                                params=params)
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            msg = (
                f'Эндпоинт {settings.ENDPOINT} недоступен.'
                f' Код ответа API: {response.status_code}')
            logger.error(msg)
            raise exceptions.APIResponseStatusCodeException(msg)
    except Exception as error:
        raise logging.error(f'Ошибка при обращении к API: {error}')


def check_response(response):
    """Проверяет ответ API на корректность."""
    homeworks = response['homeworks']
    if 'homeworks' not in response:
        msg = 'Ошибка доступа по ключу homeworks'
        logger.error(msg)
        raise KeyError(msg)
    if not isinstance(homeworks, list):
        msg = 'Неправильный тип данных от API'
        logger.error(msg)
        raise TypeError(msg)
    if not homeworks:
        msg = 'Сейчас домашек нет'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    return homeworks


def parse_status(homework):
    """Извлекает статус конкретной домашней работы."""
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework:
        msg = 'Ошибка доступа по ключу homework_name'
        logger.error(msg)
        raise KeyError(msg)
    homework_status = homework.get('status')
    if 'status' not in homework:
        msg = 'Ошибка доступа по ключу status'
        logger.error(msg)
        raise KeyError(msg)
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        msg = 'Неизвестный статус'
        logger.error(msg)
        raise exceptions.UnknownStatusException(msg)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        msg = 'Не найдены переменные окружения'
        logger.error(msg)
        raise exceptions.MissingRequiredTokenException(msg)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if not homework:
                logger.debug('Обновлений нет')
            else:
                message = parse_status(homework)
                send_message(bot, message)
            current_timestamp = homework['status']

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)

        finally:
            time.sleep(settings.RETRY_TIME)


if __name__ == '__main__':
    main()
