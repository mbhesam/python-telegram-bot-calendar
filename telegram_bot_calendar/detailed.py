from calendar import monthrange
from datetime import date
from dateutil.relativedelta import relativedelta
import jdatetime

from telegram_bot_calendar.base import *
from telegram_bot_calendar.static import MONTHS, DAYS_OF_WEEK

STEPS = {YEAR: MONTH, MONTH: DAY}
PREV_STEPS = {DAY: MONTH, MONTH: YEAR, YEAR: YEAR}
PREV_ACTIONS = {DAY: GOTO, MONTH: GOTO, YEAR: NOTHING}


class DetailedTelegramCalendar(TelegramCalendar):
    first_step = YEAR

    def __init__(self, calendar_id=0, current_date=None, additional_buttons=None,
                 locale='en', min_date=None, max_date=None, telethon=False, **kwargs):
        self.locale = locale

        # Set a proper default date
        if current_date is None:
            if self.locale == "fa":
                current_date = jdatetime.date.today()
            else:
                current_date = date.today()

        super().__init__(calendar_id, current_date, additional_buttons, locale,
                         min_date, max_date, telethon, **kwargs)

    def _is_jalali(self):
        return self.locale == "fa"

    def _build_years(self):
        years_num = self.size_year * self.size_year_column
        half_range = (years_num - 1) // 2
        start_year = self.current_date.year - half_range
        start = jdatetime.date(start_year, 1, 1) if self._is_jalali() else date(start_year, 1, 1)
        years = self._get_period(YEAR, start, years_num)
        years_buttons = rows(
            [self._build_button(d.year if d else self.empty_year_button,
                                SELECT if d else NOTHING, YEAR, d, locale=self.locale)
             for d in years],
            self.size_year
        )
        maxd = jdatetime.date(start.year + years_num - 1, 12, 29) if self._is_jalali() else date(start.year + years_num - 1, 12, 31)
        nav_buttons = self._build_nav_buttons(YEAR, diff=relativedelta(years=years_num),
                                              mind=min_date(start, YEAR), maxd=maxd)
        self._keyboard = self._build_keyboard(years_buttons + nav_buttons)

    def _build_nav_buttons(self, step, diff, mind, maxd, *args, **kwargs):
        text = self.nav_buttons[step]
        month_name = self.months['fa'][self.current_date.month - 1] if self._is_jalali() else self.months[self.locale][self.current_date.month - 1]
        data = {"year": str(self.current_date.year),
                "month": month_name,
                "day": str(self.current_date.day),
                "locale": self.locale}

        # Prev / Next pages
        if self._is_jalali():
            curr_page = self.current_date
            if step == YEAR:
                prev_page = self.current_date.replace(year=self.current_date.year - diff.years)
                next_page = self.current_date.replace(year=self.current_date.year + diff.years)
            elif step == MONTH:
                new_year = self.current_date.year
                new_month = self.current_date.month - diff.months
                if new_month < 1:
                    new_year -= 1
                    new_month += 12
                prev_page = self.current_date.replace(year=new_year, month=new_month)
                new_year = self.current_date.year
                new_month = self.current_date.month + diff.months
                if new_month > 12:
                    new_year += 1
                    new_month -= 12
                next_page = self.current_date.replace(year=new_year, month=new_month)
            else:  # DAY
                cur_tmp = self.current_date.togregorian() - relativedelta(days=diff.days)
                prev_page = jdatetime.date.fromgregorian(date=cur_tmp)
                cur_tmp = self.current_date.togregorian() + relativedelta(days=diff.days)
                next_page = jdatetime.date.fromgregorian(date=cur_tmp)
            prev_exists = (prev_page >= self.min_date) if self.min_date else True
            next_exists = (next_page <= self.max_date) if self.max_date else True
        else:
            curr_page = self.current_date
            prev_page = self.current_date - diff
            next_page = self.current_date + diff
            prev_exists = (prev_page >= self.min_date) if self.min_date else True
            next_exists = (next_page <= self.max_date) if self.max_date else True

        buttons = [[
            self._build_button(text[0].format(**data) if prev_exists else self.empty_nav_button,
                               GOTO if prev_exists else NOTHING, step, prev_page, locale=self.locale),
            self._build_button(text[1].format(**data),
                               PREV_ACTIONS[step], PREV_STEPS[step], curr_page, locale=self.locale),
            self._build_button(text[2].format(**data) if next_exists else self.empty_nav_button,
                               GOTO if next_exists else NOTHING, step, next_page, locale=self.locale),
        ]]
        return buttons

    def _process(self, call_data):
        params = call_data.split("_")
        expected_params = ["start", "calendar_id", "action", "step", "year", "month", "day", "locale"]
        params = dict(zip(expected_params[:len(params)], params))

        if params['action'] == NOTHING:
            return None, None, None

        # Restore locale
        if "locale" in params and params["locale"]:
            self.locale = params["locale"]

        step = params['step']

        try:
            year = int(params['year'])
            month = int(params['month'])
            day = int(params['day'])
        except (ValueError, TypeError):
            return None, None, None

        if self._is_jalali():
            try:
                self.current_date = jdatetime.date(year, month, day)
            except Exception:
                self.current_date = jdatetime.date.today()
        else:
            try:
                self.current_date = date(year, month, day)
            except Exception:
                self.current_date = date.today()

        if params['action'] == GOTO:
            self._build(step=step)
            return None, self._keyboard, step

        if params['action'] == SELECT:
            if step in STEPS:
                next_step = STEPS[step]
                self._build(step=next_step)
                return None, self._keyboard, next_step
            else:
                return self.current_date, None, step

    def _build(self, step=None):
        if not step:
            step = self.first_step
        self.step = step

        if step == YEAR:
            self._build_years()
        elif step == MONTH:
            self._build_months()
        else:  # DAY
            self._build_days()

    def _build_months(self):
        months_buttons = []
        for i in range(1, 13):
            if self._is_jalali():
                d = jdatetime.date(self.current_date.year, i, 1)
            else:
                d = date(self.current_date.year, i, 1)
            if self._valid_date(d):
                month_name = self.months['fa'][i - 1] if self._is_jalali() else self.months[self.locale][i - 1]
                months_buttons.append(self._build_button(month_name, SELECT, MONTH, d, locale=self.locale))
            else:
                months_buttons.append(self._build_button(self.empty_month_button, NOTHING, locale=self.locale))
        months_buttons = rows(months_buttons, self.size_month)

        if self._is_jalali():
            start = jdatetime.date(self.current_date.year, 1, 1)
            maxd = jdatetime.date(self.current_date.year, 12, 1)
        else:
            start = date(self.current_date.year, 1, 1)
            maxd = date(self.current_date.year, 12, 1)
        nav_buttons = self._build_nav_buttons(MONTH, diff=relativedelta(months=12),
                                              mind=min_date(start, MONTH), maxd=maxd)
        self._keyboard = self._build_keyboard(months_buttons + nav_buttons)

    def _build_days(self):
        if self._is_jalali():
            days_num = jdatetime.j_days_in_month[self.current_date.month - 1]
            if self.current_date.month == 12 and self.current_date.isleap():
                days_num += 1
            start = jdatetime.date(self.current_date.year, self.current_date.month, 1)
        else:
            days_num = monthrange(self.current_date.year, self.current_date.month)[1]
            start = date(self.current_date.year, self.current_date.month, 1)

        days = self._get_period(DAY, start, days_num)
        days_buttons = rows(
            [self._build_button(d.day if d else self.empty_day_button,
                                SELECT if d else NOTHING, DAY, d, locale=self.locale)
             for d in days],
            self.size_day
        )
        locale_key = 'fa' if self._is_jalali() else self.locale
        days_of_week_buttons = [[self._build_button(self.days_of_week[locale_key][i], NOTHING, locale=self.locale)
                                 for i in range(7)]]

        mind = min_date(start, MONTH)
        if self._is_jalali():
            maxd_date = start.replace(day=days_num)
        else:
            maxd_date = date(self.current_date.year, self.current_date.month, days_num)

        nav_buttons = self._build_nav_buttons(DAY, diff=relativedelta(months=1),
                                              mind=mind, maxd=max_date(maxd_date, MONTH))
        self._keyboard = self._build_keyboard(days_of_week_buttons + days_buttons + nav_buttons)
