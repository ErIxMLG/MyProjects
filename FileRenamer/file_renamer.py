import os
import re


def remove_prefix_from_filename(file_path, pattern=r'^\d+\.\s*'):
    """
    Удаляет указанный префикс из названия файла.
    
    Args:
        file_path: путь к файлу
        pattern: регулярное выражение для поиска префикса (по умолчанию: цифры и точка в начале)
    
    Returns:
        True если файл был переименован, False в противном случае
    """
    try:
        # Получаем директорию и имя файла
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        
        # Удаляем префикс из имени файла
        new_filename = re.sub(pattern, '', filename)
        
        # Проверяем, изменилось ли имя
        if new_filename != filename:
            # Создаем полный путь к новому файлу
            if directory:
                new_path = os.path.join(directory, new_filename)
            else:
                new_path = new_filename
            
            # Проверяем, не существует ли уже файл с таким именем
            if os.path.exists(new_path):
                print(f"⚠ Файл с именем '{new_filename}' уже существует")
                return False
            
            # Переименовываем файл
            os.rename(file_path, new_path)
            print(f"✓ '{filename}' → '{new_filename}'")
            return True
        else:
            print(f"⚠ '{filename}' - префикс не найден")
            return False
    
    except Exception as e:
        print(f"✗ Ошибка при обработке '{file_path}': {e}")
        return False


def process_directory(directory_path, pattern=r'^\d+\.\s*'):
    """
    Обрабатывает все файлы в указанной директории.
    
    Args:
        directory_path: путь к директории
        pattern: регулярное выражение для поиска префикса
    """
    try:
        files = os.listdir(directory_path)
        renamed_count = 0
        
        for filename in files:
            file_path = os.path.join(directory_path, filename)
            
            # Обрабатываем только файлы (не директории)
            if os.path.isfile(file_path):
                if remove_prefix_from_filename(file_path, pattern):
                    renamed_count += 1
        
        print(f"\n📊 Всего переименовано файлов: {renamed_count}")
    
    except FileNotFoundError:
        print(f"✗ Директория не найдена: {directory_path}")
    except Exception as e:
        print(f"✗ Ошибка: {e}")


def add_numbering_to_files(directory_path, start_number=1, digits=2, separator='. ', verbose=True):
    """
    Добавляет нумерацию к файлам в директории.
    
    Args:
        directory_path: путь к директории
        start_number: начальный номер (по умолчанию 1)
        digits: количество цифр (например, 2 = 01, 02; 3 = 001, 002)
        separator: разделитель после номера (по умолчанию '. ')
        verbose: выводить информацию о каждом файле (False = только итог)
    """
    try:
        # Получаем список файлов один раз
        files = [f for f in os.listdir(directory_path) 
                if os.path.isfile(os.path.join(directory_path, f))]
        
        total_files = len(files)
        print(f"🔍 Найдено файлов: {total_files}")
        
        # Сортируем файлы по имени
        files.sort()
        
        renamed_count = 0
        current_number = start_number
        
        # Переименовываем в обратном порядке, чтобы избежать конфликтов имен
        for i, filename in enumerate(files, 1):
            file_path = os.path.join(directory_path, filename)
            
            # Формируем номер с нужным количеством цифр
            number_prefix = str(current_number).zfill(digits)
            new_filename = f"{number_prefix}{separator}{filename}"
            new_path = os.path.join(directory_path, new_filename)
            
            # Проверяем, не существует ли уже файл с таким именем
            if os.path.exists(new_path):
                if verbose:
                    print(f"⚠ [{i}/{total_files}] Файл '{new_filename}' уже существует, пропускаем")
                current_number += 1
                continue
            
            # Переименовываем файл
            os.rename(file_path, new_path)
            if verbose:
                print(f"✓ [{i}/{total_files}] '{filename}' → '{new_filename}'")
            renamed_count += 1
            current_number += 1
        
        print(f"\n📊 Всего пронумеровано файлов: {renamed_count} из {total_files}")
    
    except FileNotFoundError:
        print(f"✗ Директория не найдена: {directory_path}")
    except Exception as e:
        print(f"✗ Ошибка: {e}")


# Пример использования
if __name__ == "__main__":
    directory_path = "."  # Текущая директория, укажите свой путь
    
    # Вариант 1: Удалить нумерацию из всех файлов
    # process_directory(directory_path)
    
    # Вариант 2: Добавить нумерацию к файлам
    # add_numbering_to_files(directory_path)
    
    # Вариант 3: Добавить нумерацию с настройками
    # add_numbering_to_files(directory_path, start_number=1, digits=3, separator='. ')
    # Результат: 001. filename.mp3, 002. filename.mp3, и т.д.
    
    # Вариант 4: Быстрый режим (без вывода каждого файла, только итог)
    # add_numbering_to_files(directory_path, verbose=False)
    
    # Вариант 4: Переименовать один файл
    # remove_prefix_from_filename("132. Modern Talking - We Take The Chance.mp3")