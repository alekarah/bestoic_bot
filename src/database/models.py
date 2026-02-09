"""Модели базы данных — основной класс Database, собранный из миксинов."""

import sqlite3
import config

from src.database.books import BooksMixin
from src.database.quotes import QuotesMixin
from src.database.users import UsersMixin
from src.database.favorites import FavoritesMixin
from src.database.library import LibraryMixin
from src.database.statistics import StatisticsMixin


class Database(BooksMixin, QuotesMixin, UsersMixin, FavoritesMixin, LibraryMixin, StatisticsMixin):
    """Основной класс базы данных, объединяющий все миксины операций."""

    def __init__(self, db_path: str = config.DATABASE_PATH):
        """Инициализация подключения к базе данных."""
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Создать и вернуть соединение с базой данных."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Инициализация таблиц базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Таблица книг
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица цитат
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                category TEXT NOT NULL CHECK(category IN ('quotes', 'daily')),
                text TEXT NOT NULL,
                quote_author TEXT,
                quote_source TEXT,
                day_of_year INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE SET NULL
            )
        ''')

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                category_preference TEXT DEFAULT 'all' CHECK(category_preference IN ('quotes', 'daily', 'all')),
                time_slot TEXT DEFAULT 'morning' CHECK(time_slot IN ('morning', 'day', 'evening')),
                is_active INTEGER DEFAULT 1,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица отправленных цитат
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

        # Таблица подписок пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL CHECK(category IN ('quotes', 'daily')),
                time_slot TEXT NOT NULL CHECK(time_slot IN ('morning', 'day', 'evening')),
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                UNIQUE(user_id, category)
            )
        ''')

        # Таблица избранного
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                quote_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY (quote_id) REFERENCES quotes (id) ON DELETE CASCADE,
                UNIQUE(user_id, quote_id)
            )
        ''')

        # Таблица библиотеки (книги для скачивания)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS library_books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                description TEXT,
                buy_url TEXT,
                display_order INTEGER DEFAULT 999,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица файлов книг (несколько форматов на книгу)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS book_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                library_book_id INTEGER NOT NULL,
                format TEXT NOT NULL,
                file_id TEXT,
                file_path TEXT,
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (library_book_id) REFERENCES library_books (id) ON DELETE CASCADE,
                UNIQUE(library_book_id, format)
            )
        ''')

        # Миграция: добавить колонку display_order если её нет
        cursor.execute("PRAGMA table_info(library_books)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'display_order' not in columns:
            cursor.execute('ALTER TABLE library_books ADD COLUMN display_order INTEGER DEFAULT 999')

        # Миграция: добавить колонку category в library_books если её нет
        if 'category' not in columns:
            cursor.execute('ALTER TABLE library_books ADD COLUMN category TEXT DEFAULT NULL')

        conn.commit()
        conn.close()
