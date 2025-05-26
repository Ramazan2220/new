# Интеграция SessionManager в InstaBot2.0

from instagram.session_manager import SessionManager, SessionStatus
import logging
import threading
import time

class SessionManagerIntegration:
    def __init__(self, bot, config):
        """
        Интеграция менеджера сессий в существующую систему InstaBot2.0

        Args:
            bot: Экземпляр основного класса бота
            config: Конфигурация
        """
        self.bot = bot
        self.config = config
        self.logger = logging.getLogger('session_manager_integration')

        # Инициализация менеджера сессий
        self.session_manager = SessionManager(config, bot.db_connection if hasattr(bot, 'db_connection') else None)

        # Флаг для контроля фонового потока
        self.running = False
        self.check_thread = None

        # Интервал проверки здоровья сессий (в минутах)
        self.check_interval = config.get('session_check_interval_minutes', 30) if isinstance(config, dict) else 30

    def start(self):
        """Запуск интеграции и фонового потока проверки сессий"""
        self.logger.info("Starting session manager integration")
        self.running = True

        # Запуск фонового потока для проверки здоровья сессий
        self.check_thread = threading.Thread(target=self._health_check_loop)
        self.check_thread.daemon = True
        self.check_thread.start()

        self.logger.info("Session manager integration started")

    def stop(self):
        """Остановка фонового потока"""
        self.logger.info("Stopping session manager integration")
        self.running = False

        if self.check_thread and self.check_thread.is_alive():
            self.check_thread.join(timeout=5)

        self.logger.info("Session manager integration stopped")

    def _health_check_loop(self):
        """Фоновый поток для периодической проверки здоровья сессий"""
        while self.running:
            try:
                self.logger.debug("Running periodic health checks")

                # Получаем словарь сессий из бота
                sessions_dict = self._get_sessions_from_bot()

                # Проверяем здоровье сессий
                health_results = self.session_manager.schedule_health_checks(sessions_dict)

                # Обрабатываем результаты проверки
                self._process_health_results(health_results)

                # Пауза перед следующей проверкой
                time.sleep(self.check_interval * 60)
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                time.sleep(60)  # Короткая пауза перед повторной попыткой

    def _get_sessions_from_bot(self):
        """
        Получение словаря сессий из бота

        Returns:
            dict: Словарь {username: session}
        """
        from database.db_manager import get_all_instagram_accounts
        from instagram.client import get_instagram_client

        sessions_dict = {}

        try:
            # Получаем все аккаунты из базы данных
            accounts = get_all_instagram_accounts()

            for account in accounts:
                try:
                    # Получаем клиент для аккаунта
                    client = get_instagram_client(account.id)
                    if client:
                        sessions_dict[account.username] = client
                except Exception as e:
                    self.logger.error(f"Ошибка при получении клиента для аккаунта {account.username}: {e}")
        except Exception as e:
            self.logger.error(f"Ошибка при получении аккаунтов: {e}")

        return sessions_dict

    def _process_health_results(self, health_results):
        """
        Обработка результатов проверки здоровья сессий

        Args:
            health_results: Результаты проверок {username: SessionStatus}
        """
        for username, status in health_results.items():
            if status != SessionStatus.HEALTHY:
                self.logger.warning(f"Unhealthy session detected for {username}: {status.value}")

                # Получаем аккаунт из бота
                account = self._get_account_by_username(username)

                if account:
                    # Если сессия временно заблокирована, ставим на паузу
                    if status == SessionStatus.TEMP_BLOCKED:
                        self.logger.info(f"Pausing account {username} due to temporary block")
                        # Здесь код для паузы аккаунта
                        # Например: account.pause(3600)  # Пауза на 1 час

                    # Если сессия истекла или требует challenge, пытаемся восстановить
                    elif status in [SessionStatus.EXPIRED, SessionStatus.CHALLENGED]:
                        self.logger.info(f"Attempting to recover session for {username}")
                        # Получаем пароль и прокси
                        password = account.password if hasattr(account, 'password') else None
                        proxy = account.proxy if hasattr(account, 'proxy') else None

                        if password:
                            # Пытаемся восстановить сессию
                            success = self.session_manager.recover_session(
                                account.session,
                                username,
                                password,
                                proxy
                            )

                            if success:
                                self.logger.info(f"Successfully recovered session for {username}")
                            else:
                                self.logger.warning(f"Failed to recover session for {username}")
                        else:
                            self.logger.error(f"Cannot recover session for {username}: password not available")

    def _get_account_by_username(self, username):
        """
        Получение объекта аккаунта по имени пользователя

        Args:
            username: Имя пользователя

        Returns:
            object: Объект аккаунта или None
        """
        from database.db_manager import get_instagram_account_by_username

        # Получаем аккаунт из базы данных
        account = get_instagram_account_by_username(username)

        return account

    def check_session(self, username):
        """
        Проверка здоровья конкретной сессии

        Args:
            username: Имя пользователя

        Returns:
            SessionStatus: Статус сессии
        """
        account = self._get_account_by_username(username)

        if account and hasattr(account, 'session'):
            return self.session_manager.check_session_health(account.session, username)

        return None

    def get_stats(self):
        """
        Получение статистики по сессиям

        Returns:
            dict: Статистика по сессиям
        """
        return self.session_manager.get_session_stats()

    def check_all_sessions_health(self):
        """Проверяет здоровье всех сессий Instagram"""
        try:
            from database.db_manager import get_all_instagram_accounts
            accounts = get_all_instagram_accounts()

            for account in accounts:
                try:
                    # Проверяем сессию для каждого аккаунта
                    self.check_session_health(account.id)
                except Exception as e:
                    self.logger.error(f"Ошибка при проверке здоровья сессии для аккаунта {account.username}: {e}")

            self.logger.info(f"Проверка здоровья сессий завершена для {len(accounts)} аккаунтов")
        except Exception as e:
            self.logger.error(f"Ошибка при проверке здоровья сессий: {e}")

    def check_session_health(self, account_id):
        """Проверяет здоровье сессии для конкретного аккаунта"""
        from database.db_manager import get_instagram_account
        from instagram.client import get_instagram_client

        try:
            account = get_instagram_account(account_id)
            if not account:
                self.logger.warning(f"Аккаунт с ID {account_id} не найден")
                return False

            client = get_instagram_client(account_id)
            if not client:
                self.logger.warning(f"Не удалось получить клиент для аккаунта {account.username}")
                return False

            # Проверяем здоровье сессии через менеджер сессий
            # Используем клиент как объект сессии
            status = self.session_manager.check_session_health(client, account.username)

            if status == SessionStatus.HEALTHY:
                self.logger.info(f"Сессия для аккаунта {account.username} активна")
                return True
            else:
                self.logger.warning(f"Сессия для аккаунта {account.username} имеет статус: {status.value}")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка при проверке сессии для аккаунта {account_id}: {e}")
            return False