"""Shared utilities for CLI admin commands"""

import click
from src.database.models import Database

db = Database()

# Mapping for category names
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

# Library book categories
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
    """Convert user input to internal library category name"""
    if not value or value == '-':
        return None
    normalized = LIBRARY_CATEGORY_MAP.get(value.lower())
    if normalized is None and value.lower() not in LIBRARY_CATEGORY_MAP:
        raise click.BadParameter(
            'Категория: Классика (c) или Современные (m), или пустое для без категории'
        )
    return normalized


def normalize_category(value):
    """Convert user input to internal category name"""
    normalized = CATEGORY_MAP.get(value.lower())
    if not normalized:
        raise click.BadParameter(
            f'Категория должна быть: Цитаты (q) или Стоицизм на каждый день (d)'
        )
    return normalized
