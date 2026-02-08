"""Admin handler for broadcast messages"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
)
from src.bot.admin.common import admin_required, db

# Broadcast states
BROADCAST_SELECT_AUDIENCE, BROADCAST_CONFIRM = 20, 21


@admin_required
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast - send message to all users. Usage: /broadcast <message>"""
    # Get text after /broadcast command (supports multiline)
    full_text = update.message.text
    # Remove "/broadcast" or "/broadcast " prefix
    if full_text.startswith('/broadcast '):
        message_text = full_text[11:]  # len('/broadcast ') = 11
    elif full_text.startswith('/broadcast\n'):
        message_text = full_text[11:]  # len('/broadcast\n') = 11
    else:
        message_text = None

    if not message_text or not message_text.strip():
        await update.message.reply_text(
            "📢 *Рассылка сообщений*\n\n"
            "Использование: `/broadcast <текст сообщения>`\n\n"
            "Поддерживается многострочный текст.\n\n"
            "Пример:\n"
            "`/broadcast Привет! Напоминаю, что вы можете настроить подписки в /settings`",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    context.user_data['broadcast_message'] = message_text

    # Get counts
    all_users = db.get_all_users()
    users_without_subs = [u for u in all_users if not db.get_user_subscriptions(u['user_id'])]

    keyboard = [
        [InlineKeyboardButton(f"👥 Всем ({len(all_users)})", callback_data='broadcast_audience_all')],
        [InlineKeyboardButton(f"📭 Только без подписок ({len(users_without_subs)})", callback_data='broadcast_audience_nosubs')],
        [InlineKeyboardButton("❌ Отмена", callback_data='broadcast_cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Show preview without Markdown to avoid parsing issues with user text
    await update.message.reply_text(
        f"📢 Рассылка\n\n"
        f"Сообщение:\n{message_text}\n\n"
        f"Кому отправить?",
        reply_markup=reply_markup
    )
    return BROADCAST_SELECT_AUDIENCE


async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast audience selection and confirmation"""
    query = update.callback_query
    await query.answer()

    if query.data == 'broadcast_cancel':
        await query.edit_message_text("❌ Рассылка отменена")
        return ConversationHandler.END

    # Audience selection
    if query.data == 'broadcast_audience_all':
        context.user_data['broadcast_audience'] = 'all'
        all_users = db.get_all_users()
        count = len(all_users)
    elif query.data == 'broadcast_audience_nosubs':
        context.user_data['broadcast_audience'] = 'nosubs'
        all_users = db.get_all_users()
        users_without_subs = [u for u in all_users if not db.get_user_subscriptions(u['user_id'])]
        count = len(users_without_subs)
    else:
        count = None

    if count is not None:
        message_text = context.user_data.get('broadcast_message')
        keyboard = [
            [InlineKeyboardButton("✅ Да, отправить", callback_data='broadcast_confirm')],
            [InlineKeyboardButton("❌ Отмена", callback_data='broadcast_cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"📢 Подтверждение\n\n"
            f"Сообщение:\n{message_text}\n\n"
            f"Получателей: {count}\n\n"
            f"Отправить?",
            reply_markup=reply_markup
        )
        return BROADCAST_CONFIRM

    if query.data == 'broadcast_confirm':
        message_text = context.user_data.get('broadcast_message')
        audience = context.user_data.get('broadcast_audience', 'all')

        if not message_text:
            await query.edit_message_text("❌ Ошибка: сообщение не найдено")
            return ConversationHandler.END

        await query.edit_message_text("📤 Отправка сообщений...")

        # Get users based on audience
        all_users = db.get_all_users()
        if audience == 'nosubs':
            users_to_send = [u for u in all_users if not db.get_user_subscriptions(u['user_id'])]
        else:
            users_to_send = all_users

        sent = 0
        failed = 0

        for user in users_to_send:
            try:
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text=message_text
                )
                sent += 1
            except Exception:
                failed += 1

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"✅ *Рассылка завершена*\n\n"
                 f"Отправлено: {sent}\n"
                 f"Ошибок: {failed}",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    return BROADCAST_CONFIRM


def get_broadcast_handler():
    """Get handler for /broadcast command"""
    return ConversationHandler(
        entry_points=[CommandHandler('broadcast', broadcast_command)],
        states={
            BROADCAST_SELECT_AUDIENCE: [CallbackQueryHandler(broadcast_callback, pattern='^broadcast_')],
            BROADCAST_CONFIRM: [CallbackQueryHandler(broadcast_callback, pattern='^broadcast_')],
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
    )
