"""CLI команды для управления цитатами"""

import click
from src.cli.common import db, CATEGORY_DISPLAY
from src.utils.quote_parser import parse_quote


@click.group()
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

    # Получить или создать книгу для ручных цитат
    manual_book_id = db.get_or_create_manual_book(source='CLI')

    # Очищаем ввод
    quote_text = text.strip()
    quote_author = author.strip() if author else None
    quote_source = source.strip() if source else None

    # Проверяем наличие дубликата перед добавлением
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
@click.option('--offset', '-o', default=0, help='Пропустить первых N цитат')
@click.option('--search', '-s', default=None, help='Поиск по тексту цитаты')
def list_quotes(category, limit, offset, search):
    """Показать цитаты с фильтрами"""
    quotes = db.get_all_quotes(category if category != 'all' else None)

    # Фильтруем по тексту поиска, если указан
    if search:
        search_lower = search.lower()
        quotes = [q for q in quotes if search_lower in q['text'].lower()]

    if not quotes:
        click.echo('Цитаты не найдены')
        return

    total = len(quotes)
    quotes = quotes[offset:offset + limit]

    if not quotes:
        click.echo(f'Цитаты не найдены (offset {offset} превышает общее количество {total})')
        return

    click.echo(f'\nНайдено цитат: {total}')
    click.echo(f'Показано: {offset + 1}-{offset + len(quotes)}\n')
    click.echo('='*80)

    for i, q in enumerate(quotes, offset + 1):
        book_info = f'{q["title"]} - {q["author"]}' if q["title"] else 'Без книги'
        category_name = CATEGORY_DISPLAY.get(q["category"], q["category"])
        click.echo(f'\nID: {q["id"]} | Категория: {category_name} | Книга: {book_info}')

        # Показать автора/источник цитаты, если доступны
        if q["quote_author"] or q["quote_source"]:
            attribution = []
            if q["quote_author"]:
                attribution.append(q["quote_author"])
            if q["quote_source"]:
                attribution.append(q["quote_source"])
            click.echo(f'Атрибуция: {" / ".join(attribution)}')

        click.echo('-'*80)

        # Показать превью цитаты (первые 200 символов)
        text_preview = q["text"][:200] + '...' if len(q["text"]) > 200 else q["text"]
        click.echo(text_preview)
        click.echo('='*80)


@quote.command('view')
@click.argument('quote_id', type=int)
def view_quote(quote_id):
    """Показать полный текст цитаты"""
    quotes = db.get_all_quotes()
    q = next((q for q in quotes if q["id"] == quote_id), None)

    if not q:
        click.echo(f'✗ Цитата ID:{quote_id} не найдена', err=True)
        return

    click.echo('\n' + '='*80)
    click.echo(f'ID: {q["id"]}')
    category_name = CATEGORY_DISPLAY.get(q["category"], q["category"])
    click.echo(f'Категория: {category_name}')

    if q["title"]:
        click.echo(f'Книга: {q["title"]} - {q["author"]}')

    if q["quote_author"] or q["quote_source"]:
        attribution = []
        if q["quote_author"]:
            attribution.append(q["quote_author"])
        if q["quote_source"]:
            attribution.append(q["quote_source"])
        click.echo(f'Атрибуция: {" / ".join(attribution)}')

    click.echo('-'*80)
    click.echo(q["text"])
    click.echo('='*80 + '\n')


@quote.command('edit')
@click.argument('quote_id', type=int)
@click.option('--text', prompt='Новый текст цитаты (можно с атрибуцией)', help='Новый текст цитаты')
def edit_quote(quote_id, text):
    """Редактировать цитату"""
    # Категория всегда 'quotes' для редактируемых цитат
    category = 'quotes'

    # Парсим цитату для извлечения автора и источника
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
    # Сначала получаем информацию о цитате
    quotes = db.get_all_quotes()
    q = next((q for q in quotes if q["id"] == quote_id), None)

    if not q:
        click.echo(f'✗ Цитата ID:{quote_id} не найдена', err=True)
        return

    # Показываем цитату
    click.echo('\n' + '='*80)
    click.echo(f'ID: {q["id"]}')
    category_name = CATEGORY_DISPLAY.get(q["category"], q["category"])
    click.echo(f'Категория: {category_name}')

    if q["title"]:
        click.echo(f'Книга: {q["title"]} - {q["author"]}')

    if q["quote_author"] or q["quote_source"]:
        attribution = []
        if q["quote_author"]:
            attribution.append(q["quote_author"])
        if q["quote_source"]:
            attribution.append(q["quote_source"])
        click.echo(f'Атрибуция: {" / ".join(attribution)}')

    click.echo('-'*80)
    # Показать превью, если цитата длинная
    if len(q["text"]) > 300:
        click.echo(q["text"][:300] + '...')
    else:
        click.echo(q["text"])
    click.echo('='*80 + '\n')

    # Подтверждение удаления
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

    # Находим пары со схожестью выше порога
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

        # Показать первую цитату
        click.echo(f'[1] ID: {q1["id"]} | Категория: {CATEGORY_DISPLAY.get(q1["category"], q1["category"])}')
        if q1["title"]:
            click.echo(f'    Книга: {q1["title"]} - {q1["author"]}')
        click.echo(f'    Текст: {q1["text"][:150]}...' if len(q1["text"]) > 150 else f'    Текст: {q1["text"]}')

        click.echo()

        # Показать вторую цитату
        click.echo(f'[2] ID: {q2["id"]} | Категория: {CATEGORY_DISPLAY.get(q2["category"], q2["category"])}')
        if q2["title"]:
            click.echo(f'    Книга: {q2["title"]} - {q2["author"]}')
        click.echo(f'    Текст: {q2["text"][:150]}...' if len(q2["text"]) > 150 else f'    Текст: {q2["text"]}')

        click.echo()

        # Спрашиваем что делать
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

    # Топ цитат
    if stats['top_quotes']:
        click.echo(f'\nТОП-{len(stats["top_quotes"])} ЦИТАТ В ИЗБРАННОМ:\n')
        for i, q in enumerate(stats['top_quotes'], 1):
            category_name = 'Daily' if q['category'] == 'daily' else 'Quotes'
            preview = q['text'][:80] + '...' if len(q['text']) > 80 else q['text']

            click.echo(f'{i}. [{q["favorites_count"]} раз] ID:{q["id"]} ({category_name})')
            click.echo(f'   "{preview}"')
            if q['quote_author'] or q['quote_source']:
                attr_parts = []
                if q['quote_author']:
                    attr_parts.append(q['quote_author'])
                if q['quote_source']:
                    attr_parts.append(q['quote_source'])
                click.echo(f'   — {", ".join(attr_parts)}')
            click.echo()
    else:
        click.echo('\nНет цитат в избранном\n')

    # По категориям
    if stats['by_category']:
        click.echo('ПО КАТЕГОРИЯМ:')
        for category, count in stats['by_category'].items():
            category_name = 'Quotes' if category == 'quotes' else 'Daily'
            click.echo(f'   {category_name}: {count} цитат в избранном')
        click.echo()

    # Общая статистика
    click.echo('ОБЩАЯ СТАТИСТИКА:')
    click.echo(f'   Всего цитат: {stats["total_quotes"]}')
    click.echo(f'   Хотя бы раз в избранном: {stats["quotes_in_favorites"]} ({stats["quotes_in_favorites"]/stats["total_quotes"]*100:.1f}%)')
    click.echo(f'   Никогда не добавляли: {stats["never_favorited"]} ({stats["never_favorited"]/stats["total_quotes"]*100:.1f}%)')
    click.echo('='*80 + '\n')
