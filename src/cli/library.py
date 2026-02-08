"""CLI commands for library management (downloadable books)"""

import os
import click
from src.cli.common import db, normalize_library_category, LIBRARY_CATEGORY_DISPLAY


@click.group()
def library():
    """Управление библиотекой книг для скачивания"""
    pass


@library.command('add')
@click.option('--author', prompt='Автор', help='Автор книги')
@click.option('--title', prompt='Название книги', help='Название книги')
@click.option('--description', prompt='Описание (можно пустое)', default='', help='Описание книги')
@click.option('--buy-url', prompt='Ссылка на покупку (можно пустое)', default='', help='Ссылка на покупку бумажной версии')
@click.option('--category', prompt='Категория [Классика (c) / Современные (m) / - без категории]', default='-', help='Категория книги')
def library_add(author, title, description, buy_url, category):
    """Добавить книгу в библиотеку"""
    cat = normalize_library_category(category)
    book_id = db.add_library_book(
        title=title.strip(),
        author=author.strip(),
        description=description.strip() if description else None,
        buy_url=buy_url.strip() if buy_url else None,
        category=cat
    )
    cat_display = LIBRARY_CATEGORY_DISPLAY.get(cat, 'без категории') if cat else 'без категории'
    click.echo(f'✓ Книга "{author} — {title}" добавлена в библиотеку (ID: {book_id})')
    click.echo(f'  Категория: {cat_display}')
    click.echo(f'  Теперь добавьте файлы: python admin.py library add-file {book_id} <путь_к_файлу>')


@library.command('list')
@click.option('--category', '-c', default=None, help='Фильтр по категории (classic/modern)')
def library_list(category):
    """Показать все книги в библиотеке"""
    cat = normalize_library_category(category) if category else None
    books = db.get_all_library_books(category=cat)

    if not books:
        click.echo('Библиотека пуста')
        return

    click.echo('\n' + '='*115)
    click.echo(f'{"ID":<5} {"Порядок":<8} {"Категория":<12} {"Автор":<22} {"Название":<35} {"Форматы"}')
    click.echo('='*115)

    for b in books:
        # Get file formats for this book
        files = db.get_book_files(b['id'])
        formats = ', '.join([f['format'] for f in files]) if files else '—'
        order_str = f'[{b["display_order"]}]' if b["display_order"] < 999 else '—'
        cat_short = {'classic': 'Классика', 'modern': 'Совр.'}.get(b['category'], '—')
        click.echo(f'{b["id"]:<5} {order_str:<8} {cat_short:<12} {b["author"][:21]:<22} {b["title"][:34]:<35} {formats}')

    click.echo('='*115)
    click.echo(f'Всего книг: {len(books)}\n')


@library.command('view')
@click.argument('book_id', type=int)
def library_view(book_id):
    """Показать детали книги"""
    b = db.get_library_book(book_id)

    if not b:
        click.echo(f'✗ Книга ID:{book_id} не найдена', err=True)
        return

    cat_display = LIBRARY_CATEGORY_DISPLAY.get(b['category'], 'без категории')

    click.echo('\n' + '='*60)
    click.echo(f'ID: {b["id"]}')
    click.echo(f'Автор: {b["author"]}')
    click.echo(f'Название: {b["title"]}')
    click.echo(f'Категория: {cat_display}')

    if b['description']:
        click.echo('-'*60)
        click.echo(f'Описание:\n{b["description"]}')

    if b['buy_url']:
        click.echo('-'*60)
        click.echo(f'Купить: {b["buy_url"]}')

    # Show files
    files = db.get_book_files(book_id)
    click.echo('-'*60)
    click.echo('Файлы:')
    if files:
        for f in files:
            size = f'({f["file_size"] // 1024} KB)' if f['file_size'] else ''
            cached = '+ cache' if f['file_id'] else ''
            click.echo(f'  - {f["format"].upper()}: {f["file_path"]} {size} {cached}')
    else:
        click.echo('  Нет загруженных файлов')

    click.echo('='*60 + '\n')


@library.command('edit')
@click.argument('book_id', type=int)
@click.option('--title', default=None, help='Новое название')
@click.option('--author', default=None, help='Новый автор')
@click.option('--description', default=None, help='Новое описание')
@click.option('--buy-url', default=None, help='Новая ссылка на покупку')
@click.option('--category', default=None, help='Новая категория (classic/modern/-)')
def library_edit(book_id, title, author, description, buy_url, category):
    """Редактировать книгу в библиотеке"""
    b = db.get_library_book(book_id)
    if not b:
        click.echo(f'✗ Книга ID:{book_id} не найдена', err=True)
        return

    # If no options provided, prompt for each
    if not any([title, author, description, buy_url, category]):
        click.echo(f'Текущее название: {b["title"]}')
        title = click.prompt('Новое название', default=b['title'])

        click.echo(f'Текущий автор: {b["author"]}')
        author = click.prompt('Новый автор', default=b['author'])

        click.echo(f'Текущее описание: {b["description"] or "(пусто)"}')
        description = click.prompt('Новое описание', default=b['description'] or '')

        click.echo(f'Текущая ссылка: {b["buy_url"] or "(пусто)"}')
        buy_url = click.prompt('Новая ссылка на покупку', default=b['buy_url'] or '')

        current_cat = LIBRARY_CATEGORY_DISPLAY.get(b['category'], 'без категории')
        click.echo(f'Текущая категория: {current_cat}')
        category = click.prompt('Новая категория [Классика (c) / Современные (m) / - без]', default=b['category'] or '-')

    cat = normalize_library_category(category) if category else None

    if db.update_library_book(book_id, title, author, description, buy_url, cat):
        click.echo(f'✓ Книга ID:{book_id} обновлена')
    else:
        click.echo(f'✗ Ошибка при обновлении', err=True)


@library.command('delete')
@click.argument('book_id', type=int)
def library_delete(book_id):
    """Удалить книгу из библиотеки"""
    b = db.get_library_book(book_id)
    if not b:
        click.echo(f'✗ Книга ID:{book_id} не найдена', err=True)
        return

    click.echo(f'\nКнига: {b["title"]} - {b["author"]}')

    files = db.get_book_files(book_id)
    if files:
        click.echo(f'Файлов: {len(files)}')

    if not click.confirm('Удалить книгу и все её файлы?'):
        click.echo('Отменено')
        return

    if db.delete_library_book(book_id):
        click.echo(f'✓ Книга ID:{book_id} удалена')
    else:
        click.echo(f'✗ Ошибка при удалении', err=True)


@library.command('add-file')
@click.argument('book_id', type=int)
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--format', 'file_format', default=None, help='Формат файла (fb2, epub, mobi, pdf). Определяется автоматически по расширению.')
def library_add_file(book_id, file_path, file_format):
    """Добавить файл книги"""
    b = db.get_library_book(book_id)
    if not b:
        click.echo(f'✗ Книга ID:{book_id} не найдена', err=True)
        return

    # Determine format from extension if not provided
    if not file_format:
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        if ext in ['fb2', 'epub', 'mobi', 'pdf']:
            file_format = ext
        else:
            click.echo(f'✗ Неизвестный формат: {ext}. Укажите --format', err=True)
            return

    # Get file size
    file_size = os.path.getsize(file_path)

    # Store absolute path
    abs_path = os.path.abspath(file_path)

    db.add_book_file(book_id, file_format, file_path=abs_path, file_size=file_size)
    click.echo(f'✓ Файл {file_format.upper()} добавлен для книги "{b["title"]}"')
    click.echo(f'  Путь: {abs_path}')
    click.echo(f'  Размер: {file_size // 1024} KB')


@library.command('remove-file')
@click.argument('book_id', type=int)
@click.argument('file_format', type=click.Choice(['fb2', 'epub', 'mobi', 'pdf'], case_sensitive=False))
def library_remove_file(book_id, file_format):
    """Удалить файл книги"""
    b = db.get_library_book(book_id)
    if not b:
        click.echo(f'✗ Книга ID:{book_id} не найдена', err=True)
        return

    if db.delete_book_file(book_id, file_format.lower()):
        click.echo(f'✓ Файл {file_format.upper()} удалён')
    else:
        click.echo(f'✗ Файл не найден', err=True)


@library.command('set-order')
@click.argument('book_id', type=int)
@click.argument('order', type=int)
def library_set_order(book_id, order):
    """Установить порядок отображения книги

    Книги с меньшим номером показываются первыми.
    Например: 1, 2, 3 для топ-книг, 999 для обычных книг (по умолчанию).
    """
    b = db.get_library_book(book_id)
    if not b:
        click.echo(f'✗ Книга ID:{book_id} не найдена', err=True)
        return

    if db.set_book_display_order(book_id, order):
        click.echo(f'✓ Порядок отображения для книги "{b["author"]} — {b["title"]}" установлен: {order}')
        if order <= 10:
            click.echo(f'  📌 Эта книга будет показана в начале списка')
    else:
        click.echo(f'✗ Не удалось обновить порядок', err=True)
