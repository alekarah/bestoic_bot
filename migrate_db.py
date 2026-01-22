#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database migration script for adding day_of_year column and updating categories.

This script:
1. Adds day_of_year column to quotes table if it doesn't exist
2. Updates CHECK constraints for new categories (quotes, daily)
3. Safe to run multiple times - checks if changes already exist
"""

import sqlite3
import sys
import config

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def migrate_database():
    """Run database migration"""
    print("Starting database migration...")
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Check current schema for quotes table
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='quotes'")
        result = cursor.fetchone()

        if result is None:
            print("[!] quotes table does not exist, skipping migration")
            conn.close()
            return

        current_schema = result[0]

        # Check if we need to update the CHECK constraint
        needs_constraint_update = "'daily'" not in current_schema and "category IN" in current_schema

        # Check if day_of_year column exists
        cursor.execute("PRAGMA table_info(quotes)")
        columns = [col[1] for col in cursor.fetchall()]
        needs_day_of_year = 'day_of_year' not in columns

        if needs_constraint_update:
            print("[+] Updating CHECK constraint to include 'daily' category...")

            # SQLite requires recreating the table to change CHECK constraints
            # Step 1: Create new table with correct schema
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

            # Step 2: Copy data, converting old categories to 'quotes'
            cursor.execute('''
                INSERT INTO quotes_new (id, book_id, category, text, quote_author, quote_source, created_at, day_of_year)
                SELECT id, book_id,
                       CASE WHEN category IN ('theory', 'practice', 'quotes') THEN 'quotes' ELSE category END,
                       text, quote_author, quote_source, created_at,
                       CASE WHEN 'day_of_year' IN (SELECT name FROM pragma_table_info('quotes')) THEN day_of_year ELSE NULL END
                FROM quotes
            ''')

            # Step 3: Drop old table and rename new one
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
