"""
Диагностика: показывает, что именно видит сервисный аккаунт.
Запуск: python3 debug_drive_access.py
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
ROOT_FOLDER_ID = "1KUYw9aQ6eoPHtqI6M6EzbeOWZtVNgDdO"

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build("drive", "v3", credentials=creds)

print(f"Email сервисного аккаунта: {creds.service_account_email}\n")

# 1. Пробуем получить саму корневую папку напрямую
print("=== 1. Метаданные корневой папки ===")
try:
    folder = (
        service.files()
        .get(
            fileId=ROOT_FOLDER_ID,
            fields="id, name, mimeType, driveId, permissions",
            supportsAllDrives=True,
        )
        .execute()
    )
    print(folder)
except Exception as e:
    print(f"ОШИБКА: {e}")

# 2. Пробуем перечислить её содержимое, максимально широко (без trashed-фильтра)
print("\n=== 2. Прямое содержимое корневой папки (без фильтров) ===")
try:
    response = (
        service.files()
        .list(
            q=f"'{ROOT_FOLDER_ID}' in parents",
            spaces="drive",
            fields="files(id, name, mimeType, trashed, driveId)",
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
        )
        .execute()
    )
    files = response.get("files", [])
    print(f"Найдено: {len(files)}")
    for f in files:
        print(f"  {f}")
except Exception as e:
    print(f"ОШИБКА: {e}")

# 3. Список всех дисков/общих дисков, к которым вообще есть доступ
print("\n=== 3. Общие диски (Shared Drives), доступные сервисному аккаунту ===")
try:
    drives = service.drives().list(pageSize=50).execute().get("drives", [])
    if drives:
        for d in drives:
            print(f"  {d['id']}  {d['name']}")
    else:
        print("  Нет доступных общих дисков (это нормально, если папка на обычном Диске).")
except Exception as e:
    print(f"ОШИБКА: {e}")
