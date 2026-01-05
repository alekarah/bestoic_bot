import click
import os
from src.database.models import Database
from src.utils.quote_parser import parse_quote


db = Database()


# Mapping for category names
CATEGORY_MAP = {
    'theory': 'theory',
    't': 'theory',
    'теория': 'theory',
    'practice': 'practice',
    'p': 'practice',
    'практика': 'practice',
    'quotes': 'quotes',
    'q': 'quotes',
    'цитаты': 'quotes'
}

CATEGORY_DISPLAY = {
    'theory': 'Теория',
    'practice': 'Практика',
    'quotes': 'Цитаты'
}


def normalize_category(value):
    """Convert user input to internal category name"""
    normalized = CATEGORY_MAP.get(value.lower())
    if not normalized:
        raise click.BadParameter(
            f'Категория должна быть: Теория (t), Практика (p), или Цитаты (q)'
        )
    return normalized


@click.group()
def cli():
    """Bestoic Bot Admin CLI - Управление книгами и цитатами"""
    pass


# Book commands
@cli.group()
def book():
    """Управление книгами"""
    pass


@book.command('add')
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--title', prompt='Название книги', help='Название книги')
@click.option('--author', prompt='Автор', help='Автор книги')
@click.option('--category',
              prompt='Категория [Теория (t) / Практика (p) / Цитаты (q)]',
              help='Категория цитат из книги')
def add_book(file_path, title, author, category):
    """Загрузить книгу из файла и разделить на цитаты"""
    try:
        # Normalize category input
        category = normalize_category(category)

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add book to database
        book_id = db.add_book(title, author)
        click.echo(f'✓ Книга "{title}" добавлена (ID: {book_id})')

        # Split into paragraphs (quotes)
        # Use triple newline for stronger separation, or double as fallback
        if '\n\n\n' in content:
            paragraphs = [p.strip() for p in content.split('\n\n\n') if p.strip()]
        else:
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        added_count = 0
        for paragraph in paragraphs:
            # Skip very short paragraphs (likely not quotes)
            if len(paragraph) > 50:
                # Parse quote to extract author and source
                quote_text, quote_author, quote_source = parse_quote(paragraph)
                db.add_quote(quote_text, category, book_id, quote_author, quote_source)
                added_count += 1

        category_name = CATEGORY_DISPLAY.get(category, category)
        click.echo(f'✓ Добавлено {added_count} цитат из категории "{category_name}"')
        click.echo(f'✓ Всего обработано {len(paragraphs)} абзацев')

    except Exception as e:
        click.echo(f'✗ Ошибка: {str(e)}', err=True)


@book.command('list')
def list_books():
    """Показать все книги"""
    books = db.get_all_books()

    if not books:
        click.echo('Книги не найдены')
        return

    click.echo('\n' + '='*80)
    click.echo(f'{"ID":<5} {"Название":<40} {"Автор":<25} {"Дата"}')
    click.echo('='*80)

    for book in books:
        click.echo(f'{book["id"]:<5} {book["title"]:<40} {book["author"]:<25} {book["uploaded_at"][:10]}')

    click.echo('='*80 + '\n')


@book.command('delete')
@click.argument('book_id', type=int)
@click.confirmation_option(prompt='Вы уверены? Все цитаты из этой книги будут удалены.')
def delete_book(book_id):
    """Удалить книгу"""
    if db.delete_book(book_id):
        click.echo(f'✓ Книга ID:{book_id} удалена')
    else:
        click.echo(f'✗ Книга ID:{book_id} не найдена', err=True)


# Quote commands
@cli.group()
def quote():
    """Управление цитатами"""
    pass


@quote.command('add')
@click.option('--text', prompt='Текст цитаты (можно с атрибуцией через - Автор / Источник)', help='Текст цитаты')
@click.option('--category',
              prompt='Категория [Теория (t) / Практика (p) / Цитаты (q)]',
              help='Категория цитаты')
def add_quote(text, category):
    """Добавить новую цитату вручную"""
    # Normalize category input
    category = normalize_category(category)

    # Get or create manual quotes book
    manual_book_id = db.get_or_create_manual_book(source='CLI')

    # Parse quote to extract author and source if provided
    quote_text, quote_author, quote_source = parse_quote(text)
    quote_id = db.add_quote(quote_text, category, manual_book_id, quote_author, quote_source)

    category_name = CATEGORY_DISPLAY.get(category, category)
    click.echo(f'✓ Цитата добавлена (ID: {quote_id}) в категорию "{category_name}"')
    click.echo(f'  Книга: Ручные цитаты (CLI)')
    if quote_author:
        click.echo(f'  Автор: {quote_author}')
    if quote_source:
        click.echo(f'  Источник: {quote_source}')


@quote.command('list')
@click.option('--category',
              type=click.Choice(['theory', 'practice', 'quotes', 'all'], case_sensitive=False),
              default='all',
              help='Фильтр по категории')
@click.option('--limit', default=20, help='Количество цитат для показа')
def list_quotes(category, limit):
    """Показать все цитаты"""
    quotes = db.get_all_quotes(category if category != 'all' else None)

    if not quotes:
        click.echo('Цитаты не найдены')
        return

    click.echo(f'\nНайдено цитат: {len(quotes)}')
    click.echo(f'Показано первых: {min(limit, len(quotes))}\n')
    click.echo('='*80)

    for i, quote in enumerate(quotes[:limit], 1):
        book_info = f'{quote["title"]} - {quote["author"]}' if quote["title"] else 'Без книги'
        category_name = CATEGORY_DISPLAY.get(quote["category"], quote["category"])
        click.echo(f'\nID: {quote["id"]} | Категория: {category_name} | Книга: {book_info}')

        # Show quote author/source if available
        if quote["quote_author"] or quote["quote_source"]:
            attribution = []
            if quote["quote_author"]:
                attribution.append(quote["quote_author"])
            if quote["quote_source"]:
                attribution.append(quote["quote_source"])
            click.echo(f'Атрибуция: {" / ".join(attribution)}')

        click.echo('-'*80)

        # Show preview of quote (first 200 chars)
        text_preview = quote["text"][:200] + '...' if len(quote["text"]) > 200 else quote["text"]
        click.echo(text_preview)
        click.echo('='*80)


@quote.command('view')
@click.argument('quote_id', type=int)
def view_quote(quote_id):
    """Показать полный текст цитаты"""
    quotes = db.get_all_quotes()
    quote = next((q for q in quotes if q["id"] == quote_id), None)

    if not quote:
        click.echo(f'✗ Цитата ID:{quote_id} не найдена', err=True)
        return

    click.echo('\n' + '='*80)
    click.echo(f'ID: {quote["id"]}')
    category_name = CATEGORY_DISPLAY.get(quote["category"], quote["category"])
    click.echo(f'Категория: {category_name}')

    if quote["title"]:
        click.echo(f'Книга: {quote["title"]} - {quote["author"]}')

    if quote["quote_author"] or quote["quote_source"]:
        attribution = []
        if quote["quote_author"]:
            attribution.append(quote["quote_author"])
        if quote["quote_source"]:
            attribution.append(quote["quote_source"])
        click.echo(f'Атрибуция: {" / ".join(attribution)}')

    click.echo('-'*80)
    click.echo(quote["text"])
    click.echo('='*80 + '\n')


@quote.command('edit')
@click.argument('quote_id', type=int)
@click.option('--text', prompt='Новый текст цитаты (можно с атрибуцией)', help='Новый текст цитаты')
@click.option('--category',
              prompt='Новая категория [Теория (t) / Практика (p) / Цитаты (q)]',
              help='Новая категория цитаты')
def edit_quote(quote_id, text, category):
    """Редактировать цитату"""
    # Normalize category input
    category = normalize_category(category)

    # Parse quote to extract author and source if provided
    quote_text, quote_author, quote_source = parse_quote(text)

    if db.update_quote(quote_id, quote_text, category, quote_author, quote_source):
        category_name = CATEGORY_DISPLAY.get(category, category)
        click.echo(f'✓ Цитата ID:{quote_id} обновлена (категория: {category_name})')
        if quote_author:
            click.echo(f'  Автор: {quote_author}')
        if quote_source:
            click.echo(f'  Источник: {quote_source}')
    else:
        click.echo(f'✗ Цитата ID:{quote_id} не найдена', err=True)


@quote.command('delete')
@click.argument('quote_id', type=int)
@click.confirmation_option(prompt='Вы уверены?')
def delete_quote(quote_id):
    """Удалить цитату"""
    if db.delete_quote(quote_id):
        click.echo(f'✓ Цитата ID:{quote_id} удалена')
    else:
        click.echo(f'✗ Цитата ID:{quote_id} не найдена', err=True)


@cli.command('stats')
def stats():
    """Показать статистику"""
    books = db.get_all_books()
    all_quotes = db.get_all_quotes()
    theory_quotes = db.get_all_quotes('theory')
    practice_quotes = db.get_all_quotes('practice')
    quotes_category = db.get_all_quotes('quotes')

    click.echo('\n' + '='*50)
    click.echo('СТАТИСТИКА BESTOIC BOT')
    click.echo('='*50)
    click.echo(f'Всего книг: {len(books)}')
    click.echo(f'Всего цитат: {len(all_quotes)}')
    click.echo('-'*50)
    click.echo(f'  Теория: {len(theory_quotes)}')
    click.echo(f'  Практика: {len(practice_quotes)}')
    click.echo(f'  Цитаты: {len(quotes_category)}')
    click.echo('='*50 + '\n')


if __name__ == '__main__':
    cli()
