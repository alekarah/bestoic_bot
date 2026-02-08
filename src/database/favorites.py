import sqlite3
from typing import List, Optional, Tuple


class FavoritesMixin:
    """Favorites operations"""

    def add_to_favorites(self, user_id: int, quote_id: int) -> bool:
        """Add a quote to user's favorites"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO favorites (user_id, quote_id)
                VALUES (?, ?)
            ''', (user_id, quote_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def remove_from_favorites(self, user_id: int, quote_id: int) -> bool:
        """Remove a quote from user's favorites"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM favorites
            WHERE user_id = ? AND quote_id = ?
        ''', (user_id, quote_id))
        removed = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return removed

    def is_favorite(self, user_id: int, quote_id: int) -> bool:
        """Check if a quote is in user's favorites"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 1 FROM favorites
            WHERE user_id = ? AND quote_id = ?
            LIMIT 1
        ''', (user_id, quote_id))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def get_user_favorites(self, user_id: int, limit: int = 10, offset: int = 0) -> List[Tuple]:
        """Get user's favorite quotes with pagination"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT q.id, q.text, q.category, q.quote_author, q.quote_source,
                   q.day_of_year, b.title, b.author, f.added_at
            FROM favorites f
            JOIN quotes q ON f.quote_id = q.id
            LEFT JOIN books b ON q.book_id = b.id
            WHERE f.user_id = ?
            ORDER BY f.added_at DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset))
        quotes = cursor.fetchall()
        conn.close()
        return quotes

    def count_user_favorites(self, user_id: int) -> int:
        """Count total favorites for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM favorites
            WHERE user_id = ?
        ''', (user_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
