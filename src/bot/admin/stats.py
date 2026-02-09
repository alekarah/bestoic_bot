"""Админские обработчики статистики пользователей и цитат"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from src.bot.admin.common import admin_required, db
import config


@admin_required
async def admin_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пользователей для администратора"""
    stats = db.get_user_statistics()
    users_data = db.get_all_users_with_subscriptions()

    # Формируем сообщение
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
        time_order = ['morning', 'day', 'evening']
        time_names = {'morning': 'Утро (8:00)', 'day': 'День (14:00)', 'evening': 'Вечер (20:00)'}
        for time in time_order:
            if time in stats['by_time_slot']:
                message += f"   {time_names[time]}: {stats['by_time_slot'][time]}\n"

    # Показать последних 10 пользователей
    if users_data:
        message += "\n👤 *Последние пользователи:*\n"
        for i, user in enumerate(users_data[:10], 1):
            if user['username']:
                # Экранируем подчёркивания для Markdown
                escaped_username = user['username'].replace('_', '\\_')
                username = f"@{escaped_username}"
            else:
                username = user['first_name'] or f"ID:{user['user_id']}"

            # Разбираем подписки
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
    """Получить обработчик команды /admin_users"""
    return CommandHandler('admin_users', admin_users_command)


@admin_required
async def admin_quote_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику цитат (избранное)"""
    _ = context  # unused
    stats = db.get_favorites_statistics(limit=10)

    message = "📊 *СТАТИСТИКА ПО ИЗБРАННОМУ*\n\n"

    # Топ цитат
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

    # По категориям
    if stats['by_category']:
        message += "📈 *ПО КАТЕГОРИЯМ:*\n"
        for category, count in stats['by_category'].items():
            emoji = '💭' if category == 'quotes' else '📅'
            cat_name = 'Quotes' if category == 'quotes' else 'Daily'
            message += f"   {emoji} {cat_name}: {count} цитат\n"
        message += "\n"

    # Общая статистика
    message += "📊 *ОБЩАЯ СТАТИСТИКА:*\n"
    message += f"   Всего цитат: {stats['total_quotes']}\n"
    percent_in_fav = stats['quotes_in_favorites']/stats['total_quotes']*100 if stats['total_quotes'] > 0 else 0
    message += f"   В избранном: {stats['quotes_in_favorites']} ({percent_in_fav:.1f}%)\n"
    percent_never = stats['never_favorited']/stats['total_quotes']*100 if stats['total_quotes'] > 0 else 0
    message += f"   Ни разу не добавляли: {stats['never_favorited']} ({percent_never:.1f}%)"

    await update.message.reply_text(message, parse_mode='Markdown')


def get_admin_quote_stats_handler():
    """Получить обработчик команды /admin_quote_stats"""
    return CommandHandler('admin_quote_stats', admin_quote_stats_command)
