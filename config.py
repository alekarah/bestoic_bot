import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Admin User IDs (supports multiple admins)
# Can be a single ID or comma-separated list of IDs
admin_ids_str = os.getenv('ADMIN_USER_IDS', os.getenv('ADMIN_USER_ID', '0'))
ADMIN_USER_IDS = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]

# Backward compatibility - keep ADMIN_USER_ID as the first admin
ADMIN_USER_ID = ADMIN_USER_IDS[0] if ADMIN_USER_IDS else 0

# Database Configuration
# Use environment variable for deployment, fallback to local file for development
DATABASE_PATH = os.getenv('DATABASE_PATH', 'bestoic_bot.db')

# Time Slots for Notifications
TIME_SLOTS = {
    'morning': '08:00',
    'day': '14:00',
    'evening': '20:00'
}

# Categories
CATEGORIES = {
    'quotes': 'Цитаты',
    'daily': 'Стоицизм на каждый день'
}

# Time Slot Descriptions (motivational messages when selecting time)
TIME_SLOT_DESCRIPTIONS = {
    'morning': 'Утренняя цитата — как чашка кофе для ума: бодрит, фокусирует, напоминает, что вы сильнее обстоятельств.',
    'day': 'Дневная пауза — момент вернуться к себе посреди суеты. Цитата напомнит, что важно, а что можно отпустить.',
    'evening': 'Вечерняя мудрость — время подвести итоги дня со спокойствием стоика. Завтра новый день, сегодня — урок.'
}

# Subscription Confirmation Messages (category + time)
SUBSCRIPTION_CONFIRMATIONS = {
    'quotes': {
        'morning': 'Отлично! Теперь каждое утро в 8:00 вас будет ждать цитата стоика. Пусть день будет мудрым!',
        'day': 'Готово! В 14:00 приходит цитата — короткая передышка и напоминание о главном.',
        'evening': 'Прекрасно! Вечером в 20:00 — момент мудрости перед отдыхом. Спокойной ночи будет обеспечено!'
    },
    'daily': {
        'morning': 'Замечательно! Каждое утро в 8:00 — размышление дня из стоического календаря. Год мудрости начался!',
        'day': 'Отлично! В 14:00 вас ждёт ежедневная практика стоика. Философия посреди дня!',
        'evening': 'Идеально! Вечером в 20:00 — глубокое размышление дня. Завершайте день с мудростью!'
    }
}

# Library settings
BOOKS_PER_PAGE = 5  # Number of books per page in /books command
BOOK_FILES_PATH = os.getenv('BOOK_FILES_PATH', 'data/books')  # Path to store book files
