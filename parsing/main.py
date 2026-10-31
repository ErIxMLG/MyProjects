
import os
import sys

import requests
from typing import TypedDict
from bs4 import BeautifulSoup

#sys.base_prefix - путь до глобального python
#sys.prefix - путь где сейчас запустили скрипт
# print(sys.prefix, "- sys.prefix")
# print(sys.base_prefix, "- sys.base_prefix")

if sys.prefix == sys.base_prefix:

    if os.name == 'nt':  # Для Windows
        venv_python = os.path.join(os.getcwd(), 'venv', 'Scripts', 'python.exe')
    else:
        venv_python = os.path.join(os.getcwd(), 'venv', 'bin', 'python')

    # Если виртуальная среда найдена, перезапускаем скрипт в ней
    if os.path.exists(venv_python):
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print("Ошибка: Виртуальная среда .venv не найдена в папке со скриптом!")
        input("\nНажмите Enter для выхода...")
        sys.exit(1)


class Lesson(TypedDict):
    lesson: str
    time: str
    room: str
    teacher: str

class DaySchedule(TypedDict):
    day: str
    lessons: list[Lesson]
    
Schedule = dict[str, DaySchedule]

url = "https://akademiks.urtt.ru/lk/all-schedules/student/e-464"

response = requests.get(url)

soup = BeautifulSoup(response.text, "lxml")

schedule: Schedule = {}

#Example

# schedule = {
#     "8/31/2026": {
#         "day": "Понедельник",
#         "lessons": [
#             {"lesson": "Производство микропроцессорных систем",
#             "time": "08:00 - 09:35",
#             "room": "Дистант",
#             "teacher": "Быльцев И.А."
#             },
#             {
                
#             },
#         ]
#     },
# }
# print(list(schedule.keys()))

# Верхняя строчка с датами и днями
DaysStroke = soup.find("tr", class_="border-b transition-colors data-[state=selected]:bg-muted hover:bg-muted")

DaysColumn = DaysStroke.find_all("th", recursive=False)

# Добавление в список дней и дат
for i in DaysColumn[1:]:
    dates = i.find_all("span")
    date_key = dates[1].text
    day_of_week = dates[0].text
    
    TEMP = {date_key:{
        "day": day_of_week,
        "lessons": []
    }}
    schedule.update(TEMP)
    
# print("Расписание: ", schedule)

# Возвращает массив состоящий из названия, времени, аудитории и преподавателя
# за всю строку
def ParseStroke(Stroke):
    # collected = {
    #     "lesson": "Производство микропроцессорных систем",
    #     "time": "08:00 - 09:35",
    #     "room": "Дистант",
    #     "teacher": "Быльцев И.А."
    # }
    collected = []
    # Цифры слева - порядок пар
    LessonNumber = Stroke[0].text
    # print("Пара по счёту: ", LessonNumber)
    
    # Идем по дням слева направо
    for i in Stroke[1:]:
        
        LESSON = None
        TIME = None
        ROOM = None
        TEACHER = None
        
        LessonDiv = i.find("div", class_="relative grid h-full w-full min-w-[225px] content-start gap-1 p-3")
    
    # Если блок не найден, значит пары нет или изменился html код страницы
        if LessonDiv is None:
            LessonDivText = i.find("div")
            # print(LessonDivText.text)

            LESSON = LessonDivText.text
            
        else:
            LessonDivText = LessonDiv.find_all("div", recursive=False)
            for i,v in enumerate(LessonDivText):
                if i == 0:
                    LESSON = v.text
                if i == 1:
                    TIME = v.text
                if i == 2:
                    ROOM, TEACHER = v.text.split(", ")
                # print(v.text)
        TEMP = {
            "lesson": LESSON,
            "time": TIME,
            "room": ROOM,
            "teacher": TEACHER
        }
        collected.append(TEMP)
    return collected
      
# Основной body с парами
Body = soup.find("tbody", class_="[&_tr:last-child]:border-0")

AllStrokes = Body.find_all("tr")

for index, i in enumerate(AllStrokes):
    # print("Текущая строка / номер пары: ", index)
    
    Lessons = i.find_all("td")
    
    collected = ParseStroke(Lessons)

    for index, date in enumerate(list(schedule.keys())):
        lessons = collected[index]
        schedule[date]["lessons"].append(lessons)


for index, date in enumerate(list(schedule.keys())):
    print("\nДата: ", date, "День: ", schedule[date]["day"])
    print("-----Пары-----")
    lessons = schedule[date]["lessons"]
    for i,v in enumerate(lessons):
        if v["time"] or v["room"] or v["teacher"] is not None:
            print(i+1, ": ",v["lesson"])
            print(v["time"])
            print("Аудитория: ", v["room"])
            print("Преподаватель: ", v["teacher"], "\n")

input("Press any key to exit...")
print("Exiting")