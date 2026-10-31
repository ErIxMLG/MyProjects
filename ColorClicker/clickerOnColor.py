import pyautogui
import keyboard
import time
from PIL import ImageGrab
import threading
import numpy as np

class ColorClicker:
    def __init__(self):
        self.is_active = False
        self.running = True
        self.check_interval = 0.001  # Минимальный интервал проверки
        self.target_color = None
        self.color_tolerance = 30  # Допуск по цвету (0-100)
        
        # Предварительные вычисления для оптимизации
        self.max_color_distance = np.sqrt(3 * 255**2)  # Максимальное расстояние между цветами
        self.last_position = None
        self.last_color = None
        
    def set_target_color(self):
        """Устанавливает целевой цвет из текущей позиции курсора"""
        self.target_color = self.get_cursor_color()
        if self.target_color:
            # Конвертируем в numpy array для быстрых вычислений
            self.target_color_np = np.array(self.target_color)
            print(f"Целевой цвет установлен: RGB{self.target_color}")
        else:
            print("Не удалось установить целевой цвет")
    
    def get_cursor_color(self):
        """Получает цвет пикселя под курсором мыши - оптимизированная версия"""
        try:
            x, y = pyautogui.position()
            
            # Проверяем, не изменилась ли позиция курсора
            if self.last_position == (x, y) and self.last_color:
                return self.last_color
                
            # Используем более быстрый метод захвата экрана
            screenshot = ImageGrab.grab(bbox=(x, y, x+1, y+1))
            color = screenshot.getpixel((0, 0))
            
            # Кэшируем результат
            self.last_position = (x, y)
            self.last_color = color
            
            return color
        except Exception as e:
            print(f"Ошибка при получении цвета: {e}")
            return None
    
    def colors_are_similar_optimized(self, color1, color2, tolerance_percent):
        """Оптимизированная проверка похожести цветов с использованием numpy"""
        if color1 is None or color2 is None:
            return False
            
        # Конвертируем в numpy arrays для векторных операций
        color1_np = np.array(color1)
        color2_np = np.array(color2)
        
        # Быстрое вычисление евклидова расстояния
        distance = np.linalg.norm(color1_np - color2_np)
        
        # Допуск в абсолютных единицах
        tolerance_absolute = self.max_color_distance * (tolerance_percent / 100)
        
        return distance <= tolerance_absolute
    
    def click_at_cursor(self):
        """Нажимает левую кнопку мыши в текущей позиции курсора"""
        try:
            # Используем более быстрый метод клика
            pyautogui.mouseDown()
            time.sleep(0.01)  # Минимальная задержка для надежности
            pyautogui.mouseUp()
            print(f"Клик выполнен в позиции {pyautogui.position()}")
        except Exception as e:
            print(f"Ошибка при клике: {e}")
    
    def monitor_color_and_click_optimized(self):
        """Оптимизированный мониторинг цвета под курсором"""
        last_click_time = 0
        click_cooldown = 0.1  # Уменьшенная задержка между кликами
        consecutive_matches = 0
        required_consecutive = 2  # Требуемое количество последовательных совпадений
        
        print("Мониторинг цвета запущен...")
        
        while self.is_active and self.running:
            if self.target_color is None:
                time.sleep(0.1)
                continue
                
            current_color = self.get_cursor_color()
            current_time = time.time()
            
            if current_color and self.colors_are_similar_optimized(
                self.target_color, current_color, self.color_tolerance):
                
                consecutive_matches += 1
                
                if (consecutive_matches >= required_consecutive and 
                    current_time - last_click_time >= click_cooldown):
                    
                    self.click_at_cursor()
                    last_click_time = current_time
                    consecutive_matches = 0  # Сбрасываем счетчик после клика
            else:
                consecutive_matches = 0  # Сбрасываем при несовпадении
            
            # Минимальная задержка для снижения нагрузки на CPU
            time.sleep(self.check_interval)
    
    def monitor_color_fast(self):
        """Сверхбыстрая версия мониторинга с минимальными проверками"""
        last_click_time = 0
        click_cooldown = 0.05  # Очень короткая задержка
        
        # Предварительные вычисления
        tolerance_absolute = self.max_color_distance * (self.color_tolerance / 100)
        target_np = self.target_color_np
        
        print("Быстрый мониторинг цвета запущен...")
        
        while self.is_active and self.running:
            try:
                # Быстрое получение позиции и цвета
                x, y = pyautogui.position()
                
                # Быстрый захват экрана без создания объекта Image
                screenshot = ImageGrab.grab(bbox=(x, y, x+1, y+1))
                current_color = screenshot.getpixel((0, 0))
                
                # Быстрая проверка расстояния
                current_np = np.array(current_color)
                distance = np.linalg.norm(target_np - current_np)
                
                if distance <= tolerance_absolute:
                    current_time = time.time()
                    if current_time - last_click_time >= click_cooldown:
                        pyautogui.click()
                        last_click_time = current_time
                        print("CLICKED!")
                        
            except Exception:
                pass  # Игнорируем ошибки для максимальной скорости
            
            # Минимальная задержка
            time.sleep(0.001)
    
    def increase_tolerance(self):
        """Увеличивает допуск по цвету"""
        self.color_tolerance = min(100, self.color_tolerance + 5)
        print(f"Допуск увеличен: {self.color_tolerance}%")
    
    def decrease_tolerance(self):
        """Уменьшает допуск по цвету"""
        self.color_tolerance = max(0, self.color_tolerance - 5)
        print(f"Допуск уменьшен: {self.color_tolerance}%")
    
    def show_status(self):
        """Показывает текущий статус"""
        status = "АКТИВЕН" if self.is_active else "ВЫКЛЮЧЕН"
        target_info = f"RGB{self.target_color}" if self.target_color else "НЕ УСТАНОВЛЕН"
        print(f"Статус: {status} | Целевой цвет: {target_info} | Допуск: {self.color_tolerance}%")
    
    def toggle_function(self):
        """Переключает состояние функции"""
        self.is_active = not self.is_active
        
        if self.is_active:
            if self.target_color is None:
                print("Сначала установите целевой цвет (`)")
                self.is_active = False
                return
            print("Функция активирована!")
            # Используем быструю версию мониторинга
            thread = threading.Thread(target=self.monitor_color_fast)
            thread.daemon = True
            thread.start()
        else:
            print("Функция деактивирована")
        
        self.show_status()
    
    def start(self):
        """Запускает основную программу"""
        print("=" * 50)
        print("БЫСТРЫЙ ЦВЕТОВОЙ КЛИКЕР (ОПТИМИЗИРОВАННЫЙ)")
        print("=" * 50)
        print("Управление:")
        print("R - Включить/выключить автоклик")
        print("` - Установить целевой цвет (под курсором)")
        print("+ - Увеличить допуск по цвету")
        print("- - Уменьшить допуск по цвету")
        print("S - Показать статус")
        print("Esc - Выход")
        print("=" * 50)
        
        # Регистрируем горячие клавиши
        keyboard.add_hotkey('r', self.toggle_function)
        keyboard.add_hotkey('`', self.set_target_color)
        keyboard.add_hotkey('+', self.increase_tolerance)
        keyboard.add_hotkey('-', self.decrease_tolerance)
        keyboard.add_hotkey('s', self.show_status)
        
        self.show_status()
        
        # Ожидаем нажатия Esc для выхода
        keyboard.wait('esc')
        self.running = False
        self.is_active = False
        print("Программа завершена")

if __name__ == "__main__":
    # Минимизируем задержки pyautogui
    pyautogui.PAUSE = 0.01
    pyautogui.FAILSAFE = True
    
    clicker = ColorClicker()
    clicker.start()