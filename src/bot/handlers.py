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
Привет, {user.first_name}! 🤝

Я - твой проводник в мир стоицизма. 
Что я могу тебе предложить?

📅 Стоицизм на каждый день
366 уроков от Райана Холидея. Практикуй уже сегодня.

📚 Библиотека лучших книг по стоицизму
Углубленное изучение темы. 
Скачивай бесплатно и читай в любое удобное время.

💭 Цитаты великих стоиков
Читай, вдохновляйся, действуй.

Желаем тебе удачи и добро пожаловать. 
Это трудный, но достойный путь.
"""

    await update.message.reply_text(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
Доступные команды:

/start - начать свой путь
/settings - управляй своими подписками
/favorites - твои избранные цитаты
/books - библиотека книг
/quote - получить случайную цитату
/help - это сообщение

✍️ Подписки:
• Цитаты великих стоиков - Сенеки, Марка Аврелия, Эпиктета и других.
• Стоицизм на каждый день - 366 уроков мудрости по книге Райана Холидея.

⏰ Время отправки:
• Утро - 8:00
• День - 14:00
• Вечер - 20:00

📬 Система подписок:
Вы можете подписаться на обе категории и выбрать своё время для каждой.

❤️ Избранное:
Нажимайте лайк под цитатами, чтобы сохранять понравившиеся.

📚 Библиотека:
Скачивайте книги по стоицизму в разных форматах (fb2, epub, pdf).

📨 Поделиться ботом: t.me/bestoic_bot
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
    """Handle /quote command - send random quote from 'quotes' category"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        db.add_user(user_id, update.effective_user.username, update.effective_user.first_name)

    # Always send from 'quotes' category (not daily)
    # Daily quotes are only sent via scheduled subscriptions
    quote = db.get_random_quote(user_id, 'quotes')

    if quote:
        await send_quote(update.effective_chat.id, quote, context, user_id=user_id)
        db.mark_quote_as_sent(user_id, quote['id'])
    else:
        await update.message.reply_text("К сожалению, все цитаты уже были показаны. Попробуйте позже.")


async def send_quote(chat_id: int, quote, context: ContextTypes.DEFAULT_TYPE, user_id: int = None):
    """Send a formatted quote to user with favorite button"""
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

    # Add favorite button if user_id is provided
    reply_markup = None
    if user_id:
        is_fav = db.is_favorite(user_id, quote['id'])
        if is_fav:
            button_text = "💔 Убрать из избранного"
            callback_data = f"unfav_{quote['id']}"
        else:
            button_text = "❤️ В избранное"
            callback_data = f"fav_{quote['id']}"
        keyboard = [[InlineKeyboardButton(button_text, callback_data=callback_data)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)


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

        # Get descriptions for this category
        cat_descriptions = config.TIME_SLOT_DESCRIPTIONS.get(category, config.TIME_SLOT_DESCRIPTIONS['quotes'])
        time_desc_text += f"{cat_descriptions['morning']}\n\n"
        time_desc_text += f"{cat_descriptions['day']}\n\n"
        time_desc_text += f"{cat_descriptions['evening']}"

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


async def favorites_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle favorites-related callbacks (add/remove from favorites, pagination)"""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data

    # Add to favorites
    if data.startswith('fav_'):
        quote_id = int(data.replace('fav_', ''))
        db.add_to_favorites(user_id, quote_id)
        await query.answer("❤️ Добавлено в избранное!")

        # Update button to "remove"
        keyboard = [[InlineKeyboardButton("💔 Убрать из избранного", callback_data=f"unfav_{quote_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)

    # Remove from favorites
    elif data.startswith('unfav_'):
        quote_id = int(data.replace('unfav_', ''))
        db.remove_from_favorites(user_id, quote_id)
        await query.answer("💔 Удалено из избранного")

        # Update button to "add"
        keyboard = [[InlineKeyboardButton("❤️ В избранное", callback_data=f"fav_{quote_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)

    # Favorites pagination
    elif data.startswith('favpage_'):
        page = int(data.replace('favpage_', ''))
        await show_favorites_page(query, user_id, page)

    # Delete from favorites list view
    elif data.startswith('favdel_'):
        quote_id = int(data.replace('favdel_', ''))
        db.remove_from_favorites(user_id, quote_id)
        await query.answer("🗑 Удалено из избранного")
        # Refresh current page
        page = context.user_data.get('favorites_page', 0)
        await show_favorites_page(query, user_id, page)


async def favorites_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /favorites command - show user's favorite quotes"""
    user_id = update.effective_user.id
    context.user_data['favorites_page'] = 0

    total = db.count_user_favorites(user_id)

    if total == 0:
        await update.message.reply_text(
            "❤️ У вас пока нет избранных цитат.\n\n"
            "Нажимайте ❤️ под цитатами, чтобы сохранять их!"
        )
        return

    favorites = db.get_user_favorites(user_id, limit=1, offset=0)
    if favorites:
        await send_favorite_quote(update.message, favorites[0], 0, total)


async def show_favorites_page(query, user_id: int, page: int):
    """Show a specific page of favorites"""
    total = db.count_user_favorites(user_id)

    if total == 0:
        await query.edit_message_text(
            "❤️ У вас пока нет избранных цитат.\n\n"
            "Нажимайте ❤️ под цитатами, чтобы сохранять их!"
        )
        return

    # Ensure page is within bounds
    if page < 0:
        page = 0
    if page >= total:
        page = total - 1

    favorites = db.get_user_favorites(user_id, limit=1, offset=page)
    if favorites:
        fav = favorites[0]
        message = format_favorite_message(fav, page, total)
        keyboard = build_favorites_keyboard(fav['id'], page, total)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)


async def send_favorite_quote(message_obj, fav, page: int, total: int):
    """Send a favorite quote with navigation"""
    msg = format_favorite_message(fav, page, total)
    keyboard = build_favorites_keyboard(fav['id'], page, total)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message_obj.reply_text(msg, reply_markup=reply_markup)


def format_favorite_message(fav, page: int, total: int) -> str:
    """Format a favorite quote for display"""
    # Convert Row to dict if needed
    if hasattr(fav, 'keys'):
        fav = dict(fav)

    message = format_quote_for_telegram(
        quote_text=fav['text'],
        category=fav['category'],
        quote_author=fav.get('quote_author'),
        quote_source=fav.get('quote_source'),
        book_title=fav.get('title'),
        book_author=fav.get('author'),
        day_of_year=fav.get('day_of_year')
    )

    message = f"❤️ Избранное ({page + 1}/{total})\n\n{message}"
    return message


def build_favorites_keyboard(quote_id: int, page: int, total: int) -> list:
    """Build keyboard for favorites navigation"""
    keyboard = []

    # Navigation row
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"favpage_{page - 1}"))
    if page < total - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"favpage_{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    # Delete button
    keyboard.append([InlineKeyboardButton("🗑 Удалить из избранного", callback_data=f"favdel_{quote_id}")])

    return keyboard
