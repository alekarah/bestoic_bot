import sqlite3
from typing import List, Optional, Tuple
from datetime import datetime
import config


class Database:
    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Books table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Quotes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                category TEXT NOT NULL CHECK(category IN ('theory', 'practice', 'quotes')),
                text TEXT NOT NULL,
                quote_author TEXT,
                quote_source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE SET NULL
            )
        ''')

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                category_preference TEXT DEFAULT 'all' CHECK(category_preference IN ('theory', 'practice', 'quotes', 'all')),
                time_slot TEXT DEFAULT 'morning' CHECK(time_slot IN ('morning', 'day', 'evening')),
                is_active INTEGER DEFAULT 1,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Sent quotes tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                quote_id INTEGER NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY (quote_id) REFERENCES quotes (id) ON DELETE CASCADE
            )
        ''')

        conn.commit()
        conn.close()

    # Book operations
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

    # Quote operations
    def find_exact_duplicate(self, text: str) -> Optional[Tuple]:
        """Find exact duplicate quote by text

        Returns:
            Quote row if found, None otherwise
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source, q.book_id
            FROM quotes q
            LEFT JOIN books b ON q.book_id = b.id
            WHERE q.text = ?
            LIMIT 1
        ''', (text,))
        quote = cursor.fetchone()
        conn.close()
        return quote

    def add_quote(self, text: str, category: str, book_id: Optional[int] = None,
                  quote_author: Optional[str] = None, quote_source: Optional[str] = None) -> int:
        """Add a new quote (checks for exact duplicates first)"""
        # Check for exact duplicate
        existing = self.find_exact_duplicate(text)
        if existing:
            return existing['id']  # Return existing quote ID, don't add duplicate

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO quotes (text, category, book_id, quote_author, quote_source) VALUES (?, ?, ?, ?, ?)',
                      (text, category, book_id, quote_author, quote_source))
        quote_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return quote_id

    def update_quote(self, quote_id: int, text: str, category: str,
                    quote_author: Optional[str] = None, quote_source: Optional[str] = None) -> bool:
        """Update an existing quote"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE quotes SET text = ?, category = ?, quote_author = ?, quote_source = ? WHERE id = ?',
                      (text, category, quote_author, quote_source, quote_id))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def delete_quote(self, quote_id: int) -> bool:
        """Delete a quote"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM quotes WHERE id = ?', (quote_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def update_quote(self, quote_id: int, text: Optional[str] = None,
                     category: Optional[str] = None, quote_author: Optional[str] = None,
                     quote_source: Optional[str] = None) -> bool:
        """Update quote fields"""
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

    def get_all_quotes(self, category: Optional[str] = None) -> List[Tuple]:
        """Get all quotes, optionally filtered by category"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if category and category != 'all':
            cursor.execute('''
                SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source, q.book_id
                FROM quotes q
                LEFT JOIN books b ON q.book_id = b.id
                WHERE q.category = ?
                ORDER BY q.created_at DESC
            ''', (category,))
        else:
            cursor.execute('''
                SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source, q.book_id
                FROM quotes q
                LEFT JOIN books b ON q.book_id = b.id
                ORDER BY q.created_at DESC
            ''')

        quotes = cursor.fetchall()
        conn.close()
        return quotes

    def get_random_quote(self, user_id: int, category: Optional[str] = None) -> Optional[Tuple]:
        """Get a random quote that hasn't been sent to this user yet"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if category and category != 'all':
            cursor.execute('''
                SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source
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
                SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source
                FROM quotes q
                LEFT JOIN books b ON q.book_id = b.id
                WHERE q.id NOT IN (
                    SELECT quote_id FROM sent_quotes WHERE user_id = ?
                )
                ORDER BY RANDOM()
                LIMIT 1
            ''', (user_id,))

        quote = cursor.fetchone()

        # If all quotes have been sent, reset the history for this user
        if not quote:
            cursor.execute('DELETE FROM sent_quotes WHERE user_id = ?', (user_id,))
            conn.commit()
            # Try again
            if category and category != 'all':
                cursor.execute('''
                    SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source
                    FROM quotes q
                    LEFT JOIN books b ON q.book_id = b.id
                    WHERE q.category = ?
                    ORDER BY RANDOM()
                    LIMIT 1
                ''', (category,))
            else:
                cursor.execute('''
                    SELECT q.id, q.text, q.category, b.title, b.author, q.quote_author, q.quote_source
                    FROM quotes q
                    LEFT JOIN books b ON q.book_id = b.id
                    ORDER BY RANDOM()
                    LIMIT 1
                ''')
            quote = cursor.fetchone()

        conn.close()
        return quote

    def mark_quote_as_sent(self, user_id: int, quote_id: int):
        """Mark a quote as sent to a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sent_quotes (user_id, quote_id) VALUES (?, ?)',
                      (user_id, quote_id))
        conn.commit()
        conn.close()

    # User operations
    def add_user(self, user_id: int, username: Optional[str] = None,
                 first_name: Optional[str] = None) -> bool:
        """Add a new user or update existing"""
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
        """Update user preferences"""
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
        """Get user information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    def get_users_by_time_slot(self, time_slot: str) -> List[Tuple]:
        """Get all active users for a specific time slot"""
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
        """Toggle user active status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_active = ? WHERE user_id = ?',
                      (1 if is_active else 0, user_id))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated
