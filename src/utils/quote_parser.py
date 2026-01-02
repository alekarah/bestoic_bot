import re
from typing import Tuple, Optional


def parse_quote(text: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Parse a quote to extract the main text, author, and source.

    Supports formats like:
    - "Quote text\n\n - Author / Source"
    - "Quote text\n\n— Author / Source"
    - "Quote text\n\nAuthor / Source"

    Returns:
        Tuple of (quote_text, author, source)
    """
    # Split by double newline to separate quote from attribution
    parts = text.split('\n\n')

    if len(parts) < 2:
        # No attribution found
        return text.strip(), None, None

    # The quote is everything except the last part
    quote_text = '\n\n'.join(parts[:-1]).strip()
    attribution = parts[-1].strip()

    # Try to extract author and source from attribution
    # Patterns:
    # - Author / Source
    # — Author / Source
    # Author, Source

    # Remove common prefixes
    attribution = re.sub(r'^[\-—–]\s*', '', attribution)

    # Split by / or ,
    if '/' in attribution:
        parts = attribution.split('/', 1)
        author = parts[0].strip()
        source = parts[1].strip() if len(parts) > 1 else None
    elif ',' in attribution:
        parts = attribution.split(',', 1)
        author = parts[0].strip()
        source = parts[1].strip() if len(parts) > 1 else None
    else:
        # Only author, no source
        author = attribution.strip()
        source = None

    return quote_text, author, source


def format_quote_for_telegram(quote_text: str, category: str,
                              quote_author: Optional[str] = None,
                              quote_source: Optional[str] = None,
                              book_title: Optional[str] = None,
                              book_author: Optional[str] = None) -> str:
    """
    Format a quote for sending to Telegram with proper styling.

    Args:
        quote_text: The main quote text
        category: Category of the quote (theory/practice/quotes)
        quote_author: Author extracted from quote itself
        quote_source: Source extracted from quote itself
        book_title: Title of the book (from database)
        book_author: Author of the book (from database)

    Returns:
        Formatted message string
    """
    category_emoji = {
        'theory': '📖',
        'practice': '🏃',
        'quotes': '💭'
    }

    category_names = {
        'theory': 'Теория',
        'practice': 'Практика',
        'quotes': 'Цитаты'
    }

    emoji = category_emoji.get(category, '💬')
    category_name = category_names.get(category, category)

    # Start with category and quote text
    message = f"{emoji} {category_name}\n\n{quote_text}"

    # Add attribution
    # Priority: quote_author/quote_source > book_author/book_title
    if quote_author or quote_source:
        attribution_parts = []
        if quote_author:
            attribution_parts.append(quote_author)
        if quote_source:
            attribution_parts.append(quote_source)
        message += f"\n\n— {' / '.join(attribution_parts)}"
    elif book_title and book_author:
        message += f"\n\n— {book_author} / {book_title}"

    return message
