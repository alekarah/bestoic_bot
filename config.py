import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))

# Database Configuration
DATABASE_PATH = 'bestoic_bot.db'

# Time Slots for Notifications
TIME_SLOTS = {
    'morning': '08:00',
    'day': '14:00',
    'evening': '20:00'
}

# Categories
CATEGORIES = {
    'theory': 'Теория',
    'practice': 'Практика',
    'quotes': 'Цитаты',
    'all': 'Все категории'
}
