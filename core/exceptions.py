class KompasError(Exception):
    """Базовая ошибка обёртки КОМПАС-3D."""


class KompasNotRunningError(KompasError):
    """КОМПАС-3D не запущен или недоступен через COM."""


class KompasOperationError(KompasError):
    """Ошибка при выполнении операции моделирования."""
