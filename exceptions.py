class SendMessageError(Exception):
    """Исключение отправки сообщения."""

    pass


class APIResponseStatusCodeException(Exception):
    """Исключение сбоя запроса к API."""

    pass


class CheckResponseException(Exception):
    """Исключение неверного формата ответа API."""

    pass


class UnknownStatusException(Exception):
    """Исключение неизвестного статуса домашки."""

    pass


class MissingRequiredTokenException(Exception):
    """Исключение отсутствия необходимых переменных среды."""

    pass


class EmptyHWNameOrStatus(Exception):
    """Исключение None значения имени или статуса домашки."""

    pass
