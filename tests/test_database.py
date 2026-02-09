"""Тесты для модулей базы данных (временный файл SQLite)."""

import os
import tempfile
import pytest
from src.database.models import Database


@pytest.fixture
def db():
    """Создать тестовую БД во временном файле."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    database = Database(db_path=path)
    yield database
    os.unlink(path)


# === BooksMixin ===

class TestBooks:
    """Тесты операций с книгами."""

    def test_add_book(self, db):
        book_id = db.add_book("Размышления", "Марк Аврелий")
        assert book_id is not None
        assert book_id > 0

    def test_get_all_books(self, db):
        db.add_book("Размышления", "Марк Аврелий")
        db.add_book("Письма к Луцилию", "Сенека")
        books = db.get_all_books()
        assert len(books) == 2

    def test_delete_book(self, db):
        book_id = db.add_book("Размышления", "Марк Аврелий")
        result = db.delete_book(book_id)
        assert result is True
        books = db.get_all_books()
        assert len(books) == 0

    def test_delete_nonexistent_book(self, db):
        result = db.delete_book(999)
        assert result is False

    def test_delete_book_with_quotes(self, db):
        book_id = db.add_book("Размышления", "Марк Аврелий")
        db.add_quote("Цитата 1", "quotes", book_id=book_id)
        db.delete_book(book_id, delete_quotes=True)
        quotes = db.get_all_quotes()
        assert len(quotes) == 0

    def test_get_or_create_manual_book(self, db):
        book_id_1 = db.get_or_create_manual_book("CLI")
        book_id_2 = db.get_or_create_manual_book("CLI")
        assert book_id_1 == book_id_2

    def test_get_or_create_manual_book_different_sources(self, db):
        book_id_cli = db.get_or_create_manual_book("CLI")
        book_id_tg = db.get_or_create_manual_book("Telegram")
        assert book_id_cli != book_id_tg


# === QuotesMixin ===

class TestQuotes:
    """Тесты операций с цитатами."""

    def test_add_quote(self, db):
        quote_id = db.add_quote("Будь стойким.", "quotes")
        assert quote_id is not None
        assert quote_id > 0

    def test_add_quote_with_all_fields(self, db):
        book_id = db.add_book("Размышления", "Марк Аврелий")
        quote_id = db.add_quote(
            "Будь стойким.", "quotes",
            book_id=book_id,
            quote_author="Марк Аврелий",
            quote_source="Книга V"
        )
        quote = db.get_quote_by_id(quote_id)
        assert quote['text'] == "Будь стойким."
        assert quote['quote_author'] == "Марк Аврелий"
        assert quote['quote_source'] == "Книга V"

    def test_find_exact_duplicate(self, db):
        db.add_quote("Будь стойким.", "quotes")
        duplicate = db.find_exact_duplicate("Будь стойким.")
        assert duplicate is not None

    def test_find_no_duplicate(self, db):
        result = db.find_exact_duplicate("Несуществующая цитата")
        assert result is None

    def test_add_duplicate_returns_existing_id(self, db):
        id_1 = db.add_quote("Будь стойким.", "quotes")
        id_2 = db.add_quote("Будь стойким.", "quotes")
        assert id_1 == id_2

    def test_get_quote_by_id(self, db):
        quote_id = db.add_quote("Будь стойким.", "quotes")
        quote = db.get_quote_by_id(quote_id)
        assert quote is not None
        assert quote['text'] == "Будь стойким."

    def test_get_quote_by_id_nonexistent(self, db):
        quote = db.get_quote_by_id(999)
        assert quote is None

    def test_update_quote_text(self, db):
        quote_id = db.add_quote("Старый текст", "quotes")
        result = db.update_quote(quote_id, text="Новый текст")
        assert result is True
        quote = db.get_quote_by_id(quote_id)
        assert quote['text'] == "Новый текст"

    def test_update_quote_category(self, db):
        quote_id = db.add_quote("Текст", "quotes")
        result = db.update_quote(quote_id, category="daily")
        assert result is True
        quote = db.get_quote_by_id(quote_id)
        assert quote['category'] == "daily"

    def test_update_quote_no_fields(self, db):
        quote_id = db.add_quote("Текст", "quotes")
        result = db.update_quote(quote_id)
        assert result is False

    def test_delete_quote(self, db):
        quote_id = db.add_quote("Будь стойким.", "quotes")
        result = db.delete_quote(quote_id)
        assert result is True
        assert db.get_quote_by_id(quote_id) is None

    def test_delete_nonexistent_quote(self, db):
        result = db.delete_quote(999)
        assert result is False

    def test_get_all_quotes(self, db):
        db.add_quote("Цитата 1", "quotes")
        db.add_quote("Цитата 2", "daily", day_of_year=1)
        quotes = db.get_all_quotes()
        assert len(quotes) == 2

    def test_get_all_quotes_filtered(self, db):
        db.add_quote("Цитата 1", "quotes")
        db.add_quote("Цитата 2", "daily", day_of_year=1)
        quotes = db.get_all_quotes(category="quotes")
        assert len(quotes) == 1
        assert quotes[0]['category'] == "quotes"

    def test_get_random_quote(self, db):
        db.add_user(1, "test_user")
        db.add_quote("Будь стойким.", "quotes")
        quote = db.get_random_quote(user_id=1, category="quotes")
        assert quote is not None
        assert quote['text'] == "Будь стойким."

    def test_get_random_quote_skips_sent(self, db):
        db.add_user(1, "test_user")
        q1 = db.add_quote("Цитата 1", "quotes")
        db.add_quote("Цитата 2", "quotes")
        db.mark_quote_as_sent(1, q1)
        quote = db.get_random_quote(user_id=1, category="quotes")
        assert quote['text'] == "Цитата 2"

    def test_get_random_quote_resets_when_all_sent(self, db):
        db.add_user(1, "test_user")
        q1 = db.add_quote("Единственная цитата", "quotes")
        db.mark_quote_as_sent(1, q1)
        quote = db.get_random_quote(user_id=1, category="quotes")
        assert quote is not None

    def test_mark_quote_as_sent(self, db):
        db.add_user(1, "test_user")
        q_id = db.add_quote("Цитата", "quotes")
        db.mark_quote_as_sent(1, q_id)
        # Вторая цитата должна быть выбрана вместо отправленной
        q2 = db.add_quote("Цитата 2", "quotes")
        quote = db.get_random_quote(user_id=1, category="quotes")
        assert quote['id'] == q2


# === UsersMixin ===

class TestUsers:
    """Тесты операций с пользователями."""

    def test_add_user(self, db):
        result = db.add_user(123, "test_user", "Test")
        assert result is True

    def test_get_user(self, db):
        db.add_user(123, "test_user", "Test")
        user = db.get_user(123)
        assert user is not None
        assert user['username'] == "test_user"
        assert user['first_name'] == "Test"

    def test_get_nonexistent_user(self, db):
        user = db.get_user(999)
        assert user is None

    def test_add_user_updates_existing(self, db):
        db.add_user(123, "old_name", "Old")
        db.add_user(123, "new_name", "New")
        user = db.get_user(123)
        assert user['username'] == "new_name"
        assert user['first_name'] == "New"

    def test_get_all_users(self, db):
        db.add_user(1, "user1")
        db.add_user(2, "user2")
        users = db.get_all_users()
        assert len(users) == 2

    def test_toggle_user_active(self, db):
        db.add_user(123, "test_user")
        db.toggle_user_active(123, False)
        user = db.get_user(123)
        assert user['is_active'] == 0

    def test_toggle_user_active_back(self, db):
        db.add_user(123, "test_user")
        db.toggle_user_active(123, False)
        db.toggle_user_active(123, True)
        user = db.get_user(123)
        assert user['is_active'] == 1

    def test_get_users_by_time_slot(self, db):
        db.add_user(1, "user1")
        db.add_user(2, "user2")
        db.update_user_preferences(2, time_slot="evening")
        morning_users = db.get_users_by_time_slot("morning")
        assert len(morning_users) == 1
        assert morning_users[0]['user_id'] == 1

    def test_update_user_preferences(self, db):
        db.add_user(123, "test_user")
        db.update_user_preferences(123, category="daily", time_slot="evening")
        user = db.get_user(123)
        assert user['category_preference'] == "daily"
        assert user['time_slot'] == "evening"


# === Подписки (часть UsersMixin) ===

class TestSubscriptions:
    """Тесты операций с подписками."""

    def test_add_subscription(self, db):
        db.add_user(123, "test_user")
        result = db.add_subscription(123, "quotes", "morning")
        assert result is True

    def test_get_user_subscriptions(self, db):
        db.add_user(123, "test_user")
        db.add_subscription(123, "quotes", "morning")
        db.add_subscription(123, "daily", "evening")
        subs = db.get_user_subscriptions(123)
        assert len(subs) == 2

    def test_remove_subscription(self, db):
        db.add_user(123, "test_user")
        db.add_subscription(123, "quotes", "morning")
        result = db.remove_subscription(123, "quotes")
        assert result is True
        subs = db.get_user_subscriptions(123)
        assert len(subs) == 0

    def test_remove_nonexistent_subscription(self, db):
        db.add_user(123, "test_user")
        result = db.remove_subscription(123, "quotes")
        assert result is False

    def test_has_subscription(self, db):
        db.add_user(123, "test_user")
        db.add_subscription(123, "quotes", "morning")
        assert db.has_subscription(123, "quotes") is True
        assert db.has_subscription(123, "daily") is False

    def test_get_subscriptions_by_time(self, db):
        db.add_user(1, "user1")
        db.add_user(2, "user2")
        db.add_subscription(1, "quotes", "morning")
        db.add_subscription(2, "daily", "morning")
        subs = db.get_subscriptions_by_time("morning")
        assert len(subs) == 2

    def test_get_subscriptions_by_time_and_category(self, db):
        db.add_user(1, "user1")
        db.add_user(2, "user2")
        db.add_subscription(1, "quotes", "morning")
        db.add_subscription(2, "daily", "morning")
        subs = db.get_subscriptions_by_time("morning", category="quotes")
        assert len(subs) == 1

    def test_toggle_subscription_active(self, db):
        db.add_user(123, "test_user")
        db.add_subscription(123, "quotes", "morning")
        db.toggle_subscription_active(123, "quotes", False)
        subs = db.get_user_subscriptions(123)
        assert subs[0]['is_active'] == 0

    def test_subscription_upsert(self, db):
        db.add_user(123, "test_user")
        db.add_subscription(123, "quotes", "morning")
        db.add_subscription(123, "quotes", "evening")
        subs = db.get_user_subscriptions(123)
        assert len(subs) == 1
        assert subs[0]['time_slot'] == "evening"


# === FavoritesMixin ===

class TestFavorites:
    """Тесты операций с избранным."""

    def test_add_to_favorites(self, db):
        db.add_user(123, "test_user")
        q_id = db.add_quote("Цитата", "quotes")
        result = db.add_to_favorites(123, q_id)
        assert result is True

    def test_add_duplicate_favorite(self, db):
        db.add_user(123, "test_user")
        q_id = db.add_quote("Цитата", "quotes")
        db.add_to_favorites(123, q_id)
        result = db.add_to_favorites(123, q_id)
        assert result is False

    def test_remove_from_favorites(self, db):
        db.add_user(123, "test_user")
        q_id = db.add_quote("Цитата", "quotes")
        db.add_to_favorites(123, q_id)
        result = db.remove_from_favorites(123, q_id)
        assert result is True

    def test_remove_nonexistent_favorite(self, db):
        db.add_user(123, "test_user")
        result = db.remove_from_favorites(123, 999)
        assert result is False

    def test_is_favorite(self, db):
        db.add_user(123, "test_user")
        q_id = db.add_quote("Цитата", "quotes")
        assert db.is_favorite(123, q_id) is False
        db.add_to_favorites(123, q_id)
        assert db.is_favorite(123, q_id) is True

    def test_get_user_favorites(self, db):
        db.add_user(123, "test_user")
        q1 = db.add_quote("Цитата 1", "quotes")
        q2 = db.add_quote("Цитата 2", "quotes")
        db.add_to_favorites(123, q1)
        db.add_to_favorites(123, q2)
        favorites = db.get_user_favorites(123)
        assert len(favorites) == 2

    def test_get_user_favorites_pagination(self, db):
        db.add_user(123, "test_user")
        for i in range(5):
            q_id = db.add_quote(f"Цитата {i}", "quotes")
            db.add_to_favorites(123, q_id)
        page1 = db.get_user_favorites(123, limit=2, offset=0)
        page2 = db.get_user_favorites(123, limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2

    def test_count_user_favorites(self, db):
        db.add_user(123, "test_user")
        assert db.count_user_favorites(123) == 0
        q1 = db.add_quote("Цитата 1", "quotes")
        q2 = db.add_quote("Цитата 2", "quotes")
        db.add_to_favorites(123, q1)
        db.add_to_favorites(123, q2)
        assert db.count_user_favorites(123) == 2
