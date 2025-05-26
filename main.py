import logging
import threading
import time
import sys
from datetime import datetime
from telegram.ext import Updater
from instagram.monkey_patch import *

# Импортируем наши модули
from config import (
    TELEGRAM_TOKEN, LOG_LEVEL, LOG_FORMAT, LOG_FILE,
    TELEGRAM_READ_TIMEOUT, TELEGRAM_CONNECT_TIMEOUT,
    TELEGRAM_ERROR_LOG
)
from database.db_manager import init_db
from telegram_bot.bot import setup_bot
from utils.scheduler import start_scheduler
from utils.task_queue import start_task_queue  # Добавляем импорт

print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Python path: {sys.path}")

# Настраиваем логирование
logging.basicConfig(
    format=LOG_FORMAT,
    level=getattr(logging, LOG_LEVEL),
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Глобальная переменная для менеджера сессий
session_manager = None

def error_callback(update, context):
    """Логирование ошибок Telegram"""
    logger.error(f'Update "{update}" caused error "{context.error}"')

    # Записываем ошибку в отдельный файл
    with open(TELEGRAM_ERROR_LOG, 'a') as f:
        f.write(f'{datetime.now()} - Update: {update} - Error: {context.error}\n')

def main():
    global session_manager

    # Инициализируем базу данных
    logger.info("Инициализация базы данных...")
    init_db()

    # Инициализируем менеджер сессий
    logger.info("Инициализация менеджера сессий...")
    from instagram.session_manager_integration import SessionManagerIntegration
    from config import CONFIG  # Предполагается, что у вас есть объект CONFIG в config.py

    # Создаем экземпляр менеджера сессий и делаем его глобальным
    session_manager = SessionManagerIntegration(None, CONFIG)

    # Регистрируем менеджер сессий в глобальном контексте для доступа из других модулей
    import builtins
    builtins.SESSION_MANAGER = session_manager

    # Запускаем менеджер сессий
    session_manager.start()
    logger.info("Менеджер сессий успешно запущен")

    # Запускаем планировщик задач в отдельном потоке
    logger.info("Запуск планировщика задач...")
    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()

    # Запускаем обработчик очереди задач
    logger.info("Запуск обработчика очереди задач...")
    start_task_queue()  # Добавляем запуск очереди задач

    # Запускаем Telegram бота
    logger.info("Запуск Telegram бота...")
    updater = Updater(TELEGRAM_TOKEN, request_kwargs={
        'read_timeout': TELEGRAM_READ_TIMEOUT,
        'connect_timeout': TELEGRAM_CONNECT_TIMEOUT
    })

    # Добавляем обработчик ошибок
    updater.dispatcher.add_error_handler(error_callback)

    # Настраиваем бота
    setup_bot(updater)

    try:
        # Запускаем бота и ждем сигналов для завершения
        updater.start_polling()
        logger.info("Бот запущен и готов к работе!")

        # Запускаем периодическую проверку здоровья сессий
        def check_sessions_health():
            # Добавляем начальную задержку перед первой проверкой
            time.sleep(300)  # Задержка 5 минут перед первой проверкой

            while True:
                try:
                    logger.info("Выполняется периодическая проверка здоровья сессий...")
                    session_manager.check_all_sessions_health()
                except Exception as e:
                    logger.error(f"Ошибка при проверке здоровья сессий: {e}")
                time.sleep(14400)  # Проверка каждые 2 часа

        # Запускаем проверку здоровья сессий в отдельном потоке
        health_check_thread = threading.Thread(target=check_sessions_health, daemon=True)
        health_check_thread.start()

        updater.idle()
    finally:
        # Останавливаем менеджер сессий при завершении
        logger.info("Остановка менеджера сессий...")
        if session_manager:
            session_manager.stop()

if __name__ == '__main__':
    main()