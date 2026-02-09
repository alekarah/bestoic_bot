"""Общие утилиты для CLI админских команд"""

import click
from src.database.models import Database

db = Database()

# Маппинг названий категорий
CATEGORY_MAP = {
    'quotes': 'quotes',
    'q': 'quotes',
    'цитаты': 'quotes',
    'daily': 'daily',
    'd': 'daily',
    'ежедневно': 'daily'
}

CATEGORY_DISPLAY = {
    'quotes': 'Цитаты',
    'daily': 'Стоицизм на каждый день'
}

# Категории книг библиотеки
LIBRARY_CATEGORY_MAP = {
    'classic': 'classic',
    'c': 'classic',
    'классика': 'classic',
    'modern': 'modern',
    'm': 'modern',
    'современные': 'modern',
    '': None,
    '-': None
}

LIBRARY_CATEGORY_DISPLAY = {
    'classic': 'Классические труды',
    'modern': 'Современные авторы'
}


def normalize_library_category(value):
    """Преобразовать пользовательский ввод во внутреннее название категории библиотеки"""
    if not value or value == '-':
        return None
    normalized = LIBRARY_CATEGORY_MAP.get(value.lower())
    if normalized is None and value.lower() not in LIBRARY_CATEGORY_MAP:
        raise click.BadParameter(
            'Категория: Классика (c) или Современные (m), или пустое для без категории'
        )
    return normalized


def normalize_category(value):
    """Преобразовать пользовательский ввод во внутреннее название категории"""
    normalized = CATEGORY_MAP.get(value.lower())
    if not normalized:
        raise click.BadParameter(
            f'Категория должна быть: Цитаты (q) или Стоицизм на каждый день (d)'
        )
    return normalized
