
import argparse
import json
import os
import sys
import time
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from telegram_notify import (
    send_telegram_message,
    get_updates,
    set_bot_commands,
    TELEGRAM_CHAT_ID,
)
import threading

# Команды, которые увидит пользователь при вводе "/" в чате с ботом.
# Добавите новую команду — впишите её сюда и обработайте в listen_for_commands.
BOT_COMMANDS = [
    ("check", "Проверить папки прямо сейчас"),
    ("status", "Когда была последняя проверка"),
    ("list", "Список всех отслеживаемых файлов"),
]

# ==================== НАСТРОЙКИ ====================

SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# ID корневой папки. Извлечён из ссылки:
# https://drive.google.com/drive/folders/1KUYw9aQ6eoPHtqI6M6EzbeOWZtVNgDdO
ROOT_FOLDER_ID = "1KUYw9aQ6eoPHtqI6M6EzbeOWZtVNgDdO"

# Файл, в котором сохраняется состояние между запусками
STATE_FILE = "drive_state.json"

# Интервал опроса в секундах по умолчанию (можно переопределить через --interval)
CHECK_INTERVAL = 300  # 5 минут

FIELDS = "nextPageToken, files(id, name, mimeType, modifiedTime, size, parents)"

# Заполняется в main() из --interval, используется в /status
ACTIVE_INTERVAL = CHECK_INTERVAL
_last_check_time = None

# ==================== АВТОРИЗАЦИЯ ====================


def get_drive_service():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        sys.exit(
            f"Не найден {SERVICE_ACCOUNT_FILE}. "
            "Скачайте JSON-ключ сервисного аккаунта и положите его рядом со скриптом."
        )
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


# ==================== РАБОТА С DRIVE ====================


def is_folder(item):
    return item.get("mimeType") == "application/vnd.google-apps.folder"


def list_children(service, folder_id):
    """Список файлов/папок внутри folder_id (без вложенной рекурсии)."""
    items = []
    page_token = None
    query = f"'{folder_id}' in parents and trashed = false"

    while True:
        try:
            response = (
                service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields=FIELDS,
                    pageSize=200,
                    pageToken=page_token,
                    # Нужно, чтобы видеть содержимое Общих дисков (Shared Drives),
                    # а не только обычных папок на "Моём диске".
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    corpora="allDrives",
                )
                .execute()
            )
        except HttpError as error:
            print(f"[ошибка] Не удалось получить список для {folder_id}: {error}")
            break

        items.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return items


def get_subfolders(service, root_id):
    """Возвращает список подпапок (ожидаются те самые 9 папок с заданиями)."""
    children = list_children(service, root_id)
    return [c for c in children if is_folder(c)]


def scan_all_files(service, root_id):
    """
    Сканирует корневую папку и все подпапки первого уровня.
    Возвращает dict: file_id -> {name, folder_name, folder_id, modifiedTime, mimeType, size}
    """
    snapshot = {}

    subfolders = get_subfolders(service, root_id)

    for folder in subfolders:
        files = list_children(service, folder["id"])
        for f in files:
            if is_folder(f):
                # если внутри папок с заданиями есть ещё вложенные папки —
                # тоже сканируем их (на случай подпапок внутри задания)
                nested = list_children(service, f["id"])
                for nf in nested:
                    snapshot[nf["id"]] = {
                        "name": nf["name"],
                        "folder_name": f"{folder['name']}/{f['name']}",
                        "folder_id": f["id"],
                        "modifiedTime": nf.get("modifiedTime"),
                        "mimeType": nf.get("mimeType"),
                        "size": nf.get("size"),
                    }
            else:
                snapshot[f["id"]] = {
                    "name": f["name"],
                    "folder_name": folder["name"],
                    "folder_id": folder["id"],
                    "modifiedTime": f.get("modifiedTime"),
                    "mimeType": f.get("mimeType"),
                    "size": f.get("size"),
                }

    return snapshot


# ==================== СОСТОЯНИЕ МЕЖДУ ЗАПУСКАМИ ====================


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ==================== ХУКИ ДЛЯ УВЕДОМЛЕНИЙ ====================
# Отправка идёт в Telegram (настройки токена/chat_id — в telegram_notify.py).
# При необходимости можно добавить и другие каналы (email, вебхук и т.п.)
# прямо здесь же, рядом с вызовом send_telegram_message.


def on_file_added(file_info):
    print(
        f"[НОВЫЙ ФАЙЛ] {file_info['folder_name']}: {file_info['name']} "
        f"({file_info.get('modifiedTime')})"
    )
    text = (
        "🆕 <b>Новый файл</b>\n"
        f"📁 Папка: {file_info['folder_name']}\n"
        f"📄 Файл: {file_info['name']}"
    )
    send_telegram_message(text)


def on_file_modified(file_info, old_modified_time):
    print(
        f"[ИЗМЕНЁН ФАЙЛ] {file_info['folder_name']}: {file_info['name']} "
        f"(было {old_modified_time}, стало {file_info.get('modifiedTime')})"
    )
    text = (
        "✏️ <b>Файл изменён</b>\n"
        f"📁 Папка: {file_info['folder_name']}\n"
        f"📄 Файл: {file_info['name']}"
    )
    send_telegram_message(text)


def on_file_removed(file_id, old_info):
    print(f"[УДАЛЁН/ПЕРЕМЕЩЁН ФАЙЛ] {old_info['folder_name']}: {old_info['name']}")
    text = (
        "🗑 <b>Файл удалён/перемещён</b>\n"
        f"📁 Папка: {old_info['folder_name']}\n"
        f"📄 Файл: {old_info['name']}"
    )
    send_telegram_message(text)


# ==================== ОСНОВНАЯ ЛОГИКА ПРОВЕРКИ ====================


# Лок нужен, т.к. проверка может быть вызвана либо из периодического
# цикла, либо вручную командой /check из Telegram — не должны наложиться.
_check_lock = threading.Lock()


def check_once(service):
    """Выполняет одну проверку. Возвращает сводку изменений (для /check)."""
    global _last_check_time
    with _check_lock:
        print(f"[{datetime.now().isoformat(timespec='seconds')}] Проверка изменений...")

        old_state = load_state()
        new_state = scan_all_files(service, ROOT_FOLDER_ID)

        old_ids = set(old_state.keys())
        new_ids = set(new_state.keys())

        added_ids = new_ids - old_ids
        removed_ids = old_ids - new_ids
        common_ids = new_ids & old_ids
        modified_ids = [
            fid
            for fid in common_ids
            if old_state[fid].get("modifiedTime") != new_state[fid].get("modifiedTime")
        ]

        for fid in added_ids:
            on_file_added(new_state[fid])

        for fid in removed_ids:
            on_file_removed(fid, old_state[fid])

        for fid in modified_ids:
            on_file_modified(new_state[fid], old_state[fid].get("modifiedTime"))

        save_state(new_state)
        _last_check_time = datetime.now()

        if not added_ids and not removed_ids and not modified_ids:
            print("Изменений не обнаружено.")

        print(f"Всего отслеживается файлов: {len(new_state)}")

        return {
            "added": [new_state[fid] for fid in added_ids],
            "removed": [old_state[fid] for fid in removed_ids],
            "modified": [new_state[fid] for fid in modified_ids],
            "total": len(new_state),
        }


def send_check_summary(summary):
    """Отправляет в Telegram итог проверки (используется для /check)."""
    added, removed, modified = summary["added"], summary["removed"], summary["modified"]

    if not added and not removed and not modified:
        text = f"✅ Проверка завершена: изменений нет.\nВсего файлов: {summary['total']}"
    else:
        lines = ["📋 <b>Итог ручной проверки</b>"]
        if added:
            lines.append(f"\n🆕 Новые ({len(added)}):")
            lines += [f"  • {f['folder_name']}: {f['name']}" for f in added]
        if modified:
            lines.append(f"\n✏️ Изменены ({len(modified)}):")
            lines += [f"  • {f['folder_name']}: {f['name']}" for f in modified]
        if removed:
            lines.append(f"\n🗑 Удалены ({len(removed)}):")
            lines += [f"  • {f['folder_name']}: {f['name']}" for f in removed]
        lines.append(f"\nВсего файлов: {summary['total']}")
        text = "\n".join(lines)

    send_telegram_message(text)


def send_long_message(text, chunk_size=3500):
    """Telegram режет сообщения длиннее ~4096 символов — бьём на части."""
    if len(text) <= chunk_size:
        send_telegram_message(text)
        return
    lines = text.split("\n")
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 > chunk_size:
            send_telegram_message(chunk)
            chunk = ""
        chunk += line + "\n"
    if chunk.strip():
        send_telegram_message(chunk)


def send_status():
    state = load_state()
    if _last_check_time:
        last_check_str = _last_check_time.strftime("%d.%m.%Y %H:%M:%S")
        seconds_ago = int((datetime.now() - _last_check_time).total_seconds())
        ago_str = f"{seconds_ago} сек. назад" if seconds_ago < 60 else f"{seconds_ago // 60} мин. назад"
    else:
        last_check_str = "ещё не выполнялась"
        ago_str = "-"

    text = (
        "ℹ️ <b>Статус</b>\n"
        f"Последняя проверка: {last_check_str} ({ago_str})\n"
        f"Интервал проверки: {ACTIVE_INTERVAL} сек.\n"
        f"Отслеживается файлов: {len(state)}"
    )
    send_telegram_message(text)


def send_file_list():
    state = load_state()
    if not state:
        if _last_check_time:
            send_telegram_message(
                "Список пуст: последняя проверка не нашла ни одного файла.\n"
                "Возможно, папка не расшарена на сервисный аккаунт, "
                "либо файлы лежат не внутри подпапок."
            )
        else:
            send_telegram_message("Список пуст — проверка ещё не выполнялась ни разу.")
        return

    by_folder = {}
    for info in state.values():
        by_folder.setdefault(info["folder_name"], []).append(info["name"])

    lines = ["📂 <b>Отслеживаемые файлы</b>"]
    for folder_name in sorted(by_folder):
        lines.append(f"\n<b>{folder_name}</b> ({len(by_folder[folder_name])}):")
        for name in sorted(by_folder[folder_name]):
            lines.append(f"  • {name}")

    send_long_message("\n".join(lines))


def listen_for_commands(service):
    """
    Слушает входящие сообщения боту (long polling) и реагирует на /check —
    делает внеочередную проверку и присылает итог в чат.
    Работает в отдельном потоке, пока основной процесс жив.
    """
    print("[telegram] Слушаю команду /check...")
    offset = None
    while True:
        try:
            updates = get_updates(offset=offset, timeout=30)
        except Exception as e:
            print(f"[telegram] Ошибка получения обновлений: {e}")
            time.sleep(10)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message") or update.get("edited_message")
            if not message:
                continue

            text = (message.get("text") or "").strip().lower()
            chat_id = str(message.get("chat", {}).get("id"))

            # Реагируем только на команды из настроенного чата — чтобы
            # посторонний, случайно написавший боту, не мог дёргать проверку.
            if chat_id != str(TELEGRAM_CHAT_ID):
                continue

            if text.startswith("/check"):
                send_telegram_message("🔍 Запускаю проверку...")
                summary = check_once(service)
                send_check_summary(summary)
            elif text.startswith("/status"):
                send_status()
            elif text.startswith("/list"):
                send_file_list()


def run_loop(service, interval):
    print(f"Запуск в режиме постоянного опроса, интервал {interval} сек. Ctrl+C для остановки.")
    while True:
        try:
            check_once(service)
        except Exception as e:
            # не даём процессу упасть из-за единичной сетевой ошибки
            print(f"[ошибка цикла] {e}")
        time.sleep(interval)


# ==================== ТОЧКА ВХОДА ====================


def main():
    parser = argparse.ArgumentParser(description="Наблюдатель за папками Google Drive")
    parser.add_argument(
        "--interval",
        type=int,
        default=CHECK_INTERVAL,
        help="Интервал опроса в секундах",
    )
    args = parser.parse_args()

    global ACTIVE_INTERVAL
    ACTIVE_INTERVAL = args.interval

    service = get_drive_service()
    set_bot_commands(BOT_COMMANDS)

    # Слушатель команды /check работает в фоновом потоке параллельно
    # с периодической проверкой в основном потоке.
    listener_thread = threading.Thread(
        target=listen_for_commands, args=(service,), daemon=True
    )
    listener_thread.start()
    run_loop(service, args.interval)


if __name__ == "__main__":
    main()