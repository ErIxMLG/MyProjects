
Наблюдатель за папками Google Drive: отслеживает появление новых
и изменение существующих файлов в подпапках заданной папки.

Рассчитан на автономную работу на удалённом сервере через сервисный
аккаунт (service account) — без интерактивного входа в браузере.

УСТАНОВКА:
    pip install google-api-python-client google-auth requests

НАСТРОЙКА:
    1. Создать сервисный аккаунт в Google Cloud Console
    2. Скачать JSON-ключ, сохранить как service_account.json рядом со скриптом
    3. Расшарить корневую папку на Google Drive с email сервисного аккаунта
       (email вида xxx@project-id.iam.gserviceaccount.com, права "Читатель")
    4. Настроить телеграм-бота: см. telegram_notify.py
       (нужны TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID)

ИСПОЛЬЗОВАНИЕ:
    Уведомления при появлении/изменении/удалении файла уходят в Telegram
    (файл telegram_notify.py, функции-хуки on_file_added / on_file_modified
    / on_file_removed ниже). Хотите добавить ещё канал — пишите прямо там.

    В том же чате можно в любой момент написать боту /check —
    произойдёт внеочередная проверка и придёт итог.

    Запуск (постоянный процесс, опрос раз в CHECK_INTERVAL секунд, по дефолту 5 минут): 
        python3 gdrive_watcher.py

    Свой интервал опроса (в секундах):
        python3 gdrive_watcher.py --interval 60