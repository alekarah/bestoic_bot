import click
import os
from src.database.models import Database
from src.utils.quote_parser import parse_quote, parse_daily_stoicism_book


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


def normalize_category(value):
    """Convert user input to internal category name"""
    normalized = CATEGORY_MAP.get(value.lower())
    if not normalized:
        raise click.BadParameter(
            f'Категория должна быть: Цитаты (q) или Стоицизм на каждый день (d)'
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

    for book in books:
        click.echo(f'{book["id"]:<5} {book["title"]:<40} {book["author"]:<25} {book["uploaded_at"][:10]}')

    click.echo('='*80 + '\n')


@book.command('delete')
@click.argument('book_id', type=int)
def delete_book(book_id):
    """Удалить книгу"""
    # Get book info first
    books = db.get_all_books()
    book = next((b for b in books if b['id'] == book_id), None)

    if not book:
        click.echo(f'✗ Книга ID:{book_id} не найдена', err=True)
        return

    # Count quotes in this book
    all_quotes = db.get_all_quotes()
    book_quotes_count = sum(1 for q in all_quotes if q['book_id'] == book_id)

    click.echo(f'\nКнига: {book["title"]} - {book["author"]}')
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


# Quote commands
@cli.group()
def quote():
    """Управление цитатами"""
    pass


@quote.command('add')
@click.option('--text', prompt='Текст цитаты', help='Текст цитаты')
@click.option('--author', prompt='Автор (например: Марк Аврелий)', help='Автор цитаты')
@click.option('--source', prompt='Источник (например: Размышления)', default='', help='Источник/книга')
def add_quote(text, author, source):
    """Добавить новую цитату вручную"""
    category = 'quotes'

    # Get or create manual quotes book
    manual_book_id = db.get_or_create_manual_book(source='CLI')

    # Clean up inputs
    quote_text = text.strip()
    quote_author = author.strip() if author else None
    quote_source = source.strip() if source else None

    # Check for existing duplicate before adding
    existing = db.find_exact_duplicate(quote_text)
    if existing:
        click.echo(f'⚠ Цитата уже существует (ID: {existing["id"]})', err=True)
        category_name = CATEGORY_DISPLAY.get(existing["category"], existing["category"])
        click.echo(f'  Категория: {category_name}')
        if existing["title"]:
            click.echo(f'  Книга: {existing["title"]} - {existing["author"]}')
        return

    quote_id = db.add_quote(quote_text, category, manual_book_id, quote_author, quote_source)

    category_name = CATEGORY_DISPLAY.get(category, category)
    click.echo(f'✓ Цитата добавлена (ID: {quote_id}) в категорию "{category_name}"')
    if quote_author:
        click.echo(f'  Автор: {quote_author}')
    if quote_source:
        click.echo(f'  Источник: {quote_source}')


@quote.command('list')
@click.option('--category', '-c',
              type=click.Choice(['quotes', 'daily', 'all'], case_sensitive=False),
              default='all',
              help='Фильтр по категории (quotes/daily/all)')
@click.option('--limit', '-l', default=20, help='Количество цитат для показа')
@click.option('--search', '-s', default=None, help='Поиск по тексту цитаты')
def list_quotes(category, limit, search):
    """Показать цитаты с фильтрами"""
    quotes = db.get_all_quotes(category if category != 'all' else None)

    # Filter by search text if provided
    if search:
        search_lower = search.lower()
        quotes = [q for q in quotes if search_lower in q['text'].lower()]

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
def edit_quote(quote_id, text):
    """Редактировать цитату"""
    # Category is always 'quotes' for edited quotes
    category = 'quotes'

    # Parse quote to extract author and source if provided
    quote_text, quote_author, quote_source = parse_quote(text)

    if db.update_quote(quote_id, quote_text, category, quote_author, quote_source):
        click.echo(f'✓ Цитата ID:{quote_id} обновлена')
        if quote_author:
            click.echo(f'  Автор: {quote_author}')
        if quote_source:
            click.echo(f'  Источник: {quote_source}')
    else:
        click.echo(f'✗ Цитата ID:{quote_id} не найдена', err=True)


@quote.command('delete')
@click.argument('quote_id', type=int)
def delete_quote(quote_id):
    """Удалить цитату"""
    # Get quote info first
    quotes = db.get_all_quotes()
    quote = next((q for q in quotes if q["id"] == quote_id), None)

    if not quote:
        click.echo(f'✗ Цитата ID:{quote_id} не найдена', err=True)
        return

    # Display quote
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
    # Show preview if quote is long
    if len(quote["text"]) > 300:
        click.echo(quote["text"][:300] + '...')
    else:
        click.echo(quote["text"])
    click.echo('='*80 + '\n')

    # Confirm deletion
    if not click.confirm('Вы уверены что хотите удалить эту цитату?'):
        click.echo('Отменено')
        return

    if db.delete_quote(quote_id):
        click.echo(f'✓ Цитата ID:{quote_id} удалена')
    else:
        click.echo(f'✗ Ошибка при удалении цитаты', err=True)


@quote.command('find-duplicates')
@click.option('--threshold', default=90, type=int, help='Порог схожести (0-100)')
def find_duplicates(threshold):
    """Найти похожие дубликаты цитат"""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        click.echo('✗ Требуется библиотека scikit-learn', err=True)
        click.echo('Установите: pip install scikit-learn')
        return

    quotes = db.get_all_quotes()
    total = len(quotes)

    click.echo(f'\n🔍 Поиск похожих цитат (порог схожести: {threshold}%)...')
    click.echo(f'Всего цитат: {total}\n')

    texts = [q['text'] for q in quotes]

    click.echo('Векторизация текстов...')
    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform(texts)

    click.echo('Вычисление схожести...')
    similarity_matrix = cosine_similarity(tfidf_matrix)

    duplicates = []

    # Find pairs with similarity above threshold
    for i in range(total):
        if i % max(1, total // 10) == 0:
            progress = int((i / total) * 100)
            click.echo(f'Прогресс: {progress}%')

        for j in range(i + 1, total):
            sim_score = int(similarity_matrix[i, j] * 100)
            if sim_score >= threshold:
                duplicates.append((quotes[i], quotes[j], sim_score))

    click.echo('Прогресс: 100%')
    click.echo(f'\n✓ Проверка завершена\n')

    if not duplicates:
        click.echo('✓ Похожих дубликатов не найдено!')
        return

    click.echo(f'Найдено {len(duplicates)} пар похожих цитат:\n')

    for idx, (q1, q2, sim) in enumerate(duplicates, 1):
        click.echo('='*80)
        click.echo(f'Пара #{idx} (схожесть {sim}%):')
        click.echo('-'*80)

        # Show first quote
        click.echo(f'[1] ID: {q1["id"]} | Категория: {CATEGORY_DISPLAY.get(q1["category"], q1["category"])}')
        if q1["title"]:
            click.echo(f'    Книга: {q1["title"]} - {q1["author"]}')
        click.echo(f'    Текст: {q1["text"][:150]}...' if len(q1["text"]) > 150 else f'    Текст: {q1["text"]}')

        click.echo()

        # Show second quote
        click.echo(f'[2] ID: {q2["id"]} | Категория: {CATEGORY_DISPLAY.get(q2["category"], q2["category"])}')
        if q2["title"]:
            click.echo(f'    Книга: {q2["title"]} - {q2["author"]}')
        click.echo(f'    Текст: {q2["text"][:150]}...' if len(q2["text"]) > 150 else f'    Текст: {q2["text"]}')

        click.echo()

        # Ask what to do
        choice = click.prompt(
            'Действие: [1] Оставить только ID:' + str(q1["id"]) + '  [2] Оставить только ID:' + str(q2["id"]) + '  [B] Оставить обе  [S] Пропустить',
            type=str,
            default='B'
        ).upper()

        if choice == '1':
            if db.delete_quote(q2["id"]):
                click.echo(f'✓ Цитата ID:{q2["id"]} удалена\n')
        elif choice == '2':
            if db.delete_quote(q1["id"]):
                click.echo(f'✓ Цитата ID:{q1["id"]} удалена\n')
        elif choice == 'S':
            click.echo('Пропущено\n')
        else:  # 'B' or anything else
            click.echo('Обе цитаты сохранены\n')


@cli.command('stats')
def stats():
    """Показать статистику"""
    books = db.get_all_books()
    all_quotes = db.get_all_quotes()
    quotes_category = db.get_all_quotes('quotes')
    daily_category = db.get_all_quotes('daily')

    click.echo('\n' + '='*50)
    click.echo('СТАТИСТИКА BESTOIC BOT')
    click.echo('='*50)
    click.echo(f'Всего книг: {len(books)}')
    click.echo(f'Всего цитат: {len(all_quotes)}')
    click.echo('-'*50)
    click.echo(f'  Цитаты: {len(quotes_category)}')
    click.echo(f'  Стоицизм на каждый день: {len(daily_category)}')
    click.echo('='*50 + '\n')


if __name__ == '__main__':
    cli()
