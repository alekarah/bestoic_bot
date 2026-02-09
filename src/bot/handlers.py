"""Основные обработчики бота: команды, подписки, избранное, шаринг."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, SwitchInlineQueryChosenChat
from telegram.ext import ContextTypes
from src.database.models import Database
from src.utils.quote_parser import format_quote_for_telegram
import config

logger = logging.getLogger(__name__)


db = Database()


def _build_share_button(text: str, quote_id: int = None) -> InlineKeyboardButton:
    """Создать кнопку «Поделиться» через switch_inline_query_chosen_chat"""
    is_truncated = len(text) > 200
    truncated = text[:200] + '...' if is_truncated else text
    # Для обрезанных цитат используем deep link, чтобы получатель мог прочитать полную версию
    if is_truncated and quote_id:
        bot_link = f"Читать полностью 👉 t.me/{config.BOT_USERNAME}?start=quote_{quote_id}"
    else:
        bot_link = f"t.me/{config.BOT_USERNAME}"
    share_text = f"\n{truncated}\n\n{bot_link}"
    return InlineKeyboardButton("📤 Поделиться", switch_inline_query_chosen_chat=SwitchInlineQueryChosenChat(
        query=share_text,
        allow_user_chats=True,
        allow_group_chats=True,
        allow_channel_chats=True,
    ))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start, включая deep links вида /start quote_123"""
    user = update.effective_user

    # Добавить пользователя в базу данных
    db.add_user(user.id, user.username, user.first_name)

    # Проверка параметра deep link (например, /start quote_123)
    if context.args and len(context.args) > 0:
        param = context.args[0]
        if param.startswith('quote_'):
            try:
                quote_id = int(param.replace('quote_', ''))
                quote = db.get_quote_by_id(quote_id)
                if quote:
                    # Отправить вступительное сообщение для расшаренной цитаты
                    await update.message.reply_text("Привет! Вот цитата, которой с тобой поделились:")
                    await send_quote(update.effective_chat.id, quote, context, user_id=user.id)
                    await update.message.reply_text("👉 Нажми /start чтобы узнать больше о боте")
                    return
            except (ValueError, Exception):
                pass  # Невалидный quote_id — показываем обычное приветствие

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

👇 Нажми «Подписаться» или открой Меню
"""

    # Кнопка подписки
    keyboard = [[InlineKeyboardButton("Подписаться", callback_data="open_settings")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help"""
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

🔗 Поделиться:
Делитесь с друзьями — кнопка под каждой цитатой.
"""

    await update.message.reply_text(help_text)


def _build_settings_content(user_id: int):
    """Сформировать текст и клавиатуру меню настроек"""
    subscriptions = db.get_user_subscriptions(user_id)

    # Формируем сообщение настроек
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

    # Формируем клавиатуру
    keyboard = []

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
    return settings_text, reply_markup


async def show_settings_menu(query, user_id: int):
    """Показать меню настроек редактированием сообщения (для callback-кнопок)"""
    settings_text, reply_markup = _build_settings_content(user_id)
    await query.edit_message_text(settings_text, reply_markup=reply_markup)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /settings — меню управления подписками"""
    user_id = update.effective_user.id
    settings_text, reply_markup = _build_settings_content(user_id)
    await update.message.reply_text(settings_text, reply_markup=reply_markup)


async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /quote — отправить случайную цитату из категории 'quotes'"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        db.add_user(user_id, update.effective_user.username, update.effective_user.first_name)

    # Всегда отправляем из категории 'quotes' (не daily)
    # Ежедневные цитаты отправляются только по расписанию через подписки
    quote = db.get_random_quote(user_id, 'quotes')

    if quote:
        await send_quote(update.effective_chat.id, quote, context, user_id=user_id)
        db.mark_quote_as_sent(user_id, quote['id'])
    else:
        await update.message.reply_text("К сожалению, все цитаты уже были показаны. Попробуйте позже.")


async def send_quote(chat_id: int, quote, context: ContextTypes.DEFAULT_TYPE, user_id: int = None):
    """Отправить отформатированную цитату пользователю с кнопками избранного и шаринга"""
    # Конвертируем sqlite3.Row в dict при необходимости (Row не поддерживает .get())
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

    # Формируем клавиатуру с кнопками избранного и шаринга
    reply_markup = None
    if user_id:
        is_fav = db.is_favorite(user_id, quote['id'])
        if is_fav:
            fav_button_text = "💔 Убрать из избранного"
            fav_callback_data = f"unfav_{quote['id']}"
        else:
            fav_button_text = "❤️ В избранное"
            fav_callback_data = f"fav_{quote['id']}"

        keyboard = [
            [InlineKeyboardButton(fav_button_text, callback_data=fav_callback_data)],
            [_build_share_button(message, quote_id=quote['id'])]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback-кнопок управления подписками"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    # Открыть настройки из кнопки приветственного сообщения
    if data == 'open_settings':
        await show_settings_menu(query, user_id)
        return

    # Добавить подписку ИЛИ изменить время — показать выбор времени
    if data.startswith('add_sub_') or data.startswith('change_time_'):
        if data.startswith('add_sub_'):
            category = data.replace('add_sub_', '')
            action = 'add'
        else:
            category = data.replace('change_time_', '')
            action = 'change'

        category_name = config.CATEGORIES.get(category, category)

        # Сохраняем категорию и действие в контексте для следующего шага
        context.user_data['pending_subscription_category'] = category
        context.user_data['pending_subscription_action'] = action

        keyboard = [
            [InlineKeyboardButton("🌅 Утро (8:00)", callback_data=f'select_time_morning')],
            [InlineKeyboardButton("☀️ День (14:00)", callback_data=f'select_time_day')],
            [InlineKeyboardButton("🌙 Вечер (20:00)", callback_data=f'select_time_evening')],
            [InlineKeyboardButton("« Отмена", callback_data='cancel_subscription')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Показываем описания времени
        if action == 'add':
            time_desc_text = f"📬 Подписка на: {category_name}\n\n⏰ Выберите время:\n\n"
        else:
            time_desc_text = f"⏰ Изменить время: {category_name}\n\n⏰ Выберите новое время:\n\n"

        # Получаем описания для данной категории
        cat_descriptions = config.TIME_SLOT_DESCRIPTIONS.get(category, config.TIME_SLOT_DESCRIPTIONS['quotes'])
        time_desc_text += f"{cat_descriptions['morning']}\n\n"
        time_desc_text += f"{cat_descriptions['day']}\n\n"
        time_desc_text += f"{cat_descriptions['evening']}"

        await query.edit_message_text(time_desc_text, reply_markup=reply_markup)

    # Выбор времени для подписки (добавление или изменение)
    elif data.startswith('select_time_'):
        time_slot = data.replace('select_time_', '')
        category = context.user_data.get('pending_subscription_category')
        action = context.user_data.get('pending_subscription_action', 'add')

        if not category:
            await query.edit_message_text("❌ Ошибка: категория не выбрана. Попробуйте снова через /settings")
            return

        # Добавить или обновить подписку
        success = db.add_subscription(user_id, category, time_slot)

        if success:
            if action == 'change':
                # Сообщение об изменении времени
                time_name = config.TIME_SLOTS.get(time_slot, time_slot)
                category_name = config.CATEGORIES.get(category, category)
                await query.edit_message_text(
                    f"✅ Время подписки '{category_name}' изменено на {time_name}!\n\n"
                    f"Используй /settings для управления подписками."
                )
            else:
                # Подтверждение новой подписки
                confirmation = config.SUBSCRIPTION_CONFIRMATIONS.get(category, {}).get(time_slot,
                    "✅ Подписка оформлена!")
                await query.edit_message_text(f"{confirmation}\n\nИспользуй /settings для управления подписками.")
        else:
            await query.edit_message_text("❌ Ошибка при оформлении подписки. Попробуйте позже.")

        # Очищаем контекст
        context.user_data.pop('pending_subscription_category', None)
        context.user_data.pop('pending_subscription_action', None)

    # Удалить подписку
    elif data.startswith('remove_sub_'):
        category = data.replace('remove_sub_', '')
        category_name = config.CATEGORIES.get(category, category)

        success = db.remove_subscription(user_id, category)

        if success:
            await query.edit_message_text(f"✅ Подписка на '{category_name}' удалена.\n\nИспользуй /settings для управления подписками.")
        else:
            await query.edit_message_text("❌ Ошибка при удалении подписки.")

    # Отмена подписки
    elif data == 'cancel_subscription':
        context.user_data.pop('pending_subscription_category', None)
        context.user_data.pop('pending_subscription_action', None)
        await query.edit_message_text("❌ Отменено.\n\nИспользуй /settings для управления подписками.")


async def favorites_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback-ов избранного (добавление/удаление, пагинация)"""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data

    # Добавить в избранное
    if data.startswith('fav_'):
        quote_id = int(data.replace('fav_', ''))
        db.add_to_favorites(user_id, quote_id)
        await query.answer("❤️ Добавлено в избранное!")

        # Обновить кнопку на «убрать», сохранить кнопку шаринга
        keyboard = [
            [InlineKeyboardButton("💔 Убрать из избранного", callback_data=f"unfav_{quote_id}")],
            [_build_share_button(query.message.text, quote_id=quote_id)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)

    # Убрать из избранного
    elif data.startswith('unfav_'):
        quote_id = int(data.replace('unfav_', ''))
        db.remove_from_favorites(user_id, quote_id)
        await query.answer("💔 Удалено из избранного")

        # Обновить кнопку на «добавить», сохранить кнопку шаринга
        keyboard = [
            [InlineKeyboardButton("❤️ В избранное", callback_data=f"fav_{quote_id}")],
            [_build_share_button(query.message.text, quote_id=quote_id)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)

    # Пагинация избранного
    elif data.startswith('favpage_'):
        page = int(data.replace('favpage_', ''))
        await show_favorites_page(query, user_id, page)

    # Удалить из списка избранного
    elif data.startswith('favdel_'):
        quote_id = int(data.replace('favdel_', ''))
        db.remove_from_favorites(user_id, quote_id)
        await query.answer("🗑 Удалено из избранного")
        # Обновить текущую страницу
        page = context.user_data.get('favorites_page', 0)
        await show_favorites_page(query, user_id, page)


async def favorites_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /favorites — показать избранные цитаты пользователя"""
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
    """Показать конкретную страницу избранного"""
    total = db.count_user_favorites(user_id)

    if total == 0:
        await query.edit_message_text(
            "❤️ У вас пока нет избранных цитат.\n\n"
            "Нажимайте ❤️ под цитатами, чтобы сохранять их!"
        )
        return

    # Проверяем границы страницы
    if page < 0:
        page = 0
    if page >= total:
        page = total - 1

    favorites = db.get_user_favorites(user_id, limit=1, offset=page)
    if favorites:
        fav = favorites[0]
        message = format_favorite_message(fav, page, total)
        # Получаем текст цитаты для шаринга (без заголовка и ссылки на бота)
        share_text = format_quote_for_telegram(
            quote_text=dict(fav)['text'] if hasattr(fav, 'keys') else fav['text'],
            category=dict(fav)['category'] if hasattr(fav, 'keys') else fav['category'],
            quote_author=dict(fav).get('quote_author') if hasattr(fav, 'keys') else fav.get('quote_author'),
            quote_source=dict(fav).get('quote_source') if hasattr(fav, 'keys') else fav.get('quote_source'),
            book_title=dict(fav).get('title') if hasattr(fav, 'keys') else fav.get('title'),
            book_author=dict(fav).get('author') if hasattr(fav, 'keys') else fav.get('author'),
            day_of_year=dict(fav).get('day_of_year') if hasattr(fav, 'keys') else fav.get('day_of_year')
        )
        keyboard = build_favorites_keyboard(fav['id'], page, total, share_text)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)


async def send_favorite_quote(message_obj, fav, page: int, total: int):
    """Отправить избранную цитату с навигацией"""
    msg = format_favorite_message(fav, page, total)
    # Получаем текст цитаты для шаринга (без заголовка и ссылки на бота)
    share_text = format_quote_for_telegram(
        quote_text=dict(fav)['text'] if hasattr(fav, 'keys') else fav['text'],
        category=dict(fav)['category'] if hasattr(fav, 'keys') else fav['category'],
        quote_author=dict(fav).get('quote_author') if hasattr(fav, 'keys') else fav.get('quote_author'),
        quote_source=dict(fav).get('quote_source') if hasattr(fav, 'keys') else fav.get('quote_source'),
        book_title=dict(fav).get('title') if hasattr(fav, 'keys') else fav.get('title'),
        book_author=dict(fav).get('author') if hasattr(fav, 'keys') else fav.get('author'),
        day_of_year=dict(fav).get('day_of_year') if hasattr(fav, 'keys') else fav.get('day_of_year')
    )
    keyboard = build_favorites_keyboard(fav['id'], page, total, share_text)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message_obj.reply_text(msg, reply_markup=reply_markup)


def format_favorite_message(fav, page: int, total: int) -> str:
    """Форматировать избранную цитату для отображения"""
    # Конвертируем Row в dict при необходимости
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


def build_favorites_keyboard(quote_id: int, page: int, total: int, share_text: str = None) -> list:
    """Сформировать клавиатуру навигации по избранному"""
    keyboard = []

    # Ряд навигации
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"favpage_{page - 1}"))
    if page < total - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"favpage_{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    # Кнопка удаления
    keyboard.append([InlineKeyboardButton("🗑 Удалить из избранного", callback_data=f"favdel_{quote_id}")])

    # Кнопка шаринга
    if share_text:
        keyboard.append([_build_share_button(share_text, quote_id=quote_id)])

    return keyboard
