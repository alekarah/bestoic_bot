"""Обработчики библиотеки: просмотр, навигация, скачивание книг."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.database.models import Database
import config
import os

db = Database()


async def books_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /books — показать список книг библиотеки"""
    await show_books_page(update.message, context, page=0)


async def show_books_page(message_or_query, context: ContextTypes.DEFAULT_TYPE, page: int = 0, edit: bool = False, category: str = None):
    """Показать страницу книг из библиотеки"""
    total = db.count_library_books(category=category)

    if total == 0:
        if category:
            text = "📚 В этой категории пока нет книг."
        else:
            text = "📚 Библиотека пока пуста.\n\nКниги скоро появятся!"
        keyboard = [[InlineKeyboardButton("« Назад", callback_data="lib_back")]] if category else []
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        if edit:
            await message_or_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await message_or_query.reply_text(text, reply_markup=reply_markup)
        return

    # Вычисляем пагинацию
    per_page = config.BOOKS_PER_PAGE
    total_pages = (total + per_page - 1) // per_page
    offset = page * per_page

    # Проверяем границы страницы
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    books = db.get_all_library_books(limit=per_page, offset=offset, category=category)

    # Формируем сообщение
    if category:
        cat_name = config.LIBRARY_CATEGORIES.get(category, category)
        text = f"📚 {cat_name} ({page + 1}/{total_pages})\n\n"
    else:
        text = f"📚 Библиотека ({page + 1}/{total_pages})\n\n"

    # Формируем клавиатуру
    keyboard = []

    for book in books:
        # Получаем форматы файлов для этой книги
        files = db.get_book_files(book['id'])
        formats = ' '.join([f['format'].upper() for f in files]) if files else ''

        # Кнопка книги — сначала автор, потом название
        author_part = book['author'][:15] if len(book['author']) <= 15 else book['author'][:15]
        title_part = book['title'][:25] if len(book['title']) <= 25 else book['title'][:22] + "..."
        button_text = f"{author_part} — {title_part}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"lib_book_{book['id']}")])

    # Ряд навигации
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ Назад", callback_data=f"lib_cpage_{category}_{page - 1}" if category else f"lib_page_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"lib_cpage_{category}_{page + 1}" if category else f"lib_page_{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    # Кнопки фильтрации — три варианта
    keyboard.append([InlineKeyboardButton("👤 По авторам", callback_data="lib_authors")])
    keyboard.append([
        InlineKeyboardButton("📜 Классические труды", callback_data="lib_cat_classic"),
        InlineKeyboardButton("✍️ Современные авторы", callback_data="lib_cat_modern")
    ])

    # Кнопка «назад» при просмотре категории
    if category:
        keyboard.append([InlineKeyboardButton("« Все книги", callback_data="lib_back")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if edit:
        await message_or_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await message_or_query.reply_text(text, reply_markup=reply_markup)


async def library_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback-ов библиотеки"""
    query = update.callback_query
    await query.answer()

    data = query.data

    # Постраничная навигация
    if data.startswith('lib_page_'):
        page = int(data.replace('lib_page_', ''))
        await show_books_page(query, context, page=page, edit=True)

    # Навигация по страницам категории (lib_cpage_CATEGORY_PAGE)
    elif data.startswith('lib_cpage_'):
        parts = data.replace('lib_cpage_', '').rsplit('_', 1)
        category = parts[0]
        page = int(parts[1])
        await show_books_page(query, context, page=page, edit=True, category=category)

    # Показать детали книги
    elif data.startswith('lib_book_'):
        book_id = int(data.replace('lib_book_', ''))
        await show_book_details(query, book_id)

    # Фильтр по категории
    elif data.startswith('lib_cat_'):
        category = data.replace('lib_cat_', '')
        await show_books_page(query, context, page=0, edit=True, category=category)

    # Показать список авторов
    elif data == 'lib_authors':
        await show_authors_list(query)

    # Фильтр по автору
    elif data.startswith('lib_author_'):
        author = data.replace('lib_author_', '')
        await show_books_by_author(query, author)

    # Скачать файл
    elif data.startswith('lib_dl_'):
        parts = data.replace('lib_dl_', '').split('_')
        book_id = int(parts[0])
        file_format = parts[1]
        await send_book_file(query, context, book_id, file_format)

    # Назад к списку книг
    elif data == 'lib_back':
        await show_books_page(query, context, page=0, edit=True)


async def show_book_details(query, book_id: int):
    """Показать подробную информацию о книге с кнопками скачивания"""
    book = db.get_library_book(book_id)

    if not book:
        await query.edit_message_text("Книга не найдена")
        return

    # Формируем сообщение — сначала автор, потом название
    text = f"👤 *{book['author']}*\n"
    text += f"📖 {book['title']}\n"

    if book['description']:
        text += f"\n{book['description']}\n"

    # Получаем доступные файлы
    files = db.get_book_files(book_id)

    # Формируем клавиатуру с кнопками скачивания
    keyboard = []

    if files:
        text += "\n📥 Скачать:"
        format_row = []
        for f in files:
            size_kb = f['file_size'] // 1024 if f['file_size'] else 0
            btn_text = f"{f['format'].upper()}"
            if size_kb > 0:
                if size_kb > 1024:
                    btn_text += f" ({size_kb // 1024} MB)"
                else:
                    btn_text += f" ({size_kb} KB)"
            format_row.append(InlineKeyboardButton(btn_text, callback_data=f"lib_dl_{book_id}_{f['format']}"))

        # Разбиваем на ряды по 2-3 кнопки
        for i in range(0, len(format_row), 3):
            keyboard.append(format_row[i:i+3])
    else:
        text += "\n⚠️ Файлы пока не загружены"

    # Ссылка на покупку, если есть
    if book['buy_url']:
        keyboard.append([InlineKeyboardButton("🛒 Купить бумажную версию", url=book['buy_url'])])

    # Кнопка «назад»
    keyboard.append([InlineKeyboardButton("« Назад к списку", callback_data="lib_back")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_authors_list(query):
    """Показать список уникальных авторов"""
    authors = db.get_library_authors()

    if not authors:
        await query.edit_message_text("Авторы не найдены")
        return

    text = "👤 Авторы:\n\nВыберите автора:"

    keyboard = []
    for author in authors:
        # Подсчитываем количество книг автора
        author_books = db.get_library_books_by_author(author)
        btn_text = f"{author} ({len(author_books)})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"lib_author_{author}")])

    keyboard.append([InlineKeyboardButton("« Назад к списку", callback_data="lib_back")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)


async def show_books_by_author(query, author: str):
    """Показать все книги конкретного автора"""
    books = db.get_library_books_by_author(author)

    if not books:
        await query.edit_message_text(f"Книги автора {author} не найдены")
        return

    text = f"👤 {author}\n\nКниги автора:"

    keyboard = []
    for book in books:
        files = db.get_book_files(book['id'])
        formats = ' '.join([f['format'].upper() for f in files]) if files else ''
        btn_text = f"📖 {book['title'][:35]}"
        if len(book['title']) > 35:
            btn_text += "..."
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"lib_book_{book['id']}")])

    keyboard.append([InlineKeyboardButton("« К авторам", callback_data="lib_authors")])
    keyboard.append([InlineKeyboardButton("« К списку книг", callback_data="lib_back")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)


async def send_book_file(query, context: ContextTypes.DEFAULT_TYPE, book_id: int, file_format: str):
    """Отправить файл книги пользователю"""
    book = db.get_library_book(book_id)
    file_info = db.get_book_file(book_id, file_format)

    if not book or not file_info:
        await query.answer("Файл не найден", show_alert=True)
        return

    # Проверяем наличие кэшированного file_id
    if file_info['file_id']:
        # Отправляем через кэшированный file_id (быстро)
        try:
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=file_info['file_id'],
                filename=f"{book['author']} - {book['title']}.{file_format}",
                caption=f"📖 {book['title']}\n👤 {book['author']}"
            )
            await query.answer("Отправляю файл...")
            return
        except Exception:
            # file_id может быть невалидным, пробуем отправить из файла
            pass

    # Отправляем из файла на диске
    if not file_info['file_path'] or not os.path.exists(file_info['file_path']):
        await query.answer("Файл не найден на сервере", show_alert=True)
        return

    await query.answer("Отправляю файл...")

    try:
        with open(file_info['file_path'], 'rb') as f:
            message = await context.bot.send_document(
                chat_id=query.from_user.id,
                document=f,
                filename=f"{book['author']} - {book['title']}.{file_format}",
                caption=f"📖 {book['title']}\n👤 {book['author']}"
            )

        # Кэшируем file_id для последующего использования
        if message.document:
            db.update_book_file_id(book_id, file_format, message.document.file_id)

    except Exception as e:
        await query.answer(f"Ошибка: {str(e)}", show_alert=True)
