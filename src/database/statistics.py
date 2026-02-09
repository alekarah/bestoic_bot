"""Миксин статистики и аналитики пользователей."""

from typing import List, Optional


class StatisticsMixin:
    """Статистика и аналитика пользователей"""

    def get_all_users_with_subscriptions(self) -> List[dict]:
        """Получить всех пользователей с информацией о подписках"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                u.user_id,
                u.username,
                u.first_name,
                u.is_active,
                u.registered_at,
                (SELECT GROUP_CONCAT(category || ':' || time_slot, ', ')
                 FROM user_subscriptions WHERE user_id = u.user_id) as subscriptions,
                (SELECT COUNT(*) FROM favorites WHERE user_id = u.user_id) as favorites_count
            FROM users u
            ORDER BY u.registered_at DESC
        ''')
        users = cursor.fetchall()
        conn.close()
        return [dict(user) for user in users]

    def get_user_statistics(self) -> dict:
        """Получить общую статистику пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Всего пользователей
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]

        # Активные пользователи (хотя бы одна подписка)
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id)
            FROM user_subscriptions
        ''')
        active_subscribers = cursor.fetchone()[0]

        # Пользователи по категориям
        cursor.execute('''
            SELECT category, COUNT(DISTINCT user_id) as count
            FROM user_subscriptions
            GROUP BY category
        ''')
        by_category = {row['category']: row['count'] for row in cursor.fetchall()}

        # Пользователи по времени
        cursor.execute('''
            SELECT time_slot, COUNT(DISTINCT user_id) as count
            FROM user_subscriptions
            GROUP BY time_slot
        ''')
        by_time_slot = {row['time_slot']: row['count'] for row in cursor.fetchall()}

        conn.close()

        return {
            'total_users': total_users,
            'active_subscribers': active_subscribers,
            'by_category': by_category,
            'by_time_slot': by_time_slot
        }

    def get_user_detail(self, user_id: int) -> Optional[dict]:
        """Получить детальную информацию о пользователе"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Получить информацию о пользователе
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return None

        user_dict = dict(user)

        # Получить подписки
        cursor.execute('''
            SELECT category, time_slot, created_at
            FROM user_subscriptions
            WHERE user_id = ?
        ''', (user_id,))
        user_dict['subscriptions'] = [dict(row) for row in cursor.fetchall()]

        # Получить количество избранного
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM favorites
            WHERE user_id = ?
        ''', (user_id,))
        user_dict['favorites_count'] = cursor.fetchone()['count']

        # Получить последнюю отправленную цитату
        cursor.execute('''
            SELECT sent_at
            FROM sent_quotes
            WHERE user_id = ?
            ORDER BY sent_at DESC
            LIMIT 1
        ''', (user_id,))
        last_sent = cursor.fetchone()
        user_dict['last_activity'] = last_sent['sent_at'] if last_sent else None

        conn.close()
        return user_dict

    def get_favorites_statistics(self, limit: int = 10) -> dict:
        """Получить статистику по избранному"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Топ цитат по количеству добавлений в избранное (только ненулевые)
        cursor.execute('''
            SELECT q.id, q.text, q.category, q.quote_author, q.quote_source,
                   COUNT(f.id) as favorites_count
            FROM quotes q
            INNER JOIN favorites f ON q.id = f.quote_id
            GROUP BY q.id
            HAVING favorites_count > 0
            ORDER BY favorites_count DESC, q.id
            LIMIT ?
        ''', (limit,))
        top_quotes = [dict(row) for row in cursor.fetchall()]

        # Статистика по категориям
        cursor.execute('''
            SELECT q.category, COUNT(DISTINCT f.quote_id) as unique_quotes
            FROM favorites f
            INNER JOIN quotes q ON f.quote_id = q.id
            GROUP BY q.category
        ''')
        by_category = {row['category']: row['unique_quotes'] for row in cursor.fetchall()}

        # Общая статистика
        cursor.execute('SELECT COUNT(*) as total FROM quotes')
        total_quotes = cursor.fetchone()['total']

        cursor.execute('SELECT COUNT(DISTINCT quote_id) as total FROM favorites')
        quotes_in_favorites = cursor.fetchone()['total']

        conn.close()

        return {
            'top_quotes': top_quotes,
            'by_category': by_category,
            'total_quotes': total_quotes,
            'quotes_in_favorites': quotes_in_favorites,
            'never_favorited': total_quotes - quotes_in_favorites
        }
