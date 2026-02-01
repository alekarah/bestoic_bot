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


@quote.command('stats')
@click.option('--limit', '-l', default=10, type=int, help='Количество цитат в топе')
def quote_stats(limit):
    """Показать статистику по избранному"""
    stats = db.get_favorites_statistics(limit)

    click.echo('\n' + '='*80)
    click.echo('СТАТИСТИКА ПО ИЗБРАННОМУ')
    click.echo('='*80)

    # Top quotes
    if stats['top_quotes']:
        click.echo(f'\nТОП-{len(stats["top_quotes"])} ЦИТАТ В ИЗБРАННОМ:\n')
        for i, quote in enumerate(stats['top_quotes'], 1):
            category_name = 'Daily' if quote['category'] == 'daily' else 'Quotes'
            preview = quote['text'][:80] + '...' if len(quote['text']) > 80 else quote['text']

            click.echo(f'{i}. [{quote["favorites_count"]} раз] ID:{quote["id"]} ({category_name})')
            click.echo(f'   "{preview}"')
            if quote['quote_author'] or quote['quote_source']:
                attr_parts = []
                if quote['quote_author']:
                    attr_parts.append(quote['quote_author'])
                if quote['quote_source']:
                    attr_parts.append(quote['quote_source'])
                click.echo(f'   — {", ".join(attr_parts)}')
            click.echo()
    else:
        click.echo('\nНет цитат в избранном\n')

    # By category
    if stats['by_category']:
        click.echo('ПО КАТЕГОРИЯМ:')
        for category, count in stats['by_category'].items():
            category_name = 'Quotes' if category == 'quotes' else 'Daily'
            click.echo(f'   {category_name}: {count} цитат в избранном')
        click.echo()

    # Overall statistics
    click.echo('ОБЩАЯ СТАТИСТИКА:')
    click.echo(f'   Всего цитат: {stats["total_quotes"]}')
    click.echo(f'   Хотя бы раз в избранном: {stats["quotes_in_favorites"]} ({stats["quotes_in_favorites"]/stats["total_quotes"]*100:.1f}%)')
    click.echo(f'   Никогда не добавляли: {stats["never_favorited"]} ({stats["never_favorited"]/stats["total_quotes"]*100:.1f}%)')
    click.echo('='*80 + '\n')


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


# Library commands (downloadable books)
@cli.group()
def library():
    """Управление библиотекой книг для скачивания"""
    pass


@library.command('add')
@click.option('--author', prompt='Автор', help='Автор книги')
@click.option('--title', prompt='Название книги', help='Название книги')
@click.option('--description', prompt='Описание (можно пустое)', default='', help='Описание книги')
@click.option('--buy-url', prompt='Ссылка на покупку (можно пустое)', default='', help='Ссылка на покупку бумажной версии')
def library_add(author, title, description, buy_url):
    """Добавить книгу в библиотеку"""
    book_id = db.add_library_book(
        title=title.strip(),
        author=author.strip(),
        description=description.strip() if description else None,
        buy_url=buy_url.strip() if buy_url else None
    )
    click.echo(f'✓ Книга "{author} — {title}" добавлена в библиотеку (ID: {book_id})')
    click.echo(f'  Теперь добавьте файлы: python admin.py library add-file {book_id} <путь_к_файлу>')


@library.command('list')
def library_list():
    """Показать все книги в библиотеке"""
    books = db.get_all_library_books()

    if not books:
        click.echo('Библиотека пуста')
        return

    click.echo('\n' + '='*100)
    click.echo(f'{"ID":<5} {"Порядок":<8} {"Автор":<25} {"Название":<35} {"Форматы"}')
    click.echo('='*100)

    for book in books:
        # Get file formats for this book
        files = db.get_book_files(book['id'])
        formats = ', '.join([f['format'] for f in files]) if files else '—'
        order_str = f'[{book["display_order"]}]' if book["display_order"] < 999 else '—'
        click.echo(f'{book["id"]:<5} {order_str:<8} {book["author"][:24]:<25} {book["title"][:34]:<35} {formats}')

    click.echo('='*100)
    click.echo(f'Всего книг: {len(books)}\n')


@library.command('view')
@click.argument('book_id', type=int)
def library_view(book_id):
    """Показать детали книги"""
    book = db.get_library_book(book_id)

    if not book:
        click.echo(f'✗ Книга ID:{book_id} не найдена', err=True)
        return

    click.echo('\n' + '='*60)
    click.echo(f'ID: {book["id"]}')
    click.echo(f'Автор: {book["author"]}')
    click.echo(f'Название: {book["title"]}')

    if book['description']:
        click.echo('-'*60)
        click.echo(f'Описание:\n{book["description"]}')

    if book['buy_url']:
        click.echo('-'*60)
        click.echo(f'Купить: {book["buy_url"]}')

    # Show files
    files = db.get_book_files(book_id)
    click.echo('-'*60)
    click.echo('Файлы:')
    if files:
        for f in files:
            size = f'({f["file_size"] // 1024} KB)' if f['file_size'] else ''
            cached = '✓ кэш' if f['file_id'] else ''
            click.echo(f'  • {f["format"].upper()}: {f["file_path"]} {size} {cached}')
    else:
        click.echo('  Нет загруженных файлов')

    click.echo('='*60 + '\n')


@library.command('edit')
@click.argument('book_id', type=int)
@click.option('--title', default=None, help='Новое название')
@click.option('--author', default=None, help='Новый автор')
@click.option('--description', default=None, help='Новое описание')
@click.option('--buy-url', default=None, help='Новая ссылка на покупку')
def library_edit(book_id, title, author, description, buy_url):
    """Редактировать книгу в библиотеке"""
    book = db.get_library_book(book_id)
    if not book:
        click.echo(f'✗ Книга ID:{book_id} не найдена', err=True)
        return

    # If no options provided, prompt for each
    if not any([title, author, description, buy_url]):
        click.echo(f'Текущее название: {book["title"]}')
        title = click.prompt('Новое название', default=book['title'])

        click.echo(f'Текущий автор: {book["author"]}')
        author = click.prompt('Новый автор', default=book['author'])

        click.echo(f'Текущее описание: {book["description"] or "(пусто)"}')
        description = click.prompt('Новое описание', default=book['description'] or '')

        click.echo(f'Текущая ссылка: {book["buy_url"] or "(пусто)"}')
        buy_url = click.prompt('Новая ссылка на покупку', default=book['buy_url'] or '')

    if db.update_library_book(book_id, title, author, description, buy_url):
        click.echo(f'✓ Книга ID:{book_id} обновлена')
    else:
        click.echo(f'✗ Ошибка при обновлении', err=True)


@library.command('delete')
@click.argument('book_id', type=int)
def library_delete(book_id):
    """Удалить книгу из библиотеки"""
    book = db.get_library_book(book_id)
    if not book:
        click.echo(f'✗ Книга ID:{book_id} не найдена', err=True)
        return

    click.echo(f'\nКнига: {book["title"]} - {book["author"]}')

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
    book = db.get_library_book(book_id)
    if not book:
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
    click.echo(f'✓ Файл {file_format.upper()} добавлен для книги "{book["title"]}"')
    click.echo(f'  Путь: {abs_path}')
    click.echo(f'  Размер: {file_size // 1024} KB')


@library.command('remove-file')
@click.argument('book_id', type=int)
@click.argument('file_format', type=click.Choice(['fb2', 'epub', 'mobi', 'pdf'], case_sensitive=False))
def library_remove_file(book_id, file_format):
    """Удалить файл книги"""
    book = db.get_library_book(book_id)
    if not book:
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
    book = db.get_library_book(book_id)
    if not book:
        click.echo(f'✗ Книга ID:{book_id} не найдена', err=True)
        return

    if db.set_book_display_order(book_id, order):
        click.echo(f'✓ Порядок отображения для книги "{book["author"]} — {book["title"]}" установлен: {order}')
        if order <= 10:
            click.echo(f'  📌 Эта книга будет показана в начале списка')
    else:
        click.echo(f'✗ Не удалось обновить порядок', err=True)


# User commands
@cli.group()
def users():
    """Управление пользователями"""
    pass


@users.command('list')
@click.option('--limit', '-l', default=20, help='Количество пользователей для показа')
def users_list(limit):
    """Показать список пользователей с подписками"""
    users_data = db.get_all_users_with_subscriptions()

    if not users_data:
        click.echo('Пользователи не найдены')
        return

    click.echo(f'\nВсего пользователей: {len(users_data)}')
    click.echo(f'Показано: {min(limit, len(users_data))}\n')
    click.echo('='*100)
    click.echo(f'{"ID":<12} {"Username":<20} {"Имя":<20} {"Подписки":<30} {"Избранное"}')
    click.echo('='*100)

    for user in users_data[:limit]:
        user_id = str(user['user_id'])
        username = user['username'] or '—'
        first_name = user['first_name'] or '—'

        # Parse subscriptions
        subs = user['subscriptions'] or '—'
        if subs != '—':
            # Format: "quotes:morning, daily:evening" -> "Quotes 8:00, Daily 14:00"
            sub_parts = []
            for sub in subs.split(', '):
                if ':' in sub:
                    cat, time = sub.split(':')
                    cat_name = 'Quotes' if cat == 'quotes' else 'Daily'
                    time_str = {'morning': '8:00', 'day': '14:00', 'evening': '20:00'}.get(time, time)
                    sub_parts.append(f"{cat_name} {time_str}")
            subs = ', '.join(sub_parts) if sub_parts else '—'

        favorites = str(user['favorites_count']) if user['favorites_count'] else '0'

        click.echo(f'{user_id:<12} {username[:19]:<20} {first_name[:19]:<20} {subs[:29]:<30} {favorites}')

    click.echo('='*100)


@users.command('stats')
def users_stats():
    """Показать статистику пользователей"""
    stats = db.get_user_statistics()

    click.echo('\n' + '='*50)
    click.echo('📊 СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ')
    click.echo('='*50)

    click.echo(f'\n👥 Всего пользователей: {stats["total_users"]}')
    click.echo(f'✅ С активными подписками: {stats["active_subscribers"]}')

    if stats['by_category']:
        click.echo('\n📂 По категориям:')
        for cat, count in stats['by_category'].items():
            emoji = '💭' if cat == 'quotes' else '📅'
            cat_name = 'Цитаты' if cat == 'quotes' else 'Daily'
            click.echo(f'   {emoji} {cat_name}: {count}')

    if stats['by_time_slot']:
        click.echo('\n⏰ По времени:')
        for time, count in stats['by_time_slot'].items():
            time_name = {'morning': 'Утро (8:00)', 'day': 'День (14:00)', 'evening': 'Вечер (20:00)'}.get(time, time)
            click.echo(f'   {time_name}: {count}')

    click.echo('='*50 + '\n')


@users.command('view')
@click.argument('user_id', type=int)
def users_view(user_id):
    """Показать детальную информацию о пользователе"""
    user = db.get_user_detail(user_id)

    if not user:
        click.echo(f'✗ Пользователь ID:{user_id} не найден', err=True)
        return

    click.echo('\n' + '='*60)
    click.echo(f'👤 Пользователь ID: {user["user_id"]}')
    click.echo('='*60)

    click.echo(f'Username: @{user["username"]}' if user['username'] else 'Username: —')
    click.echo(f'Имя: {user["first_name"]}' if user['first_name'] else 'Имя: —')
    click.echo(f'Статус: {"✅ Активен" if user["is_active"] else "❌ Неактивен"}')
    click.echo(f'Зарегистрирован: {user["registered_at"]}')

    if user['last_activity']:
        click.echo(f'Последняя активность: {user["last_activity"]}')

    click.echo(f'\n❤️ Избранных цитат: {user["favorites_count"]}')

    if user['subscriptions']:
        click.echo('\n📬 Подписки:')
        for sub in user['subscriptions']:
            emoji = '💭' if sub['category'] == 'quotes' else '📅'
            cat_name = 'Цитаты' if sub['category'] == 'quotes' else 'Стоицизм на каждый день'
            time_name = {'morning': 'Утро (8:00)', 'day': 'День (14:00)', 'evening': 'Вечер (20:00)'}.get(sub['time_slot'], sub['time_slot'])
            click.echo(f'  {emoji} {cat_name} — {time_name}')
            click.echo(f'     Создана: {sub["created_at"]}')
    else:
        click.echo('\n📬 Подписок нет')

    click.echo('='*60 + '\n')


if __name__ == '__main__':
    cli()
