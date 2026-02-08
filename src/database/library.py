from typing import List, Optional, Tuple


class LibraryMixin:
    """Library books and book files operations"""

    # Library books operations
    def add_library_book(self, title: str, author: str, description: str = None,
                         buy_url: str = None, category: str = None) -> int:
        """Add a new book to the library"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO library_books (title, author, description, buy_url, category)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, author, description, buy_url, category))
        book_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return book_id

    def update_library_book(self, book_id: int, title: str = None, author: str = None,
                            description: str = None, buy_url: str = None, category: str = None) -> bool:
        """Update library book info"""
        conn = self.get_connection()
        cursor = conn.cursor()

        updates = []
        params = []

        if title is not None:
            updates.append('title = ?')
            params.append(title)
        if author is not None:
            updates.append('author = ?')
            params.append(author)
        if description is not None:
            updates.append('description = ?')
            params.append(description)
        if buy_url is not None:
            updates.append('buy_url = ?')
            params.append(buy_url)
        if category is not None:
            updates.append('category = ?')
            params.append(category if category else None)

        if not updates:
            conn.close()
            return False

        params.append(book_id)
        query = f'UPDATE library_books SET {", ".join(updates)} WHERE id = ?'

        cursor.execute(query, params)
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def delete_library_book(self, book_id: int) -> bool:
        """Delete a library book and all its files"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM library_books WHERE id = ?', (book_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def set_book_display_order(self, book_id: int, order: int) -> bool:
        """Set display order for a library book"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE library_books
            SET display_order = ?
            WHERE id = ?
        ''', (order, book_id))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def get_library_book(self, book_id: int) -> Optional[Tuple]:
        """Get a single library book by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, title, author, description, buy_url, display_order, created_at, category
            FROM library_books
            WHERE id = ?
        ''', (book_id,))
        book = cursor.fetchone()
        conn.close()
        return book

    def get_all_library_books(self, limit: int = None, offset: int = 0, category: str = None) -> List[Tuple]:
        """Get all library books with pagination, sorted by display_order then author"""
        conn = self.get_connection()
        cursor = conn.cursor()

        where_clause = ""
        params = []
        if category:
            where_clause = "WHERE category = ?"
            params.append(category)

        if limit:
            cursor.execute(f'''
                SELECT id, title, author, description, buy_url, display_order, created_at, category
                FROM library_books
                {where_clause}
                ORDER BY display_order ASC, author ASC, title ASC
                LIMIT ? OFFSET ?
            ''', params + [limit, offset])
        else:
            cursor.execute(f'''
                SELECT id, title, author, description, buy_url, display_order, created_at, category
                FROM library_books
                {where_clause}
                ORDER BY display_order ASC, author ASC, title ASC
            ''', params)

        books = cursor.fetchall()
        conn.close()
        return books

    def count_library_books(self, category: str = None) -> int:
        """Count total library books"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if category:
            cursor.execute('SELECT COUNT(*) FROM library_books WHERE category = ?', (category,))
        else:
            cursor.execute('SELECT COUNT(*) FROM library_books')
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_library_authors(self) -> List[str]:
        """Get unique authors from library"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT author
            FROM library_books
            ORDER BY author
        ''')
        authors = [row[0] for row in cursor.fetchall()]
        conn.close()
        return authors

    def get_library_books_by_author(self, author: str) -> List[Tuple]:
        """Get all library books by a specific author"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, title, author, description, buy_url, created_at, category
            FROM library_books
            WHERE author = ?
            ORDER BY title
        ''', (author,))
        books = cursor.fetchall()
        conn.close()
        return books

    def get_library_categories_with_counts(self) -> dict:
        """Get count of books in each category"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT category, COUNT(*) as count
            FROM library_books
            WHERE category IS NOT NULL
            GROUP BY category
        ''')
        result = {row['category']: row['count'] for row in cursor.fetchall()}
        conn.close()
        return result

    # Book files operations
    def add_book_file(self, library_book_id: int, format: str,
                      file_id: str = None, file_path: str = None,
                      file_size: int = None) -> int:
        """Add a file format to a library book"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO book_files (library_book_id, format, file_id, file_path, file_size)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(library_book_id, format) DO UPDATE SET
                file_id = excluded.file_id,
                file_path = excluded.file_path,
                file_size = excluded.file_size
        ''', (library_book_id, format, file_id, file_path, file_size))
        file_record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return file_record_id

    def update_book_file_id(self, library_book_id: int, format: str, file_id: str) -> bool:
        """Update Telegram file_id for a book file (for caching)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE book_files
            SET file_id = ?
            WHERE library_book_id = ? AND format = ?
        ''', (file_id, library_book_id, format))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def get_book_files(self, library_book_id: int) -> List[Tuple]:
        """Get all files for a library book"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, format, file_id, file_path, file_size
            FROM book_files
            WHERE library_book_id = ?
            ORDER BY format
        ''', (library_book_id,))
        files = cursor.fetchall()
        conn.close()
        return files

    def get_book_file(self, library_book_id: int, format: str) -> Optional[Tuple]:
        """Get a specific file format for a book"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, format, file_id, file_path, file_size
            FROM book_files
            WHERE library_book_id = ? AND format = ?
        ''', (library_book_id, format))
        file = cursor.fetchone()
        conn.close()
        return file

    def delete_book_file(self, library_book_id: int, format: str) -> bool:
        """Delete a specific file format from a book"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM book_files
            WHERE library_book_id = ? AND format = ?
        ''', (library_book_id, format))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
