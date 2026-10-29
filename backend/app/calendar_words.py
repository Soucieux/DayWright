"""The words a message names months, weekdays and areas by, which several of the service's readers share, and the
weekdays' names as an answer writes them."""

# Each month's English names, January first, as alternatives a pattern can join: "september|sept|sep".
MONTHS = ("january|jan", "february|feb", "march|mar", "april|apr", "may", "june|jun", "july|jul", "august|aug",
          "september|sept|sep", "october|oct", "november|nov", "december|dec")
# The weekdays in English, Monday first, so a name's index is its weekday number.
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
# The same weekdays as an answer writes them: "Monday".
WEEKDAY_NAMES = tuple(day.capitalize() for day in WEEKDAYS)
# The weekdays as Chinese writes them after 周 or 星期, Monday first; 天 is read as 日.
CHINESE_WEEKDAYS = "一二三四五六日"
# The four areas by their names in English and in Chinese; a reader adds the other words it takes for one.
AREA_NAMES = {"learning": "learning", "life": "life", "work": "work", "project": "project",
              "学习": "learning", "生活": "life", "工作": "work", "项目": "project"}
