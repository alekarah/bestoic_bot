"""Парсер цитат: извлечение текста, авторов, форматирование для Telegram."""

import re
from typing import Tuple, Optional, List, Dict
from datetime import datetime


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


def parse_daily_stoicism_book(text: str) -> List[Dict]:
    """
    Парсинг книги формата «Стоицизм на каждый день» на отдельные записи.

    Формат:
    ДАТА (напр. "1 ЯНВАРЯ")
    Заголовок (на следующей строке, без пустой строки после даты)

    Текст цитаты (может быть многострочным, без пустых строк внутри)

    Атрибуция (Автор / Источник ИЛИ просто имя автора, короткая одна строка)

    Текст размышления (может быть многострочным)


    В 4 конкретных дня (9 мар, 22 мая, 13 окт, 1 нояб) есть 2 цитаты:
    Цитата1

    Атрибуция1

    Цитата2

    Атрибуция2

    Размышление

    Returns:
        Список словарей с ключами: day_of_year, title, text, quote_author, quote_source
    """
    # Русские названия месяцев → числа
    MONTHS_RU = {
        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
        'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
        'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
    }

    def is_attribution(text):
        """
        Проверяет, является ли текст строкой атрибуции.
        Атрибуция — КОРОТКАЯ, ОДНОСТРОЧНАЯ запись с именем автора и опционально источником.
        Примеры: "Эпиктет / Беседы", "Сенека", "Феогнид Мегарский", "Марк Аврелий / Размышления"

        НЕ атрибуция: "Барбара Джордан / лидер правозащитного движения" (продолжение предложения после /)
        """
        text = text.strip()
        # Должна быть одной строкой (без переносов)
        if '\n' in text:
            return False
        # Должна быть КОРОТКОЙ — атрибуция обычно < 50 символов
        if len(text) > 50:
            return False
        # Должна начинаться с заглавной буквы (имя)
        if not text or not text[0].isupper():
            return False
        # Должна быть очень короткой (имя автора 1-3 слова + источник 1-4 слова)
        words = text.split()
        if len(words) > 6:
            return False
        # Если содержит "/", проверяем:
        # 1. Часть автора — 1-3 слова
        # 2. Часть источника начинается с заглавной (название книги) и короткая
        if '/' in text:
            parts = text.split('/', 1)
            author_part = parts[0].strip()
            source_part = parts[1].strip() if len(parts) > 1 else ''
            # Автор должен быть 1-3 слова (имя)
            author_words = author_part.split()
            if len(author_words) > 3:
                return False
            # Источник должен начинаться с заглавной буквы (название книги)
            if source_part and not source_part[0].isupper():
                return False
            # Источник должен быть коротким (макс. 1-4 слова, название книги)
            source_words = source_part.split()
            if len(source_words) > 5:
                return False
        return True

    def parse_attribution(text):
        """Парсинг атрибуции: извлечение автора и источника"""
        text = text.strip()
        if '/' in text:
            parts = text.split('/', 1)
            return parts[0].strip(), parts[1].strip() if len(parts) > 1 else None
        return text, None

    # Разделяем по заголовкам дат (напр. "1 ЯНВАРЯ", "29 ФЕВРАЛЯ")
    # Дата в начале строки, за ней перенос и заголовок
    date_pattern = r'(\d+\s+[А-ЯЁ]+)\n'
    parts = re.split(date_pattern, text)

    entries = []
    i = 1  # Пропускаем первую пустую часть
    while i < len(parts) - 1:
        date_header = parts[i].strip()
        content = parts[i + 1].strip()

        # Парсим дату
        match = re.match(r'(\d+)\s+([А-ЯЁ]+)', date_header)
        if not match:
            i += 2
            continue

        day = int(match.group(1))
        month_name = match.group(2).lower()

        # Получаем номер месяца
        month = None
        for key, value in MONTHS_RU.items():
            if key.startswith(month_name.lower()[:3]):  # Совпадение по первым 3 буквам
                month = value
                break

        if not month:
            i += 2
            continue

        # Вычисляем день года
        try:
            date_obj = datetime(2024, month, day)  # Используем високосный год для поддержки 29 февраля
            day_of_year = date_obj.timetuple().tm_yday
        except ValueError:
            i += 2
            continue

        # Парсим содержимое по пустым строкам
        # Разделяем по двойному переносу (пустая строка = разделитель абзацев)
        content_parts = [p.strip() for p in content.split('\n\n') if p.strip()]

        if len(content_parts) < 2:
            i += 2
            continue

        # [0] = Заголовок
        title = content_parts[0].strip()

        # Ищем первую атрибуцию (идёт после первой цитаты)
        # Структура: Заголовок, Цитата, Атрибуция, [Цитата2, Атрибуция2], Размышление
        quote_text = None
        quote_author = None
        quote_source = None

        # [1] — всегда первая цитата
        if len(content_parts) >= 2:
            quote_text = content_parts[1].strip()

        # [2] — должна быть атрибуция первой цитаты
        if len(content_parts) >= 3 and is_attribution(content_parts[2]):
            quote_author, quote_source = parse_attribution(content_parts[2])

        if not quote_text:
            # Запасной вариант: используем вторую часть как цитату
            if len(content_parts) >= 2:
                quote_text = content_parts[1]

        # Используем содержимое как полный текст (уже начинается с заголовка)
        full_text = content

        entries.append({
            'day_of_year': day_of_year,
            'title': title,
            'text': full_text,
            'quote_author': quote_author,
            'quote_source': quote_source
        })

        i += 2

    return entries


def day_of_year_to_date(day_of_year: int) -> str:
    """Конвертация дня года (1-366) в строку с русской датой, напр. '9 марта'"""
    from datetime import datetime

    MONTHS_RU_GENITIVE = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }

    # Используем високосный год для поддержки дня 366
    date = datetime(2024, 1, 1) + __import__('datetime').timedelta(days=day_of_year - 1)
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
