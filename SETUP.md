# Инструкция по установке и запуску Bestoic Bot

## Требования

- Python 3.10 или выше
- Telegram Bot Token (получить у @BotFather)
- Ваш Telegram User ID (получить у @userinfobot)

## Установка

### 1. Клонировать репозиторий

```bash
git clone <repository-url>
cd bestoic_bot
```

### 2. Создать виртуальное окружение

```bash
python -m venv venv
```

### 3. Активировать виртуальное окружение

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Установить зависимости

```bash
pip install -r requirements.txt
```

### 5. Настроить переменные окружения

Скопируйте `.env.example` в `.env`:

```bash
cp .env.example .env
```

Отредактируйте `.env` файл и добавьте:
- `TELEGRAM_BOT_TOKEN` - токен вашего бота от @BotFather
- `ADMIN_USER_IDS` - ваш Telegram User ID (или несколько ID через запятую) от @userinfobot

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Один администратор:
ADMIN_USER_IDS=123456789

# Или несколько администраторов (через запятую):
ADMIN_USER_IDS=123456789,987654321
```

**Примечание:** Старый формат `ADMIN_USER_ID` также поддерживается для обратной совместимости.

## Использование

### Запуск бота

```bash
python bot.py
```

Бот будет работать 24/7 и автоматически отправлять цитаты в назначенное время.

### Управление цитатами (Admin CLI)

```bash
python admin.py stats                    # Статистика
python admin.py quote add               # Добавить цитату
python admin.py quote list              # Список цитат
python admin.py quote list -c quotes    # Фильтр по категории
python admin.py quote view <ID>         # Посмотреть цитату
python admin.py quote edit <ID>         # Редактировать
python admin.py quote delete <ID>       # Удалить
python admin.py quote find-duplicates   # Найти дубликаты
```

Подробнее: [ADMIN_GUIDE.md](ADMIN_GUIDE.md)

### Тесты

```bash
pytest tests/ -v
```

## Команды бота для пользователей

- `/start` - начать работу с ботом
- `/quote` - получить случайную цитату прямо сейчас
- `/settings` - настроить категорию цитат и время получения
- `/help` - справка по командам

## Категории цитат

- **Цитаты** (quotes) - вдохновляющие мысли стоиков
- **Стоицизм на каждый день** (daily) - ежедневные размышления (366 дней)

## Время отправки

Пользователи могут выбрать одно из трех времен для получения ежедневных цитат:
- **Утро** - 8:00
- **День** - 14:00
- **Вечер** - 20:00

## Структура проекта

```
bestoic_bot/
├── bot.py                  # Главный файл бота
├── admin.py                # CLI для администратора
├── config.py               # Конфигурация
├── requirements.txt        # Зависимости
├── .env                    # Переменные окружения (создать вручную)
├── .env.example            # Пример переменных окружения
├── src/
│   ├── bot/                # Обработчики Telegram бота
│   ├── cli/                # CLI команды администратора
│   ├── database/           # Модели и операции с БД
│   └── utils/              # Утилиты (парсер цитат)
├── tests/                  # Тесты (pytest)
└── data/books/             # Файлы книг для библиотеки
```

## Troubleshooting

### Бот не отправляет сообщения

Проверьте:
1. Правильность токена бота в `.env`
2. Что бот запущен (`python bot.py`)
3. Что пользователь активировал уведомления в `/settings`

### База данных не создается

Убедитесь, что у вас есть права на запись в директорию проекта.

## Поддержка

Если возникли вопросы или проблемы, создайте Issue в репозитории проекта.
