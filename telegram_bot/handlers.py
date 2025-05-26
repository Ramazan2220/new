import logging
import os
from datetime import datetime
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext, ConversationHandler

from config import MEDIA_DIR, ADMIN_USER_IDS
from database.db_manager import (
    add_instagram_account, get_instagram_accounts, get_instagram_account,
    add_proxy, get_proxies, assign_proxy_to_account,
    create_publish_task, create_warming_task, get_warming_tasks, update_warming_task_status
)
from telegram.keyboards import (
    get_main_menu_keyboard, get_accounts_menu_keyboard,
    get_tasks_menu_keyboard, get_proxy_menu_keyboard,
    get_accounts_list_keyboard, get_warming_menu_keyboard,
    get_warming_accounts_keyboard, get_warming_duration_keyboard,
    get_warming_frequency_keyboard, get_warming_intensity_keyboard
)
from utils.proxy_manager import distribute_proxies, check_proxy
from instagram.post_manager import PostManager
from instagram.reels_manager import ReelsManager, publish_reels_in_parallel
from instagram.account_warmer import AccountWarmer

# Импорты из нового модуля profile_setup
from profile_setup.name_manager import update_profile_name
from profile_setup.username_manager import update_username
from profile_setup.bio_manager import update_biography, clear_biography
from profile_setup.links_manager import update_profile_links
from profile_setup.avatar_manager import update_profile_picture, remove_profile_picture
from profile_setup.post_manager import upload_photo, upload_video, delete_all_posts
from profile_setup.cleanup_manager import clear_profile

# Импорт состояний
from telegram.states import (
    WAITING_USERNAME, WAITING_PASSWORD, WAITING_ACCOUNT_SELECTION,
    WAITING_BIO_OR_AVATAR, WAITING_TASK_TYPE, WAITING_MEDIA,
    WAITING_CAPTION, WAITING_SCHEDULE_TIME, WAITING_PROXY_INFO,
    WAITING_PROFILE_PHOTO, BULK_ADD_ACCOUNTS,
    WARMING_MENU, WARMING_ACCOUNT_SELECTION, WARMING_SETTINGS,
    WARMING_FREQUENCY, WARMING_INTENSITY
)

logger = logging.getLogger(__name__)

# Временное хранилище данных пользователя
user_data_store = {}

def start_handler(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    user_id = update.effective_user.id

    # Проверяем, является ли пользователь администратором
    if user_id not in ADMIN_USER_IDS:
        update.message.reply_text("У вас нет доступа к этому боту.")
        return

    # Приветственное сообщение
    update.message.reply_text(
        f"Привет, {update.effective_user.first_name}! Я бот для управления аккаунтами Instagram.\n\n"
        "Используйте кнопки меню для навигации:",
        reply_markup=get_main_menu_keyboard()
    )

def help_handler(update: Update, context: CallbackContext):
    """Обработчик команды /help"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    help_text = (
        "*Основные команды:*\n"
        "/start - Запустить бота\n"
        "/help - Показать эту справку\n\n"

        "*Управление аккаунтами:*\n"
        "/accounts - Меню аккаунтов\n"
        "/add_account - Добавить аккаунт Instagram\n"
        "/list_accounts - Список добавленных аккаунтов\n"
        "/profile_setup - Настройка профиля\n\n"

        "*Публикация контента:*\n"
        "/tasks - Меню задач\n"
        "/publish_now - Опубликовать сейчас\n"
        "/schedule_publish - Отложенная публикация\n\n"

        "*Управление прокси:*\n"
        "/proxy - Меню прокси\n"
        "/add_proxy - Добавить прокси\n"
        "/distribute_proxies - Распределить прокси\n"
        "/list_proxies - Список добавленных прокси\n\n"

        "*Прогрев аккаунтов:*\n"
        "/warming - Меню прогрева\n"
        "/start_warming - Начать прогрев аккаунта\n"
        "/stop_warming - Остановить прогрев аккаунта\n"
        "/warming_status - Статус прогрева аккаунтов\n\n"

        "*Дополнительно:*\n"
        "/cancel - Отменить текущую операцию"
    )

    update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

def accounts_handler(update: Update, context: CallbackContext):
    """Обработчик команды /accounts"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    update.message.reply_text(
        "Меню управления аккаунтами Instagram:",
        reply_markup=get_accounts_menu_keyboard()
    )

def tasks_handler(update: Update, context: CallbackContext):
    """Обработчик команды /tasks"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    update.message.reply_text(
        "Меню публикации контента:",
        reply_markup=get_tasks_menu_keyboard()
    )

def proxy_handler(update: Update, context: CallbackContext):
    """Обработчик команды /proxy"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    update.message.reply_text(
        "Меню управления прокси:",
        reply_markup=get_proxy_menu_keyboard()
    )

def warming_handler(update: Update, context: CallbackContext):
    """Обработчик команды /warming"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    update.message.reply_text(
        "Меню прогрева аккаунтов Instagram:",
        reply_markup=get_warming_menu_keyboard()
    )

# Обработчики для аккаунтов
def add_account_handler(update: Update, context: CallbackContext):
    """Обработчик для добавления аккаунта Instagram"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    # Если это первый вызов команды
    if context.args is None or len(context.args) == 0:
        update.message.reply_text(
            "Пожалуйста, введите имя пользователя (логин) аккаунта Instagram:"
        )
        return WAITING_USERNAME

    # Если пользователь ввел имя пользователя
    if not user_id in user_data_store:
        user_data_store[user_id] = {}

    if 'instagram_username' not in user_data_store[user_id]:
        user_data_store[user_id]['instagram_username'] = update.message.text
        update.message.reply_text(
            "Теперь введите пароль для аккаунта:"
        )
        return WAITING_PASSWORD

    # Если пользователь ввел пароль
    if 'instagram_password' not in user_data_store[user_id]:
        user_data_store[user_id]['instagram_password'] = update.message.text

        # Добавляем аккаунт в базу данных
        username = user_data_store[user_id]['instagram_username']
        password = user_data_store[user_id]['instagram_password']

        success, result = add_instagram_account(username, password)

        if success:
            update.message.reply_text(
                f"Аккаунт {username} успешно добавлен!",
                reply_markup=get_accounts_menu_keyboard()
            )
        else:
            update.message.reply_text(
                f"Ошибка при добавлении аккаунта: {result}",
                reply_markup=get_accounts_menu_keyboard()
            )

        # Очищаем данные пользователя
        del user_data_store[user_id]

        return ConversationHandler.END

def list_accounts_handler(update: Update, context: CallbackContext):
    """Обработчик для отображения списка аккаунтов"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    accounts = get_instagram_accounts()

    if not accounts:
        update.message.reply_text(
            "Список аккаунтов пуст. Добавьте аккаунты с помощью команды /add_account",
            reply_markup=get_accounts_menu_keyboard()
        )
        return

    # Создаем клавиатуру со списком аккаунтов
    keyboard = get_accounts_list_keyboard(accounts)

    update.message.reply_text(
        "Список добавленных аккаунтов Instagram:",
        reply_markup=keyboard
    )

def profile_setup_handler(update: Update, context: CallbackContext):
    """Обработчик для настройки профиля Instagram"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    # Если это первый вызов команды
    if context.args is None or len(context.args) == 0:
        accounts = get_instagram_accounts()

        if not accounts:
            update.message.reply_text(
                "Список аккаунтов пуст. Добавьте аккаунты с помощью команды /add_account",
                reply_markup=get_accounts_menu_keyboard()
            )
            return ConversationHandler.END

        # Создаем клавиатуру для выбора аккаунта
        keyboard = []
        for account in accounts:
            keyboard.append([InlineKeyboardButton(account.username, callback_data=f"profile_setup_{account.id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            "Выберите аккаунт для настройки профиля:",
            reply_markup=reply_markup
        )

        return WAITING_ACCOUNT_SELECTION

    # Если пользователь выбрал аккаунт (через callback_handler)
    if 'selected_account_id' in user_data_store.get(user_id, {}):
        # Если пользователь отправил текст (описание профиля)
        if update.message.text:
            user_data_store[user_id]['profile_bio'] = update.message.text

            update.message.reply_text(
                "Отправьте фотографию для аватара профиля или введите 'пропустить', чтобы не менять аватар:"
            )

            return WAITING_BIO_OR_AVATAR

        # Если пользователь отправил фото (аватар)
        if update.message.photo:
            # Получаем файл с наилучшим качеством
            photo_file = update.message.photo[-1].get_file()

            # Создаем директорию для аватаров, если её нет
            avatar_dir = Path(MEDIA_DIR) / "avatars"
            os.makedirs(avatar_dir, exist_ok=True)

            # Сохраняем файл
            avatar_path = avatar_dir / f"avatar_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            photo_file.download(avatar_path)

            user_data_store[user_id]['avatar_path'] = str(avatar_path)

            # Создаем задачу на обновление профиля
            account_id = user_data_store[user_id]['selected_account_id']
            bio = user_data_store[user_id].get('profile_bio')

            success, task_id = create_publish_task(
                account_id=account_id,
                task_type='profile',
                media_path=str(avatar_path),
                caption=bio
            )

            if success:
                # Запускаем обновление профиля
                account = get_instagram_account(account_id)

                update.message.reply_text(
                    f"Задача на обновление профиля {account.username} создана. Выполняется обновление..."
                )

                # Выполняем задачу
                from database.db_manager import get_pending_tasks
                tasks = get_pending_tasks()
                for task in tasks:
                    if task.id == task_id:
                        # Используем новые функции вместо ProfileManager
                        success = True
                        error = None

                        if task.media_path:
                            success, error = update_profile_picture(account_id, task.media_path)

                        if task.caption:
                            bio_success, bio_error = update_biography(account_id, task.caption)
                            if not success:  # Если фото не обновлялось или была ошибка
                                success, error = bio_success, bio_error

                        if success:
                            update.message.reply_text(
                                f"Профиль {account.username} успешно обновлен!",
                                reply_markup=get_accounts_menu_keyboard()
                            )
                        else:
                            update.message.reply_text(
                                f"Ошибка при обновлении профиля: {error}",
                                reply_markup=get_accounts_menu_keyboard()
                            )

                        break
            else:
                update.message.reply_text(
                    f"Ошибка при создании задачи: {task_id}",
                    reply_markup=get_accounts_menu_keyboard()
                )

            # Очищаем данные пользователя
            del user_data_store[user_id]

            return ConversationHandler.END

        # Если пользователь решил пропустить аватар
        if update.message.text.lower() == 'пропустить':
            # Создаем задачу только на обновление био
            account_id = user_data_store[user_id]['selected_account_id']
            bio = user_data_store[user_id].get('profile_bio')

            success, task_id = create_publish_task(
                account_id=account_id,
                task_type='profile',
                caption=bio
            )

            if success:
                # Запускаем обновление профиля
                account = get_instagram_account(account_id)

                update.message.reply_text(
                    f"Задача на обновление профиля {account.username} создана. Выполняется обновление..."
                )

                # Выполняем задачу
                from database.db_manager import get_pending_tasks
                tasks = get_pending_tasks()
                for task in tasks:
                    if task.id == task_id:
                        # Используем новую функцию вместо ProfileManager
                        success, error = update_biography(account_id, bio)

                        if success:
                            update.message.reply_text(
                                f"Профиль {account.username} успешно обновлен!",
                                reply_markup=get_accounts_menu_keyboard()
                            )
                        else:
                            update.message.reply_text(
                                f"Ошибка при обновлении профиля: {error}",
                                reply_markup=get_accounts_menu_keyboard()
                            )

                        break
            else:
                update.message.reply_text(
                    f"Ошибка при создании задачи: {task_id}",
                    reply_markup=get_accounts_menu_keyboard()
                )

            # Очищаем данные пользователя
            del user_data_store[user_id]

            return ConversationHandler.END

# Обработчики для публикации контента
def publish_now_handler(update: Update, context: CallbackContext):
    """Обработчик для немедленной публикации контента"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    # Если это первый вызов команды
    if context.args is None or len(context.args) == 0:
        # Запрашиваем тип публикации
        keyboard = [
            [InlineKeyboardButton("Reels (видео)", callback_data="publish_type_reel")],
            [InlineKeyboardButton("Фото", callback_data="publish_type_post")],
            [InlineKeyboardButton("Мозаика (6 частей)", callback_data="publish_type_mosaic")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            "Выберите тип публикации:",
            reply_markup=reply_markup
        )

        return WAITING_TASK_TYPE

    # Если пользователь выбрал тип публикации (через callback_handler)
    if 'publish_type' in user_data_store.get(user_id, {}):
        # Если пользователь еще не выбрал аккаунт
        if 'selected_account_id' not in user_data_store[user_id]:
            accounts = get_instagram_accounts()

            if not accounts:
                update.message.reply_text(
                    "Список аккаунтов пуст. Добавьте аккаунты с помощью команды /add_account",
                    reply_markup=get_tasks_menu_keyboard()
                )
                return ConversationHandler.END

            # Создаем клавиатуру для выбора аккаунта
            keyboard = []
            for account in accounts:
                keyboard.append([InlineKeyboardButton(account.username, callback_data=f"publish_account_{account.id}")])

            # Добавляем опцию публикации во все аккаунты для Reels
            if user_data_store[user_id]['publish_type'] == 'reel':
                keyboard.append([InlineKeyboardButton("Опубликовать во все аккаунты", callback_data="publish_account_all")])

            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.reply_text(
                "Выберите аккаунт для публикации:",
                reply_markup=reply_markup
            )

            return WAITING_ACCOUNT_SELECTION

        # Если пользователь еще не отправил медиафайл
        if 'media_path' not in user_data_store[user_id]:
            # Если пользователь отправил фото
            if update.message.photo and user_data_store[user_id]['publish_type'] in ['post', 'mosaic']:
                # Получаем файл с наилучшим качеством
                photo_file = update.message.photo[-1].get_file()

                # Создаем директорию для фото, если её нет
                photo_dir = Path(MEDIA_DIR) / "photos"
                os.makedirs(photo_dir, exist_ok=True)

                # Сохраняем файл
                photo_path = photo_dir / f"photo_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                photo_file.download(photo_path)

                user_data_store[user_id]['media_path'] = str(photo_path)

                update.message.reply_text(
                    "Введите описание для публикации (или 'пропустить' для публикации без описания):"
                )

                return WAITING_CAPTION

            # Если пользователь отправил видео
            elif (update.message.video or update.message.document) and user_data_store[user_id]['publish_type'] == 'reel':
                # Получаем файл
                if update.message.video:
                    video_file = update.message.video.get_file()
                    file_name = f"video_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                else:
                    video_file = update.message.document.get_file()
                    file_name = update.message.document.file_name

                # Создаем директорию для видео, если её нет
                video_dir = Path(MEDIA_DIR) / "videos"
                os.makedirs(video_dir, exist_ok=True)

                # Сохраняем файл
                video_path = video_dir / file_name
                video_file.download(video_path)

                user_data_store[user_id]['media_path'] = str(video_path)

                update.message.reply_text(
                    "Введите описание для публикации (или 'пропустить' для публикации без описания):"
                )

                return WAITING_CAPTION

            # Если пользователь отправил неподходящий тип файла
            else:
                update.message.reply_text(
                    f"Пожалуйста, отправьте {'фото' if user_data_store[user_id]['publish_type'] in ['post', 'mosaic'] else 'видео'} для публикации."
                )
                return WAITING_MEDIA

        # Если пользователь ввел описание
        if 'caption' not in user_data_store[user_id]:
            if update.message.text.lower() == 'пропустить':
                user_data_store[user_id]['caption'] = ""
            else:
                user_data_store[user_id]['caption'] = update.message.text

            # Создаем и выполняем задачу на публикацию
            publish_type = user_data_store[user_id]['publish_type']
            media_path = user_data_store[user_id]['media_path']
            caption = user_data_store[user_id]['caption']

            # Если публикация во все аккаунты
            if user_data_store[user_id].get('selected_account_id') == 'all':
                if publish_type == 'reel':
                    update.message.reply_text(
                        "Начинаю публикацию Reels во все аккаунты..."
                    )

                    # Получаем все аккаунты
                    accounts = get_instagram_accounts()
                    account_ids = [account.id for account in accounts]

                    # Публикуем Reels параллельно
                    results = publish_reels_in_parallel(media_path, caption, account_ids)

                    # Формируем отчет
                    report = "Результаты публикации Reels:\n\n"
                    for account_id, result in results.items():
                        account = get_instagram_account(account_id)
                        status = "✅ Успешно" if result['success'] else f"❌ Ошибка: {result['result']}"
                        report += f"{account.username}: {status}\n"

                    update.message.reply_text(
                        report,
                        reply_markup=get_tasks_menu_keyboard()
                    )
            else:
                # Публикация в один аккаунт
                account_id = user_data_store[user_id]['selected_account_id']

                success, task_id = create_publish_task(
                    account_id=account_id,
                    task_type=publish_type,
                    media_path=media_path,
                    caption=caption
                )

                if success:
                    # Запускаем публикацию
                    account = get_instagram_account(account_id)

                    update.message.reply_text(
                        f"Задача на публикацию в аккаунт {account.username} создана. Выполняется публикация..."
                    )

                    # Выполняем задачу
                    from database.db_manager import get_pending_tasks
                    tasks = get_pending_tasks()

                    for task in tasks:
                        if task.id == task_id:
                            if publish_type == 'reel':
                                manager = ReelsManager(account_id)
                                success, error = manager.execute_reel_task(task)
                            else:  # 'post' или 'mosaic'
                                # Используем новую функцию вместо PostManager
                                if publish_type == 'post':
                                    success, error = upload_photo(account_id, media_path, caption)
                                else:  # 'mosaic'
                                    manager = PostManager(account_id)
                                    success, error = manager.execute_post_task(task)

                            if success:
                                update.message.reply_text(
                                    f"Публикация в аккаунт {account.username} успешно выполнена!",
                                    reply_markup=get_tasks_menu_keyboard()
                                )
                            else:
                                update.message.reply_text(
                                    f"Ошибка при публикации: {error}",
                                    reply_markup=get_tasks_menu_keyboard()
                                )

                            break
                else:
                    update.message.reply_text(
                        f"Ошибка при создании задачи: {task_id}",
                        reply_markup=get_tasks_menu_keyboard()
                    )

            # Очищаем данные пользователя
            del user_data_store[user_id]

            return ConversationHandler.END

def schedule_publish_handler(update: Update, context: CallbackContext):
    """Обработчик для отложенной публикации контента"""
    # Аналогично publish_now_handler, но с дополнительным шагом для выбора времени
    # Реализация будет похожа, но с добавлением обработки времени публикации
    pass

# Обработчики для прокси
def add_proxy_handler(update: Update, context: CallbackContext):
    """Обработчик для добавления прокси"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    # Если это первый вызов команды
    if context.args is None or len(context.args) == 0:
        update.message.reply_text(
            "Введите данные прокси в формате:\n"
            "протокол://логин:пароль@хост:порт\n\n"
            "Например: http://user:pass@1.2.3.4:8080\n"
            "Или без авторизации: http://1.2.3.4:8080"
        )
        return WAITING_PROXY_INFO

    # Если пользователь ввел данные прокси
    proxy_info = update.message.text

    # Парсим данные прокси
    try:
        # Разбираем протокол
        protocol, rest = proxy_info.split('://', 1)

        # Разбираем логин:пароль@хост:порт или хост:порт
        if '@' in rest:
            auth, host_port = rest.split('@', 1)
            username, password = auth.split(':', 1)
        else:
            host_port = rest
            username = None
            password = None

        # Разбираем хост:порт
        host, port = host_port.split(':', 1)
        port = int(port)

        # Добавляем прокси в базу данных
        success, result = add_proxy(host, port, username, password, protocol)

        if success:
            update.message.reply_text(
                f"Прокси {host}:{port} успешно добавлен!",
                reply_markup=get_proxy_menu_keyboard()
            )
        else:
            update.message.reply_text(
                f"Ошибка при добавлении прокси: {result}",
                reply_markup=get_proxy_menu_keyboard()
            )
    except Exception as e:
        update.message.reply_text(
            f"Ошибка при разборе данных прокси: {e}\n"
            "Пожалуйста, проверьте формат и попробуйте снова.",
            reply_markup=get_proxy_menu_keyboard()
        )

    return ConversationHandler.END

def distribute_proxies_handler(update: Update, context: CallbackContext):
    """Обработчик для распределения прокси по аккаунтам"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    update.message.reply_text("Начинаю распределение прокси по аккаунтам...")

    success, message = distribute_proxies()

    if success:
        update.message.reply_text(
            f"Прокси успешно распределены: {message}",
            reply_markup=get_proxy_menu_keyboard()
        )
    else:
        update.message.reply_text(
            f"Ошибка при распределении прокси: {message}",
            reply_markup=get_proxy_menu_keyboard()
        )

def list_proxies_handler(update: Update, context: CallbackContext):
    """Обработчик для отображения списка прокси"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    proxies = get_proxies()

    if not proxies:
        update.message.reply_text(
            "Список прокси пуст. Добавьте прокси с помощью команды /add_proxy",
            reply_markup=get_proxy_menu_keyboard()
        )
        return

    # Формируем список прокси
    proxy_list = "Список добавленных прокси:\n\n"

    for proxy in proxies:
        status = "✅ Активен" if proxy.is_active else "❌ Неактивен"
        last_checked = proxy.last_checked.strftime("%d.%m.%Y %H:%M") if proxy.last_checked else "Не проверялся"

        proxy_list += f"ID: {proxy.id}\n"
        proxy_list += f"Адрес: {proxy.protocol}://{proxy.host}:{proxy.port}\n"
        if proxy.username and proxy.password:
            proxy_list += f"Авторизация: {proxy.username}:{'*' * len(proxy.password)}\n"
        proxy_list += f"Статус: {status}\n"
        proxy_list += f"Последняя проверка: {last_checked}\n\n"

    # Добавляем кнопки для проверки прокси
    keyboard = [
        [InlineKeyboardButton("Проверить все прокси", callback_data="check_all_proxies")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        proxy_list,
        reply_markup=reply_markup
    )

# Обработчики для прогрева аккаунтов
def start_warming_handler(update: Update, context: CallbackContext):
    """Обработчик для начала прогрева аккаунта"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    # Если это первый вызов команды
    accounts = get_instagram_accounts()

    if not accounts:
        update.message.reply_text(
            "Список аккаунтов пуст. Добавьте аккаунты с помощью команды /add_account",
            reply_markup=get_warming_menu_keyboard()
        )
        return ConversationHandler.END

    # Создаем клавиатуру для выбора аккаунта
    keyboard = get_warming_accounts_keyboard(accounts)

    update.message.reply_text(
        "Выберите аккаунт для прогрева:",
        reply_markup=keyboard
    )

    return WARMING_ACCOUNT_SELECTION

def stop_warming_handler(update: Update, context: CallbackContext):
    """Обработчик для остановки прогрева аккаунта"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    # Получаем активные задачи прогрева
    warming_tasks = get_warming_tasks(status='active')

    if not warming_tasks:
        update.message.reply_text(
            "Нет активных задач прогрева.",
            reply_markup=get_warming_menu_keyboard()
        )
        return

    # Создаем клавиатуру для выбора задачи прогрева
    keyboard = []
    for task in warming_tasks:
        account = get_instagram_account(task.account_id)
        keyboard.append([InlineKeyboardButton(
            f"{account.username} (запущен {task.created_at.strftime('%d.%m.%Y %H:%M')})",
            callback_data=f"stop_warming_{task.id}"
        )])

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "Выберите задачу прогрева для остановки:",
        reply_markup=reply_markup
    )

def warming_status_handler(update: Update, context: CallbackContext):
    """Обработчик для отображения статуса прогрева аккаунтов"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    # Получаем все задачи прогрева
    warming_tasks = get_warming_tasks()

    if not warming_tasks:
        update.message.reply_text(
            "Нет задач прогрева.",
            reply_markup=get_warming_menu_keyboard()
        )
        return

    # Формируем отчет о задачах прогрева
    status_text = "Статус прогрева аккаунтов:\n\n"

    for task in warming_tasks:
        account = get_instagram_account(task.account_id)
        status = "✅ Активен" if task.status == 'active' else "❌ Остановлен"
        created = task.created_at.strftime("%d.%m.%Y %H:%M")

        status_text += f"Аккаунт: {account.username}\n"
        status_text += f"Статус: {status}\n"
        status_text += f"Запущен: {created}\n"
        status_text += f"Длительность: {task.duration} минут\n"
        status_text += f"Интенсивность: {task.intensity}\n\n"

    update.message.reply_text(
        status_text,
        reply_markup=get_warming_menu_keyboard()
    )

# Обработчики для медиафайлов
def photo_handler(update: Update, context: CallbackContext):
    """Обработчик для фотографий"""
    # Этот обработчик будет вызываться, когда пользователь отправляет фото вне контекста диалога
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    update.message.reply_text(
        "Вы отправили фотографию. Чтобы опубликовать её, используйте команду /publish_now",
        reply_markup=get_main_menu_keyboard()
    )

def video_handler(update: Update, context: CallbackContext):
    """Обработчик для видео"""
    # Этот обработчик будет вызываться, когда пользователь отправляет видео вне контекста диалога
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    update.message.reply_text(
        "Вы отправили видео. Чтобы опубликовать его в Reels, используйте команду /publish_now",
        reply_markup=get_main_menu_keyboard()
    )

def text_handler(update: Update, context: CallbackContext):
    """Обработчик для текстовых сообщений"""
    # Этот обработчик будет вызываться для всех текстовых сообщений, не являющихся командами
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    update.message.reply_text(
        "Используйте кнопки меню или команды для взаимодействия с ботом.",
        reply_markup=get_main_menu_keyboard()
    )

def callback_handler(update: Update, context: CallbackContext):
    """Обработчик для кнопок"""
    query = update.callback_query
    user_id = query.from_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    # Получаем данные кнопки
    data = query.data

    # Инициализируем хранилище данных пользователя, если его нет
    if not user_id in user_data_store:
        user_data_store[user_id] = {}

    # Обрабатываем различные типы кнопок

    # Кнопки выбора типа публикации
    if data.startswith("publish_type_"):
        publish_type = data.replace("publish_type_", "")
        user_data_store[user_id]['publish_type'] = publish_type

        # Запрашиваем выбор аккаунта
        accounts = get_instagram_accounts()

        if not accounts:
            query.edit_message_text(
                "Список аккаунтов пуст. Добавьте аккаунты с помощью команды /add_account"
            )
            return ConversationHandler.END

        # Создаем клавиатуру для выбора аккаунта
        keyboard = []
        for account in accounts:
            keyboard.append([InlineKeyboardButton(account.username, callback_data=f"publish_account_{account.id}")])

        # Добавляем опцию публикации во все аккаунты для Reels
        if publish_type == 'reel':
            keyboard.append([InlineKeyboardButton("Опубликовать во все аккаунты", callback_data="publish_account_all")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            text=f"Выбран тип публикации: {publish_type}. Теперь выберите аккаунт:",
            reply_markup=reply_markup
        )

    # Кнопки выбора аккаунта для публикации
    elif data.startswith("publish_account_"):
        account_id = data.replace("publish_account_", "")
        user_data_store[user_id]['selected_account_id'] = account_id

        # Запрашиваем медиафайл
        if user_data_store[user_id]['publish_type'] in ['post', 'mosaic']:
            query.edit_message_text(
                "Отправьте фотографию для публикации:"
            )
        else:  # 'reel'
            query.edit_message_text(
                "Отправьте видео для публикации в Reels:"
            )

    # Кнопки выбора аккаунта для настройки профиля
    elif data.startswith("profile_setup_"):
        account_id = data.replace("profile_setup_", "")
        user_data_store[user_id]['selected_account_id'] = account_id

        # Запрашиваем описание профиля
        query.edit_message_text(
            "Введите новое описание профиля (или 'пропустить', чтобы не менять описание):"
        )

    # Кнопки выбора аккаунта для прогрева
    elif data.startswith("warming_account_"):
        account_id = int(data.replace("warming_account_", ""))
        user_data_store[user_id]['selected_account_id'] = account_id
        account = get_instagram_account(account_id)

        # Показываем настройки прогрева
        keyboard = [
            [InlineKeyboardButton("Настроить параметры прогрева", callback_data=f"warming_settings_{account_id}")],
            [InlineKeyboardButton("Использовать стандартные настройки", callback_data=f"warming_default_{account_id}")],
            [InlineKeyboardButton("Отмена", callback_data="warming_cancel")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            f"Выбран аккаунт: {account.username}\n\n"
            "Вы можете использовать стандартные настройки прогрева или настроить параметры вручную.",
            reply_markup=reply_markup
        )

        return WARMING_SETTINGS

    # Кнопка настройки параметров прогрева
    elif data.startswith("warming_settings_"):
        account_id = int(data.replace("warming_settings_", ""))
        user_data_store[user_id]['selected_account_id'] = account_id

        # Показываем клавиатуру для выбора частоты прогрева
        keyboard = get_warming_frequency_keyboard()

        query.edit_message_text(
            "Выберите частоту прогрева (как часто будут выполняться действия):",
            reply_markup=keyboard
        )

        return WARMING_FREQUENCY

    # Кнопка использования стандартных настроек прогрева
    elif data.startswith("warming_default_"):
        account_id = int(data.replace("warming_default_", ""))
        user_data_store[user_id]['selected_account_id'] = account_id
        account = get_instagram_account(account_id)

        # Устанавливаем стандартные настройки
        frequency = "medium"  # Средняя частота
        intensity = "medium"  # Средняя интенсивность
        duration = 60  # 60 минут

        # Создаем задачу на прогрев
        success, task_id = create_warming_task(
            account_id=account_id,
            duration=duration,
            frequency=frequency,
            intensity=intensity
        )

        if success:
            # Запускаем прогрев
            warmer = AccountWarmer(account_id)
            warmer.start_warming(duration, frequency, intensity)

            query.edit_message_text(
                f"Прогрев аккаунта {account.username} успешно запущен!\n"
                f"Используются стандартные настройки:\n"
                f"- Длительность: {duration} минут\n"
                f"- Частота: {frequency}\n"
                f"- Интенсивность: {intensity}"
            )

            # Отправляем дополнительное сообщение с клавиатурой меню
            context.bot.send_message(
                chat_id=user_id,
                text="Вы можете отслеживать статус прогрева с помощью команды /warming_status",
                reply_markup=get_warming_menu_keyboard()
            )
        else:
            query.edit_message_text(
                f"Ошибка при создании задачи прогрева: {task_id}"
            )

        # Очищаем данные пользователя
        del user_data_store[user_id]

        return ConversationHandler.END

    # Кнопка отмены прогрева
    elif data == "warming_cancel":
        query.edit_message_text(
            "Операция прогрева отменена."
        )

        # Отправляем дополнительное сообщение с клавиатурой меню
        context.bot.send_message(
            chat_id=user_id,
            text="Вы можете вернуться в меню прогрева с помощью команды /warming",
            reply_markup=get_warming_menu_keyboard()
        )

        # Очищаем данные пользователя
        if user_id in user_data_store:
            del user_data_store[user_id]

        return ConversationHandler.END

    # Кнопки выбора частоты прогрева
    elif data.startswith("warming_frequency_"):
        frequency = data.replace("warming_frequency_", "")
        user_data_store[user_id]['warming_frequency'] = frequency

        # Показываем клавиатуру для выбора интенсивности
        keyboard = get_warming_intensity_keyboard()

        query.edit_message_text(
            "Выберите интенсивность прогрева (количество действий):",
            reply_markup=keyboard
        )

        return WARMING_INTENSITY

    # Кнопки выбора интенсивности прогрева
    elif data.startswith("warming_intensity_"):
        intensity = data.replace("warming_intensity_", "")
        user_data_store[user_id]['warming_intensity'] = intensity

        # Показываем клавиатуру для выбора длительности
        keyboard = get_warming_duration_keyboard()

        query.edit_message_text(
            "Выберите длительность прогрева:",
            reply_markup=keyboard
        )

    # Кнопки выбора длительности прогрева
    elif data.startswith("warming_duration_"):
        duration = int(data.replace("warming_duration_", ""))
        user_data_store[user_id]['warming_duration'] = duration

        account_id = user_data_store[user_id]['selected_account_id']
        frequency = user_data_store[user_id]['warming_frequency']
        intensity = user_data_store[user_id]['warming_intensity']
        account = get_instagram_account(account_id)

        # Создаем задачу на прогрев
        success, task_id = create_warming_task(
            account_id=account_id,
            duration=duration,
            frequency=frequency,
            intensity=intensity
        )

        if success:
            # Запускаем прогрев
            warmer = AccountWarmer(account_id)
            warmer.start_warming(duration, frequency, intensity)

            query.edit_message_text(
                f"Прогрев аккаунта {account.username} успешно запущен!\n"
                f"Настройки прогрева:\n"
                f"- Длительность: {duration} минут\n"
                f"- Частота: {frequency}\n"
                f"- Интенсивность: {intensity}"
            )

            # Отправляем дополнительное сообщение с клавиатурой меню
            context.bot.send_message(
                chat_id=user_id,
                text="Вы можете отслеживать статус прогрева с помощью команды /warming_status",
                reply_markup=get_warming_menu_keyboard()
            )
        else:
            query.edit_message_text(
                f"Ошибка при создании задачи прогрева: {task_id}"
            )

        # Очищаем данные пользователя
        del user_data_store[user_id]

        return ConversationHandler.END

    # Кнопка остановки прогрева
    elif data.startswith("stop_warming_"):
        task_id = int(data.replace("stop_warming_", ""))

        # Останавливаем прогрев
        warmer = AccountWarmer(None)  # ID аккаунта не нужен для остановки по ID задачи
        success = warmer.stop_warming_by_task_id(task_id)

        if success:
            # Обновляем статус задачи в БД
            update_warming_task_status(task_id, 'stopped')

            query.edit_message_text(
                "Прогрев успешно остановлен!"
            )

            # Отправляем дополнительное сообщение с клавиатурой меню
            context.bot.send_message(
                chat_id=user_id,
                text="Вы можете запустить новый прогрев с помощью команды /start_warming",
                reply_markup=get_warming_menu_keyboard()
            )
        else:
            query.edit_message_text(
                "Ошибка при остановке прогрева. Возможно, задача уже завершена."
            )

    # Кнопка удаления всех постов
    elif data == "profile_delete_posts":
        account_id = user_data_store[user_id].get('selected_account_id')
        if account_id:
            query.edit_message_text("⏳ Удаление всех постов...")
            success, result = delete_all_posts(account_id)
            if success:
                query.edit_message_text(
                    "✅ Все посты успешно удалены!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data=f"profile_account_{account_id}")]
                    ])
                )
            else:
                query.edit_message_text(
                    f"❌ Ошибка при удалении постов: {result}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data=f"profile_account_{account_id}")]
                    ])
                )

    # Кнопка очистки описания профиля
    elif data == "profile_delete_bio":
        account_id = user_data_store[user_id].get('selected_account_id')
        if account_id:
            query.edit_message_text("⏳ Очистка описания профиля...")
            success, result = clear_biography(account_id)
            if success:
                query.edit_message_text(
                    "✅ Описание профиля успешно очищено!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data=f"profile_account_{account_id}")]
                    ])
                )
            else:
                query.edit_message_text(
                    f"❌ Ошибка при очистке профиля: {result}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data=f"profile_account_{account_id}")]
                    ])
                )

    # Кнопка проверки всех прокси
    elif data == "check_all_proxies":
        query.edit_message_text(
            "Начинаю проверку всех прокси. Это может занять некоторое время..."
        )

        # Запускаем проверку прокси
        results = check_all_proxies()

        # Формируем отчет
        report = "Результаты проверки прокси:\n\n"

        for proxy_id, result in results.items():
            proxy = next((p for p in get_proxies() if p.id == proxy_id), None)
            if proxy:
                status = "✅ Работает" if result['working'] else f"❌ Не работает: {result['error']}"
                report += f"ID: {proxy.id}, {proxy.host}:{proxy.port} - {status}\n"

        context.bot.send_message(
            chat_id=user_id,
            text=report,
            reply_markup=get_proxy_menu_keyboard()
        )

    # Подтверждаем обработку callback
    query.answer()

def cancel_handler(update: Update, context: CallbackContext):
    """Обработчик для отмены текущей операции"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    # Очищаем данные пользователя
    if user_id in user_data_store:
        del user_data_store[user_id]

    update.message.reply_text(
        "Операция отменена.",
        reply_markup=get_main_menu_keyboard()
    )

    return ConversationHandler.END

# Обработчик для кнопки "Добавить фото профиля"
def process_add_profile_photo(update: Update, context: CallbackContext):
    """Обработчик для добавления фото профиля"""
    query = update.callback_query
    user_id = query.from_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    # Получаем ID аккаунта из callback_data
    account_id = int(query.data.split('_')[-1])

    # Сохраняем ID аккаунта в данных пользователя
    if not user_id in user_data_store:
        user_data_store[user_id] = {}

    user_data_store[user_id]['selected_account_id'] = account_id

    # Запрашиваем фото профиля
    query.edit_message_text(
        "Отправьте фотографию для установки в качестве фото профиля:"
    )

    return WAITING_PROFILE_PHOTO

# Обработчик для получения фото профиля
def handle_profile_photo(update: Update, context: CallbackContext):
    """Обработчик для получения фото профиля"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    # Получаем ID аккаунта из данных пользователя
    if user_id not in user_data_store or 'selected_account_id' not in user_data_store[user_id]:
        update.message.reply_text(
            "Ошибка: не выбран аккаунт. Пожалуйста, начните процесс заново.",
            reply_markup=get_accounts_menu_keyboard()
        )
        return ConversationHandler.END

    account_id = user_data_store[user_id]['selected_account_id']

    # Получаем файл с наилучшим качеством
    photo_file = update.message.photo[-1].get_file()

    # Создаем директорию для аватаров, если её нет
    avatar_dir = Path(MEDIA_DIR) / "avatars"
    os.makedirs(avatar_dir, exist_ok=True)

    # Сохраняем файл
    avatar_path = avatar_dir / f"avatar_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    photo_file.download(avatar_path)

    update.message.reply_text(
        "Фото получено. Устанавливаю фото профиля..."
    )

    try:
        # Используем новую функцию вместо ProfileManager
        success, result = update_profile_picture(account_id, str(avatar_path))

        if success:
            account = get_instagram_account(account_id)
            update.message.reply_text(
                f"✅ Фото профиля для аккаунта {account.username} успешно установлено!",
                reply_markup=get_accounts_menu_keyboard()
            )
        else:
            update.message.reply_text(
                f"❌ Ошибка при установке фото профиля: {result}",
                reply_markup=get_accounts_menu_keyboard()
            )
    except Exception as e:
        update.message.reply_text(
            f"❌ Произошла ошибка: {str(e)}",
            reply_markup=get_accounts_menu_keyboard()
        )
    finally:
        # Очищаем данные пользователя
        if user_id in user_data_store:
            del user_data_store[user_id]

        return ConversationHandler.END