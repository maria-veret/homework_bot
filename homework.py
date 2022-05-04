import logging
import os
import time

import requests
import telegram
from http import HTTPStatus
from dotenv import load_dotenv

import exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
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
    except exceptions.SendMessageError:
        logger.error('Сообщение не отправлено')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except exceptions.APIResponseStatusCodeException:
        logger.error('Сбой при запросе к эндпоинту')
    if response.status_code != HTTPStatus.OK:
        api_msg = (
            f'Эндпоинт {ENDPOINT} недоступен.'
            f' Код ответа API: {response.status_code}')
        logger.error(api_msg)
        raise exceptions.APIResponseStatusCodeException(api_msg)
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    try:
        homeworks = response['homeworks']
    except KeyError as error:
        msg = f'Ошибка доступа по ключу homeworks: {error}'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    if homeworks is None:
        msg = 'В ответе API нет домашек'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    if len(homeworks) == 0:
        msg = 'Сейчас домашек нет'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    if not isinstance(homeworks, list):
        msg = 'Неправильный тип данных от API'
        logger.error(msg)
        raise TypeError(msg)
    return homeworks


def parse_status(homework):
    """Извлекает статус конкретной домашней работы."""
    try:
        homework_name = homework.get('homework_name')
    except KeyError as error:
        msg = f'Ошибка доступа по ключу homework_name: {error}'
        logger.error(msg)
    try:
        homework_status = homework.get('status')
    except KeyError as error:
        msg = f'Ошибка доступа по ключу status: {error}'
        logger.error(msg)
    verdict = HOMEWORK_STATUSES[homework_status]
    if verdict is None:
        msg = 'Неизвестный статус'
        logger.error(msg)
        raise exceptions.UnknownStatusException(msg)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    err_msg = (
        'Программа принудительно остановлена. '
        'Отсутствует обязательная переменная окружения:')
    if PRACTICUM_TOKEN is None:
        logger.critical(
            f'{err_msg} PRACTICUM_TOKEN')
        return False
    if TELEGRAM_TOKEN is None:
        logger.critical(
            f'{err_msg} TELEGRAM_TOKEN')
        return False
    if TELEGRAM_CHAT_ID is None:
        logger.critical(
            f'{err_msg} TELEGRAM_CHAT_ID')
        return False
    return True


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
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
