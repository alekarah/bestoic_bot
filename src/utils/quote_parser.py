"""Парсер цитат: извлечение текста, авторов, форматирование для Telegram."""

import re
from typing import Tuple, Optional
from datetime import datetime, timedelta


def parse_quote(text: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Парсинг цитаты: извлечение текста, автора и источника.

    Поддерживаемые форматы:
    - "Текст цитаты\n\n - Автор / Источник"
    - "Текст цитаты\n\n— Автор / Источник"
    - "Текст цитаты\n\nАвтор / Источник"

    Returns:
        Кортеж (текст_цитаты, автор, источник)
    """
    # Разделяем по двойному переносу строки, чтобы отделить цитату от атрибуции
    parts = text.split('\n\n')

    if len(parts) < 2:
        # Атрибуция не найдена
        return text.strip(), None, None

    # Цитата — всё, кроме последней части
    quote_text = '\n\n'.join(parts[:-1]).strip()
    attribution = parts[-1].strip()

    # Пытаемся извлечь автора и источник из атрибуции
    # Форматы:
    # - Автор / Источник
    # — Автор / Источник
    # Автор, Источник

    # Убираем распространённые префиксы
    attribution = re.sub(r'^[\-—–]\s*', '', attribution)

    # Разделяем по / или ,
    if '/' in attribution:
        parts = attribution.split('/', 1)
        author = parts[0].strip()
        source = parts[1].strip() if len(parts) > 1 else None
    elif ',' in attribution:
        parts = attribution.split(',', 1)
        author = parts[0].strip()
        source = parts[1].strip() if len(parts) > 1 else None
    else:
        # Только автор, без источника
        author = attribution.strip()
        source = None

    return quote_text, author, source


def day_of_year_to_date(day_of_year: int) -> str:
    """Конвертация дня года (1-366) в строку с русской датой, напр. '9 марта'"""
    MONTHS_RU_GENITIVE = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }

    # Используем високосный год для поддержки дня 366
    date = datetime(2024, 1, 1) + timedelta(days=day_of_year - 1)
    return f"{date.day} {MONTHS_RU_GENITIVE[date.month]}"


def format_quote_for_telegram(quote_text: str, category: str,
                              quote_author: Optional[str] = None,
                              quote_source: Optional[str] = None,
                              book_title: Optional[str] = None,
                              book_author: Optional[str] = None,
                              day_of_year: Optional[int] = None) -> str:
    """
    Форматирование цитаты для отправки в Telegram с правильной стилизацией.

    Args:
        quote_text: Основной текст цитаты
        category: Категория цитаты (quotes/daily)
        quote_author: Автор, извлечённый из самой цитаты
        quote_source: Источник, извлечённый из самой цитаты
        book_title: Название книги (из базы данных)
        book_author: Автор книги (из базы данных)
        day_of_year: День года (1-366) для категории daily

    Returns:
        Отформатированная строка сообщения
    """
    category_emoji = {
        'quotes': '💭',
        'daily': '📅'
    }

    # Для категории daily показываем дату вместо названия категории
    # Для категории quotes заголовок не нужен
    if category == 'daily' and day_of_year:
        header = f"📅 {day_of_year_to_date(day_of_year)}\n\n"
    elif category == 'quotes':
        header = ""  # Без заголовка для обычных цитат
    else:
        emoji = category_emoji.get(category, '💬')
        category_names = {
            'quotes': 'Цитаты',
            'daily': 'Стоицизм на каждый день'
        }
        header = f"{emoji} {category_names.get(category, category)}\n\n"

    # Начинаем с заголовка (если есть) и текста цитаты
    message = f"{header}{quote_text}"

    # Для категории 'daily' атрибуция уже встроена в текст
    # Не добавляем её повторно в конце
    if category != 'daily':
        # Добавляем атрибуцию
        # Приоритет: quote_author/quote_source > book_author/book_title
        if quote_author or quote_source:
            attribution_parts = []
            if quote_author:
                attribution_parts.append(quote_author)
            if quote_source:
                attribution_parts.append(quote_source)
            message += f"\n\n— {' / '.join(attribution_parts)}"
        elif book_title and book_author:
            message += f"\n\n— {book_author} / {book_title}"

    return message
