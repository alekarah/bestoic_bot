"""CLI commands for book management (source books for quotes)"""

import click
from src.cli.common import db, normalize_category, CATEGORY_DISPLAY
from src.utils.quote_parser import parse_quote, parse_daily_stoicism_book


@click.group()
def book():
    """Управление книгами"""
    pass


@book.command('add')
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--title', prompt='Название книги', help='Название книги')
@click.option('--author', prompt='Автор', help='Автор книги')
@click.option('--category',
              prompt='Категория [Цитаты (q) / Стоицизм на каждый день (d)]',
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
        skipped_duplicates = 0
        for paragraph in paragraphs:
            # Skip very short paragraphs (likely not quotes)
            if len(paragraph) > 50:
                # Parse quote to extract author and source
                quote_text, quote_author, quote_source = parse_quote(paragraph)

                # Check for duplicate
                existing = db.find_exact_duplicate(quote_text)
                if existing:
                    skipped_duplicates += 1
                    continue

                db.add_quote(quote_text, category, book_id, quote_author, quote_source)
                added_count += 1

        category_name = CATEGORY_DISPLAY.get(category, category)
        click.echo(f'✓ Добавлено {added_count} цитат из категории "{category_name}"')
        if skipped_duplicates > 0:
            click.echo(f'⚠ Пропущено {skipped_duplicates} дубликатов')
        click.echo(f'✓ Всего обработано {len(paragraphs)} абзацев')

    except Exception as e:
        click.echo(f'✗ Ошибка: {str(e)}', err=True)


@book.command('add-daily')
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--title', prompt='Название книги', help='Название книги')
@click.option('--author', prompt='Автор', help='Автор книги')
def add_daily_book(file_path, title, author):
    """Загрузить книгу в формате 'Стоицизм на каждый день' (366 записей с датами)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add book to database
        book_id = db.add_book(title, author)
        click.echo(f'✓ Книга "{title}" добавлена (ID: {book_id})')

        # Parse daily stoicism format
        click.echo('Парсинг записей по датам...')
        entries = parse_daily_stoicism_book(content)

        if not entries:
            click.echo('✗ Не удалось распарсить записи. Проверьте формат файла.', err=True)
            return

        added_count = 0
        skipped_duplicates = 0
        for entry in entries:
            # Check for duplicate
            existing = db.find_exact_duplicate(entry['text'])
            if existing:
                skipped_duplicates += 1
                continue

            db.add_quote(
                text=entry['text'],
                category='daily',
                book_id=book_id,
                quote_author=entry['quote_author'],
                quote_source=entry['quote_source'],
                day_of_year=entry['day_of_year']
            )
            added_count += 1

        click.echo(f'✓ Добавлено {added_count} записей из категории "Стоицизм на каждый день"')
        if skipped_duplicates > 0:
            click.echo(f'⚠ Пропущено {skipped_duplicates} дубликатов')
        click.echo(f'✓ Всего обработано {len(entries)} записей')

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

    for b in books:
        click.echo(f'{b["id"]:<5} {b["title"]:<40} {b["author"]:<25} {b["uploaded_at"][:10]}')

    click.echo('='*80 + '\n')


@book.command('delete')
@click.argument('book_id', type=int)
def delete_book(book_id):
    """Удалить книгу"""
    # Get book info first
    books = db.get_all_books()
    b = next((b for b in books if b['id'] == book_id), None)

    if not b:
        click.echo(f'✗ Книга ID:{book_id} не найдена', err=True)
        return

    # Count quotes in this book
    all_quotes = db.get_all_quotes()
    book_quotes_count = sum(1 for q in all_quotes if q['book_id'] == book_id)

    click.echo(f'\nКнига: {b["title"]} - {b["author"]}')
    click.echo(f'Цитат в книге: {book_quotes_count}')
    click.echo()

    # Ask what to do
    if not click.confirm('Вы уверены что хотите удалить эту книгу?'):
        click.echo('Отменено')
        return

    if book_quotes_count > 0:
        delete_quotes = click.confirm('\nУдалить также все цитаты из этой книги?', default=False)
    else:
        delete_quotes = False

    # Delete book
    if db.delete_book(book_id, delete_quotes=delete_quotes):
        if delete_quotes:
            click.echo(f'✓ Книга ID:{book_id} и {book_quotes_count} цитат удалены')
        else:
            click.echo(f'✓ Книга ID:{book_id} удалена (цитаты сохранены без привязки к книге)')
    else:
        click.echo(f'✗ Ошибка при удалении книги', err=True)
