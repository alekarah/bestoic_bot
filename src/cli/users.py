"""CLI commands for user management"""

import click
from src.cli.common import db


@click.group()
def users():
    """Управление пользователями"""
    pass


@users.command('list')
@click.option('--limit', '-l', default=20, help='Количество пользователей для показа')
def users_list(limit):
    """Показать список пользователей с подписками"""
    users_data = db.get_all_users_with_subscriptions()

    if not users_data:
        click.echo('Пользователи не найдены')
        return

    click.echo(f'\nВсего пользователей: {len(users_data)}')
    click.echo(f'Показано: {min(limit, len(users_data))}\n')
    click.echo('='*100)
    click.echo(f'{"ID":<12} {"Username":<20} {"Имя":<20} {"Подписки":<30} {"Избранное"}')
    click.echo('='*100)

    for user in users_data[:limit]:
        user_id = str(user['user_id'])
        username = user['username'] or '—'
        first_name = user['first_name'] or '—'

        # Parse subscriptions
        subs = user['subscriptions'] or '—'
        if subs != '—':
            # Format: "quotes:morning, daily:evening" -> "Quotes 8:00, Daily 14:00"
            sub_parts = []
            for sub in subs.split(', '):
                if ':' in sub:
                    cat, time = sub.split(':')
                    cat_name = 'Quotes' if cat == 'quotes' else 'Daily'
                    time_str = {'morning': '8:00', 'day': '14:00', 'evening': '20:00'}.get(time, time)
                    sub_parts.append(f"{cat_name} {time_str}")
            subs = ', '.join(sub_parts) if sub_parts else '—'

        favorites = str(user['favorites_count']) if user['favorites_count'] else '0'

        click.echo(f'{user_id:<12} {username[:19]:<20} {first_name[:19]:<20} {subs[:29]:<30} {favorites}')

    click.echo('='*100)


@users.command('stats')
def users_stats():
    """Показать статистику пользователей"""
    stats = db.get_user_statistics()

    click.echo('\n' + '='*50)
    click.echo('📊 СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ')
    click.echo('='*50)

    click.echo(f'\n👥 Всего пользователей: {stats["total_users"]}')
    click.echo(f'✅ С активными подписками: {stats["active_subscribers"]}')

    if stats['by_category']:
        click.echo('\n📂 По категориям:')
        for cat, count in stats['by_category'].items():
            emoji = '💭' if cat == 'quotes' else '📅'
            cat_name = 'Цитаты' if cat == 'quotes' else 'Daily'
            click.echo(f'   {emoji} {cat_name}: {count}')

    if stats['by_time_slot']:
        click.echo('\n⏰ По времени:')
        for time, count in stats['by_time_slot'].items():
            time_name = {'morning': 'Утро (8:00)', 'day': 'День (14:00)', 'evening': 'Вечер (20:00)'}.get(time, time)
            click.echo(f'   {time_name}: {count}')

    click.echo('='*50 + '\n')


@users.command('view')
@click.argument('user_id', type=int)
def users_view(user_id):
    """Показать детальную информацию о пользователе"""
    user = db.get_user_detail(user_id)

    if not user:
        click.echo(f'✗ Пользователь ID:{user_id} не найден', err=True)
        return

    click.echo('\n' + '='*60)
    click.echo(f'👤 Пользователь ID: {user["user_id"]}')
    click.echo('='*60)

    click.echo(f'Username: @{user["username"]}' if user['username'] else 'Username: —')
    click.echo(f'Имя: {user["first_name"]}' if user['first_name'] else 'Имя: —')
    click.echo(f'Статус: {"✅ Активен" if user["is_active"] else "❌ Неактивен"}')
    click.echo(f'Зарегистрирован: {user["registered_at"]}')

    if user['last_activity']:
        click.echo(f'Последняя активность: {user["last_activity"]}')

    click.echo(f'\n❤️ Избранных цитат: {user["favorites_count"]}')

    if user['subscriptions']:
        click.echo('\n📬 Подписки:')
        for sub in user['subscriptions']:
            emoji = '💭' if sub['category'] == 'quotes' else '📅'
            cat_name = 'Цитаты' if sub['category'] == 'quotes' else 'Стоицизм на каждый день'
            time_name = {'morning': 'Утро (8:00)', 'day': 'День (14:00)', 'evening': 'Вечер (20:00)'}.get(sub['time_slot'], sub['time_slot'])
            click.echo(f'  {emoji} {cat_name} — {time_name}')
            click.echo(f'     Создана: {sub["created_at"]}')
    else:
        click.echo('\n📬 Подписок нет')

    click.echo('='*60 + '\n')
