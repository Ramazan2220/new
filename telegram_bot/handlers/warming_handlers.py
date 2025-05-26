import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, CallbackQueryHandler

from config import ADMIN_USER_IDS
from database.db_manager import get_instagram_accounts, get_instagram_account, create_warming_task, get_warming_tasks, update_warming_task_status
from telegram_bot.keyboards import (
    get_warming_menu_keyboard, get_warming_accounts_keyboard,
    get_warming_frequency_keyboard, get_warming_intensity_keyboard,
    get_warming_duration_keyboard
)
from instagram.account_warmer import AccountWarmer
from telegram_bot.states import WARMING_MENU, WARMING_ACCOUNT_SELECTION, WARMING_SETTINGS, WARMING_FREQUENCY, WARMING_INTENSITY

logger = logging.getLogger(__name__)

# Временное хранилище данных пользователя
user_data_store = {}

def warming_menu(update: Update, context: CallbackContext):
    """Обработчик для меню прогрева аккаунтов"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    if update.callback_query:
        update.callback_query.answer()
        update.callback_query.edit_message_text(
            "Меню прогрева аккаунтов Instagram:",
            reply_markup=get_warming_menu_keyboard()
        )
    else:
        update.message.reply_text(
            "Меню прогрева аккаунтов Instagram:",
            reply_markup=get_warming_menu_keyboard()
        )

    return WARMING_MENU

def start_warming(update: Update, context: CallbackContext):
    """Обработчик для начала прогрева аккаунта"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    query = update.callback_query
    query.answer()

    # Получаем список аккаунтов
    accounts = get_instagram_accounts()

    if not accounts:
        query.edit_message_text(
            "Список аккаунтов пуст. Добавьте аккаунты с помощью команды /add_account"
        )
        return ConversationHandler.END

    # Создаем клавиатуру для выбора аккаунта
    keyboard = get_warming_accounts_keyboard(accounts)

    query.edit_message_text(
        "Выберите аккаунт для прогрева:",
        reply_markup=keyboard
    )

    return WARMING_ACCOUNT_SELECTION

def select_warming_account(update: Update, context: CallbackContext):
    """Обработчик для выбора аккаунта для прогрева"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    query = update.callback_query
    query.answer()

    # Получаем ID аккаунта из callback_data
    account_id = int(query.data.replace("warming_account_", ""))

    # Сохраняем ID аккаунта в данных пользователя
    if not user_id in user_data_store:
        user_data_store[user_id] = {}

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

def warming_settings(update: Update, context: CallbackContext):
    """Обработчик для настройки параметров прогрева"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    query = update.callback_query
    query.answer()

    # Получаем ID аккаунта из callback_data
    if query.data == "warming_settings_all":
        # Используем уже сохраненные ID аккаунтов
        pass
    else:
        account_id = int(query.data.replace("warming_settings_", ""))
        user_data_store[user_id]['selected_account_id'] = account_id

    # Показываем клавиатуру для выбора частоты прогрева
    keyboard = get_warming_frequency_keyboard()

    query.edit_message_text(
        "Выберите частоту прогрева (как часто будут выполняться действия):",
        reply_markup=keyboard
    )

    return WARMING_FREQUENCY

def warming_frequency(update: Update, context: CallbackContext):
    """Обработчик для выбора частоты прогрева"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    query = update.callback_query
    query.answer()

    # Получаем частоту из callback_data
    frequency = query.data.replace("warming_frequency_", "")
    user_data_store[user_id]['warming_frequency'] = frequency

    # Показываем клавиатуру для выбора интенсивности
    keyboard = get_warming_intensity_keyboard()

    query.edit_message_text(
        "Выберите интенсивность прогрева (количество действий):",
        reply_markup=keyboard
    )

    return WARMING_INTENSITY

def warming_intensity(update: Update, context: CallbackContext):
    """Обработчик для выбора интенсивности прогрева"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    query = update.callback_query
    query.answer()

    # Получаем интенсивность из callback_data
    intensity = query.data.replace("warming_intensity_", "")
    user_data_store[user_id]['warming_intensity'] = intensity

    # Показываем клавиатуру для выбора длительности
    keyboard = get_warming_duration_keyboard()

    query.edit_message_text(
        "Выберите длительность прогрева:",
        reply_markup=keyboard
    )

    return ConversationHandler.END

def warming_duration(update: Update, context: CallbackContext):
    """Обработчик для выбора длительности прогрева"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    query = update.callback_query
    query.answer()

    # Получаем длительность из callback_data
    duration = int(query.data.replace("warming_duration_", ""))
    frequency = user_data_store[user_id]['warming_frequency']
    intensity = user_data_store[user_id]['warming_intensity']

    # Проверяем, выбраны ли все аккаунты
    if 'selected_account_ids' in user_data_store[user_id]:
        account_ids = user_data_store[user_id]['selected_account_ids']
        success_count = 0

        for account_id in account_ids:
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
                success_count += 1

        query.edit_message_text(
            f"Прогрев успешно запущен для {success_count} из {len(account_ids)} аккаунтов!\n"
            f"Настройки прогрева:\n"
            f"- Длительность: {duration} минут\n"
            f"- Частота: {frequency}\n"
            f"- Интенсивность: {intensity}"
        )
    else:
        account_id = user_data_store[user_id]['selected_account_id']
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
        else:
            query.edit_message_text(
                f"Ошибка при создании задачи прогрева: {task_id}"
            )

    # Отправляем дополнительное сообщение с клавиатурой меню
    context.bot.send_message(
        chat_id=user_id,
        text="Вы можете отслеживать статус прогрева с помощью команды /warming_status",
        reply_markup=get_warming_menu_keyboard()
    )

    # Очищаем данные пользователя
    del user_data_store[user_id]

    return ConversationHandler.END

def warming_default(update: Update, context: CallbackContext):
    """Обработчик для использования стандартных настроек прогрева"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    query = update.callback_query
    query.answer()

    # Устанавливаем стандартные настройки
    frequency = "medium"  # Средняя частота
    intensity = "medium"  # Средняя интенсивность
    duration = 60  # 60 минут

    # Проверяем, выбраны ли все аккаунты
    if query.data == "warming_default_all":
        account_ids = user_data_store[user_id]['selected_account_ids']
        success_count = 0

        for account_id in account_ids:
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
                success_count += 1

        query.edit_message_text(
            f"Прогрев успешно запущен для {success_count} из {len(account_ids)} аккаунтов!\n"
            f"Используются стандартные настройки:\n"
            f"- Длительность: {duration} минут\n"
            f"- Частота: {frequency}\n"
            f"- Интенсивность: {intensity}"
        )
    else:
        # Получаем ID аккаунта из callback_data
        account_id = int(query.data.replace("warming_default_", ""))
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
                f"Используются стандартные настройки:\n"
                f"- Длительность: {duration} минут\n"
                f"- Частота: {frequency}\n"
                f"- Интенсивность: {intensity}"
            )
        else:
            query.edit_message_text(
                f"Ошибка при создании задачи прогрева: {task_id}"
            )

    # Отправляем дополнительное сообщение с клавиатурой меню
    context.bot.send_message(
        chat_id=user_id,
        text="Вы можете отслеживать статус прогрева с помощью команды /warming_status",
        reply_markup=get_warming_menu_keyboard()
    )

    return ConversationHandler.END

def stop_warming(update: Update, context: CallbackContext):
    """Обработчик для остановки прогрева аккаунта"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    query = update.callback_query
    query.answer()

    # Получаем активные задачи прогрева
    warming_tasks = get_warming_tasks(status='active')

    if not warming_tasks:
        query.edit_message_text(
            "Нет активных задач прогрева.",
            reply_markup=get_warming_menu_keyboard()
        )
        return ConversationHandler.END

    # Создаем клавиатуру для выбора задачи прогрева
    keyboard = []
    for task in warming_tasks:
        account = get_instagram_account(task.account_id)
        keyboard.append([InlineKeyboardButton(
            f"{account.username} (запущен {task.created_at.strftime('%d.%m.%Y %H:%M')})",
            callback_data=f"stop_warming_{task.id}"
        )])

    # Добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="warming_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        "Выберите задачу прогрева для остановки:",
        reply_markup=reply_markup
    )

    return ConversationHandler.END

def stop_warming_task(update: Update, context: CallbackContext):
    """Обработчик для остановки конкретной задачи прогрева"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    query = update.callback_query
    query.answer()

    # Получаем ID задачи из callback_data
    task_id = int(query.data.replace("stop_warming_", ""))

    # Останавливаем прогрев
    warmer = AccountWarmer(None)  # ID аккаунта не нужен для остановки по ID задачи
    success = warmer.stop_warming_by_task_id(task_id)

    if success:
        # Обновляем статус задачи в БД
        update_warming_task_status(task_id, 'stopped')

        query.edit_message_text(
            "Прогрев успешно остановлен!",
            reply_markup=get_warming_menu_keyboard()
        )
    else:
        query.edit_message_text(
            "Ошибка при остановке прогрева. Возможно, задача уже завершена.",
            reply_markup=get_warming_menu_keyboard()
        )

    return ConversationHandler.END

def warming_status(update: Update, context: CallbackContext):
    """Обработчик для отображения статуса прогрева аккаунтов"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    query = update.callback_query
    query.answer()

    # Получаем все задачи прогрева
    warming_tasks = get_warming_tasks()

    if not warming_tasks:
        try:
            query.edit_message_text(
                "Нет задач прогрева.",
                reply_markup=get_warming_menu_keyboard()
            )
        except Exception as e:
            if "Message is not modified" not in str(e):
                logger.error(f"Ошибка при обновлении сообщения: {e}")
        return ConversationHandler.END

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

    try:
        query.edit_message_text(
            status_text,
            reply_markup=get_warming_menu_keyboard()
        )
    except Exception as e:
        if "Message is not modified" not in str(e):
            logger.error(f"Ошибка при обновлении сообщения: {e}")

    return ConversationHandler.END

def warming_cancel(update: Update, context: CallbackContext):
    """Обработчик для отмены операции прогрева"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    query = update.callback_query
    query.answer()

    query.edit_message_text(
        "Операция прогрева отменена.",
        reply_markup=get_warming_menu_keyboard()
    )

    # Очищаем данные пользователя
    if user_id in user_data_store:
        del user_data_store[user_id]

    return ConversationHandler.END

def get_warming_handlers():
    """Возвращает обработчики для прогрева аккаунтов"""
    warming_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_warming, pattern='^start_warming$'),
        ],
        states={
            WARMING_ACCOUNT_SELECTION: [
                CallbackQueryHandler(select_all_accounts_warming, pattern='^warming_account_all$'),
                CallbackQueryHandler(select_warming_account, pattern='^warming_account_\d+$'),
            ],
            WARMING_SETTINGS: [
                CallbackQueryHandler(warming_settings, pattern='^warming_settings_all$'),
                CallbackQueryHandler(warming_settings, pattern='^warming_settings_\d+$'),
                CallbackQueryHandler(warming_default, pattern='^warming_default_all$'),
                CallbackQueryHandler(warming_default, pattern='^warming_default_\d+$'),
            ],
            WARMING_FREQUENCY: [
                CallbackQueryHandler(warming_frequency, pattern='^warming_frequency_'),
            ],
            WARMING_INTENSITY: [
                CallbackQueryHandler(warming_intensity, pattern='^warming_intensity_'),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(warming_cancel, pattern='^warming_cancel$'),
        ],
        name="warming_conversation",
        persistent=False,
    )

    handlers = [
        CallbackQueryHandler(warming_menu, pattern='^warming_menu$'),
        CallbackQueryHandler(stop_warming, pattern='^stop_warming$'),
        CallbackQueryHandler(stop_warming_task, pattern='^stop_warming_\d+$'),
        CallbackQueryHandler(warming_status, pattern='^warming_status$'),
        CallbackQueryHandler(warming_duration, pattern='^warming_duration_\d+$'),
        warming_conv_handler,
    ]

    return handlers

def select_all_accounts_warming(update: Update, context: CallbackContext):
    """Обработчик для выбора всех аккаунтов для прогрева"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    query = update.callback_query
    query.answer()

    # Получаем список всех аккаунтов
    accounts = get_instagram_accounts()

    if not accounts:
        query.edit_message_text(
            "Список аккаунтов пуст. Добавьте аккаунты с помощью команды /add_account"
        )
        return ConversationHandler.END

    # Сохраняем список ID всех аккаунтов в данных пользователя
    if not user_id in user_data_store:
        user_data_store[user_id] = {}

    account_ids = [account.id for account in accounts]
    user_data_store[user_id]['selected_account_ids'] = account_ids

    # Показываем настройки прогрева
    keyboard = [
        [InlineKeyboardButton("Настроить параметры прогрева", callback_data="warming_settings_all")],
        [InlineKeyboardButton("Использовать стандартные настройки", callback_data="warming_default_all")],
        [InlineKeyboardButton("Отмена", callback_data="warming_cancel")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        f"Выбрано аккаунтов: {len(accounts)}\n\n"
        "Вы можете использовать стандартные настройки прогрева или настроить параметры вручную.",
        reply_markup=reply_markup
    )

    return WARMING_SETTINGS

def select_account_for_warming(update: Update, context: CallbackContext):
    """Обработчик для выбора аккаунта для прогрева"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        return

    query = update.callback_query
    query.answer()

    # Получаем список аккаунтов
    accounts = get_instagram_accounts()

    if not accounts:
        query.edit_message_text(
            "Список аккаунтов пуст. Добавьте аккаунты с помощью команды /add_account"
        )
        return ConversationHandler.END

    # Создаем клавиатуру для выбора аккаунта
    keyboard = get_warming_accounts_keyboard(accounts)

    query.edit_message_text(
        "Выберите аккаунт для прогрева:",
        reply_markup=keyboard
    )

    return WARMING_ACCOUNT_SELECTION

# Алиасы для совместимости с bot.py
select_account_for_warming = select_warming_account
start_account_warming = warming_default
show_warming_status = warming_status
show_warming_settings = warming_settings