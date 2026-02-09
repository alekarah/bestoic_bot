"""Миксин операций с пользователями и подписками."""

from typing import List, Optional, Tuple


class UsersMixin:
    """Операции с пользователями и подписками"""

    # Операции с пользователями
    def add_user(self, user_id: int, username: Optional[str] = None,
                 first_name: Optional[str] = None) -> bool:
        """Добавить нового пользователя или обновить существующего"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
        ''', (user_id, username, first_name))
        conn.commit()
        conn.close()
        return True

    def update_user_preferences(self, user_id: int, category: Optional[str] = None,
                               time_slot: Optional[str] = None) -> bool:
        """Обновить настройки пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if category:
            cursor.execute('UPDATE users SET category_preference = ? WHERE user_id = ?',
                          (category, user_id))
        if time_slot:
            cursor.execute('UPDATE users SET time_slot = ? WHERE user_id = ?',
                          (time_slot, user_id))

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def get_user(self, user_id: int) -> Optional[Tuple]:
        """Получить информацию о пользователе"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    def get_all_users(self) -> List[dict]:
        """Получить всех пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, username, first_name, is_active FROM users')
        users = cursor.fetchall()
        conn.close()
        return [{'user_id': u[0], 'username': u[1], 'first_name': u[2], 'is_active': u[3]} for u in users]

    def get_users_by_time_slot(self, time_slot: str) -> List[Tuple]:
        """Получить всех активных пользователей для временного слота"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, category_preference
            FROM users
            WHERE time_slot = ? AND is_active = 1
        ''', (time_slot,))
        users = cursor.fetchall()
        conn.close()
        return users

    def toggle_user_active(self, user_id: int, is_active: bool) -> bool:
        """Переключить статус активности пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_active = ? WHERE user_id = ?',
                      (1 if is_active else 0, user_id))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    # Операции с подписками
    def add_subscription(self, user_id: int, category: str, time_slot: str) -> bool:
        """Добавить или обновить подписку пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO user_subscriptions (user_id, category, time_slot, is_active)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id, category) DO UPDATE SET
                    time_slot = excluded.time_slot,
                    is_active = 1
            ''', (user_id, category, time_slot))
            conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка добавления подписки: {e}")
            return False
        finally:
            conn.close()

    def remove_subscription(self, user_id: int, category: str) -> bool:
        """Удалить подписку пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user_subscriptions WHERE user_id = ? AND category = ?',
                      (user_id, category))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_user_subscriptions(self, user_id: int) -> List[Tuple]:
        """Получить все активные подписки пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, category, time_slot, is_active, created_at
            FROM user_subscriptions
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        subscriptions = cursor.fetchall()
        conn.close()
        return subscriptions

    def get_subscriptions_by_time(self, time_slot: str, category: Optional[str] = None) -> List[Tuple]:
        """Получить все активные подписки для временного слота"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if category:
            cursor.execute('''
                SELECT user_id, category
                FROM user_subscriptions
                WHERE time_slot = ? AND category = ? AND is_active = 1
            ''', (time_slot, category))
        else:
            cursor.execute('''
                SELECT user_id, category
                FROM user_subscriptions
                WHERE time_slot = ? AND is_active = 1
            ''', (time_slot,))

        subscriptions = cursor.fetchall()
        conn.close()
        return subscriptions

    def toggle_subscription_active(self, user_id: int, category: str, is_active: bool) -> bool:
        """Переключить статус активности подписки"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_subscriptions
            SET is_active = ?
            WHERE user_id = ? AND category = ?
        ''', (1 if is_active else 0, user_id, category))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def has_subscription(self, user_id: int, category: str) -> bool:
        """Проверить, есть ли у пользователя подписка на категорию"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 1 FROM user_subscriptions
            WHERE user_id = ? AND category = ?
            LIMIT 1
        ''', (user_id, category))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
