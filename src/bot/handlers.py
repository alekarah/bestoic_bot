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
/settings - управление подписками
/help - это сообщение

🎯 Категории цитат:
• 💭 Цитаты - мысли Сенеки, Марка Аврелия, Эпиктета
• 📅 Стоицизм на каждый день - 366 размышлений по книге Райана Холидея

⏰ Время отправки:
• Утро - 8:00
• День - 14:00
• Вечер - 20:00

📬 Система подписок:
Вы можете подписаться на обе категории и выбрать своё время для каждой!
"""

    await update.message.reply_text(help_text)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command - show subscription management menu"""
    user_id = update.effective_user.id

    # Get user's current subscriptions
    subscriptions = db.get_user_subscriptions(user_id)

    # Build settings message
    if subscriptions:
        settings_text = "📬 Ваши подписки:\n\n"
        for sub in subscriptions:
            category_name = config.CATEGORIES.get(sub['category'], sub['category'])
            time_name = config.TIME_SLOTS.get(sub['time_slot'], sub['time_slot'])
            status = "✅" if sub['is_active'] else "⏸"
            settings_text += f"{status} {category_name} — {time_name}\n"
        settings_text += "\nВыберите действие:"
    else:
        settings_text = "📬 У вас пока нет активных подписок.\n\nДобавьте первую подписку!"

    # Build keyboard
    keyboard = []

    # Add subscription buttons
    if not db.has_subscription(user_id, 'quotes'):
        keyboard.append([InlineKeyboardButton("➕ Добавить: Цитаты", callback_data='add_sub_quotes')])
    else:
        keyboard.append([InlineKeyboardButton("⏰ Изменить время: Цитаты", callback_data='change_time_quotes')])
        keyboard.append([InlineKeyboardButton("🗑 Удалить: Цитаты", callback_data='remove_sub_quotes')])

    if not db.has_subscription(user_id, 'daily'):
        keyboard.append([InlineKeyboardButton("➕ Добавить: Стоицизм на каждый день", callback_data='add_sub_daily')])
    else:
        keyboard.append([InlineKeyboardButton("⏰ Изменить время: Стоицизм на каждый день", callback_data='change_time_daily')])
        keyboard.append([InlineKeyboardButton("🗑 Удалить: Стоицизм на каждый день", callback_data='remove_sub_daily')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(settings_text, reply_markup=reply_markup)


async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /quote command - send random quote"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        db.add_user(user_id, update.effective_user.username, update.effective_user.first_name)

    # Get user's subscriptions to determine which category to use
    subscriptions = db.get_user_subscriptions(user_id)

    if not subscriptions:
        # No subscriptions, send a random quote from any category
        quote = db.get_random_quote(user_id, None)
        category_text = "случайная"
    else:
        # Send from first subscription category
        category = subscriptions[0]['category']
        quote = db.get_random_quote(user_id, category)
        category_text = config.CATEGORIES.get(category, category)

    if quote:
        await send_quote(update.effective_chat.id, quote, context)
        db.mark_quote_as_sent(user_id, quote['id'])
    else:
        await update.message.reply_text(f"К сожалению, цитаты из категории '{category_text}' закончились. Попробуйте позже.")


async def send_quote(chat_id: int, quote, context: ContextTypes.DEFAULT_TYPE):
    """Send a formatted quote to user"""
    # Convert sqlite3.Row to dict if needed (Row doesn't support .get())
    if hasattr(quote, 'keys'):
        quote = dict(quote)

    message = format_quote_for_telegram(
        quote_text=quote['text'],
        category=quote['category'],
        quote_author=quote.get('quote_author'),
        quote_source=quote.get('quote_source'),
        book_title=quote.get('title'),
        book_author=quote.get('author'),
        day_of_year=quote.get('day_of_year')
    )

    await context.bot.send_message(chat_id=chat_id, text=message)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks for subscription management"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    # Add subscription OR change time - show time selection
    if data.startswith('add_sub_') or data.startswith('change_time_'):
        if data.startswith('add_sub_'):
            category = data.replace('add_sub_', '')
            action = 'add'
        else:
            category = data.replace('change_time_', '')
            action = 'change'

        category_name = config.CATEGORIES.get(category, category)

        # Store category and action in context for next step
        context.user_data['pending_subscription_category'] = category
        context.user_data['pending_subscription_action'] = action

        keyboard = [
            [InlineKeyboardButton("🌅 Утро (8:00)", callback_data=f'select_time_morning')],
            [InlineKeyboardButton("☀️ День (14:00)", callback_data=f'select_time_day')],
            [InlineKeyboardButton("🌙 Вечер (20:00)", callback_data=f'select_time_evening')],
            [InlineKeyboardButton("« Отмена", callback_data='cancel_subscription')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Show time descriptions
        if action == 'add':
            time_desc_text = f"📬 Подписка на: {category_name}\n\n⏰ Выберите время:\n\n"
        else:
            time_desc_text = f"⏰ Изменить время: {category_name}\n\n⏰ Выберите новое время:\n\n"

        time_desc_text += f"🌅 Утро: {config.TIME_SLOT_DESCRIPTIONS['morning']}\n\n"
        time_desc_text += f"☀️ День: {config.TIME_SLOT_DESCRIPTIONS['day']}\n\n"
        time_desc_text += f"🌙 Вечер: {config.TIME_SLOT_DESCRIPTIONS['evening']}"

        await query.edit_message_text(time_desc_text, reply_markup=reply_markup)

    # Time selection for subscription (add or change)
    elif data.startswith('select_time_'):
        time_slot = data.replace('select_time_', '')
        category = context.user_data.get('pending_subscription_category')
        action = context.user_data.get('pending_subscription_action', 'add')

        if not category:
            await query.edit_message_text("❌ Ошибка: категория не выбрана. Попробуйте снова через /settings")
            return

        # Add or update subscription
        success = db.add_subscription(user_id, category, time_slot)

        if success:
            if action == 'change':
                # Show message for time change
                time_name = config.TIME_SLOTS.get(time_slot, time_slot)
                category_name = config.CATEGORIES.get(category, category)
                await query.edit_message_text(
                    f"✅ Время подписки '{category_name}' изменено на {time_name}!\n\n"
                    f"Используй /settings для управления подписками."
                )
            else:
                # Show confirmation message for new subscription
                confirmation = config.SUBSCRIPTION_CONFIRMATIONS.get(category, {}).get(time_slot,
                    "✅ Подписка оформлена!")
                await query.edit_message_text(f"{confirmation}\n\nИспользуй /settings для управления подписками.")
        else:
            await query.edit_message_text("❌ Ошибка при оформлении подписки. Попробуйте позже.")

        # Clear context
        context.user_data.pop('pending_subscription_category', None)
        context.user_data.pop('pending_subscription_action', None)

    # Remove subscription
    elif data.startswith('remove_sub_'):
        category = data.replace('remove_sub_', '')
        category_name = config.CATEGORIES.get(category, category)

        success = db.remove_subscription(user_id, category)

        if success:
            await query.edit_message_text(f"✅ Подписка на '{category_name}' удалена.\n\nИспользуй /settings для управления подписками.")
        else:
            await query.edit_message_text("❌ Ошибка при удалении подписки.")

    # Cancel subscription
    elif data == 'cancel_subscription':
        context.user_data.pop('pending_subscription_category', None)
        context.user_data.pop('pending_subscription_action', None)
        await query.edit_message_text("❌ Отменено.\n\nИспользуй /settings для управления подписками.")
