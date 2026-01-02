from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.database.models import Database
from src.utils.quote_parser import format_quote_for_telegram
import config


db = Database()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user

    # Add user to database
    db.add_user(user.id, user.username, user.first_name)

    welcome_text = f"""
Привет, {user.first_name}! 👋

Я Bestoic Bot - твой проводник в мир стоической философии.

Каждый день я буду присылать тебе мудрые цитаты из классических трудов стоиков.

Используй команды:
/settings - настроить категорию и время получения цитат
/quote - получить случайную цитату сейчас
/help - помощь
"""

    await update.message.reply_text(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
📚 Доступные команды:

/start - начать работу с ботом
/quote - получить случайную цитату
/settings - настроить категорию и время
/help - это сообщение

🎯 Категории цитат:
• Теория - философские концепции стоицизма
• Практика - практические упражнения
• Цитаты - вдохновляющие мысли
• Все категории - случайная цитата из любой категории

⏰ Время отправки:
• Утро - 8:00
• День - 14:00
• Вечер - 20:00
"""

    await update.message.reply_text(help_text)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command - show settings menu"""
    keyboard = [
        [
            InlineKeyboardButton("📚 Категория", callback_data='settings_category'),
            InlineKeyboardButton("⏰ Время", callback_data='settings_time')
        ],
        [
            InlineKeyboardButton("✅ Включить уведомления", callback_data='settings_enable'),
            InlineKeyboardButton("⏸ Отключить", callback_data='settings_disable')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    user = db.get_user(update.effective_user.id)
    if user:
        category_name = config.CATEGORIES.get(user['category_preference'], 'Не выбрано')
        time_name = user['time_slot'].capitalize()
        status = 'Включены' if user['is_active'] else 'Отключены'

        settings_text = f"""
⚙️ Текущие настройки:

📚 Категория: {category_name}
⏰ Время: {time_name} ({config.TIME_SLOTS[user['time_slot']]})
🔔 Уведомления: {status}

Выбери что хочешь изменить:
"""
    else:
        settings_text = "⚙️ Настройки:\n\nВыбери что хочешь настроить:"

    await update.message.reply_text(settings_text, reply_markup=reply_markup)


async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /quote command - send random quote"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        db.add_user(user_id, update.effective_user.username, update.effective_user.first_name)
        user = db.get_user(user_id)

    category = user['category_preference'] if user else 'all'
    quote = db.get_random_quote(user_id, category)

    if quote:
        await send_quote(update.effective_chat.id, quote, context)
        db.mark_quote_as_sent(user_id, quote['id'])
    else:
        await update.message.reply_text("К сожалению, цитаты закончились. Попробуйте позже.")


async def send_quote(chat_id: int, quote: tuple, context: ContextTypes.DEFAULT_TYPE):
    """Send a formatted quote to user"""
    message = format_quote_for_telegram(
        quote_text=quote['text'],
        category=quote['category'],
        quote_author=quote['quote_author'],
        quote_source=quote['quote_source'],
        book_title=quote['title'],
        book_author=quote['author']
    )

    await context.bot.send_message(chat_id=chat_id, text=message)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    # Settings menu
    if data == 'settings_category':
        keyboard = [
            [InlineKeyboardButton("📖 Теория", callback_data='category_theory')],
            [InlineKeyboardButton("🏃 Практика", callback_data='category_practice')],
            [InlineKeyboardButton("💭 Цитаты", callback_data='category_quotes')],
            [InlineKeyboardButton("🎲 Все категории", callback_data='category_all')],
            [InlineKeyboardButton("« Назад", callback_data='settings_back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📚 Выбери категорию цитат:", reply_markup=reply_markup)

    elif data == 'settings_time':
        keyboard = [
            [InlineKeyboardButton("🌅 Утро (8:00)", callback_data='time_morning')],
            [InlineKeyboardButton("☀️ День (14:00)", callback_data='time_day')],
            [InlineKeyboardButton("🌙 Вечер (20:00)", callback_data='time_evening')],
            [InlineKeyboardButton("« Назад", callback_data='settings_back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("⏰ Выбери время получения цитат:", reply_markup=reply_markup)

    elif data == 'settings_enable':
        db.toggle_user_active(user_id, True)
        await query.edit_message_text("✅ Уведомления включены!\n\nИспользуй /settings для настройки.")

    elif data == 'settings_disable':
        db.toggle_user_active(user_id, False)
        await query.edit_message_text("⏸ Уведомления отключены.\n\nИспользуй /settings чтобы включить снова.")

    elif data == 'settings_back':
        await settings_command(update, context)

    # Category selection
    elif data.startswith('category_'):
        category = data.replace('category_', '')
        db.update_user_preferences(user_id, category=category)
        category_name = config.CATEGORIES.get(category, category)
        await query.edit_message_text(f"✅ Категория изменена на: {category_name}\n\nИспользуй /settings для других настроек.")

    # Time selection
    elif data.startswith('time_'):
        time_slot = data.replace('time_', '')
        db.update_user_preferences(user_id, time_slot=time_slot)
        time_name = config.TIME_SLOTS.get(time_slot, time_slot)
        await query.edit_message_text(f"✅ Время изменено на: {time_name}\n\nИспользуй /settings для других настроек.")
