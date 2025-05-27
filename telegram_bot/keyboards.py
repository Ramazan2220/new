# telegram_bot/keyboards.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

def get_main_menu_keyboard():
    """Создает клавиатуру главного меню"""
    keyboard = [
        [InlineKeyboardButton("👤 Аккаунты", callback_data="menu_accounts")],
        [InlineKeyboardButton("📝 Задачи", callback_data="menu_tasks")],
        [InlineKeyboardButton("🔄 Прокси", callback_data="menu_proxy")],
        [InlineKeyboardButton("🔥 Прогрев", callback_data="menu_warming")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="menu_help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_accounts_menu_keyboard():
    """Создает клавиатуру меню аккаунтов"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить аккаунт", callback_data="add_account")],
        [InlineKeyboardButton("📥 Массовая загрузка", callback_data='bulk_add_accounts')],
        [InlineKeyboardButton("📋 Список аккаунтов", callback_data="list_accounts")],
        [InlineKeyboardButton("📊 Статистика сессий", callback_data="refresh_session_stats")],
        [InlineKeyboardButton("📤 Загрузить файл", callback_data="upload_accounts")],
        [InlineKeyboardButton("⚙️ Настройка профиля", callback_data="profile_setup")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_tasks_menu_keyboard():
    """Создает клавиатуру меню задач"""
    keyboard = [
        [InlineKeyboardButton("📤 Опубликовать сейчас", callback_data="publish_now")],
        [InlineKeyboardButton("⏰ Запланировать", callback_data="schedule_publish")],
        [InlineKeyboardButton("📊 Статистика", callback_data="publication_stats")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_proxy_menu_keyboard():
    """Создает клавиатуру меню прокси"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить прокси", callback_data="add_proxy")],
        [InlineKeyboardButton("📋 Список прокси", callback_data="list_proxies")],
        [InlineKeyboardButton("🔄 Распределить", callback_data="distribute_proxies")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_warming_menu_keyboard():
    """Создает клавиатуру меню прогрева аккаунтов"""
    keyboard = [
        [InlineKeyboardButton("🔥 Начать прогрев", callback_data="start_warming")],
        [InlineKeyboardButton("❄️ Остановить прогрев", callback_data="stop_warming")],
        [InlineKeyboardButton("📊 Статус прогрева", callback_data="warming_stats")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="warming_settings_menu")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_accounts_list_keyboard(accounts):
    """Создает клавиатуру со списком аккаунтов"""
    keyboard = []

    for account in accounts:
        # Добавляем кнопку для каждого аккаунта
        status_icon = "✅" if account.is_active else "❌"
        keyboard.append([InlineKeyboardButton(
            f"{account.username} {status_icon}",
            callback_data=f"account_details_{account.id}"
        )])

    # Кнопки управления
    keyboard.extend([
        [InlineKeyboardButton("🔄 Обновить", callback_data="list_accounts")],
        [InlineKeyboardButton("🔙 Меню аккаунтов", callback_data="menu_accounts")]
    ])

    return InlineKeyboardMarkup(keyboard)

def get_account_details_keyboard(account_id):
    """Создает клавиатуру для детальной информации об аккаунте"""
    keyboard = [
        [InlineKeyboardButton("⚙️ Настроить профиль", callback_data=f"profile_account_{account_id}")],
        [InlineKeyboardButton("🔥 Прогреть аккаунт", callback_data=f"warm_account_{account_id}")],
        [InlineKeyboardButton("📤 Опубликовать", callback_data=f"publish_to_{account_id}")],
        [InlineKeyboardButton("🌐 Назначить прокси", callback_data=f"assign_proxy_{account_id}")],
        [InlineKeyboardButton("🔑 Изменить пароль", callback_data=f"change_password_{account_id}")],
        [InlineKeyboardButton("❌ Удалить аккаунт", callback_data=f"delete_account_{account_id}")],
        [InlineKeyboardButton("🔙 К списку", callback_data="list_accounts")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_profile_setup_keyboard():
    """Создает клавиатуру выбора аккаунта для настройки профиля"""
    keyboard = [
        [InlineKeyboardButton("🔙 Меню аккаунтов", callback_data="menu_accounts")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_profile_actions_keyboard(account_id):
    """Создает клавиатуру действий для профиля аккаунта"""
    keyboard = [
        [InlineKeyboardButton("🖼️ Изменить аватар", callback_data=f"change_avatar_{account_id}")],
        [InlineKeyboardButton("📝 Изменить био", callback_data=f"change_bio_{account_id}")],
        [InlineKeyboardButton("👤 Изменить имя", callback_data=f"change_name_{account_id}")],
        [InlineKeyboardButton("🔗 Изменить ссылки", callback_data=f"change_links_{account_id}")],
        [InlineKeyboardButton("📋 Изменить username", callback_data=f"change_username_{account_id}")],
        [InlineKeyboardButton("🗑️ Удалить аватар", callback_data=f"remove_avatar_{account_id}")],
        [InlineKeyboardButton("🧹 Очистить био", callback_data=f"clear_bio_{account_id}")],
        [InlineKeyboardButton("📤 Загрузить пост", callback_data=f"upload_post_{account_id}")],
        [InlineKeyboardButton("🗑️ Удалить все посты", callback_data=f"delete_posts_{account_id}")],
        [InlineKeyboardButton("🧽 Полная очистка", callback_data=f"full_cleanup_{account_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="profile_setup")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_warming_accounts_keyboard(accounts):
    """Создает клавиатуру со списком аккаунтов для прогрева"""
    keyboard = []

    # Добавляем кнопку "Выбрать все аккаунты"
    keyboard.append([InlineKeyboardButton(
        "🔄 Выбрать все аккаунты",
        callback_data="warm_all_accounts"
    )])

    # Добавляем кнопки для отдельных аккаунтов
    for account in accounts:
        status_icon = "✅" if account.is_active else "❌"
        keyboard.append([InlineKeyboardButton(
            f"{account.username} {status_icon}",
            callback_data=f"warm_account_{account.id}"
        )])

    # Кнопка "Назад"
    keyboard.append([InlineKeyboardButton("🔙 Меню прогрева", callback_data="menu_warming")])

    return InlineKeyboardMarkup(keyboard)

def get_warming_settings_keyboard(account_id):
    """Создает клавиатуру настроек прогрева для аккаунта"""
    keyboard = [
        [InlineKeyboardButton("⚙️ Настроить параметры", callback_data=f"warming_custom_{account_id}")],
        [InlineKeyboardButton("🔥 Стандартный прогрев", callback_data=f"warming_default_{account_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="start_warming")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_warming_frequency_keyboard():
    """Создает клавиатуру выбора частоты прогрева"""
    keyboard = [
        [InlineKeyboardButton("🐢 Низкая частота", callback_data="frequency_low")],
        [InlineKeyboardButton("🚶 Средняя частота", callback_data="frequency_medium")],
        [InlineKeyboardButton("🏃 Высокая частота", callback_data="frequency_high")],
        [InlineKeyboardButton("🔙 Назад", callback_data="start_warming")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_warming_intensity_keyboard():
    """Создает клавиатуру выбора интенсивности прогрева"""
    keyboard = [
        [InlineKeyboardButton("🐢 Низкая интенсивность", callback_data="intensity_low")],
        [InlineKeyboardButton("🚶 Средняя интенсивность", callback_data="intensity_medium")],
        [InlineKeyboardButton("🏃 Высокая интенсивность", callback_data="intensity_high")],
        [InlineKeyboardButton("🔙 Назад", callback_data="start_warming")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_warming_duration_keyboard():
    """Создает клавиатуру выбора длительности прогрева"""
    keyboard = [
        [InlineKeyboardButton("30 минут", callback_data="duration_30")],
        [InlineKeyboardButton("1 час", callback_data="duration_60")],
        [InlineKeyboardButton("2 часа", callback_data="duration_120")],
        [InlineKeyboardButton("4 часа", callback_data="duration_240")],
        [InlineKeyboardButton("🔙 Назад", callback_data="start_warming")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_publish_type_keyboard():
    """Создает клавиатуру выбора типа публикации"""
    keyboard = [
        [InlineKeyboardButton("📹 Reels (видео)", callback_data="publish_type_reel")],
        [InlineKeyboardButton("🖼️ Фото", callback_data="publish_type_photo")],
        [InlineKeyboardButton("🧩 Мозаика (6 частей)", callback_data="publish_type_mosaic")],
        [InlineKeyboardButton("📸 Карусель", callback_data="publish_type_carousel")],
        [InlineKeyboardButton("🔙 Меню задач", callback_data="menu_tasks")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_publish_accounts_keyboard(accounts, publish_type):
    """Создает клавиатуру выбора аккаунтов для публикации"""
    keyboard = []

    # Для Reels добавляем опцию "Во все аккаунты"
    if publish_type == "reel":
        keyboard.append([InlineKeyboardButton(
            "🔄 Опубликовать во все аккаунты",
            callback_data="publish_all_accounts"
        )])

    # Добавляем отдельные аккаунты
    for account in accounts:
        status_icon = "✅" if account.is_active else "❌"
        keyboard.append([InlineKeyboardButton(
            f"{account.username} {status_icon}",
            callback_data=f"publish_account_{account.id}"
        )])

    # Кнопка "Назад"
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="publish_now")])

    return InlineKeyboardMarkup(keyboard)

def get_confirmation_keyboard(action, item_id):
    """Создает клавиатуру подтверждения действия"""
    keyboard = [
        [InlineKeyboardButton("✅ Да", callback_data=f"confirm_{action}_{item_id}")],
        [InlineKeyboardButton("❌ Нет", callback_data=f"cancel_{action}_{item_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard(callback_data):
    """Создает простую клавиатуру с кнопкой "Назад" """
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=callback_data)]
    ]
    return InlineKeyboardMarkup(keyboard)
