import re
from typing import Tuple, Optional, List, Dict
from datetime import datetime


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


def parse_daily_stoicism_book(text: str) -> List[Dict]:
    """
    Parse "Daily Stoicism" book format into individual entries.

    Expected format:
    1 МАРТА
    Title

    Quote text
    Author / Source

    Reflection text

    2 МАРТА
    ...

    Returns:
        List of dicts with keys: day_of_year, title, quote_text, quote_author, quote_source
    """
    # Russian month names to numbers
    MONTHS_RU = {
        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
        'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
        'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
    }

    # Split by date headers (e.g., "1 МАРТА", "29 ФЕВРАЛЯ")
    date_pattern = r'(\d+\s+[А-ЯЁ]+)'
    parts = re.split(date_pattern, text)

    entries = []
    i = 1  # Skip first empty part
    while i < len(parts) - 1:
        date_header = parts[i].strip()
        content = parts[i + 1].strip()

        # Parse date
        match = re.match(r'(\d+)\s+([А-ЯЁ]+)', date_header)
        if not match:
            i += 2
            continue

        day = int(match.group(1))
        month_name = match.group(2).lower()

        # Get month number
        month = None
        for key, value in MONTHS_RU.items():
            if key.startswith(month_name.lower()[:3]):  # Match first 3 letters
                month = value
                break

        if not month:
            i += 2
            continue

        # Calculate day of year
        try:
            date_obj = datetime(2024, month, day)  # Use leap year to support Feb 29
            day_of_year = date_obj.timetuple().tm_yday
        except ValueError:
            i += 2
            continue

        # Parse content: Title, Quote+Attribution, Reflection
        # Split by double newline
        content_parts = content.split('\n\n')
        if len(content_parts) < 2:
            i += 2
            continue

        title = content_parts[0].strip()

        # Find the quote and attribution (middle section)
        # Quote is the section with attribution (contains author/source)
        quote_text = None
        quote_author = None
        quote_source = None

        # Try to find attribution pattern in content
        for j in range(1, len(content_parts)):
            part = content_parts[j]
            # Check if this part has attribution (name / source pattern)
            if '/' in part or re.search(r'[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\.', part):
                # This is likely the quote with attribution
                lines = part.split('\n')
                if len(lines) >= 2:
                    quote_text = '\n'.join(lines[:-1]).strip()
                    attribution = lines[-1].strip()
                    # Parse attribution
                    if '/' in attribution:
                        attr_parts = attribution.split('/', 1)
                        quote_author = attr_parts[0].strip()
                        quote_source = attr_parts[1].strip() if len(attr_parts) > 1 else None
                    else:
                        quote_author = attribution
                break

        if not quote_text:
            # Fallback: use second part as quote
            if len(content_parts) >= 2:
                quote_text = content_parts[1]

        # Combine all content (title + quote + reflection)
        full_text = f"{title}\n\n{content}"

        entries.append({
            'day_of_year': day_of_year,
            'title': title,
            'text': full_text,
            'quote_author': quote_author,
            'quote_source': quote_source
        })

        i += 2

    return entries


def format_quote_for_telegram(quote_text: str, category: str,
                              quote_author: Optional[str] = None,
                              quote_source: Optional[str] = None,
                              book_title: Optional[str] = None,
                              book_author: Optional[str] = None) -> str:
    """
    Format a quote for sending to Telegram with proper styling.

    Args:
        quote_text: The main quote text
        category: Category of the quote (quotes/daily)
        quote_author: Author extracted from quote itself
        quote_source: Source extracted from quote itself
        book_title: Title of the book (from database)
        book_author: Author of the book (from database)

    Returns:
        Formatted message string
    """
    category_emoji = {
        'quotes': '💭',
        'daily': '📅'
    }

    category_names = {
        'quotes': 'Цитаты',
        'daily': 'Стоицизм на каждый день'
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
