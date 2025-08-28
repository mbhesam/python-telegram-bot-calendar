from calendar import monthrange

from telegram_bot_calendar.base import *
from telegram_bot_calendar.base import jdate

STEPS = {YEAR: MONTH, MONTH: DAY}

PREV_STEPS = {DAY: MONTH, MONTH: YEAR, YEAR: YEAR}
PREV_ACTIONS = {DAY: GOTO, MONTH: GOTO, YEAR: NOTHING}


class DetailedTelegramCalendar(TelegramCalendar):
    first_step = YEAR

    def __init__(self, calendar_id=0, current_date=None, additional_buttons=None, locale='en',
                 min_date=None,
                 max_date=None, telethon=False, **kwargs):
        super(DetailedTelegramCalendar, self).__init__(calendar_id, current_date=current_date,
                                                       additional_buttons=additional_buttons, locale=locale,
                                                       min_date=min_date, max_date=max_date, is_random=False, telethon=telethon, **kwargs)

    def _build(self, step=None, **kwargs):
        if not step:
            step = self.first_step

        self.step = step
        if step == YEAR:
            self._build_years()
        elif step == MONTH:
            self._build_months()
        elif step == DAY:
            self._build_days()

    def _process(self, call_data, *args, **kwargs):
        params = call_data.split("_")
        params = dict(
            zip(["start", "calendar_id", "action", "step", "year", "month", "day"][:len(params)], params))

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

    def _build_years(self, *args, **kwargs):
        years_num = self.size_year * self.size_year_column

        if self.jdate:
            gregorian_date = self.current_date.togregorian()
            start_gregorian = gregorian_date - relativedelta(years=(years_num - 1) // 2)
            start = jdate.fromgregorian(date=start_gregorian)
        else:
            start = self.current_date - relativedelta(years=(years_num - 1) // 2)
        years = self._get_period(YEAR, start, years_num)
        years_buttons = rows(
            [
                self._build_button(d.year if d else self.empty_year_button, SELECT if d else NOTHING, YEAR, d,
                                   is_random=self.is_random)
                for d in years
            ],
            self.size_year
        )

        if self.jdate:
            maxd_gregorian = start.togregorian() + relativedelta(years=years_num - 1)
            maxd = min_date(jdate.fromgregorian(date=maxd_gregorian), YEAR)
        else:
            maxd = min_date(start + relativedelta(years=years_num - 1), YEAR)

        if self.jdate:
            def jalali_shift(date_obj, years):
                g_date = date_obj.togregorian()
                g_new = g_date + relativedelta(years=years)
                return jdatetime.date.fromgregorian(date=g_new)

            # instead of giving diff=relativedelta(...)
            nav_buttons = self._build_nav_buttons(
                YEAR,
                diff=relativedelta(years=years_num), # function-based shift
                mind=max_date(start, YEAR),
                maxd=maxd
            )
        else:
            nav_buttons = self._build_nav_buttons(
                YEAR,
                diff=relativedelta(years=years_num),
                mind=max_date(start, YEAR),
                maxd=maxd
            )

        self._keyboard = self._build_keyboard(years_buttons + nav_buttons)

    def _build_months(self, *args, **kwargs):
        months_buttons = []
        for i in range(1, 13):
            d = self.current_date.replace(month=i, day=1)
            if self._valid_date(d):
                months_buttons.append(self._build_button(self.months[self.locale][i-1], SELECT, MONTH, d, is_random=self.is_random))
            else:
                months_buttons.append(self._build_button(self.empty_month_button, NOTHING))

        months_buttons = rows(months_buttons, self.size_month)
        start = self.current_date.replace(month=1)
        nav_buttons = self._build_nav_buttons(MONTH, diff=relativedelta(months=12),
                                              mind=max_date(start, MONTH),
                                              maxd=min_date(start.replace(month=12), MONTH))

        self._keyboard = self._build_keyboard(months_buttons + nav_buttons)

    def _build_days(self, *args, **kwargs):
        if self.jdate:
            days_num = jdatetime.j_days_in_month[self.current_date.month-1]
            if self.current_date.month == 12 and self.current_date.isleap():
                days_num += 1
        else:
            days_num = monthrange(self.current_date.year, self.current_date.month)[1]

        start = self.current_date.replace(day=1)
        days = self._get_period(DAY, start, days_num)

        days_buttons = rows(
            [
                self._build_button(d.day if d else self.empty_day_button, SELECT if d else NOTHING, DAY, d,
                                   is_random=self.is_random)
                for d in days
            ],
            self.size_day
        )

        days_of_week_buttons = [[
            self._build_button(self.days_of_week[self.locale][i], NOTHING) for i in range(7)
        ]]

        # mind and maxd are swapped since we need maximum and minimum days in the month
        # without swapping next page can generated incorrectly
        if self.jdate:
            mind_gregorian = start.togregorian() + relativedelta(days=days_num - 1)
            mind = min_date(jdate.fromgregorian(date=mind_gregorian), MONTH)
        else:
            mind = min_date(start + relativedelta(days=days_num - 1), MONTH)

        nav_buttons = self._build_nav_buttons(DAY, diff=relativedelta(months=1),
                                              maxd=max_date(start, MONTH),
                                              mind=mind)

        self._keyboard = self._build_keyboard(days_of_week_buttons + days_buttons + nav_buttons)

    def _build_nav_buttons(self, step, diff, mind, maxd, *args, **kwargs):
        text = self.nav_buttons[step]

        # Prepare year/month/day for button labels
        if self.jdate:
            sld = [str(self.current_date.year), str(self.current_date.month), str(self.current_date.day)]
            # Use Jalali month names
            month_name = self.months['fa'][int(sld[1]) - 1]
        else:
            sld = list(map(str, self.current_date.timetuple()[:3]))
            month_name = self.months[self.locale][int(sld[1]) - 1]

        data = dict(zip(["year", "month", "day"], [sld[0], month_name, sld[2]]))

        if self.jdate:
            # Shift dates in Gregorian and convert back to Jalali
            gregorian_date = self.current_date.togregorian()
            prev_page = jdate.fromgregorian(date=gregorian_date - diff)
            next_page = jdate.fromgregorian(date=gregorian_date + diff)
            curr_page = self.current_date  # keep current as jdate

            prev_exists = (mind.togregorian() - relativedelta(**{LSTEP[step] + "s": 1})) >= self.min_date.togregorian()
            next_exists = (maxd.togregorian() + relativedelta(**{LSTEP[step] + "s": 1})) <= self.max_date.togregorian()
        else:
            prev_page = self.current_date - diff
            next_page = self.current_date + diff
            curr_page = self.current_date

            prev_exists = mind - relativedelta(**{LSTEP[step] + "s": 1}) >= self.min_date
            next_exists = maxd + relativedelta(**{LSTEP[step] + "s": 1}) <= self.max_date

        # Build nav buttons
        return [[
            self._build_button(
                text[0].format(**data) if prev_exists else self.empty_nav_button,
                GOTO if prev_exists else NOTHING, step, prev_page, is_random=self.is_random
            ),
            self._build_button(
                text[1].format(**data),
                PREV_ACTIONS[step], PREV_STEPS[step], curr_page, is_random=self.is_random
            ),
            self._build_button(
                text[2].format(**data) if next_exists else self.empty_nav_button,
                GOTO if next_exists else NOTHING, step, next_page, is_random=self.is_random
            ),
        ]]

    # def _build_nav_buttons(self, step, diff, mind, maxd, *args, **kwargs):
    #
    #     text = self.nav_buttons[step]
    #
    #     if self.jdate:
    #         sld = [str(self.current_date.year), str(self.current_date.month), str(self.current_date.day)]
    #     else:
    #         sld = list(map(str, self.current_date.timetuple()[:3]))
    #     data = [sld[0], self.months[self.locale][int(sld[1]) - 1], sld[2]]
    #     data = dict(zip(["year", "month", "day"], data))
    #     if self.jdate:
    #         print(type(self.current_date))
    #         gregorian_date = self.current_date.togregorian()
    #         print(type(gregorian_date))
    #         prev_page = jdate.fromgregorian(date=gregorian_date - diff)
    #         next_page = jdate.fromgregorian(date=gregorian_date + diff)
    #
    #         prev_exists = (mind.togregorian() - relativedelta(
    #             **{LSTEP[step] + "s": 1})) >= self.min_date.togregorian()
    #         next_exists = (maxd.togregorian() + relativedelta(
    #             **{LSTEP[step] + "s": 1})) <= self.max_date.togregorian()
    #     else:
    #         print(type(self.current_date))
    #         prev_page = self.current_date - diff
    #         next_page = self.current_date + diff
    #
    #         prev_exists = mind - relativedelta(**{LSTEP[step] + "s": 1}) >= self.min_date
    #         next_exists = maxd + relativedelta(**{LSTEP[step] + "s": 1}) <= self.max_date
    #
    #     return [[
    #         self._build_button(text[0].format(**data) if prev_exists else self.empty_nav_button,
    #                            GOTO if prev_exists else NOTHING, step, prev_page, is_random=self.is_random),
    #         self._build_button(text[1].format(**data),
    #                            PREV_ACTIONS[step], PREV_STEPS[step], self.current_date, is_random=self.is_random),
    #         self._build_button(text[2].format(**data) if next_exists else self.empty_nav_button,
    #                            GOTO if next_exists else NOTHING, step, next_page, is_random=self.is_random),
    #     ]]

    def _get_period(self, step, start, diff, *args, **kwargs):
        if step != DAY:
            return super(DetailedTelegramCalendar, self)._get_period(step, start, diff, *args, **kwargs)

        dates = []
        if self.jdate:
            days_in_month = jdatetime.j_days_in_month[start.month-1]
            if start.month == 12 and start.isleap():
                days_in_month += 1
            first_day_weekday = jdate(start.year, start.month, 1, locale=jdatetime.FA_LOCALE).weekday()
            # jdatetime: Saturday is 0, Sunday is 1, ...

            for i in range(first_day_weekday):
                dates.append(None)
            for day in range(1, days_in_month + 1):
                d = jdate(start.year, start.month, day)
                if self._valid_date(d):
                    dates.append(d)
                else:
                    dates.append(None)
        else:
            cl = calendar.monthcalendar(start.year, start.month)
            for week in cl:
                for day in week:
                    if day != 0:
                        d = date(start.year, start.month, day)
                        if self._valid_date(d):
                            dates.append(d)
                        else:
                            dates.append(None)
                    else:
                        dates.append(None)

        return dates
