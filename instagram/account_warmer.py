import logging
import random
import time
from datetime import datetime, timedelta
import json
import os

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError

from config import ACCOUNTS_DIR
from database.models import InstagramAccount, TaskStatus
from database.db_manager import get_session, get_instagram_account

logger = logging.getLogger(__name__)

class AccountWarmer:
    def __init__(self, account_id=None, client=None):
        self.account_id = account_id
        self.client = client
        self.account = None

        if account_id and not client:
            self.account = get_instagram_account(account_id)
            if not self.account:
                logger.error(f"Аккаунт с ID {account_id} не найден")
                raise ValueError(f"Аккаунт с ID {account_id} не найден")

            self.client = self._get_client()

        # Настройки прогрева
        self.min_likes = 3  # Минимальное количество лайков за сессию
        self.max_likes = 10  # Максимальное количество лайков за сессию
        self.min_feed_scroll = 10  # Минимальное количество прокруток ленты
        self.max_feed_scroll = 30  # Максимальное количество прокруток ленты
        self.min_reels_watch = 5  # Минимальное количество просмотренных рилс
        self.max_reels_watch = 15  # Максимальное количество просмотренных рилс
        self.like_probability = 0.3  # Вероятность лайка (30%)
        self.comment_probability = 0.05  # Вероятность комментария (5%)
        self.follow_probability = 0.02  # Вероятность подписки (2%)

        # Комментарии для случайного выбора
        self.comments = [
            "👍", "🔥", "Nice!", "Cool!", "Amazing!", "Great content!",
            "Love it!", "Awesome!", "Wow!", "Fantastic!", "Beautiful!",
            "Impressive!", "Brilliant!", "Superb!", "Excellent!"
        ]

        # Хештеги для поиска контента
        self.hashtags = [
            "photography", "nature", "travel", "food", "fitness",
            "fashion", "art", "beauty", "music", "style", "design"
        ]

        # Журнал активности
        self.activity_log = {
            "session_start": datetime.now().isoformat(),
            "likes": 0,
            "comments": 0,
            "follows": 0,
            "feed_scrolls": 0,
            "reels_watched": 0,
            "hashtags_explored": 0,
            "errors": []
        }

    def _get_client(self):
        #Получает клиент Instagram для указанного аккаунта
        client = Client()

        # Проверяем наличие сессии
        session_file = os.path.join(ACCOUNTS_DIR, str(self.account_id), 'session.json')
        if os.path.exists(session_file):
            try:
                client.load_settings(session_file)
                logger.info(f"Загружены настройки для аккаунта {self.account.username}")
            except Exception as e:
                logger.error(f"Ошибка при загрузке настроек: {e}")

        # Проверяем, нужно ли выполнить вход
        try:
            # Исправлено: убран параметр amount
            client.get_timeline_feed()
        except (LoginRequired, ClientError) as e:
            logger.info(f"Требуется вход для аккаунта {self.account.username}: {e}")
            try:
                client.login(self.account.username, self.account.password)
                logger.info(f"Успешный вход в аккаунт {self.account.username}")

                # Сохраняем сессию
                os.makedirs(os.path.join(ACCOUNTS_DIR, str(self.account_id)), exist_ok=True)
                client.dump_settings(session_file)
            except Exception as e:
                logger.error(f"Ошибка при входе в аккаунт {self.account.username}: {e}")
                raise

        return client

    def _random_delay(self, min_seconds=1, max_seconds=5):
        #Случайная задержка между действиями
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        return delay

    def _save_activity_log(self):
        #Сохраняет журнал активности
        self.activity_log["session_end"] = datetime.now().isoformat()

        # Создаем директорию для логов, если она не существует
        log_dir = os.path.join(ACCOUNTS_DIR, str(self.account_id), 'warming_logs')
        os.makedirs(log_dir, exist_ok=True)

        # Имя файла с датой и временем
        log_file = os.path.join(log_dir, f"warming_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

        # Сохраняем лог в файл
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(self.activity_log, f, ensure_ascii=False, indent=4)

        logger.info(f"Сохранен журнал активности прогрева для аккаунта {self.account.username}")

    def browse_feed(self):
        #Просмотр ленты с возможными лайками и комментариями
        logger.info(f"Начинаем просмотр ленты для аккаунта {self.account.username}")

        try:
            # Определяем количество прокруток ленты
            scroll_count = random.randint(self.min_feed_scroll, self.max_feed_scroll)

            # Получаем ленту (исправлено: убран параметр amount)
            feed_items = self.client.get_timeline_feed()
            # Ограничиваем количество обрабатываемых элементов
            feed_items = feed_items[:scroll_count] if len(feed_items) > scroll_count else feed_items

            logger.info(f"Получено {len(feed_items)} постов из ленты")
            self.activity_log["feed_scrolls"] = len(feed_items)

            # Просматриваем посты
            for item in feed_items:
                # Случайная задержка перед действием
                self._random_delay(2, 8)

                # Проверяем, есть ли у поста медиа
                if not hasattr(item, 'media_id'):
                    continue

                media_id = item.id

                # С определенной вероятностью ставим лайк
                if random.random() < self.like_probability:
                    try:
                        self.client.media_like(media_id)
                        logger.info(f"Поставлен лайк на пост {media_id}")
                        self.activity_log["likes"] += 1
                        self._random_delay(1, 3)
                    except Exception as e:
                        logger.error(f"Ошибка при попытке поставить лайк: {e}")
                        self.activity_log["errors"].append(f"Like error: {str(e)}")

                # С меньшей вероятностью оставляем комментарий
                if random.random() < self.comment_probability:
                    try:
                        comment_text = random.choice(self.comments)
                        self.client.media_comment(media_id, comment_text)
                        logger.info(f"Оставлен комментарий на пост {media_id}: {comment_text}")
                        self.activity_log["comments"] += 1
                        self._random_delay(3, 7)
                    except Exception as e:
                        logger.error(f"Ошибка при попытке оставить комментарий: {e}")
                        self.activity_log["errors"].append(f"Comment error: {str(e)}")

                # С очень малой вероятностью подписываемся на пользователя
                if random.random() < self.follow_probability:
                    try:
                        user_id = item.user.pk
                        self.client.user_follow(user_id)
                        logger.info(f"Подписка на пользователя {item.user.username}")
                        self.activity_log["follows"] += 1
                        self._random_delay(4, 10)
                    except Exception as e:
                        logger.error(f"Ошибка при попытке подписаться: {e}")
                        self.activity_log["errors"].append(f"Follow error: {str(e)}")

            return True
        except Exception as e:
            logger.error(f"Ошибка при просмотре ленты: {e}")
            self.activity_log["errors"].append(f"Feed browsing error: {str(e)}")
            return False

    def watch_reels(self):
        #Просмотр рилс с возможными лайками
        logger.info(f"Начинаем просмотр рилс для аккаунта {self.account.username}")

        try:
            # Определяем количество рилс для просмотра
            reels_count = random.randint(self.min_reels_watch, self.max_reels_watch)

            # Получаем рилс
            reels = self.client.reels_feed(amount=reels_count)

            logger.info(f"Получено {len(reels)} рилс")
            self.activity_log["reels_watched"] = len(reels)

            # Просматриваем рилс
            for reel in reels:
                # Имитируем просмотр рилс (задержка 5-15 секунд)
                watch_time = self._random_delay(5, 15)

                # С определенной вероятностью ставим лайк
                if random.random() < self.like_probability:
                    try:
                        self.client.media_like(reel.id)
                        logger.info(f"Поставлен лайк на рилс {reel.id}")
                        self.activity_log["likes"] += 1
                        self._random_delay(1, 3)
                    except Exception as e:
                        logger.error(f"Ошибка при попытке поставить лайк на рилс: {e}")
                        self.activity_log["errors"].append(f"Reel like error: {str(e)}")

            return True
        except Exception as e:
            logger.error(f"Ошибка при просмотре рилс: {e}")
            self.activity_log["errors"].append(f"Reels watching error: {str(e)}")
            return False

    def explore_hashtags(self):
        #Просмотр постов по хештегам
        logger.info(f"Начинаем просмотр хештегов для аккаунта {self.account.username}")

        try:
            # Выбираем случайный хештег
            hashtag = random.choice(self.hashtags)

            # Получаем посты по хештегу
            medias = self.client.hashtag_medias_recent(hashtag, amount=10)

            logger.info(f"Получено {len(medias)} постов по хештегу #{hashtag}")
            self.activity_log["hashtags_explored"] += 1

            # Просматриваем посты
            for media in medias:
                # Случайная задержка перед действием
                self._random_delay(2, 6)

                # С определенной вероятностью ставим лайк
                if random.random() < self.like_probability:
                    try:
                        self.client.media_like(media.id)
                        logger.info(f"Поставлен лайк на пост {media.id} по хештегу #{hashtag}")
                        self.activity_log["likes"] += 1
                        self._random_delay(1, 3)
                    except Exception as e:
                        logger.error(f"Ошибка при попытке поставить лайк на пост по хештегу: {e}")
                        self.activity_log["errors"].append(f"Hashtag like error: {str(e)}")

            return True
        except Exception as e:
            logger.error(f"Ошибка при просмотре хештегов: {e}")
            self.activity_log["errors"].append(f"Hashtag exploration error: {str(e)}")
            return False

    def stop_warming_by_task_id(self, task_id):
        """Останавливает прогрев по ID задачи"""
        try:
            # Обновляем статус задачи в БД
            from database.db_manager import update_warming_task_status
            update_warming_task_status(task_id, 'stopped')
            logger.info(f"Прогрев по задаче ID {task_id} остановлен")
            return True
        except Exception as e:
            logger.error(f"Ошибка при остановке прогрева по задаче ID {task_id}: {e}")
            return False

    def warm_account(self):
        #Основной метод прогрева аккаунта
        logger.info(f"Начинаем прогрев аккаунта {self.account.username}")

        try:
            # Выполняем различные действия для прогрева
            actions = [
                (self.browse_feed, 0.7),  # Просмотр ленты с вероятностью 70%
                (self.watch_reels, 0.5),  # Просмотр рилс с вероятностью 50%
                (self.explore_hashtags, 0.3)  # Просмотр хештегов с вероятностью 30%
            ]

            # Выполняем действия с учетом их вероятности
            for action, probability in actions:
                if random.random() < probability:
                    action()
                    # Делаем паузу между действиями
                    self._random_delay(5, 15)

            # Сохраняем журнал активности
            self._save_activity_log()

            logger.info(f"Прогрев аккаунта {self.account.username} завершен успешно")
            return True, "Прогрев выполнен успешно"
        except Exception as e:
            logger.error(f"Ошибка при прогреве аккаунта {self.account.username}: {e}")
            return False, f"Ошибка при прогреве аккаунта: {str(e)}"

    def start_warming(self, duration, frequency, intensity):
        """Запускает прогрев аккаунта с указанными параметрами"""
        logger.info(f"Запуск прогрева аккаунта {self.account.username} на {duration} минут")

        # Настраиваем параметры прогрева в зависимости от интенсивности
        if intensity == "low":
            self.min_likes = 1
            self.max_likes = 5
            self.min_feed_scroll = 5
            self.max_feed_scroll = 15
            self.min_reels_watch = 2
            self.max_reels_watch = 8
        elif intensity == "high":
            self.min_likes = 5
            self.max_likes = 15
            self.min_feed_scroll = 15
            self.max_feed_scroll = 40
            self.min_reels_watch = 8
            self.max_reels_watch = 20

        # Запускаем прогрев
        success, message = self.warm_account()

        return success



def warm_account(account_id):
    """Функция для прогрева аккаунта по ID"""
    try:
        warmer = AccountWarmer(account_id)
        success, message = warmer.warm_account()
        return success, message
    except Exception as e:
        logger.error(f"Ошибка при прогреве аккаунта {account_id}: {e}")
        return False, str(e)