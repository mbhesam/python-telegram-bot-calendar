from calendar import monthrange
from datetime import date
from dateutil.relativedelta import relativedelta
import jdatetime
from jdatetime import date as jdate

from telegram_bot_calendar.base import *
from telegram_bot_calendar.static import MONTHS, DAYS_OF_WEEK

STEPS = {YEAR: MONTH, MONTH: DAY}
PREV_STEPS = {DAY: MONTH, MONTH: YEAR, YEAR: YEAR}
PREV_ACTIONS = {DAY: GOTO, MONTH: GOTO, YEAR: NOTHING}


class DetailedTelegramCalendar(TelegramCalendar):
    first_step = YEAR

    def __init__(self, calendar_id=0, current_date=None, additional_buttons=None, locale='en',
                 min_date=None, max_date=None, telethon=False, **kwargs):
        super().__init__(calendar_id, current_date, additional_buttons, locale, min_date, max_date, telethon, **kwargs)

    def _build(self, step=None):
        if not step:
            step = self.first_step
        self.step = step
        if step == YEAR:
            self._build_years()
        elif step == MONTH:
            self._build_months()
        elif step == DAY:
            self._build_days()

    def _process(self, call_data):
        params = call_data.split("_")
        params = dict(zip(["start", "calendar_id", "action", "step", "year", "month", "day"][:len(params)], params))

        if params['action'] == NOTHING:
            return None, None, None

        step = params['step']
        year = int(params['year'])
        month = int(params['month'])
        day = int(params['day'])

        if self.jdate:
            self.current_date = jdate(year, month, day)
        else:
            self.current_date = date(year, month, day)

        if params['action'] == GOTO:
            self._build(step=step)
            return None, self._keyboard, step

        if params['action'] == SELECT:
            if step in STEPS:
                self._build(step=STEPS[step])
                return None, self._keyboard, STEPS[step]
            else:
                return self.current_date, None, step

    # ---------------------- BUILD YEARS / MONTHS / DAYS ----------------------

    def _build_years(self):
        years_num = self.size_year * self.size_year_column
        half_range = (years_num - 1) // 2

        start = self.current_date + relativedelta(years=-half_range)
        years = self._get_period(YEAR, start, years_num)

        years_buttons = rows(
            [self._build_button(d.year if d else self.empty_year_button, SELECT if d else NOTHING, YEAR, d)
             for d in years],
            self.size_year
        )

        maxd = max_date(start + relativedelta(years=years_num - 1), YEAR)
        nav_buttons = self._build_nav_buttons(YEAR, diff=relativedelta(years=years_num),
                                              mind=min_date(start, YEAR), maxd=maxd)

        self._keyboard = self._build_keyboard(years_buttons + nav_buttons)

    def _build_months(self):
        months_buttons = []
        for i in range(1, 13):
            d = self.current_date.replace(month=i, day=1)
            if self._valid_date(d):
                month_name = self.months['fa'][i-1] if self.jdate else self.months[self.locale][i-1]
                months_buttons.append(self._build_button(month_name, SELECT, MONTH, d))
            else:
                months_buttons.append(self._build_button(self.empty_month_button, NOTHING))

        months_buttons = rows(months_buttons, self.size_month)
        start = self.current_date.replace(day=1)
        nav_buttons = self._build_nav_buttons(MONTH, diff=relativedelta(months=12),
                                              mind=min_date(start, MONTH),
                                              maxd=max_date(start.replace(month=12), MONTH))

        self._keyboard = self._build_keyboard(months_buttons + nav_buttons)

    def _build_days(self):
        if self.jdate:
            days_num = jdatetime.j_days_in_month[self.current_date.month-1]
            if self.current_date.month == 12 and self.current_date.isleap():
                days_num += 1
        else:
            days_num = monthrange(self.current_date.year, self.current_date.month)[1]

        start = self.current_date.replace(day=1)
        days = self._get_period(DAY, start, days_num)

        days_buttons = rows(
            [self._build_button(d.day if d else self.empty_day_button, SELECT if d else NOTHING, DAY, d)
             for d in days],
            self.size_day
        )

        days_of_week_buttons = [[self._build_button(self.days_of_week[self.locale][i], NOTHING) for i in range(7)]]

        mind = min_date(start, MONTH)
        nav_buttons = self._build_nav_buttons(DAY, diff=relativedelta(months=1),
                                              mind=mind, maxd=max_date(start.replace(day=days_num), MONTH))

        self._keyboard = self._build_keyboard(days_of_week_buttons + days_buttons + nav_buttons)

    # ---------------------- NAV BUTTONS ----------------------

    def _build_nav_buttons(self, step, diff, mind, maxd, *args, **kwargs):
        text = self.nav_buttons[step]

        # Labels
        if self.jdate:
            month_name = self.months['fa'][self.current_date.month - 1]
            data = {"year": str(self.current_date.year),
                    "month": month_name,
                    "day": str(self.current_date.day)}
        else:
            month_name = self.months[self.locale][self.current_date.month - 1]
            data = {"year": str(self.current_date.year),
                    "month": month_name,
                    "day": str(self.current_date.day)}

        # Prev / Next pages
        if self.jdate:
            curr_page = self.current_date
            prev_page = self.current_date + relativedelta(**{LSTEP[step] + "s": -diff.years if step==YEAR else -diff.months if step==MONTH else -diff.days})
            next_page = self.current_date + relativedelta(**{LSTEP[step] + "s": diff.years if step==YEAR else diff.months if step==MONTH else diff.days})

            prev_exists = (mind <= prev_page)
            next_exists = (next_page <= maxd)
        else:
            curr_page = self.current_date
            prev_page = self.current_date - diff
            next_page = self.current_date + diff

            prev_exists = (mind <= prev_page)
            next_exists = (next_page <= maxd)

        return [[
            self._build_button(text[0].format(**data) if prev_exists else self.empty_nav_button,
                               GOTO if prev_exists else NOTHING, step, prev_page),
            self._build_button(text[1].format(**data),
                               PREV_ACTIONS[step], PREV_STEPS[step], curr_page),
            self._build_button(text[2].format(**data) if next_exists else self.empty_nav_button,
                               GOTO if next_exists else NOTHING, step, next_page),
        ]]
