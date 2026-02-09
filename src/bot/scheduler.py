"""Планировщик рассылки цитат по расписанию (APScheduler)."""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import ContextTypes
from src.database.models import Database
from src.bot.handlers import send_quote
import config


logger = logging.getLogger(__name__)
db = Database()


async def send_scheduled_quotes(context: ContextTypes.DEFAULT_TYPE, time_slot: str):
    """Отправить цитаты всем пользователям с подписками на указанный временной слот"""
    logger.info(f"Sending scheduled quotes for time slot: {time_slot}")

    # Получаем все активные подписки для этого временного слота
    subscriptions = db.get_subscriptions_by_time(time_slot)
    sent_count = 0

    for subscription in subscriptions:
        user_id = subscription['user_id']
        category = subscription['category']

        # Для категории 'daily' отправляем только раз в день
        # Метод get_random_quote уже обрабатывает это, возвращая цитату текущего дня
        quote = db.get_random_quote(user_id, category)

        if quote:
            try:
                await send_quote(user_id, quote, context, user_id=user_id)
                # Отмечаем как отправленную только для не-daily цитат
                # Ежедневные цитаты должны быть доступны каждый день независимо от статуса отправки
                if category != 'daily':
                    db.mark_quote_as_sent(user_id, quote['id'])
                sent_count += 1
                logger.info(f"Sent {category} quote to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send quote to user {user_id}: {e}")
        else:
            logger.warning(f"No quotes available for user {user_id} in category {category}")

    logger.info(f"Finished sending quotes for {time_slot}. Sent {sent_count} quotes.")


def setup_scheduler(application):
    """Настроить APScheduler для отправки цитат по расписанию"""
    scheduler = AsyncIOScheduler()

    # Утренние цитаты — 8:00
    scheduler.add_job(
        send_scheduled_quotes,
        CronTrigger(hour=8, minute=0),
        args=[application, 'morning'],
        id='morning_quotes',
        name='Отправка утренних цитат',
        replace_existing=True
    )

    # Дневные цитаты — 14:00
    scheduler.add_job(
        send_scheduled_quotes,
        CronTrigger(hour=14, minute=0),
        args=[application, 'day'],
        id='day_quotes',
        name='Отправка дневных цитат',
        replace_existing=True
    )

    # Вечерние цитаты — 20:00
    scheduler.add_job(
        send_scheduled_quotes,
        CronTrigger(hour=20, minute=0),
        args=[application, 'evening'],
        id='evening_quotes',
        name='Отправка вечерних цитат',
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started successfully")

    return scheduler
