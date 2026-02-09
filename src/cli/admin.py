"""
Admin CLI for Bestoic Bot
Управление книгами и цитатами через командную строку
"""

import click
from src.cli.common import db
from src.cli.quotes import quote
from src.cli.library import library
from src.cli.users import users


@click.group()
def cli():
    """Bestoic Bot Admin CLI - Управление книгами и цитатами"""
    pass


# Регистрация групп команд
cli.add_command(quote)
cli.add_command(library)
cli.add_command(users)


@cli.command('stats')
def stats():
    """Показать статистику"""
    books = db.get_all_books()
    all_quotes = db.get_all_quotes()
    quotes_category = db.get_all_quotes('quotes')
    daily_category = db.get_all_quotes('daily')
    library_count = db.count_library_books()

    click.echo('\n' + '='*50)
    click.echo('СТАТИСТИКА BESTOIC BOT')
    click.echo('='*50)
    click.echo(f'Всего книг (источники цитат): {len(books)}')
    click.echo(f'Всего цитат: {len(all_quotes)}')
    click.echo('-'*50)
    click.echo(f'  Цитаты: {len(quotes_category)}')
    click.echo(f'  Стоицизм на каждый день: {len(daily_category)}')
    click.echo('-'*50)
    click.echo(f'Библиотека (скачиваемые книги): {library_count}')
    click.echo('='*50 + '\n')


if __name__ == '__main__':
    cli()
