from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.database.models import Database
import config
import os

db = Database()


async def books_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /books command - show library books list"""
    await show_books_page(update.message, context, page=0)


async def show_books_page(message_or_query, context: ContextTypes.DEFAULT_TYPE, page: int = 0, edit: bool = False):
    """Show a page of books from the library"""
    total = db.count_library_books()

    if total == 0:
        text = "📚 Библиотека пока пуста.\n\nКниги скоро появятся!"
        if edit:
            await message_or_query.edit_message_text(text)
        else:
            await message_or_query.reply_text(text)
        return

    # Calculate pagination
    per_page = config.BOOKS_PER_PAGE
    total_pages = (total + per_page - 1) // per_page
    offset = page * per_page

    # Ensure page is within bounds
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    books = db.get_all_library_books(limit=per_page, offset=offset)

    # Build message
    text = f"📚 Библиотека ({page + 1}/{total_pages})\n\n"

    # Build keyboard
    keyboard = []

    for book in books:
        # Get file formats for this book
        files = db.get_book_files(book['id'])
        formats = ' '.join([f['format'].upper() for f in files]) if files else ''

        # Add book button - Author first, then title
        author_part = book['author'][:15] if len(book['author']) <= 15 else book['author'][:15]
        title_part = book['title'][:25] if len(book['title']) <= 25 else book['title'][:22] + "..."
        button_text = f"👤 {author_part} — {title_part}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"lib_book_{book['id']}")])

    # Navigation row
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ Назад", callback_data=f"lib_page_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"lib_page_{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    # Filter by author button
    keyboard.append([InlineKeyboardButton("👤 По авторам", callback_data="lib_authors")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if edit:
        await message_or_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await message_or_query.reply_text(text, reply_markup=reply_markup)


async def library_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle library-related callbacks"""
    query = update.callback_query
    await query.answer()

    data = query.data

    # Page navigation
    if data.startswith('lib_page_'):
        page = int(data.replace('lib_page_', ''))
        await show_books_page(query, context, page=page, edit=True)

    # Show book details
    elif data.startswith('lib_book_'):
        book_id = int(data.replace('lib_book_', ''))
        await show_book_details(query, book_id)

    # Show authors list
    elif data == 'lib_authors':
        await show_authors_list(query)

    # Filter by author
    elif data.startswith('lib_author_'):
        author = data.replace('lib_author_', '')
        await show_books_by_author(query, author)

    # Download file
    elif data.startswith('lib_dl_'):
        parts = data.replace('lib_dl_', '').split('_')
        book_id = int(parts[0])
        file_format = parts[1]
        await send_book_file(query, context, book_id, file_format)

    # Back to books list
    elif data == 'lib_back':
        await show_books_page(query, context, page=0, edit=True)


async def show_book_details(query, book_id: int):
    """Show detailed book information with download buttons"""
    book = db.get_library_book(book_id)

    if not book:
        await query.edit_message_text("Книга не найдена")
        return

    # Build message - Author first, then title
    text = f"👤 *{book['author']}*\n"
    text += f"📖 {book['title']}\n"

    if book['description']:
        text += f"\n{book['description']}\n"

    # Get available files
    files = db.get_book_files(book_id)

    # Build keyboard with download buttons
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

        # Split into rows of 2-3 buttons
        for i in range(0, len(format_row), 3):
            keyboard.append(format_row[i:i+3])
    else:
        text += "\n⚠️ Файлы пока не загружены"

    # Buy link if available
    if book['buy_url']:
        keyboard.append([InlineKeyboardButton("🛒 Купить бумажную версию", url=book['buy_url'])])

    # Back button
    keyboard.append([InlineKeyboardButton("« Назад к списку", callback_data="lib_back")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_authors_list(query):
    """Show list of unique authors"""
    authors = db.get_library_authors()

    if not authors:
        await query.edit_message_text("Авторы не найдены")
        return

    text = "👤 Авторы:\n\nВыберите автора:"

    keyboard = []
    for author in authors:
        # Count books by this author
        author_books = db.get_library_books_by_author(author)
        btn_text = f"{author} ({len(author_books)})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"lib_author_{author}")])

    keyboard.append([InlineKeyboardButton("« Назад к списку", callback_data="lib_back")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)


async def show_books_by_author(query, author: str):
    """Show all books by a specific author"""
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
    """Send book file to user"""
    book = db.get_library_book(book_id)
    file_info = db.get_book_file(book_id, file_format)

    if not book or not file_info:
        await query.answer("Файл не найден", show_alert=True)
        return

    # Check if we have cached file_id
    if file_info['file_id']:
        # Send using cached file_id (fast)
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
            # file_id might be invalid, try sending from path
            pass

    # Send from file path
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

        # Cache the file_id for future use
        if message.document:
            db.update_book_file_id(book_id, file_format, message.document.file_id)

    except Exception as e:
        await query.answer(f"Ошибка: {str(e)}", show_alert=True)
