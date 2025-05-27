# telegram_bot/bot.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram_bot.handlers.warming_handlers import get_warming_handlers
from config import TELEGRAM_TOKEN, ADMIN_USER_IDS
from telegram_bot.handlers import get_all_handlers
from telegram_bot.handlers.account_handlers import (
    bulk_upload_accounts_file, list_accounts_handler, WAITING_ACCOUNTS_FILE,
    add_account, enter_username, enter_password, enter_email, enter_email_password,
    confirm_add_account, enter_verification_code, cancel_add_account, get_session_stats_handler,
    ENTER_USERNAME, ENTER_PASSWORD, ENTER_EMAIL, ENTER_EMAIL_PASSWORD, CONFIRM_ACCOUNT, ENTER_VERIFICATION_CODE,
    bulk_add_accounts_command, bulk_add_accounts_text
)
from telegram_bot.states import BULK_ADD_ACCOUNTS, WARMING_MENU, WARMING_ACCOUNT_SELECTION, WARMING_SETTINGS
from telegram_bot.handlers.task_handlers import retry_task_callback
from telegram_bot.handlers.profile_handlers import get_profile_handlers, profile_setup_menu
from telegram_bot.handlers.warming_handlers import (
    warming_menu,
    select_warming_account as select_account_for_warming,
    warming_default as start_account_warming,
    warming_status as show_warming_status,
    warming_settings as show_warming_settings
)

logger = logging.getLogger(__name__)

def is_admin(user_id):
    return user_id in ADMIN_USER_IDS

def start_handler(update, context):
    user = update.effective_user

    keyboard = [
        [InlineKeyboardButton("👤 Аккаунты", callback_data='menu_accounts')],
        [InlineKeyboardButton("📝 Задачи", callback_data='menu_tasks')],
        [InlineKeyboardButton("🔄 Прокси", callback_data='menu_proxy')],
        [InlineKeyboardButton("🔥 Прогрев", callback_data='menu_warming')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='menu_help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        f"Привет, {user.first_name}! Я бот для автоматической загрузки контента в Instagram.\n\n"
        f"Выберите раздел из меню ниже или используйте /help для получения списка доступных команд.",
        reply_markup=reply_markup
    )

def get_main_menu_keyboard():
    """Возвращает главное меню"""
    keyboard = [
        [InlineKeyboardButton("👤 Аккаунты", callback_data='menu_accounts')],
        [InlineKeyboardButton("📝 Задачи", callback_data='menu_tasks')],
        [InlineKeyboardButton("🔄 Прокси", callback_data='menu_proxy')],
        [InlineKeyboardButton("🔥 Прогрев", callback_data='menu_warming')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='menu_help')]
    ]
    return InlineKeyboardMarkup(keyboard)

def callback_handler(update, context):
    """ИСПРАВЛЕННЫЙ обработчик для кнопок"""
    query = update.callback_query
    query.answer()

    try:
        # ГЛАВНОЕ МЕНЮ
        if query.data == 'back_to_main' or query.data == 'main_menu':
            keyboard = [
                [InlineKeyboardButton("👤 Аккаунты", callback_data='menu_accounts')],
                [InlineKeyboardButton("📝 Задачи", callback_data='menu_tasks')],
                [InlineKeyboardButton("🔄 Прокси", callback_data='menu_proxy')],
                [InlineKeyboardButton("🔥 Прогрев", callback_data='menu_warming')],
                [InlineKeyboardButton("ℹ️ Помощь", callback_data='menu_help')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "🏠 Главное меню\n\n"
                "Выберите раздел из меню ниже:",
                reply_markup=reply_markup
            )

        # МЕНЮ АККАУНТОВ
        elif query.data == 'menu_accounts' or query.data == 'accounts_menu':
            keyboard = [
                [InlineKeyboardButton("➕ Добавить аккаунт", callback_data='add_account')],
                [InlineKeyboardButton("📥 Массовая загрузка", callback_data='bulk_add_accounts')],
                [InlineKeyboardButton("📋 Список аккаунтов", callback_data='list_accounts')],
                [InlineKeyboardButton("📊 Статистика сессий", callback_data='refresh_session_stats')],
                [InlineKeyboardButton("📤 Загрузить файл", callback_data='upload_accounts')],
                [InlineKeyboardButton("⚙️ Настройка профиля", callback_data='profile_setup')],
                [InlineKeyboardButton("🔙 Главное меню", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "👤 *Меню управления аккаунтами*\n\n"
                "Выберите действие:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        # МЕНЮ ЗАДАЧ
        elif query.data == 'menu_tasks' or query.data == 'tasks_menu':
            keyboard = [
                [InlineKeyboardButton("📤 Опубликовать сейчас", callback_data='publish_now')],
                [InlineKeyboardButton("⏰ Запланировать", callback_data='schedule_publish')],
                [InlineKeyboardButton("📊 Статистика", callback_data='publication_stats')],
                [InlineKeyboardButton("🔙 Главное меню", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "📝 *Меню управления задачами*\n\n"
                "Выберите действие:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        # МЕНЮ ПРОКСИ
        elif query.data == 'menu_proxy' or query.data == 'proxy_menu':
            keyboard = [
                [InlineKeyboardButton("➕ Добавить прокси", callback_data='add_proxy')],
                [InlineKeyboardButton("📋 Список прокси", callback_data='list_proxies')],
                [InlineKeyboardButton("🔄 Распределить", callback_data='distribute_proxies')],
                [InlineKeyboardButton("🔙 Главное меню", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "🔄 *Меню управления прокси*\n\n"
                "Выберите действие:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        # МЕНЮ ПРОГРЕВА
        elif query.data == 'menu_warming' or query.data == 'warming_menu':
            keyboard = [
                [InlineKeyboardButton("🔥 Начать прогрев", callback_data='start_warming')],
                [InlineKeyboardButton("❄️ Остановить прогрев", callback_data='stop_warming')],
                [InlineKeyboardButton("📊 Статус прогрева", callback_data='warming_stats')],
                [InlineKeyboardButton("⚙️ Настройки", callback_data='warming_settings_menu')],
                [InlineKeyboardButton("🔙 Главное меню", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "🔥 *Меню прогрева аккаунтов*\n\n"
                "Выберите действие:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        # МЕНЮ ПОМОЩИ
        elif query.data == 'menu_help':
            help_text = """
*📋 Доступные команды:*

*👤 Аккаунты:*
• /accounts - Меню управления аккаунтами
• /add_account - Добавить новый аккаунт
• /list_accounts - Показать список аккаунтов

*📝 Задачи:*
• /tasks - Меню управления задачами
• /publish_now - Опубликовать контент сейчас

*🔄 Прокси:*
• /proxy - Меню управления прокси
• /add_proxy - Добавить новый прокси

*🔥 Прогрев:*
• /warming - Меню прогрева аккаунтов
• /warm_account - Прогреть аккаунт

*🛠 Общие:*
• /cancel - Отменить текущую операцию
• /help - Показать эту справку
            """

            keyboard = [
                [InlineKeyboardButton("🔙 Главное меню", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                help_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        # ДЕЙСТВИЯ С АККАУНТАМИ
        elif query.data == 'add_account':
            # Переход к добавлению аккаунта
            return add_account(update, context)

        elif query.data == 'bulk_add_accounts':
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='menu_accounts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "📥 *Массовая загрузка аккаунтов*\n\n"
                "Отправьте список аккаунтов в формате:\n"
                "`username:password:email:email_password`\n\n"
                "Каждый аккаунт на новой строке.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            context.user_data['waiting_for_bulk_accounts'] = True
            return BULK_ADD_ACCOUNTS

        elif query.data == 'list_accounts':
            return list_accounts_handler(update, context)

        elif query.data == 'refresh_session_stats':
            return get_session_stats_handler(update, context)

        elif query.data == 'upload_accounts':
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='menu_accounts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "📤 *Загрузка аккаунтов из файла*\n\n"
                "Отправьте TXT файл с аккаунтами в формате:\n"
                "`username:password`\n"
                "или\n"
                "`username:password:email:email_password`\n\n"
                "Каждый аккаунт на новой строке.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data['waiting_for_accounts_file'] = True
            return WAITING_ACCOUNTS_FILE

        elif query.data == 'profile_setup':
            return profile_setup_menu(update, context)

        # ДЕЙСТВИЯ С ПРОГРЕВОМ
        elif query.data == 'start_warming':
            return select_account_for_warming(update, context)

        elif query.data == 'warming_stats':
            return show_warming_status(update, context)

        elif query.data == 'warming_settings_menu':
            return show_warming_settings(update, context)

        elif query.data.startswith('warming_account_'):
            return select_account_for_warming(update, context)

        elif query.data.startswith('warming_default_'):
            return start_account_warming(update, context)

        # ДЕЙСТВИЯ С ЗАДАЧАМИ
        elif query.data == 'publish_now':
            keyboard = [
                [InlineKeyboardButton("📹 Reels", callback_data='publish_type_reel')],
                [InlineKeyboardButton("🖼️ Фото", callback_data='publish_type_post')],
                [InlineKeyboardButton("🧩 Мозаика", callback_data='publish_type_mosaic')],
                [InlineKeyboardButton("🔙 Назад", callback_data='menu_tasks')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "📤 *Выберите тип публикации:*",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        elif query.data == 'schedule_publish':
            query.edit_message_text(
                "⏰ *Запланированная публикация*\n\n"
                "Функция находится в разработке.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data='menu_tasks')]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )

        elif query.data == 'publication_stats':
            query.edit_message_text(
                "📊 *Статистика публикаций*\n\n"
                "Функция находится в разработке.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data='menu_tasks')]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )

        # ДЕЙСТВИЯ С ПРОКСИ
        elif query.data == 'add_proxy':
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='menu_proxy')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "➕ *Добавление прокси*\n\n"
                "Введите данные прокси в формате:\n"
                "`протокол://логин:пароль@хост:порт`\n\n"
                "Пример:\n"
                "`http://user:pass@1.2.3.4:8080`\n"
                "или без авторизации:\n"
                "`http://1.2.3.4:8080`",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        elif query.data == 'list_proxies':
            query.edit_message_text(
                "📋 *Список прокси*\n\n"
                "Функция находится в разработке.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data='menu_proxy')]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )

        elif query.data == 'distribute_proxies':
            query.edit_message_text(
                "🔄 *Распределение прокси*\n\n"
                "Функция находится в разработке.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data='menu_proxy')]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )

        # НЕИЗВЕСТНЫЕ CALLBACK DATA
        else:
            logger.warning(f"Неизвестный callback_data: {query.data}")
            query.edit_message_text(
                "❌ Неизвестная команда. Возвращаюсь в главное меню.",
                reply_markup=get_main_menu_keyboard()
            )

    except Exception as e:
        logger.error(f"Ошибка в callback_handler: {e}")
        try:
            query.edit_message_text(
                "❌ Произошла ошибка. Возвращаюсь в главное меню.",
                reply_markup=get_main_menu_keyboard()
            )
        except Exception as inner_e:
            logger.error(f"Не удалось отправить сообщение об ошибке: {inner_e}")

def text_handler(update, context):
    """Обработчик текстовых сообщений"""
    keyboard = [
        [InlineKeyboardButton("👤 Аккаунты", callback_data='menu_accounts')],
        [InlineKeyboardButton("📝 Задачи", callback_data='menu_tasks')],
        [InlineKeyboardButton("🔄 Прокси", callback_data='menu_proxy')],
        [InlineKeyboardButton("🔥 Прогрев", callback_data='menu_warming')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='menu_help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "Я понимаю только команды. Используйте кнопки меню или команды:",
        reply_markup=reply_markup
    )

def help_handler(update, context):
    """Обработчик команды /help"""
    help_text = """
*📋 Доступные команды:*

*👤 Аккаунты:*
• /accounts - Меню управления аккаунтами
• /add_account - Добавить новый аккаунт
• /list_accounts - Показать список аккаунтов

*📝 Задачи:*
• /tasks - Меню управления задачами
• /publish_now - Опубликовать контент сейчас

*🔄 Прокси:*
• /proxy - Меню управления прокси
• /add_proxy - Добавить новый прокси

*🔥 Прогрев:*
• /warming - Меню прогрева аккаунтов
• /warm_account - Прогреть аккаунт

*🛠 Общие:*
• /cancel - Отменить текущую операцию
• /help - Показать эту справку
    """

    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

def cancel_handler(update, context):
    """Обработчик команды /cancel"""
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "❌ Операция отменена.",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

def error_handler(update, context):
    """Обрабатывает ошибки"""
    if "Query is too old" in str(context.error):
        logger.warning(f"Устаревший запрос: {update}")
        return

    logger.error(f"Ошибка при обработке обновления {update}: {context.error}")

    if update and update.effective_chat:
        try:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Произошла ошибка. Попробуйте еще раз.",
                reply_markup=get_main_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке: {e}")

def setup_bot(updater):
    """ИСПРАВЛЕННАЯ настройка бота"""
    dp = updater.dispatcher

    # Основные обработчики
    dp.add_handler(CommandHandler("start", start_handler))
    dp.add_handler(CommandHandler("help", help_handler))
    dp.add_handler(CommandHandler("cancel", cancel_handler))

    # Команды для быстрого доступа
    dp.add_handler(CommandHandler("accounts", lambda u, c: callback_handler_command(u, c, 'menu_accounts')))
    dp.add_handler(CommandHandler("tasks", lambda u, c: callback_handler_command(u, c, 'menu_tasks')))
    dp.add_handler(CommandHandler("proxy", lambda u, c: callback_handler_command(u, c, 'menu_proxy')))
    dp.add_handler(CommandHandler("warming", lambda u, c: callback_handler_command(u, c, 'menu_warming')))

    # ConversationHandler для добавления аккаунта
    add_account_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("add_account", add_account),
            CallbackQueryHandler(add_account, pattern='^add_account$')
        ],
        states={
            ENTER_USERNAME: [MessageHandler(Filters.text & ~Filters.command, enter_username)],
            ENTER_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, enter_password)],
            ENTER_EMAIL: [MessageHandler(Filters.text & ~Filters.command, enter_email)],
            ENTER_EMAIL_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, enter_email_password)],
            CONFIRM_ACCOUNT: [CallbackQueryHandler(confirm_add_account, pattern='^confirm_add_account$')],
            ENTER_VERIFICATION_CODE: [MessageHandler(Filters.text & ~Filters.command, enter_verification_code)]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_add_account, pattern='^cancel_add_account$'),
            CallbackQueryHandler(lambda u, c: callback_handler_command(u, c, 'menu_accounts'), pattern='^menu_accounts$'),
            CommandHandler("cancel", cancel_handler)
        ]
    )

    dp.add_handler(add_account_conv_handler)

    # Регистрируем все остальные обработчики
    for handler in get_all_handlers():
        dp.add_handler(handler)

    for handler in get_profile_handlers():
        dp.add_handler(handler)

    for handler in get_warming_handlers():
        dp.add_handler(handler)

    # Обработчик файлов с аккаунтами
    dp.add_handler(MessageHandler(
        Filters.document.file_extension("txt"),
        lambda update, context: bulk_upload_accounts_file(update, context) if context.user_data.get('waiting_for_accounts_file', False) else None
    ))

    # Основной обработчик callback-запросов
    dp.add_handler(CallbackQueryHandler(callback_handler))

    # Обработчик для повтора задач
    dp.add_handler(CallbackQueryHandler(retry_task_callback, pattern=r'^retry_task_\d+$'))

    # Обработчик текстовых сообщений
    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command,
        lambda update, context: bulk_add_accounts_text(update, context) if context.user_data.get('waiting_for_bulk_accounts', False) else text_handler(update, context)
    ))

    # Обработчик ошибок
    dp.add_error_handler(error_handler)

    logger.info("Бот настроен с исправленной навигацией")

def callback_handler_command(update, context, callback_data):
    """Вспомогательная функция для обработки команд как callback"""
    # Создаем фиктивный callback_query
    class FakeQuery:
        def __init__(self, data):
            self.data = data
        def answer(self):
            pass
        def edit_message_text(self, *args, **kwargs):
            update.message.reply_text(*args, **kwargs)

    # Временно заменяем callback_query
    original_query = getattr(update, 'callback_query', None)
    update.callback_query = FakeQuery(callback_data)
    
    try:
        callback_handler(update, context)
    finally:
        update.callback_query = original_query
