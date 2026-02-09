"""Миксин операций с книгами (источники цитат)."""

from typing import List, Optional, Tuple


class BooksMixin:
    """Операции с книгами (источники цитат)"""

    def add_book(self, title: str, author: str) -> int:
        """Добавить новую книгу"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO books (title, author) VALUES (?, ?)', (title, author))
        book_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return book_id

    def get_all_books(self) -> List[Tuple]:
        """Получить все книги"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, author, uploaded_at FROM books ORDER BY uploaded_at DESC')
        books = cursor.fetchall()
        conn.close()
        return books

    def delete_book(self, book_id: int, delete_quotes: bool = False) -> bool:
        """Удалить книгу

        Args:
            book_id: ID книги для удаления
            delete_quotes: Если True, удалить также все цитаты из этой книги

        Returns:
            True если книга удалена, False иначе
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        if delete_quotes:
            # Сначала удалить все цитаты из этой книги
            cursor.execute('DELETE FROM quotes WHERE book_id = ?', (book_id,))

        # Удалить книгу (если delete_quotes=False, у цитат book_id станет NULL из-за ON DELETE SET NULL)
        cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_or_create_manual_book(self, source: str = 'CLI') -> int:
        """Получить или создать виртуальную книгу для вручную добавленных цитат

        Args:
            source: Источник цитат ('CLI' или 'Telegram')

        Returns:
            book_id виртуальной книги
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Проверить, существует ли виртуальная книга
        book_title = f"Ручные цитаты ({source})"
        cursor.execute('SELECT id FROM books WHERE title = ?', (book_title,))
        result = cursor.fetchone()

        if result:
            book_id = result['id']
        else:
            # Создать новую виртуальную книгу
            cursor.execute('INSERT INTO books (title, author) VALUES (?, ?)',
                          (book_title, 'Разное'))
            book_id = cursor.lastrowid
            conn.commit()

        conn.close()
        return book_id
