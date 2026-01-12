import logging
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from src.bot.handlers import start_command, help_command, settings_command, quote_command, button_callback
from src.bot.admin_handlers import get_add_quote_handler, get_delete_quote_handler, get_edit_quote_handler
from src.bot.scheduler import setup_scheduler
import config


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    """Set up bot menu commands after initialization"""
    bot_commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("quote", "Получить случайную цитату"),
        BotCommand("settings", "Настроить категорию и время"),
        BotCommand("help", "Помощь и информация"),
    ]

    # Admin commands (shown only to admin)
    admin_commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("quote", "Получить случайную цитату"),
        BotCommand("settings", "Настроить категорию и время"),
        BotCommand("help", "Помощь и информация"),
        BotCommand("admin_add", "➕ Добавить цитату"),
        BotCommand("admin_edit", "✏️ Редактировать цитату"),
        BotCommand("admin_delete", "🗑 Удалить цитату"),
    ]

    # Set commands for all users
    await application.bot.set_my_commands(bot_commands)

    # Set admin commands for admin user
    from telegram import BotCommandScopeChat
    await application.bot.set_my_commands(
        admin_commands,
        scope=BotCommandScopeChat(chat_id=config.ADMIN_USER_ID)
    )

    logger.info("Bot menu commands set successfully!")


def main():
    """Start the bot"""
    # Validate configuration
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Please check your .env file.")
        return

    # Create application
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("quote", quote_command))

    # Register admin conversation handlers (must be before general callback handler)
    application.add_handler(get_add_quote_handler())
    application.add_handler(get_edit_quote_handler())
    application.add_handler(get_delete_quote_handler())

    # Register callback handler for settings (with pattern to avoid catching admin callbacks)
    application.add_handler(CallbackQueryHandler(button_callback, pattern='^(settings_|category_|time_)'))

    # Setup scheduler
    scheduler = setup_scheduler(application)

    logger.info("Bot started successfully!")
    logger.info("Scheduler is active. Quotes will be sent at:")
    logger.info("  - Morning: 8:00")
    logger.info("  - Day: 14:00")
    logger.info("  - Evening: 20:00")

    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
