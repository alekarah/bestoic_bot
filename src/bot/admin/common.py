"""Общие утилиты для админских обработчиков"""

import functools
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from src.database.models import Database
import config

db = Database()


def admin_required(func):
    """Декоратор для ограничения доступа только администраторам"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in config.ADMIN_USER_IDS:
            if update.message:
                await update.message.reply_text("⛔️ У вас нет доступа к этой команде.")
            elif update.callback_query:
                await update.callback_query.answer("⛔️ У вас нет доступа к этой команде.", show_alert=True)
            return ConversationHandler.END
        return await func(update, context)
    return wrapper
