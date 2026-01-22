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

    Format:
    DATE (e.g. "1 ЯНВАРЯ")
    Title (on next line, no empty line after date)

    Quote text (can be multiple lines, no empty lines inside)

    Attribution (Author / Source OR just Author name, short single line)

    Reflection text (can be multiple lines)


    On 4 specific days (Mar 9, May 22, Oct 13, Nov 1) there are 2 quotes:
    Quote1

    Attribution1

    Quote2

    Attribution2

    Reflection

    Returns:
        List of dicts with keys: day_of_year, title, text, quote_author, quote_source
    """
    # Russian month names to numbers
    MONTHS_RU = {
        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
        'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
        'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
    }

    def is_attribution(text):
        """
        Check if text is an attribution line.
        Attribution is a SHORT, SINGLE LINE with author name and optionally source.
        Examples: "Эпиктет / Беседы", "Сенека", "Феогнид Мегарский", "Марк Аврелий / Размышления"

        NOT attribution: "Барбара Джордан / лидер правозащитного движения" (sentence continues after /)
        """
        text = text.strip()
        # Must be single line (no newlines)
        if '\n' in text:
            return False
        # Must be SHORT - attribution is typically < 50 chars
        if len(text) > 50:
            return False
        # Must start with capital letter (name)
        if not text or not text[0].isupper():
            return False
        # Should be very short in words (author name 1-3 words + source 1-4 words)
        words = text.split()
        if len(words) > 6:
            return False
        # If has "/", check that:
        # 1. Author part is 1-3 words
        # 2. Source part starts with capital (book title) and is short
        if '/' in text:
            parts = text.split('/', 1)
            author_part = parts[0].strip()
            source_part = parts[1].strip() if len(parts) > 1 else ''
            # Author should be 1-3 words (a name)
            author_words = author_part.split()
            if len(author_words) > 3:
                return False
            # Source should start with capital letter (book title)
            if source_part and not source_part[0].isupper():
                return False
            # Source should be short (1-4 words max, book title)
            source_words = source_part.split()
            if len(source_words) > 5:
                return False
        return True

    def parse_attribution(text):
        """Parse attribution into author and source"""
        text = text.strip()
        if '/' in text:
            parts = text.split('/', 1)
            return parts[0].strip(), parts[1].strip() if len(parts) > 1 else None
        return text, None

    # Split by date headers (e.g., "1 ЯНВАРЯ", "29 ФЕВРАЛЯ")
    # Date is at start of line, followed by newline and title
    date_pattern = r'(\d+\s+[А-ЯЁ]+)\n'
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

        # Parse content by empty lines
        # Split by double newline (one empty line = paragraph separator)
        content_parts = [p.strip() for p in content.split('\n\n') if p.strip()]

        if len(content_parts) < 2:
            i += 2
            continue

        # [0] = Title
        title = content_parts[0].strip()

        # Find first attribution (it comes after the first quote)
        # Structure: Title, Quote, Attribution, [Quote2, Attribution2], Reflection
        quote_text = None
        quote_author = None
        quote_source = None

        # [1] is always the first quote
        if len(content_parts) >= 2:
            quote_text = content_parts[1].strip()

        # [2] should be the attribution for the first quote
        if len(content_parts) >= 3 and is_attribution(content_parts[2]):
            quote_author, quote_source = parse_attribution(content_parts[2])

        if not quote_text:
            # Fallback: use second part as quote
            if len(content_parts) >= 2:
                quote_text = content_parts[1]

        # Use content as full text (it already starts with the title)
        full_text = content

        entries.append({
            'day_of_year': day_of_year,
            'title': title,
            'text': full_text,
            'quote_author': quote_author,
            'quote_source': quote_source
        })

        i += 2

    return entries


def day_of_year_to_date(day_of_year: int) -> str:
    """Convert day of year (1-366) to Russian date string like '9 марта'"""
    from datetime import datetime

    MONTHS_RU_GENITIVE = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }

    # Use leap year to support day 366
    date = datetime(2024, 1, 1) + __import__('datetime').timedelta(days=day_of_year - 1)
    return f"{date.day} {MONTHS_RU_GENITIVE[date.month]}"


def format_quote_for_telegram(quote_text: str, category: str,
                              quote_author: Optional[str] = None,
                              quote_source: Optional[str] = None,
                              book_title: Optional[str] = None,
                              book_author: Optional[str] = None,
                              day_of_year: Optional[int] = None) -> str:
    """
    Format a quote for sending to Telegram with proper styling.

    Args:
        quote_text: The main quote text
        category: Category of the quote (quotes/daily)
        quote_author: Author extracted from quote itself
        quote_source: Source extracted from quote itself
        book_title: Title of the book (from database)
        book_author: Author of the book (from database)
        day_of_year: Day of year (1-366) for daily category

    Returns:
        Formatted message string
    """
    category_emoji = {
        'quotes': '💭',
        'daily': '📅'
    }

    # For daily category, show date instead of category name
    if category == 'daily' and day_of_year:
        header = f"📅 {day_of_year_to_date(day_of_year)}"
    else:
        emoji = category_emoji.get(category, '💬')
        category_names = {
            'quotes': 'Цитаты',
            'daily': 'Стоицизм на каждый день'
        }
        header = f"{emoji} {category_names.get(category, category)}"

    # Start with header and quote text
    message = f"{header}\n\n{quote_text}"

    # For 'daily' category, attribution is already embedded in the text
    # Don't add it again at the end
    if category != 'daily':
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
