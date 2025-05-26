from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

def get_main_menu_keyboard():
    """Создает клавиатуру главного меню"""
    keyboard = [
        [KeyboardButton("🔑 Аккаунты"), KeyboardButton("📝 Новая задача")],
        [KeyboardButton("🌐 Прокси"), KeyboardButton("❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_accounts_menu_keyboard():
    """Создает клавиатуру меню аккаунтов"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить аккаунт", callback_data="add_account")],
        [InlineKeyboardButton("📥 Массовая загрузка аккаунтов", callback_data='bulk_add_accounts')],
        [InlineKeyboardButton("🍪 Добавить по cookies", callback_data="add_account_cookie")],
        [InlineKeyboardButton("📋 Список аккаунтов", callback_data="list_accounts")],
        [InlineKeyboardButton("📤 Загрузить аккаунты", callback_data="upload_accounts")],
        [InlineKeyboardButton("⚙️ Настройка профиля", callback_data="profile_setup")],
        [InlineKeyboardButton("🔙 Назад в главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_tasks_menu_keyboard():
    """Создает клавиатуру меню задач"""
    keyboard = [
        [InlineKeyboardButton("📤 Опубликовать сейчас", callback_data="publish_now")],
        [InlineKeyboardButton("⏰ Отложенная публикация", callback_data="schedule_publish")],
        [InlineKeyboardButton("🔙 Назад в главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_proxy_menu_keyboard():
    """Создает клавиатуру меню прокси"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить прокси", callback_data="add_proxy")],
        [InlineKeyboardButton("🔄 Распределить прокси", callback_data="distribute_proxies")],
        [InlineKeyboardButton("📋 Список прокси", callback_data="list_proxies")],
        [InlineKeyboardButton("🔙 Назад в главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_accounts_list_keyboard(accounts):
    """Создает клавиатуру со списком аккаунтов"""
    keyboard = []

    for account in accounts:
        # Добавляем кнопку для каждого аккаунта
        keyboard.append([InlineKeyboardButton(
            f"{account.username} {'✅' if account.is_active else '❌'}",
            callback_data=f"account_{account.id}"
        )])

    # Добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="accounts_menu")])

    return InlineKeyboardMarkup(keyboard)

def get_account_actions_keyboard(account_id):
    """Создает клавиатуру действий для конкретного аккаунта"""
    keyboard = [
        [InlineKeyboardButton("⚙️ Настроить профиль", callback_data=f"profile_setup_{account_id}")],
        [InlineKeyboardButton("📤 Опубликовать", callback_data=f"publish_to_{account_id}")],
        [InlineKeyboardButton("🔑 Сменить пароль", callback_data=f"change_password_{account_id}")],
        [InlineKeyboardButton("🌐 Назначить прокси", callback_data=f"assign_proxy_{account_id}")],
        [InlineKeyboardButton("❌ Удалить аккаунт", callback_data=f"delete_account_{account_id}")],
        [InlineKeyboardButton("🔙 Назад к списку", callback_data="list_accounts")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_publish_type_keyboard():
    """Создает клавиатуру выбора типа публикации"""
    keyboard = [
        [InlineKeyboardButton("📹 Reels (видео)", callback_data="publish_type_reel")],
        [InlineKeyboardButton("🖼️ Фото", callback_data="publish_type_post")],
        [InlineKeyboardButton("🧩 Мозаика (6 частей)", callback_data="publish_type_mosaic")],
        [InlineKeyboardButton("🔙 Назад", callback_data="tasks_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Добавляем функции для клавиатур прогрева аккаунтов
def get_warming_menu_keyboard():
    """Создает клавиатуру меню прогрева аккаунтов"""
    keyboard = [
        [InlineKeyboardButton("🔥 Начать прогрев", callback_data="start_warming")],
        [InlineKeyboardButton("❄️ Остановить прогрев", callback_data="stop_warming")],
        [InlineKeyboardButton("📊 Статус прогрева", callback_data="warming_status")],
        [InlineKeyboardButton("🔙 Назад в главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_warming_accounts_keyboard(accounts):
    """Создает клавиатуру со списком аккаунтов для прогрева"""
    keyboard = []

    # Добавляем кнопку "Выбрать все аккаунты"
    keyboard.append([InlineKeyboardButton(
        "🔄 Выбрать все аккаунты",
        callback_data="warming_account_all"
    )])

    # Добавляем кнопки для отдельных аккаунтов
    for account in accounts:
        keyboard.append([InlineKeyboardButton(
            f"{account.username} {'✅' if account.is_active else '❌'}",
            callback_data=f"warming_account_{account.id}"
        )])

    # Добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="warming_menu")])

    return InlineKeyboardMarkup(keyboard)

def get_warming_frequency_keyboard():
    """Создает клавиатуру выбора частоты прогрева"""
    keyboard = [
        [InlineKeyboardButton("🐢 Низкая (реже)", callback_data="warming_frequency_low")],
        [InlineKeyboardButton("🚶 Средняя", callback_data="warming_frequency_medium")],
        [InlineKeyboardButton("🏃 Высокая (чаще)", callback_data="warming_frequency_high")],
        [InlineKeyboardButton("🔙 Отмена", callback_data="warming_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_warming_intensity_keyboard():
    """Создает клавиатуру выбора интенсивности прогрева"""
    keyboard = [
        [InlineKeyboardButton("🐢 Низкая (меньше действий)", callback_data="warming_intensity_low")],
        [InlineKeyboardButton("🚶 Средняя", callback_data="warming_intensity_medium")],
        [InlineKeyboardButton("🏃 Высокая (больше действий)", callback_data="warming_intensity_high")],
        [InlineKeyboardButton("🔙 Отмена", callback_data="warming_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_warming_duration_keyboard():
    """Создает клавиатуру выбора длительности прогрева"""
    keyboard = [
        [InlineKeyboardButton("30 минут", callback_data="warming_duration_30")],
        [InlineKeyboardButton("1 час", callback_data="warming_duration_60")],
        [InlineKeyboardButton("2 часа", callback_data="warming_duration_120")],
        [InlineKeyboardButton("4 часа", callback_data="warming_duration_240")],
        [InlineKeyboardButton("🔙 Отмена", callback_data="warming_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)