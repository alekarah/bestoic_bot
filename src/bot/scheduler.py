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
    """Send quotes to all users with subscriptions for a specific time slot"""
    logger.info(f"Sending scheduled quotes for time slot: {time_slot}")

    # Get all active subscriptions for this time slot
    subscriptions = db.get_subscriptions_by_time(time_slot)
    sent_count = 0

    for subscription in subscriptions:
        user_id = subscription['user_id']
        category = subscription['category']

        # For 'daily' category, ensure we only send once per day
        # The get_random_quote method already handles this by returning quote for current day
        quote = db.get_random_quote(user_id, category)

        if quote:
            try:
                await send_quote(user_id, quote, context)
                # Only mark as sent for non-daily quotes
                # Daily quotes should be available every day regardless of sent status
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
    """Setup APScheduler for sending quotes"""
    scheduler = AsyncIOScheduler()

    # Morning quotes - 8:00
    scheduler.add_job(
        send_scheduled_quotes,
        CronTrigger(hour=8, minute=0),
        args=[application, 'morning'],
        id='morning_quotes',
        name='Send morning quotes',
        replace_existing=True
    )

    # Day quotes - 14:00
    scheduler.add_job(
        send_scheduled_quotes,
        CronTrigger(hour=14, minute=0),
        args=[application, 'day'],
        id='day_quotes',
        name='Send day quotes',
        replace_existing=True
    )

    # Evening quotes - 20:00
    scheduler.add_job(
        send_scheduled_quotes,
        CronTrigger(hour=20, minute=0),
        args=[application, 'evening'],
        id='evening_quotes',
        name='Send evening quotes',
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started successfully")

    return scheduler
