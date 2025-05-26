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
#from instagram.clip_upload_patch import *


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

def help_handler(update, context):
    help_text = """
*Доступные команды:*

*Аккаунты:*
/accounts - Меню управления аккаунтами
/add_account - Добавить новый аккаунт Instagram
/upload_accounts - Загрузить несколько аккаунтов из файла
/list_accounts - Показать список аккаунтов
/profile_setup - Настроить профиль аккаунта

*Задачи:*
/tasks - Меню управления задачами
/publish_now - Опубликовать контент сейчас
/schedule_publish - Запланировать публикацию

*Прокси:*
/proxy - Меню управления прокси
/add_proxy - Добавить новый прокси
/distribute_proxies - Распределить прокси по аккаунтам
/list_proxies - Показать список прокси

*Прогрев аккаунтов:*
/warming - Меню прогрева аккаунтов
/warm_account - Прогреть аккаунт
/warming_stats - Статистика прогрева

/cancel - Отменить текущую операцию
    """

    keyboard = [
    [InlineKeyboardButton("👤 Аккаунты", callback_data='menu_accounts')],
    [InlineKeyboardButton("📝 Задачи", callback_data='menu_tasks')],
    [InlineKeyboardButton("🔄 Прокси", callback_data='menu_proxy')],
    [InlineKeyboardButton("🔥 Прогрев", callback_data='menu_warming')],
    [InlineKeyboardButton("🔙 Главное меню", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

def cancel_handler(update, context):
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
    "Операция отменена.",
    reply_markup=reply_markup
    )
    return ConversationHandler.END

def callback_handler(update, context):
    query = update.callback_query
    query.answer()

    try:
        if query.data == 'menu_accounts':
            keyboard = [
            [InlineKeyboardButton("➕ Добавить аккаунт", callback_data='add_account')],
            [InlineKeyboardButton("📥 Массовая загрузка аккаунтов", callback_data='bulk_add_accounts')],
            [InlineKeyboardButton("📋 Список аккаунтов", callback_data='list_accounts')],
            [InlineKeyboardButton("📊 Статистика сессий", callback_data='refresh_session_stats')],
            [InlineKeyboardButton("📤 Загрузить аккаунты", callback_data='upload_accounts')],
            [InlineKeyboardButton("⚙️ Настройка профиля", callback_data='profile_setup')],
            [InlineKeyboardButton("🔥 Прогрев аккаунтов", callback_data='warming_menu')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
            text="🔧 *Меню управления аккаунтами*\n\n"
            "Выберите действие из списка ниже:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
            )

        elif query.data == 'menu_tasks':
            keyboard = [
            [InlineKeyboardButton("📤 Опубликовать сейчас", callback_data='publish_now')],
            [InlineKeyboardButton("⏰ Запланировать публикацию", callback_data='schedule_publish')],
            [InlineKeyboardButton("📊 Статистика публикаций", callback_data='publication_stats')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
            text="📝 *Меню управления задачами*\n\n"
            "Выберите действие из списка ниже:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
            )

        elif query.data == 'menu_proxy':
            keyboard = [
            [InlineKeyboardButton("➕ Добавить прокси", callback_data='add_proxy')],
            [InlineKeyboardButton("📋 Список прокси", callback_data='list_proxies')],
            [InlineKeyboardButton("🔄 Распределить прокси", callback_data='distribute_proxies')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
            text="🔄 *Меню управления прокси*\n\n"
            "Выберите действие из списка ниже:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
            )

        elif query.data == 'menu_warming':
            keyboard = [
            [InlineKeyboardButton("🔥 Прогреть аккаунт", callback_data='warm_account')],
            [InlineKeyboardButton("📊 Статистика прогрева", callback_data='warming_stats')],
            [InlineKeyboardButton("⚙️ Настройки прогрева", callback_data='warming_settings')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
            text="🔥 *Меню прогрева аккаунтов*\n\n"
            "Выберите действие из списка ниже:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
            )

        elif query.data == 'menu_help':
            help_text = """
*Доступные команды:*

*Аккаунты:*
/accounts - Меню управления аккаунтами
/add_account - Добавить новый аккаунт Instagram
/upload_accounts - Загрузить несколько аккаунтов из файла
/list_accounts - Показать список аккаунтов
/profile_setup - Настроить профиль аккаунта

*Задачи:*
/tasks - Меню управления задачами
/publish_now - Опубликовать контент сейчас
/schedule_publish - Запланировать публикацию

*Прокси:*
/proxy - Меню управления прокси
/add_proxy - Добавить новый прокси
/distribute_proxies - Распределить прокси по аккаунтам
/list_proxies - Показать список прокси

*Прогрев аккаунтов:*
/warming - Меню прогрева аккаунтов
/warm_account - Прогреть аккаунт
/warming_stats - Статистика прогрева

/cancel - Отменить текущую операцию
            """

            keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
            text=help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
            )

        elif query.data == 'back_to_main':
            keyboard = [
            [InlineKeyboardButton("👤 Аккаунты", callback_data='menu_accounts')],
            [InlineKeyboardButton("📝 Задачи", callback_data='menu_tasks')],
            [InlineKeyboardButton("🔄 Прокси", callback_data='menu_proxy')],
            [InlineKeyboardButton("🔥 Прогрев", callback_data='menu_warming')],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data='menu_help')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
            text="Главное меню бота для автоматической загрузки контента в Instagram.\n\n"
            "Выберите раздел из меню ниже или используйте /help для получения списка доступных команд.",
            reply_markup=reply_markup
            )

        # Обработчики для прогрева аккаунтов
        elif query.data == 'warm_account':
            return select_account_for_warming(update, context)
        elif query.data == 'warming_stats':
            return show_warming_status(update, context)
        elif query.data == 'warming_settings':
            return show_warming_settings(update, context)
        elif query.data.startswith('warming_account_'):
            return select_account_for_warming(update, context)
        elif query.data.startswith('warming_default_'):
            return start_account_warming(update, context)
        elif query.data == 'warming_menu':
            return warming_menu(update, context)

        elif query.data == 'upload_accounts':
            # Отправляем новое сообщение вместо редактирования текущего
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='menu_accounts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
            "Отправьте TXT файл с аккаунтами Instagram.\n\n"
            "Формат файла:\n"
            "username:password\n"
            "username:password\n"
            "...\n\n"
            "Каждый аккаунт должен быть на новой строке в формате username:password",
            reply_markup=reply_markup
            )

            # Устанавливаем состояние для ожидания файла
            context.user_data['waiting_for_accounts_file'] = True
            return WAITING_ACCOUNTS_FILE

        elif query.data == 'list_accounts':
            # Вызываем обработчик списка аккаунтов
            list_accounts_handler(update, context)

        elif query.data == 'refresh_session_stats':
            # Вызываем обработчик статистики сессий
            get_session_stats_handler(update, context)

        elif query.data == 'bulk_add_accounts':
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='menu_accounts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
            "📥 *Массовая загрузка аккаунтов Instagram*\n\n"
            "Отправьте список аккаунтов в формате:\n"
            "`username:password:email:email_password`\n\n"
            "Каждый аккаунт должен быть на новой строке.\n\n"
            "Пример:\n"
            "`user1:pass1:email1@example.com:email_pass1`\n"
            "`user2:pass2:email2@example.com:email_pass2`\n\n"
            "Или используйте команду:\n"
            "`/bulk_add_accounts`\n"
            "и укажите список аккаунтов после команды.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
            )

            # Устанавливаем состояние для ожидания списка аккаунтов
            context.user_data['waiting_for_bulk_accounts'] = True
            return BULK_ADD_ACCOUNTS

        elif query.data == 'profile_setup':
            # Вызываем обработчик настройки профиля
            return profile_setup_menu(update, context)

        elif query.data in ['publication_stats', 'add_proxy', 'list_proxies', 'distribute_proxies']:
            query.edit_message_text(
            text=f"Функция '{query.data}' находится в разработке.\n\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]])
            )

        else:
            # Другие callback_data обрабатываются в соответствующих обработчиках
            pass
    except Exception as e:
        logger.error(f"Ошибка в callback_handler: {e}")
        try:
            query.edit_message_text(
                "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]])
            )
        except Exception as inner_e:
            logger.error(f"Не удалось отправить сообщение об ошибке: {inner_e}")

def text_handler(update, context):
    keyboard = [
    [InlineKeyboardButton("👤 Аккаунты", callback_data='menu_accounts')],
    [InlineKeyboardButton("📝 Задачи", callback_data='menu_tasks')],
    [InlineKeyboardButton("🔄 Прокси", callback_data='menu_proxy')],
    [InlineKeyboardButton("🔥 Прогрев", callback_data='menu_warming')],
    [InlineKeyboardButton("ℹ️ Помощь", callback_data='menu_help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
    "Я понимаю только команды. Используйте /help для получения списка доступных команд или выберите раздел из меню ниже:",
    reply_markup=reply_markup
    )

def error_handler(update, context):
    """Обрабатывает ошибки"""
    # Проверяем, является ли ошибка "Query is too old"
    if "Query is too old" in str(context.error):
        logger.warning(f"Устаревший запрос: {update}")
        return  # Просто игнорируем эту ошибку

    logger.error(f"Ошибка при обработке обновления {update}: {context.error}")

    if update and update.effective_chat:
        try:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке: {e}")

def setup_bot(updater):
    dp = updater.dispatcher

    # Основные обработчики
    dp.add_handler(CommandHandler("start", start_handler))
    dp.add_handler(CommandHandler("help", help_handler))
    dp.add_handler(CommandHandler("cancel", cancel_handler))

    # Регистрируем ConversationHandler для добавления аккаунта
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
            # Удалите строку с BULK_ADD_ACCOUNTS
        },
        fallbacks=[
            CallbackQueryHandler(cancel_add_account, pattern='^cancel_add_account$'),
            CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern='^menu_accounts$'),
            CommandHandler("cancel", cancel_handler)
        ]
    )

    dp.add_handler(add_account_conv_handler)

    # Регистрируем ConversationHandler для прогрева аккаунтов
    warming_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("warming", warming_menu),
            CommandHandler("warm_account", select_account_for_warming),
            CallbackQueryHandler(warming_menu, pattern='^menu_warming$'),
            CallbackQueryHandler(select_account_for_warming, pattern='^warm_account$')
        ],
        states={
            WARMING_MENU: [
                CallbackQueryHandler(select_account_for_warming, pattern='^warm_account$'),
                CallbackQueryHandler(show_warming_status, pattern='^warming_stats$'),
                CallbackQueryHandler(show_warming_settings, pattern='^warming_settings$'),
                CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern='^back_to_main$')
            ],
            WARMING_ACCOUNT_SELECTION: [
                CallbackQueryHandler(start_account_warming, pattern='^warm_account_'),
                CallbackQueryHandler(warming_menu, pattern='^back_to_warming_menu$')
            ],
            WARMING_SETTINGS: [
                CallbackQueryHandler(warming_menu, pattern='^back_to_warming_menu$')
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_handler),
            CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern='^back_to_main$')
        ]
    )

    dp.add_handler(warming_conv_handler)

    # Добавляем обработчик для массовой загрузки аккаунтов
    dp.add_handler(CommandHandler("bulk_add_accounts", bulk_add_accounts_command, pass_args=True))

    # Добавляем все обработчики из модулей
    for handler in get_all_handlers():
        dp.add_handler(handler)

    # Добавляем обработчики для настройки профиля
    for handler in get_profile_handlers():
        dp.add_handler(handler)

    # Добавляем обработчики для прогрева
    for handler in get_warming_handlers():
        dp.add_handler(handler)

    # Добавляем обработчик для файлов с аккаунтами
    dp.add_handler(MessageHandler(
        Filters.document.file_extension("txt"),
        lambda update, context: bulk_upload_accounts_file(update, context) if context.user_data.get('waiting_for_accounts_file', False) else None
    ))

    # Обработчик callback-запросов
    dp.add_handler(CallbackQueryHandler(callback_handler))

    # Добавляем обработчик для статистики сессий
    dp.add_handler(CallbackQueryHandler(get_session_stats_handler, pattern='^refresh_session_stats$'))

    # Добавляем обработчик для кодов подтверждения
    from telegram_bot.handlers.account_handlers import verification_code_handler
    dp.add_handler(MessageHandler(
        Filters.regex(r'^\d{6}$') & ~Filters.command,
        verification_code_handler
    ))

    # Добавляем обработчик для повтора задач
    dp.add_handler(CallbackQueryHandler(retry_task_callback, pattern=r'^retry_task_\d+$'))

    # Обработчик текстовых сообщений (должен быть после обработчика кодов)
    # Добавляем обработчик для массовой загрузки аккаунтов через текст
    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command,
        lambda update, context: bulk_add_accounts_text(update, context) if context.user_data.get('waiting_for_bulk_accounts', False) else text_handler(update, context)
    ))

    dp.add_handler(CommandHandler("warming", lambda update, context: warming_menu(update, context)))

    # Обработчик ошибок
    dp.add_error_handler(error_handler)

    logger.info("Бот настроен и готов к работе")