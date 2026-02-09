"""Пакет админских обработчиков бота: цитаты, статистика, рассылка."""

from src.bot.admin.quotes import (
    get_add_quote_handler,
    get_delete_quote_handler,
    get_edit_quote_handler,
)
from src.bot.admin.stats import (
    get_admin_users_handler,
    get_admin_quote_stats_handler,
)
from src.bot.admin.broadcast import (
    get_broadcast_handler,
)
