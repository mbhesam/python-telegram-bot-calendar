import calendar
import json
import random
from datetime import date

import jdatetime
from dateutil.relativedelta import relativedelta

try:
    from telethon import Button
    TELETHON_INSTALLED = True
except ImportError:
    TELETHON_INSTALLED = False

from telegram_bot_calendar.static import MONTHS, DAYS_OF_WEEK

CB_CALENDAR = "cbcal"

YEAR = 'y'
MONTH = 'm'
DAY = 'd'
SELECT = "s"
GOTO = "g"
NOTHING = "n"
LSTEP = {'y': 'year', 'm': 'month', 'd': 'day'}


class TelegramCalendar:
    months = MONTHS
    days_of_week = DAYS_OF_WEEK
    prev_button = "<<"
    next_button = ">>"
    middle_button_day = "{month} {year}"
    middle_button_month = "{year}"
    middle_button_year = " "
    back_to_button = "<<< {name}"
    empty_nav_button = "×"
    empty_day_button = " "
    empty_month_button = " "
    empty_year_button = " "
    size_year = 2
    size_year_column = 2
    size_month = 3
    size_day = 7
    size_additional_buttons = 2
    _keyboard = None
    step = None

    def __init__(self, calendar_id=0, current_date=None, additional_buttons=None, locale='en',
                 min_date=None, max_date=None, telethon=False, is_random=True, **kwargs):

        self.locale = locale

        if self._is_jalali():
            if current_date is None:
                current_date = jdatetime.date.today()
            if min_date is None:
                min_date = jdatetime.date(1300, 1, 1)
            if max_date is None:
                max_date = jdatetime.date(1499, 12, 29)
        else:
            if current_date is None:
                current_date = date.today()
            if min_date is None:
                min_date = date(1800, 1, 1)
            if max_date is None:
                max_date = date(2999, 12, 31)

        self.min_date = min_date
        self.max_date = max_date
        self.calendar_id = calendar_id
        self.current_date = current_date
        self.telethon = telethon

        if self.telethon and not TELETHON_INSTALLED:
            raise ImportError(
                "Telethon is not installed. Please install telethon or use pip install python-telegram-bot-calendar[telethon]"
            )

        self.is_random = is_random
        if not additional_buttons:
            additional_buttons = []
        self.additional_buttons = rows(additional_buttons, self.size_additional_buttons)

        # nav button labels
        self.prev_button_year = self.prev_button
        self.next_button_year = self.next_button
        self.prev_button_month = self.prev_button
        self.next_button_month = self.next_button
        self.prev_button_day = self.prev_button
        self.next_button_day = self.next_button

        self.nav_buttons = {
            YEAR: [self.prev_button_year, self.middle_button_year, self.next_button_year],
            MONTH: [self.prev_button_month, self.middle_button_month, self.next_button_month],
            DAY: [self.prev_button_day, self.middle_button_day, self.next_button_day],
        }

    def _is_jalali(self):
        return self.locale == "fa"

    @staticmethod
    def func(calendar_id=0, telethon=False):
        def inn(callback):
            start = CB_CALENDAR + "_" + str(calendar_id)
            return callback.decode("utf-8").startswith(start) if telethon else callback.data.startswith(start)

        return inn

    def build(self):
        if not self._keyboard:
            self._build()
        return self._keyboard, self.step

    def process(self, call_data):
        return self._process(call_data)

    def _build(self, *args, **kwargs):
        """Override in subclasses to build the keyboard."""

    def _process(self, call_data, *args, **kwargs):
        """Override in subclasses to process callback data."""

    def _build_callback(self, action, step, data, *args, is_random=False, **kwargs):
        if action == NOTHING:
            params = [CB_CALENDAR, str(self.calendar_id), action]
        else:
            data = list(map(str, data.timetuple()[:3]))
            params = [CB_CALENDAR, str(self.calendar_id), action, step] + data + [self.locale]

        salt = "_" + str(random.randint(1, 1e18)) if is_random else ""
        return "_".join(params) + salt

    def _build_button(self, text, action, step=None, date_obj=None, is_random=False, *args, **kwargs):
        if (action == NOTHING) or (not date_obj):
            return {"text": text, "callback_data": NOTHING}

        callback_data = "_".join([
            "CALENDAR",
            str(self.calendar_id),
            action,
            step if step else "",
            str(date_obj.year),
            str(date_obj.month),
            str(date_obj.day),
            self.locale
        ])

        return {"text": text, "callback_data": callback_data}

    def _build_keyboard(self, buttons):
        if self.telethon:
            return buttons
        return self._build_json_keyboard(buttons)

    def _build_json_keyboard(self, buttons):
        return json.dumps({"inline_keyboard": buttons + self.additional_buttons})

    def _valid_date(self, date_obj):
        if date_obj is None:
            return False
        if self.min_date and date_obj < self.min_date:
            return False
        if self.max_date and date_obj > self.max_date:
            return False
        return True

    def _get_period(self, step, start, count):
        result = []
        for i in range(count):
            if step == YEAR:
                if self._is_jalali():
                    current = jdatetime.date(start.year + i, 1, 1)
                else:
                    current = date(start.year + i, 1, 1)
            elif step == MONTH:
                year = start.year + (start.month + i - 1) // 12
                month = (start.month + i - 1) % 12 + 1
                current = jdatetime.date(year, month, 1) if self._is_jalali() else date(year, month, 1)
            else:  # DAY
                if self._is_jalali():
                    cur_tmp = start.togregorian() + relativedelta(days=i)
                    current = jdatetime.date.fromgregorian(date=cur_tmp)
                else:
                    current = start + relativedelta(days=i)

            result.append(current if self._valid_date(current) else None)

        return result


def rows(buttons, row_size):
    return [buttons[i:i + row_size] for i in range(0, max(len(buttons) - row_size, 0) + 1, row_size)]


def max_date(d, step):
    if isinstance(d, jdatetime.date):
        if step == YEAR:
            days = 29
            if jdatetime.date(d.year, 1, 1).isleap():
                days = 30
            return d.replace(month=12, day=days)
        elif step == MONTH:
            days = jdatetime.j_days_in_month[d.month - 1]
            if d.month == 12 and d.isleap():
                days += 1
            return d.replace(day=days)
        else:
            return d

    if step == YEAR:
        return d.replace(month=12, day=31)
    elif step == MONTH:
        return d.replace(day=calendar.monthrange(d.year, d.month)[1])
    else:
        return d


def min_date(d, step):
    if step == YEAR:
        return d.replace(month=1, day=1)
    elif step == MONTH:
        return d.replace(day=1)
    else:
        return d
