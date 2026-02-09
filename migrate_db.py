#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт миграции базы данных: добавление колонки day_of_year и обновление категорий.

Скрипт выполняет:
1. Добавление колонки day_of_year в таблицу quotes (если отсутствует)
2. Обновление CHECK-ограничений для новых категорий (quotes, daily)
3. Безопасен для повторного запуска — проверяет наличие изменений
"""

import sqlite3
import sys
import config

# Исправление кодировки для консоли Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def migrate_database():
    """Запуск миграции базы данных"""
    print("Starting database migration...")
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Проверяем текущую схему таблицы quotes
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='quotes'")
        result = cursor.fetchone()

        if result is None:
            print("[!] quotes table does not exist, skipping migration")
            conn.close()
            return

        current_schema = result[0]

        # Проверяем, нужно ли обновить CHECK-ограничение
        needs_constraint_update = "'daily'" not in current_schema and "category IN" in current_schema

        # Проверяем, существует ли колонка day_of_year
        cursor.execute("PRAGMA table_info(quotes)")
        columns = [col[1] for col in cursor.fetchall()]
        needs_day_of_year = 'day_of_year' not in columns

        if needs_constraint_update:
            print("[+] Updating CHECK constraint to include 'daily' category...")

            # SQLite требует пересоздание таблицы для изменения CHECK-ограничений
            # Шаг 1: Создаём новую таблицу с правильной схемой
            cursor.execute('''
                CREATE TABLE quotes_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER,
                    category TEXT NOT NULL CHECK(category IN ('quotes', 'daily')),
                    text TEXT NOT NULL,
                    quote_author TEXT,
                    quote_source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    day_of_year INTEGER DEFAULT NULL,
                    FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE SET NULL
                )
            ''')

            # Шаг 2: Копируем данные, конвертируя старые категории в 'quotes'
            cursor.execute('''
                INSERT INTO quotes_new (id, book_id, category, text, quote_author, quote_source, created_at, day_of_year)
                SELECT id, book_id,
                       CASE WHEN category IN ('theory', 'practice', 'quotes') THEN 'quotes' ELSE category END,
                       text, quote_author, quote_source, created_at,
                       CASE WHEN 'day_of_year' IN (SELECT name FROM pragma_table_info('quotes')) THEN day_of_year ELSE NULL END
                FROM quotes
            ''')

            # Шаг 3: Удаляем старую таблицу и переименовываем новую
            cursor.execute('DROP TABLE quotes')
            cursor.execute('ALTER TABLE quotes_new RENAME TO quotes')

            conn.commit()
            print("[+] CHECK constraint updated successfully")
            print("[+] Old categories (theory, practice) converted to 'quotes'")

        elif needs_day_of_year:
            print("[+] Adding day_of_year column to quotes table...")
            cursor.execute("ALTER TABLE quotes ADD COLUMN day_of_year INTEGER DEFAULT NULL")
            conn.commit()
            print("[+] day_of_year column added successfully")
        else:
            print("[!] Database schema is already up to date")

        conn.close()
        print("\n[+] Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"\n[X] Migration error: {str(e)}")
        raise


if __name__ == '__main__':
    migrate_database()
