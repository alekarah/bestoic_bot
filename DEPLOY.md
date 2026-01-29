# Деплой Bestoic Bot на VPS (Beget)

## 1. Создание сервера

1. Зайди на https://beget.com/ru/cloud
2. **VPS** → **Заказать**
3. Выбери:
   - **ОС:** Ubuntu 22.04
   - **Тариф:** VPS 1 (199₽/мес — 1GB RAM, 1 CPU, 10GB SSD)
4. Задай пароль для root или добавь SSH-ключ
5. Создай сервер, запиши IP-адрес (будет в панели управления)

---

## 2. Подключение к серверу

```bash
ssh root@ТВОЙ_IP_АДРЕС
```

---

## 3. Настройка сервера

```bash
# Обновление системы
apt update && apt upgrade -y

# Установка Python и необходимых пакетов
apt install -y python3 python3-pip python3-venv git

# Создание пользователя для бота (безопаснее чем root)
useradd -m -s /bin/bash botuser

# Переключение на пользователя
su - botuser

# Создание директории
mkdir ~/bestoic_bot
cd ~/bestoic_bot
```

---

## 4. Загрузка файлов на сервер

### Вариант А — через Git (если репозиторий на GitHub):

```bash
git clone https://github.com/ТВОЙ_USERNAME/bestoic_bot.git .
```

### Вариант Б — через SCP (с локального компьютера):

Выполни в PowerShell на своём компьютере:

```powershell
scp -r D:\projects\pet-projects\bestoic_bot\* root@ТВОЙ_IP:/home/botuser/bestoic_bot/
```

Затем на сервере исправь владельца:

```bash
chown -R botuser:botuser /home/botuser/bestoic_bot
```

---

## 5. Настройка бота

```bash
# Переключись на botuser если ещё не
su - botuser
cd ~/bestoic_bot

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Создание .env файла
cat > .env << 'EOF'
TELEGRAM_BOT_TOKEN=твой_токен_бота
ADMIN_USER_IDS=твой_telegram_id
EOF

# Проверка запуска (Ctrl+C для остановки)
python bot.py
```

---

## 6. Настройка автозапуска (systemd)

Выйди из botuser обратно в root (`exit`) и выполни:

```bash
# Создание сервиса
cat > /etc/systemd/system/bestoic-bot.service << 'EOF'
[Unit]
Description=Bestoic Telegram Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/bestoic_bot
Environment=PATH=/home/botuser/bestoic_bot/venv/bin
ExecStart=/home/botuser/bestoic_bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Активация и запуск
systemctl daemon-reload
systemctl enable bestoic-bot
systemctl start bestoic-bot

# Проверка статуса
systemctl status bestoic-bot
```

---

## 7. Полезные команды

```bash
# Просмотр логов (в реальном времени)
journalctl -u bestoic-bot -f

# Просмотр последних 50 строк логов
journalctl -u bestoic-bot -n 50

# Перезапуск бота
systemctl restart bestoic-bot

# Остановка бота
systemctl stop bestoic-bot

# Статус бота
systemctl status bestoic-bot
```

---

## 8. Обновление бота

### Через Git:

```bash
su - botuser
cd ~/bestoic_bot
git pull
exit
systemctl restart bestoic-bot
```

### Через SCP:

1. Загрузи обновлённые файлы с локального компьютера
2. Перезапусти бота: `systemctl restart bestoic-bot`

---

## 9. Резервное копирование базы данных

```bash
# На сервере
su - botuser
cp ~/bestoic_bot/bestoic_bot.db ~/bestoic_bot/backup_$(date +%Y%m%d).db

# Скачать на локальный компьютер (выполни в PowerShell)
scp root@ТВОЙ_IP:/home/botuser/bestoic_bot/bestoic_bot.db D:\backups\
```

---

## Troubleshooting

### Бот не запускается

```bash
# Проверь логи
journalctl -u bestoic-bot -n 100

# Проверь .env файл
cat /home/botuser/bestoic_bot/.env

# Попробуй запустить вручную
su - botuser
cd ~/bestoic_bot
source venv/bin/activate
python bot.py
```

### Ошибка "Permission denied"

```bash
chown -R botuser:botuser /home/botuser/bestoic_bot
chmod +x /home/botuser/bestoic_bot/bot.py
```

### Часовой пояс (для правильного времени уведомлений)

```bash
# Проверить текущий
timedatectl

# Установить московское время
timedatectl set-timezone Europe/Moscow
```

---

## Резервное копирование

### Автоматический бэкап

На сервере настроен автоматический ежедневный бэкап базы данных в 4:00 утра (MSK).

**Настройка:**
- Скрипт: `/home/botuser/backup_db.sh`
- Директория бэкапов: `/home/botuser/backups/`
- Хранятся последние 7 дней
- Автоматическое сжатие (gzip)
- Логирование: `/home/botuser/backups/backup.log`

**Проверить бэкапы:**
```bash
ssh botuser@YOUR_SERVER_IP "ls -lh /home/botuser/backups/"
```

**Просмотреть лог:**
```bash
ssh botuser@YOUR_SERVER_IP "cat /home/botuser/backups/backup.log"
```

**Запустить бэкап вручную:**
```bash
ssh botuser@YOUR_SERVER_IP "/home/botuser/backup_db.sh"
```

### Восстановление из бэкапа

**1. Скачать бэкап на локальный компьютер:**
```bash
scp botuser@YOUR_SERVER_IP:/home/botuser/backups/bestoic_bot_YYYY-MM-DD_HH-MM-SS.db.gz D:\backups\
```

**2. Распаковать локально:**
```bash
# Windows (PowerShell)
gzip -d D:\backups\bestoic_bot_YYYY-MM-DD_HH-MM-SS.db.gz

# Linux/Mac
gunzip D:\backups\bestoic_bot_YYYY-MM-DD_HH-MM-SS.db.gz
```

**3. Восстановить на сервере (если нужно):**
```bash
# Остановить бота
ssh botuser@YOUR_SERVER_IP "sudo systemctl stop bot"

# Сделать резервную копию текущей БД
ssh botuser@YOUR_SERVER_IP "cp /home/botuser/bestoic_bot/bestoic_bot.db /home/botuser/bestoic_bot/bestoic_bot.db.before_restore"

# Скопировать бэкап из архива
ssh botuser@YOUR_SERVER_IP "gunzip -c /home/botuser/backups/bestoic_bot_YYYY-MM-DD_HH-MM-SS.db.gz > /home/botuser/bestoic_bot/bestoic_bot.db"

# Запустить бота
ssh botuser@YOUR_SERVER_IP "sudo systemctl start bot"
```

**4. Проверить статус:**
```bash
ssh botuser@YOUR_SERVER_IP "sudo systemctl status bot"
```

### Ручной бэкап (дополнительно)

Для важных изменений рекомендуется делать ручной бэкап перед:
- Массовым добавлением/удалением цитат
- Обновлением кода бота
- Изменением структуры базы данных

```bash
# Скачать текущую БД
scp botuser@YOUR_SERVER_IP:/home/botuser/bestoic_bot/bestoic_bot.db D:\backups\bestoic_bot_manual_$(date +%Y%m%d).db
```

### Настройка cron (уже настроено)

Бэкапы запускаются автоматически через cron:
```bash
# Посмотреть настройки cron
ssh botuser@YOUR_SERVER_IP "crontab -l"

# Вывод:
# 0 4 * * * /home/botuser/backup_db.sh
```

**Изменить время бэкапа:**
```bash
ssh botuser@YOUR_SERVER_IP "crontab -e"
# Изменить время в формате: минута час день месяц день_недели
# Например, 0 2 * * * = каждый день в 2:00
```
