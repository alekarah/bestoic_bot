"""Admin handlers for Telegram bot quote management"""

import functools
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from src.database.models import Database
import config

db = Database()

# Conversation states
(ADD_TEXT, ADD_AUTHOR, ADD_SOURCE,
 EDIT_SEARCH, EDIT_SELECT, EDIT_FIELD, EDIT_VALUE,
 DELETE_SEARCH, DELETE_CONFIRM) = range(9)


def admin_required(func):
    """Decorator to restrict access to admin only"""
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


# ============== ADD QUOTE ==============

@admin_required
async def admin_add_quote_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding a new quote"""
    await update.message.reply_text(
        "📝 Добавление новой цитаты\n\n"
        "Отправьте текст цитаты (без атрибуции).\n\n"
        "/cancel - отменить"
    )
    return ADD_TEXT


@admin_required
async def admin_add_quote_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive quote text and ask for author"""
    text = update.message.text.strip()

    # Check for duplicates
    existing = db.find_exact_duplicate(text)
    if existing:
        await update.message.reply_text(
            f"⚠️ Эта цитата уже существует!\n\n"
            f"ID: {existing['id']}\n"
            f"Категория: {existing['category']}\n"
            f"Книга: {existing['title'] or 'Ручная цитата'}\n\n"
            "Добавление отменено."
        )
        return ConversationHandler.END

    # Store text for later
    context.user_data['quote_text'] = text

    await update.message.reply_text(
        "👤 Введите автора цитаты:\n\n"
        "Например: Марк Аврелий\n\n"
        "/cancel - отменить"
    )
    return ADD_AUTHOR


@admin_required
async def admin_add_quote_author(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive author and ask for source"""
    author = update.message.text.strip()
    context.user_data['quote_author'] = author

    await update.message.reply_text(
        "📖 Введите источник (книгу):\n\n"
        "Например: Размышления\n\n"
        "Отправьте - чтобы пропустить\n"
        "/cancel - отменить"
    )
    return ADD_SOURCE


@admin_required
async def admin_add_quote_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive source and save the quote"""
    source = update.message.text.strip()
    if source == '-':
        source = None

    quote_text = context.user_data.get('quote_text')
    quote_author = context.user_data.get('quote_author')
    quote_source = source

    # Get or create manual quotes book for Telegram
    manual_book_id = db.get_or_create_manual_book(source='Telegram')

    # Add quote to database
    quote_id = db.add_quote(
        text=quote_text,
        category='quotes',
        book_id=manual_book_id,
        quote_author=quote_author,
        quote_source=quote_source
    )

    # Build confirmation message
    attr_parts = []
    if quote_author:
        attr_parts.append(f"Автор: {quote_author}")
    if quote_source:
        attr_parts.append(f"Источник: {quote_source}")
    attr_info = "\n📌 " + " / ".join(attr_parts) if attr_parts else ""

    preview = quote_text[:200] + "..." if len(quote_text) > 200 else quote_text

    await update.message.reply_text(
        f"✅ Цитата добавлена!\n\n"
        f"ID: {quote_id}\n"
        f"Категория: Цитаты{attr_info}\n\n"
        f"💬 {preview}"
    )

    context.user_data.clear()
    return ConversationHandler.END


@admin_required
async def admin_add_quote_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection and save quote"""
    query = update.callback_query
    await query.answer()

    if query.data == 'add_cat_cancel':
        await query.edit_message_text("❌ Добавление цитаты отменено.")
        return ConversationHandler.END

    category = query.data.replace('add_cat_', '')

    # Get or create manual quotes book for Telegram
    manual_book_id = db.get_or_create_manual_book(source='Telegram')

    # Add quote to database
    quote_id = db.add_quote(
        text=context.user_data['quote_text'],
        category=category,
        book_id=manual_book_id,
        quote_author=context.user_data.get('quote_author'),
        quote_source=context.user_data.get('quote_source')
    )

    category_name = config.CATEGORIES.get(category, category)
    await query.edit_message_text(
        f"✅ Цитата добавлена!\n\n"
        f"ID: {quote_id}\n"
        f"Категория: {category_name}"
    )

    # Clear context
    context.user_data.clear()
    return ConversationHandler.END


# ============== DELETE QUOTE ==============

@admin_required
async def admin_delete_quote_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start deleting a quote"""
    await update.message.reply_text(
        "🗑 Удаление цитаты\n\n"
        "Отправьте:\n"
        "• ID цитаты (например: 123)\n"
        "• или часть текста цитаты для поиска\n\n"
        "/cancel - отменить"
    )
    return DELETE_SEARCH


@admin_required
async def admin_delete_quote_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search for quote to delete"""
    search = update.message.text.strip()

    # Try as ID first
    if search.isdigit():
        quote_id = int(search)
        quotes = db.get_all_quotes()
        quote = next((q for q in quotes if q['id'] == quote_id), None)

        if not quote:
            await update.message.reply_text(
                f"❌ Цитата с ID {quote_id} не найдена.\n\n"
                "Попробуйте снова или /cancel для отмены."
            )
            return DELETE_SEARCH

        matching_quotes = [quote]
    else:
        # Search by text
        quotes = db.get_all_quotes()
        matching_quotes = [q for q in quotes if search.lower() in q['text'].lower()]

        if not matching_quotes:
            await update.message.reply_text(
                "❌ Цитаты не найдены.\n\n"
                "Попробуйте другой запрос или /cancel для отмены."
            )
            return DELETE_SEARCH

        if len(matching_quotes) > 10:
            await update.message.reply_text(
                f"⚠️ Найдено {len(matching_quotes)} цитат.\n"
                "Уточните запрос для более точного поиска."
            )
            return DELETE_SEARCH

    # Store matches
    context.user_data['delete_quotes'] = matching_quotes

    if len(matching_quotes) == 1:
        # Show single quote for confirmation
        quote = matching_quotes[0]
        preview = quote['text'][:300] + "..." if len(quote['text']) > 300 else quote['text']

        keyboard = [
            [
                InlineKeyboardButton("✅ Да, удалить", callback_data=f'del_confirm_{quote["id"]}'),
                InlineKeyboardButton("❌ Отменить", callback_data='del_cancel')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        category_name = config.CATEGORIES.get(quote['category'], quote['category'])
        book_info = f"📚 Книга: {quote['title']}\n" if quote['title'] else ""

        # Attribution info
        attr_info = ""
        if quote['quote_author'] or quote['quote_source']:
            parts = []
            if quote['quote_author']:
                parts.append(f"Автор: {quote['quote_author']}")
            if quote['quote_source']:
                parts.append(f"Источник: {quote['quote_source']}")
            attr_info = "📌 Атрибуция:\n" + "\n".join(parts) + "\n\n"

        await update.message.reply_text(
            f"📋 Найдена цитата:\n\n"
            f"ID: {quote['id']}\n"
            f"Категория: {category_name}\n"
            f"{book_info}"
            f"{attr_info}"
            f"{preview}\n\n"
            f"Удалить эту цитату?",
            reply_markup=reply_markup
        )
        return DELETE_CONFIRM
    else:
        # Show multiple options
        keyboard = []
        for q in matching_quotes[:10]:
            short_text = q['text'][:40] + "..." if len(q['text']) > 40 else q['text']
            category_emoji = "📅" if q['category'] == 'daily' else "💭"
            category_short = "Daily" if q['category'] == 'daily' else "Quotes"
            keyboard.append([
                InlineKeyboardButton(
                    f"ID:{q['id']} {category_emoji}{category_short} - {short_text}",
                    callback_data=f'del_select_{q["id"]}'
                )
            ])
        keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data='del_cancel')])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"📋 Найдено {len(matching_quotes)} цитат.\n"
            f"Выберите цитату для удаления:",
            reply_markup=reply_markup
        )
        return DELETE_CONFIRM


@admin_required
async def admin_delete_quote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle delete confirmation callback"""
    query = update.callback_query
    await query.answer()

    if query.data == 'del_cancel':
        await query.edit_message_text("❌ Удаление отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    if query.data.startswith('del_select_'):
        # Show selected quote for confirmation
        quote_id = int(query.data.replace('del_select_', ''))
        quotes = context.user_data.get('delete_quotes', [])
        quote = next((q for q in quotes if q['id'] == quote_id), None)

        if not quote:
            await query.edit_message_text("❌ Ошибка: цитата не найдена.")
            return ConversationHandler.END

        preview = quote['text'][:300] + "..." if len(quote['text']) > 300 else quote['text']

        keyboard = [
            [
                InlineKeyboardButton("✅ Да, удалить", callback_data=f'del_confirm_{quote["id"]}'),
                InlineKeyboardButton("❌ Отменить", callback_data='del_cancel')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        category_name = config.CATEGORIES.get(quote['category'], quote['category'])
        book_info = f"📚 Книга: {quote['title']}\n" if quote['title'] else ""

        # Attribution info
        attr_info = ""
        if quote['quote_author'] or quote['quote_source']:
            parts = []
            if quote['quote_author']:
                parts.append(f"Автор: {quote['quote_author']}")
            if quote['quote_source']:
                parts.append(f"Источник: {quote['quote_source']}")
            attr_info = "📌 Атрибуция:\n" + "\n".join(parts) + "\n\n"

        await query.edit_message_text(
            f"📋 Цитата:\n\n"
            f"ID: {quote['id']}\n"
            f"Категория: {category_name}\n"
            f"{book_info}"
            f"{attr_info}"
            f"{preview}\n\n"
            f"Удалить эту цитату?",
            reply_markup=reply_markup
        )
        return DELETE_CONFIRM

    if query.data.startswith('del_confirm_'):
        # Delete the quote
        quote_id = int(query.data.replace('del_confirm_', ''))

        if db.delete_quote(quote_id):
            await query.edit_message_text(f"✅ Цитата ID:{quote_id} удалена!")
        else:
            await query.edit_message_text(f"❌ Ошибка при удалении цитаты.")

        context.user_data.clear()
        return ConversationHandler.END


# ============== EDIT QUOTE ==============

@admin_required
async def admin_edit_quote_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start editing a quote"""
    await update.message.reply_text(
        "✏️ Редактирование цитаты\n\n"
        "Отправьте:\n"
        "• ID цитаты (например: 123)\n"
        "• или часть текста цитаты для поиска\n\n"
        "/cancel - отменить"
    )
    return EDIT_SEARCH


@admin_required
async def admin_edit_quote_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search for quote to edit"""
    search = update.message.text.strip()

    # Try as ID first
    if search.isdigit():
        quote_id = int(search)
        quotes = db.get_all_quotes()
        quote = next((q for q in quotes if q['id'] == quote_id), None)

        if not quote:
            await update.message.reply_text(
                f"❌ Цитата с ID {quote_id} не найдена.\n\n"
                "Попробуйте снова или /cancel для отмены."
            )
            return EDIT_SEARCH

        matching_quotes = [quote]
    else:
        # Search by text
        quotes = db.get_all_quotes()
        matching_quotes = [q for q in quotes if search.lower() in q['text'].lower()]

        if not matching_quotes:
            await update.message.reply_text(
                "❌ Цитаты не найдены.\n\n"
                "Попробуйте другой запрос или /cancel для отмены."
            )
            return EDIT_SEARCH

        if len(matching_quotes) > 10:
            await update.message.reply_text(
                f"⚠️ Найдено {len(matching_quotes)} цитат.\n"
                "Уточните запрос для более точного поиска."
            )
            return EDIT_SEARCH

    # Store matches
    context.user_data['edit_quotes'] = matching_quotes

    if len(matching_quotes) == 1:
        # Show single quote
        quote = matching_quotes[0]
        context.user_data['edit_quote_id'] = quote['id']
        return await show_edit_menu(update, quote, is_callback=False)
    else:
        # Show multiple options
        keyboard = []
        for q in matching_quotes[:10]:
            short_text = q['text'][:40] + "..." if len(q['text']) > 40 else q['text']
            category_emoji = "📅" if q['category'] == 'daily' else "💭"
            category_short = "Daily" if q['category'] == 'daily' else "Quotes"
            keyboard.append([
                InlineKeyboardButton(
                    f"ID:{q['id']} {category_emoji}{category_short} - {short_text}",
                    callback_data=f'edit_select_{q["id"]}'
                )
            ])
        keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data='edit_cancel')])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"📋 Найдено {len(matching_quotes)} цитат.\n"
            f"Выберите цитату для редактирования:",
            reply_markup=reply_markup
        )
        return EDIT_SELECT


async def show_edit_menu(update: Update, quote: dict, is_callback: bool = True):
    """Show edit menu for a quote"""
    preview = quote['text'][:200] + "..." if len(quote['text']) > 200 else quote['text']

    attr_info = ""
    if quote['quote_author'] or quote['quote_source']:
        parts = []
        if quote['quote_author']:
            parts.append(f"Автор: {quote['quote_author']}")
        if quote['quote_source']:
            parts.append(f"Источник: {quote['quote_source']}")
        attr_info = "📌 Атрибуция:\n" + "\n".join(parts) + "\n\n"

    keyboard = [
        [InlineKeyboardButton("👁 Показать полностью", callback_data='edit_show_full')],
        [InlineKeyboardButton("📝 Текст", callback_data='edit_field_text')],
        [InlineKeyboardButton("👤 Автор", callback_data='edit_field_author')],
        [InlineKeyboardButton("📖 Источник", callback_data='edit_field_source')],
        [
            InlineKeyboardButton("✅ Готово", callback_data='edit_done'),
            InlineKeyboardButton("❌ Отмена", callback_data='edit_cancel')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message_text = (
        f"✏️ Редактирование цитаты ID:{quote['id']}\n\n"
        f"{attr_info}"
        f"💬 Текст:\n{preview}\n\n"
        f"Что хотите изменить?"
    )

    if is_callback:
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)

    return EDIT_FIELD


@admin_required
async def admin_edit_quote_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quote selection for editing"""
    query = update.callback_query
    await query.answer()

    if query.data == 'edit_cancel':
        await query.edit_message_text("❌ Редактирование отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    quote_id = int(query.data.replace('edit_select_', ''))
    quotes = context.user_data.get('edit_quotes', [])
    quote = next((q for q in quotes if q['id'] == quote_id), None)

    if not quote:
        await query.edit_message_text("❌ Ошибка: цитата не найдена.")
        return ConversationHandler.END

    context.user_data['edit_quote_id'] = quote_id
    return await show_edit_menu(update, quote)


@admin_required
async def admin_edit_quote_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle field selection for editing"""
    query = update.callback_query
    await query.answer()

    if query.data == 'edit_cancel':
        await query.edit_message_text("❌ Редактирование отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    if query.data == 'edit_done':
        await query.edit_message_text("✅ Редактирование завершено!")
        context.user_data.clear()
        return ConversationHandler.END

    # Handle "Show full text" button
    if query.data == 'edit_show_full':
        quote_id = context.user_data.get('edit_quote_id')
        quotes = db.get_all_quotes()
        quote = next((q for q in quotes if q['id'] == quote_id), None)

        if not quote:
            await query.edit_message_text("❌ Ошибка: цитата не найдена.")
            return ConversationHandler.END

        # Send full text in a new message
        full_text = quote['text']
        attr_parts = []
        if quote['quote_author']:
            attr_parts.append(quote['quote_author'])
        if quote['quote_source']:
            attr_parts.append(quote['quote_source'])
        attribution = " / ".join(attr_parts) if attr_parts else ""

        full_message = f"📖 Полный текст цитаты ID:{quote['id']}\n\n{full_text}"
        if attribution:
            full_message += f"\n\n— {attribution}"

        await query.message.reply_text(full_message)
        # Return to edit menu
        return await show_edit_menu(update, quote)

    field = query.data.replace('edit_field_', '')
    context.user_data['edit_field'] = field

    field_names = {
        'text': 'текст цитаты',
        'category': 'категорию',
        'author': 'автора',
        'source': 'источник'
    }

    if field == 'category':
        keyboard = [
            [InlineKeyboardButton("💭 Цитаты", callback_data='edit_cat_quotes')],
            [InlineKeyboardButton("📅 Стоицизм на каждый день", callback_data='edit_cat_daily')],
            [InlineKeyboardButton("❌ Отменить", callback_data='edit_cat_cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📂 Выберите новую категорию:",
            reply_markup=reply_markup
        )
        return EDIT_VALUE

    await query.edit_message_text(
        f"✏️ Введите новое значение для поля '{field_names[field]}':\n\n"
        f"Для удаления значения отправьте: -\n"
        f"/cancel - отменить"
    )
    return EDIT_VALUE


@admin_required
async def admin_edit_quote_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new value input for editing"""
    quote_id = context.user_data.get('edit_quote_id')
    field = context.user_data.get('edit_field')

    if not quote_id or not field:
        await update.message.reply_text("❌ Ошибка: потеряны данные сессии.")
        return ConversationHandler.END

    # Handle callback (category selection)
    if update.callback_query:
        query = update.callback_query
        await query.answer()

        if query.data == 'edit_cat_cancel':
            quotes = db.get_all_quotes()
            quote = next((q for q in quotes if q['id'] == quote_id), None)
            if quote:
                return await show_edit_menu(update, quote)
            else:
                await query.edit_message_text("❌ Ошибка: цитата не найдена.")
                return ConversationHandler.END

        new_value = query.data.replace('edit_cat_', '')
        field = 'category'
    else:
        # Handle text input
        new_value = update.message.text.strip()
        if new_value == '-':
            new_value = None

    # Update database
    field_map = {
        'text': 'text',
        'category': 'category',
        'author': 'quote_author',
        'source': 'quote_source'
    }

    db_field = field_map[field]

    # Get current quote
    quotes = db.get_all_quotes()
    quote = next((q for q in quotes if q['id'] == quote_id), None)

    if not quote:
        msg = "❌ Ошибка: цитата не найдена."
        if update.callback_query:
            await update.callback_query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return ConversationHandler.END

    # Update quote
    success = db.update_quote(quote_id, **{db_field: new_value})

    if success:
        # Get updated quote
        quotes = db.get_all_quotes()
        quote = next((q for q in quotes if q['id'] == quote_id), None)

        if update.callback_query:
            return await show_edit_menu(update, quote)
        else:
            # For text input, need to send new message
            await update.message.reply_text("✅ Значение обновлено!")
            return await show_edit_menu(update, quote, is_callback=False)
    else:
        msg = "❌ Ошибка при обновлении."
        if update.callback_query:
            await update.callback_query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return ConversationHandler.END


@admin_required
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    await update.message.reply_text("❌ Операция отменена.")
    context.user_data.clear()
    return ConversationHandler.END


# ============== CONVERSATION HANDLERS ==============

def get_add_quote_handler():
    """Get conversation handler for adding quotes"""
    return ConversationHandler(
        entry_points=[CommandHandler('admin_add', admin_add_quote_start)],
        states={
            ADD_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_quote_text)],
            ADD_AUTHOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_quote_author)],
            ADD_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_quote_source)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )


def get_delete_quote_handler():
    """Get conversation handler for deleting quotes"""
    return ConversationHandler(
        entry_points=[CommandHandler('admin_delete', admin_delete_quote_start)],
        states={
            DELETE_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_delete_quote_search)],
            DELETE_CONFIRM: [CallbackQueryHandler(admin_delete_quote_callback, pattern='^del_')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )


def get_edit_quote_handler():
    """Get conversation handler for editing quotes"""
    return ConversationHandler(
        entry_points=[CommandHandler('admin_edit', admin_edit_quote_start)],
        states={
            EDIT_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_edit_quote_search)],
            EDIT_SELECT: [CallbackQueryHandler(admin_edit_quote_select, pattern='^edit_select_|^edit_cancel$')],
            EDIT_FIELD: [CallbackQueryHandler(admin_edit_quote_field, pattern='^edit_field_|^edit_done$|^edit_cancel$|^edit_show_full$')],
            EDIT_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_edit_quote_value),
                CallbackQueryHandler(admin_edit_quote_value, pattern='^edit_cat_')
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )


@admin_required
async def admin_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics for admin"""
    stats = db.get_user_statistics()
    users_data = db.get_all_users_with_subscriptions()

    # Build message
    message = "📊 *СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ*\n\n"
    message += f"👥 Всего пользователей: *{stats['total_users']}*\n"
    message += f"✅ С активными подписками: *{stats['active_subscribers']}*\n"

    if stats['by_category']:
        message += "\n📂 *По категориям:*\n"
        for cat, count in stats['by_category'].items():
            emoji = '💭' if cat == 'quotes' else '📅'
            cat_name = 'Цитаты' if cat == 'quotes' else 'Daily'
            message += f"   {emoji} {cat_name}: {count}\n"

    if stats['by_time_slot']:
        message += "\n⏰ *По времени:*\n"
        for time, count in stats['by_time_slot'].items():
            time_name = {'morning': 'Утро (8:00)', 'day': 'День (14:00)', 'evening': 'Вечер (20:00)'}.get(time, time)
            message += f"   {time_name}: {count}\n"

    # Show last 10 users
    if users_data:
        message += "\n👤 *Последние пользователи:*\n"
        for i, user in enumerate(users_data[:10], 1):
            if user['username']:
                # Escape underscores for Markdown
                escaped_username = user['username'].replace('_', '\\_')
                username = f"@{escaped_username}"
            else:
                username = user['first_name'] or f"ID:{user['user_id']}"

            # Parse subscriptions
            subs = user['subscriptions'] or '—'
            if subs != '—':
                sub_parts = []
                for sub in subs.split(', '):
                    if ':' in sub:
                        cat, time = sub.split(':')
                        emoji = '💭' if cat == 'quotes' else '📅'
                        time_str = {'morning': '8:00', 'day': '14:00', 'evening': '20:00'}.get(time, time)
                        sub_parts.append(f"{emoji}{time_str}")
                subs = ', '.join(sub_parts) if sub_parts else '—'

            message += f"{i}. {username}: {subs}\n"

    await update.message.reply_text(message, parse_mode='Markdown')


def get_admin_users_handler():
    """Get handler for /admin_users command"""
    return CommandHandler('admin_users', admin_users_command)


@admin_required
async def admin_quote_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show quote statistics (favorites)"""
    _ = context  # unused
    stats = db.get_favorites_statistics(limit=10)

    message = "📊 *СТАТИСТИКА ПО ИЗБРАННОМУ*\n\n"

    # Top quotes
    if stats['top_quotes']:
        message += f"💎 *ТОП-{len(stats['top_quotes'])} ЦИТАТ:*\n\n"
        for i, quote in enumerate(stats['top_quotes'], 1):
            category_emoji = '📅' if quote['category'] == 'daily' else '💭'
            preview = quote['text'][:100] + '...' if len(quote['text']) > 100 else quote['text']

            message += f"{i}. *[{quote['favorites_count']} раз]* ID:{quote['id']} {category_emoji}\n"
            message += f"   _{preview}_\n"
            if quote['quote_author'] or quote['quote_source']:
                attr_parts = []
                if quote['quote_author']:
                    attr_parts.append(quote['quote_author'])
                if quote['quote_source']:
                    attr_parts.append(quote['quote_source'])
                message += f"   — {', '.join(attr_parts)}\n"
            message += "\n"
    else:
        message += "Нет цитат в избранном\n\n"

    # By category
    if stats['by_category']:
        message += "📈 *ПО КАТЕГОРИЯМ:*\n"
        for category, count in stats['by_category'].items():
            emoji = '💭' if category == 'quotes' else '📅'
            cat_name = 'Quotes' if category == 'quotes' else 'Daily'
            message += f"   {emoji} {cat_name}: {count} цитат\n"
        message += "\n"

    # Overall statistics
    message += "📊 *ОБЩАЯ СТАТИСТИКА:*\n"
    message += f"   Всего цитат: {stats['total_quotes']}\n"
    percent_in_fav = stats['quotes_in_favorites']/stats['total_quotes']*100 if stats['total_quotes'] > 0 else 0
    message += f"   В избранном: {stats['quotes_in_favorites']} ({percent_in_fav:.1f}%)\n"
    percent_never = stats['never_favorited']/stats['total_quotes']*100 if stats['total_quotes'] > 0 else 0
    message += f"   Ни разу не добавляли: {stats['never_favorited']} ({percent_never:.1f}%)"

    await update.message.reply_text(message, parse_mode='Markdown')


def get_admin_quote_stats_handler():
    """Get handler for /admin_quote_stats command"""
    return CommandHandler('admin_quote_stats', admin_quote_stats_command)


# Broadcast states
BROADCAST_CONFIRM = 20


@admin_required
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast - send message to all users. Usage: /broadcast <message>"""
    if not context.args:
        await update.message.reply_text(
            "📢 *Рассылка сообщений*\n\n"
            "Использование: `/broadcast <текст сообщения>`\n\n"
            "Пример:\n"
            "`/broadcast Привет! Напоминаю, что вы можете настроить подписки в /settings`",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    message_text = ' '.join(context.args)
    context.user_data['broadcast_message'] = message_text

    # Get all users count
    all_users = db.get_all_users()
    user_count = len(all_users)

    keyboard = [
        [InlineKeyboardButton("✅ Да, отправить", callback_data='broadcast_confirm')],
        [InlineKeyboardButton("❌ Отмена", callback_data='broadcast_cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"📢 *Подтверждение рассылки*\n\n"
        f"Сообщение:\n{message_text}\n\n"
        f"Будет отправлено: *{user_count}* пользователям\n\n"
        f"Отправить?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return BROADCAST_CONFIRM


async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast confirmation"""
    query = update.callback_query
    await query.answer()

    if query.data == 'broadcast_cancel':
        await query.edit_message_text("❌ Рассылка отменена")
        return ConversationHandler.END

    if query.data == 'broadcast_confirm':
        message_text = context.user_data.get('broadcast_message')
        if not message_text:
            await query.edit_message_text("❌ Ошибка: сообщение не найдено")
            return ConversationHandler.END

        await query.edit_message_text("📤 Отправка сообщений...")

        # Get all users and send
        all_users = db.get_all_users()
        sent = 0
        failed = 0

        for user in all_users:
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
            BROADCAST_CONFIRM: [CallbackQueryHandler(broadcast_callback, pattern='^broadcast_')],
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
    )
