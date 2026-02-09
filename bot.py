"""Точка входа Telegram бота — инициализация, регистрация обработчиков, запуск."""

import logging
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from src.bot.handlers import start_command, help_command, settings_command, quote_command, button_callback, favorites_command, favorites_callback
from src.bot.admin import get_add_quote_handler, get_delete_quote_handler, get_edit_quote_handler, get_admin_users_handler, get_admin_quote_stats_handler, get_broadcast_handler
from src.bot.library_handlers import books_command, library_callback
from src.bot.scheduler import setup_scheduler
import config


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    """Настройка команд меню бота после инициализации"""
    bot_commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("settings", "Настроить подписки"),
        BotCommand("favorites", "Мои избранные цитаты"),
        BotCommand("books", "Библиотека книг"),
        BotCommand("quote", "Получить случайную цитату"),
        BotCommand("help", "Помощь и информация"),
    ]

    # Админские команды (видны только администраторам)
    admin_commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("settings", "Настроить подписки"),
        BotCommand("favorites", "Мои избранные цитаты"),
        BotCommand("books", "Библиотека книг"),
        BotCommand("quote", "Получить случайную цитату"),
        BotCommand("help", "Помощь и информация"),
        BotCommand("admin_add", "➕ Добавить цитату"),
        BotCommand("admin_edit", "✏️ Редактировать цитату"),
        BotCommand("admin_delete", "🗑 Удалить цитату"),
        BotCommand("admin_users", "👥 Статистика пользователей"),
        BotCommand("admin_quote_stats", "📊 Статистика по избранному"),
        BotCommand("broadcast", "📢 Рассылка сообщений"),
    ]

    # Устанавливаем команды для всех пользователей
    await application.bot.set_my_commands(bot_commands)

    # Устанавливаем админские команды для каждого администратора
    from telegram import BotCommandScopeChat
    for admin_id in config.ADMIN_USER_IDS:
        await application.bot.set_my_commands(
            admin_commands,
            scope=BotCommandScopeChat(chat_id=admin_id)
        )

    logger.info(f"Bot menu commands set successfully! Admin commands for {len(config.ADMIN_USER_IDS)} admin(s)")


def main():
    """Запуск бота"""
    # Проверка конфигурации
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Please check your .env file.")
        return

    # Создаём приложение
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("quote", quote_command))
    application.add_handler(CommandHandler("favorites", favorites_command))
    application.add_handler(CommandHandler("books", books_command))

    # Регистрируем админские обработчики диалогов (должны быть до общего callback обработчика)
    application.add_handler(get_add_quote_handler())
    application.add_handler(get_delete_quote_handler())
    application.add_handler(get_edit_quote_handler())
    application.add_handler(get_admin_users_handler())
    application.add_handler(get_admin_quote_stats_handler())
    application.add_handler(get_broadcast_handler())

    # Регистрируем callback обработчик для настроек и подписок (с паттерном, чтобы не перехватывать админские callback-и)
    application.add_handler(CallbackQueryHandler(button_callback, pattern='^(open_settings|add_sub_|remove_sub_|change_time_|select_time_|cancel_subscription)'))

    # Регистрируем callback обработчик для избранного
    application.add_handler(CallbackQueryHandler(favorites_callback, pattern='^(fav_|unfav_|favpage_|favdel_)'))

    # Регистрируем callback обработчик для библиотеки
    application.add_handler(CallbackQueryHandler(library_callback, pattern='^lib_'))

    # Настраиваем планировщик
    scheduler = setup_scheduler(application)

    logger.info("Bot started successfully!")
    logger.info("Scheduler is active. Quotes will be sent at:")
    logger.info("  - Morning: 8:00")
    logger.info("  - Day: 14:00")
    logger.info("  - Evening: 20:00")

    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
