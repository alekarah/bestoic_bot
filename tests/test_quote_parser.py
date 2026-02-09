"""Тесты для модуля quote_parser."""

import pytest
from src.utils.quote_parser import parse_quote, day_of_year_to_date, format_quote_for_telegram


class TestParseQuote:
    """Тесты парсинга цитат: извлечение текста, автора и источника."""

    def test_author_and_source_with_slash(self):
        text = "Будь стойким.\n\n— Марк Аврелий / Размышления"
        quote, author, source = parse_quote(text)
        assert quote == "Будь стойким."
        assert author == "Марк Аврелий"
        assert source == "Размышления"

    def test_author_and_source_with_comma(self):
        text = "Будь стойким.\n\nМарк Аврелий, Размышления"
        quote, author, source = parse_quote(text)
        assert quote == "Будь стойким."
        assert author == "Марк Аврелий"
        assert source == "Размышления"

    def test_author_with_em_dash_prefix(self):
        text = "Будь стойким.\n\n— Марк Аврелий"
        quote, author, source = parse_quote(text)
        assert quote == "Будь стойким."
        assert author == "Марк Аврелий"
        assert source is None

    def test_author_with_en_dash_prefix(self):
        text = "Будь стойким.\n\n– Марк Аврелий"
        quote, author, source = parse_quote(text)
        assert author == "Марк Аврелий"

    def test_author_with_hyphen_prefix(self):
        text = "Будь стойким.\n\n- Марк Аврелий"
        quote, author, source = parse_quote(text)
        assert author == "Марк Аврелий"

    def test_only_author_no_source(self):
        text = "Будь стойким.\n\nСенека"
        quote, author, source = parse_quote(text)
        assert quote == "Будь стойким."
        assert author == "Сенека"
        assert source is None

    def test_no_attribution(self):
        text = "Будь стойким."
        quote, author, source = parse_quote(text)
        assert quote == "Будь стойким."
        assert author is None
        assert source is None

    def test_multiline_quote(self):
        text = "Первая строка.\n\nВторая строка.\n\n— Марк Аврелий"
        quote, author, source = parse_quote(text)
        assert quote == "Первая строка.\n\nВторая строка."
        assert author == "Марк Аврелий"

    def test_whitespace_stripping(self):
        text = "  Будь стойким.  \n\n  — Марк Аврелий  "
        quote, author, source = parse_quote(text)
        assert quote == "Будь стойким."
        assert author == "Марк Аврелий"


class TestDayOfYearToDate:
    """Тесты конвертации дня года в русскую дату."""

    def test_first_day(self):
        assert day_of_year_to_date(1) == "1 января"

    def test_march_9(self):
        assert day_of_year_to_date(69) == "9 марта"

    def test_leap_day(self):
        assert day_of_year_to_date(60) == "29 февраля"

    def test_last_day(self):
        assert day_of_year_to_date(366) == "31 декабря"

    def test_new_year_eve(self):
        assert day_of_year_to_date(365) == "30 декабря"


class TestFormatQuoteForTelegram:
    """Тесты форматирования цитат для Telegram."""

    def test_quotes_category_no_header(self):
        result = format_quote_for_telegram(
            quote_text="Будь стойким.",
            category="quotes",
            quote_author="Марк Аврелий"
        )
        assert not result.startswith("💭")
        assert "Будь стойким." in result
        assert "— Марк Аврелий" in result

    def test_quotes_category_with_author_and_source(self):
        result = format_quote_for_telegram(
            quote_text="Будь стойким.",
            category="quotes",
            quote_author="Марк Аврелий",
            quote_source="Размышления"
        )
        assert "— Марк Аврелий / Размышления" in result

    def test_quotes_category_fallback_to_book(self):
        result = format_quote_for_telegram(
            quote_text="Будь стойким.",
            category="quotes",
            book_author="Марк Аврелий",
            book_title="Размышления"
        )
        assert "— Марк Аврелий / Размышления" in result

    def test_quotes_category_quote_author_priority_over_book(self):
        result = format_quote_for_telegram(
            quote_text="Будь стойким.",
            category="quotes",
            quote_author="Сенека",
            book_author="Марк Аврелий",
            book_title="Размышления"
        )
        assert "Сенека" in result
        assert "Марк Аврелий" not in result

    def test_daily_category_with_date_header(self):
        result = format_quote_for_telegram(
            quote_text="Текст дня.",
            category="daily",
            day_of_year=69
        )
        assert result.startswith("📅 9 марта")
        assert "Текст дня." in result

    def test_daily_category_no_attribution_appended(self):
        result = format_quote_for_telegram(
            quote_text="Текст дня.",
            category="daily",
            quote_author="Марк Аврелий",
            day_of_year=1
        )
        # Для daily атрибуция НЕ добавляется в конце
        assert result.count("Марк Аврелий") == 0

    def test_quotes_no_author_no_book(self):
        result = format_quote_for_telegram(
            quote_text="Просто цитата.",
            category="quotes"
        )
        assert result == "Просто цитата."
        assert "—" not in result
