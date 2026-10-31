"""
Отправка уведомлений в Telegram через Bot API.

НАСТРОЙКА:
    1. Создать бота через @BotFather в Telegram, получить токен.
    2. Написать боту /start (или добавить его в группу).
    3. Узнать chat_id: открыть в браузере
       https://api.telegram.org/bot<ТОКЕН>/getUpdates
       и найти поле "chat":{"id": ...}
    4. Задать TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID ниже
       (лучше через переменные окружения, см. комментарий).

УСТАНОВКА ЗАВИСИМОСТЕЙ:
    pip install requests
"""

import json
from pathlib import Path
import os
import requests

config_path = Path(__file__).parent / "keys.json"

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)


TELEGRAM_BOT_TOKEN = config["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = config["TELEGRAM_CHAT_ID"]

API_BASE = "https://api.telegram.org/bot{token}/"
API_URL = API_BASE + "sendMessage"


def send_telegram_message(text, parse_mode="HTML"):
    """
    Отправляет сообщение в заданный чат.
    Возвращает True при успехе, False при ошибке (и печатает причину).
    """
    if not TELEGRAM_BOT_TOKEN or "ВСТАВЬТЕ" in TELEGRAM_BOT_TOKEN:
        print("[telegram] Токен не настроен — пропускаю отправку.")
        return False

    url = API_URL.format(token=TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, data=payload, timeout=15)
        if response.status_code == 200 and response.json().get("ok"):
            return True
        print(f"[telegram] Ошибка отправки: {response.status_code} {response.text}")
        return False
    except requests.RequestException as e:
        print(f"[telegram] Сетевая ошибка при отправке: {e}")
        return False


def get_updates(offset=None, timeout=30):
    """
    Long polling: ждёт до `timeout` секунд новых сообщений боту.
    offset — id, начиная с которого запрашивать (чтобы не получать
    одни и те же сообщения повторно). Возвращает список апдейтов.
    """
    if not TELEGRAM_BOT_TOKEN or "ВСТАВЬТЕ" in TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Токен Telegram не настроен")

    url = API_BASE.format(token=TELEGRAM_BOT_TOKEN) + "getUpdates"
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset

    response = requests.get(url, params=params, timeout=timeout + 10)
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"getUpdates вернул ошибку: {data}")
    return data.get("result", [])


def set_bot_commands(commands):
    """
    Регистрирует список команд у бота, чтобы Telegram показывал
    подсказки при вводе "/". commands — список кортежей (команда, описание),
    например [("check", "Проверить папки прямо сейчас")].
    """
    if not TELEGRAM_BOT_TOKEN or "ВСТАВЬТЕ" in TELEGRAM_BOT_TOKEN:
        print("[telegram] Токен не настроен — команды не зарегистрированы.")
        return False

    url = API_BASE.format(token=TELEGRAM_BOT_TOKEN) + "setMyCommands"
    payload = {
        "commands": [
            {"command": cmd, "description": desc} for cmd, desc in commands
        ]
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200 and response.json().get("ok"):
            print("[telegram] Список команд зарегистрирован.")
            return True
        print(f"[telegram] Не удалось зарегистрировать команды: {response.text}")
        return False
    except requests.RequestException as e:
        print(f"[telegram] Сетевая ошибка при регистрации команд: {e}")
        return False


if __name__ == "__main__":
    # Быстрая проверка: python3 telegram_notify.py
    ok = send_telegram_message("✅ Тестовое сообщение от gdrive_watcher")
    print("Отправлено успешно" if ok else "Не удалось отправить")