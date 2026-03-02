"""Миксин операций с цитатами."""

from typing import List, Optional, Tuple


class QuotesMixin:
    """Операции с цитатами"""

    def find_exact_duplicate(self, text: str) -> Optional[Tuple]:
        """Найти точный дубликат цитаты по тексту

        Returns:
            Строка цитаты если найдена, None иначе
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source, q.day_of_year, q.book_id
            FROM quotes q
            LEFT JOIN books b ON q.book_id = b.id
            WHERE q.text = ?
            LIMIT 1
        ''', (text,))
        quote = cursor.fetchone()
        conn.close()
        return quote

    def add_quote(self, text: str, category: str, book_id: Optional[int] = None,
                  quote_author: Optional[str] = None, quote_source: Optional[str] = None,
                  day_of_year: Optional[int] = None) -> int:
        """Добавить новую цитату (сначала проверяет дубликаты)"""
        # Проверка на дубликат
        existing = self.find_exact_duplicate(text)
        if existing:
            return existing['id']  # Вернуть ID существующей цитаты, не добавлять дубликат

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO quotes (text, category, book_id, quote_author, quote_source, day_of_year) VALUES (?, ?, ?, ?, ?, ?)',
                      (text, category, book_id, quote_author, quote_source, day_of_year))
        quote_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return quote_id

    def update_quote(self, quote_id: int, text: Optional[str] = None,
                     category: Optional[str] = None, quote_author: Optional[str] = None,
                     quote_source: Optional[str] = None) -> bool:
        """Обновить поля цитаты"""
        conn = self.get_connection()
        cursor = conn.cursor()

        updates = []
        params = []

        if text is not None:
            updates.append('text = ?')
            params.append(text)
        if category is not None:
            updates.append('category = ?')
            params.append(category)
        if quote_author is not None:
            updates.append('quote_author = ?')
            params.append(quote_author)
        if quote_source is not None:
            updates.append('quote_source = ?')
            params.append(quote_source)

        if not updates:
            conn.close()
            return False

        params.append(quote_id)
        query = f'UPDATE quotes SET {", ".join(updates)} WHERE id = ?'

        cursor.execute(query, params)
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def delete_quote(self, quote_id: int) -> bool:
        """Удалить цитату"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM quotes WHERE id = ?', (quote_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_all_quotes(self, category: Optional[str] = None) -> List[Tuple]:
        """Получить все цитаты, опционально с фильтром по категории"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if category and category != 'all':
            cursor.execute('''
                SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source, q.day_of_year, q.book_id
                FROM quotes q
                LEFT JOIN books b ON q.book_id = b.id
                WHERE q.category = ?
                ORDER BY q.created_at DESC
            ''', (category,))
        else:
            cursor.execute('''
                SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source, q.day_of_year, q.book_id
                FROM quotes q
                LEFT JOIN books b ON q.book_id = b.id
                ORDER BY q.created_at DESC
            ''')

        quotes = cursor.fetchall()
        conn.close()
        return quotes

    def get_random_quote(self, user_id: int, category: Optional[str] = None) -> Optional[Tuple]:
        """Получить случайную цитату, которая ещё не отправлялась пользователю

        Для категории 'daily' возвращает цитату текущего дня года.
        Для остальных категорий — случайную неотправленную цитату.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Особая обработка для категории 'daily' — вернуть цитату текущего дня
        if category == 'daily':
            from datetime import datetime
            # Цитаты в базе привязаны к дням 2024 (високосного) года.
            # Чтобы в невисокосный год не было сдвига начиная с 1 марта,
            # пересчитываем номер дня через 2024: берём число и месяц сегодня,
            # но день года считаем относительно 2024.
            now = datetime.now()
            current_day = datetime(2024, now.month, now.day).timetuple().tm_yday

            cursor.execute('''
                SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source, q.day_of_year
                FROM quotes q
                LEFT JOIN books b ON q.book_id = b.id
                WHERE q.category = 'daily' AND q.day_of_year = ?
                LIMIT 1
            ''', (current_day,))
            quote = cursor.fetchone()
            conn.close()
            return quote

        if category and category != 'all':
            cursor.execute('''
                SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source, q.day_of_year
                FROM quotes q
                LEFT JOIN books b ON q.book_id = b.id
                WHERE q.category = ?
                AND q.id NOT IN (
                    SELECT quote_id FROM sent_quotes WHERE user_id = ?
                )
                ORDER BY RANDOM()
                LIMIT 1
            ''', (category, user_id))
        else:
            cursor.execute('''
                SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source, q.day_of_year
                FROM quotes q
                LEFT JOIN books b ON q.book_id = b.id
                WHERE q.id NOT IN (
                    SELECT quote_id FROM sent_quotes WHERE user_id = ?
                )
                ORDER BY RANDOM()
                LIMIT 1
            ''', (user_id,))

        quote = cursor.fetchone()

        # Если все цитаты отправлены — сбросить историю для этого пользователя
        if not quote:
            cursor.execute('DELETE FROM sent_quotes WHERE user_id = ?', (user_id,))
            conn.commit()
            # Попробовать снова
            if category and category != 'all':
                cursor.execute('''
                    SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source, q.day_of_year
                    FROM quotes q
                    LEFT JOIN books b ON q.book_id = b.id
                    WHERE q.category = ?
                    ORDER BY RANDOM()
                    LIMIT 1
                ''', (category,))
            else:
                cursor.execute('''
                    SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source, q.day_of_year
                    FROM quotes q
                    LEFT JOIN books b ON q.book_id = b.id
                    ORDER BY RANDOM()
                    LIMIT 1
                ''')
            quote = cursor.fetchone()

        conn.close()
        return quote

    def get_quote_by_id(self, quote_id: int) -> Optional[Tuple]:
        """Получить цитату по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source, q.day_of_year
            FROM quotes q
            LEFT JOIN books b ON q.book_id = b.id
            WHERE q.id = ?
        ''', (quote_id,))
        quote = cursor.fetchone()
        conn.close()
        return quote

    def mark_quote_as_sent(self, user_id: int, quote_id: int):
        """Отметить цитату как отправленную пользователю"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sent_quotes (user_id, quote_id) VALUES (?, ?)',
                      (user_id, quote_id))
        conn.commit()
        conn.close()
