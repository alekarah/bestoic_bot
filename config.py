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
