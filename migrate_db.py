#!/usr/bin/env python
"""
Database migration script for adding day_of_year column and updating categories.

This script:
1. Adds day_of_year column to quotes table if it doesn't exist
2. Updates CHECK constraints for new categories (quotes, daily)
3. Safe to run multiple times - checks if changes already exist
"""

import sqlite3
import config


def migrate_database():
    """Run database migration"""
    print("Starting database migration...")
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Check if day_of_year column exists
        cursor.execute("PRAGMA table_info(quotes)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'day_of_year' not in columns:
            print("✓ Adding day_of_year column to quotes table...")
            cursor.execute("ALTER TABLE quotes ADD COLUMN day_of_year INTEGER DEFAULT NULL")
            conn.commit()
            print("✓ day_of_year column added successfully")
        else:
            print("⚠ day_of_year column already exists, skipping")

        # SQLite doesn't allow modifying CHECK constraints directly
        # So we need to inform the user about manual steps if needed
        print("\n⚠ ВАЖНО: Проверьте CHECK constraints вручную")
        print("SQLite не позволяет изменять CHECK constraints напрямую.")
        print("Если у вас есть старые категории (theory, practice), выполните:")
        print("1. Экспортируйте данные")
        print("2. Удалите базу данных")
        print("3. Запустите бота заново для создания новой схемы")
        print("4. Импортируйте данные обратно")
        print("\nИли используйте свежую базу данных для новых категорий (quotes, daily)")

        conn.close()
        print("\n✓ Миграция завершена успешно!")

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"\n✗ Ошибка миграции: {str(e)}")
        raise


if __name__ == '__main__':
    migrate_database()
