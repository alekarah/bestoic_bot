from typing import List, Optional, Tuple


class BooksMixin:
    """Book operations (source books for quotes)"""

    def add_book(self, title: str, author: str) -> int:
        """Add a new book"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO books (title, author) VALUES (?, ?)', (title, author))
        book_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return book_id

    def get_all_books(self) -> List[Tuple]:
        """Get all books"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, author, uploaded_at FROM books ORDER BY uploaded_at DESC')
        books = cursor.fetchall()
        conn.close()
        return books

    def delete_book(self, book_id: int, delete_quotes: bool = False) -> bool:
        """Delete a book

        Args:
            book_id: ID of the book to delete
            delete_quotes: If True, also delete all quotes from this book

        Returns:
            True if book was deleted, False otherwise
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        if delete_quotes:
            # First delete all quotes from this book
            cursor.execute('DELETE FROM quotes WHERE book_id = ?', (book_id,))

        # Delete the book (if delete_quotes=False, quotes will have book_id=NULL due to ON DELETE SET NULL)
        cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_or_create_manual_book(self, source: str = 'CLI') -> int:
        """Get or create a virtual book for manually added quotes

        Args:
            source: Source of manual quotes ('CLI' or 'Telegram')

        Returns:
            book_id of the manual book
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if manual book already exists
        book_title = f"Ручные цитаты ({source})"
        cursor.execute('SELECT id FROM books WHERE title = ?', (book_title,))
        result = cursor.fetchone()

        if result:
            book_id = result['id']
        else:
            # Create new manual book
            cursor.execute('INSERT INTO books (title, author) VALUES (?, ?)',
                          (book_title, 'Разное'))
            book_id = cursor.lastrowid
            conn.commit()

        conn.close()
        return book_id
