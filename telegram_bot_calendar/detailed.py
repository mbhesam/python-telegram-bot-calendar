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
                 min_date=None, max_date=None, telethon=False, jdate=False, **kwargs):
        # If jdate is not provided, try to detect from current_date type
        if jdate is None and current_date is not None:
            jdate = isinstance(current_date, jdatetime.date)

        self.use_jdate = jdate
        print(f"🔧 INIT: use_jdate={self.use_jdate}, current_date={current_date}, type={type(current_date)}")

        # Set a proper default date
        if current_date is None:
            if self.use_jdate:
                current_date = jdatetime.date.today()
                print(f"📅 Set default Jalali date: {current_date}")
            else:
                current_date = date.today()
                print(f"📅 Set default Gregorian date: {current_date}")

        super().__init__(calendar_id, current_date, additional_buttons, locale, min_date, max_date, telethon, **kwargs)

        # Double-check that current_date is correct type
        if self.use_jdate and not isinstance(self.current_date, jdatetime.date):
            print(f"🔄 CORRECTING DATE TYPE: Converting to Jalali")
            if isinstance(self.current_date, date):
                self.current_date = jdatetime.date.fromgregorian(date=self.current_date)
            else:
                self.current_date = jdatetime.date.today()
        elif not self.use_jdate and isinstance(self.current_date, jdatetime.date):
            print(f"🔄 CORRECTING DATE TYPE: Converting to Gregorian")
            self.current_date = self.current_date.togregorian()

        print(
            f"✅ FINAL INIT: current_date={self.current_date}, type={type(self.current_date)}, use_jdate={self.use_jdate}")

    def _build_years(self):
        print(f"\n📅 BUILD YEARS START: use_jdate={self.use_jdate}, current_date={self.current_date}")

        years_num = self.size_year * self.size_year_column
        half_range = (years_num - 1) // 2

        # Handle Jalali dates properly
        if self.use_jdate:
            print("🟢 Using Jalali date arithmetic")
            start_year = self.current_date.year - half_range
            print(f"📊 Jalali start year: {start_year}, current year: {self.current_date.year}")
            start = jdate(start_year, 1, 1)
        else:
            print("🔵 Using Gregorian date arithmetic")
            start_year = self.current_date.year - half_range
            start = date(start_year, 1, 1)

        print(f"📊 Start date: {start}")

        years = self._get_period(YEAR, start, years_num)
        print(f"📋 Years list: {years}")
        print(f"📋 Years range: {[d.year for d in years if d is not None] if years else 'None'}")

        # Debug each year individually
        if years:
            for i, year_date in enumerate(years):
                print(f"📋 Year {i}: {year_date} (type: {type(year_date) if year_date else 'None'})")

        years_buttons = rows(
            [self._build_button(d.year if d else "NULL", SELECT if d else NOTHING, YEAR, d)
             for d in years],
            self.size_year
        )

        # Calculate maxd properly
        if self.use_jdate:
            maxd = jdate(start.year + years_num - 1, 12, 29)
        else:
            maxd = date(start.year + years_num - 1, 12, 31)

        print(f"📊 Navigation: mind={start}, maxd={maxd}")
        nav_buttons = self._build_nav_buttons(YEAR, diff=relativedelta(years=years_num),
                                              mind=min_date(start, YEAR), maxd=maxd)

        self._keyboard = self._build_keyboard(years_buttons + nav_buttons)
        print(f"✅ BUILD YEARS COMPLETE: use_jdate={self.use_jdate}\n")

    def _build_nav_buttons(self, step, diff, mind, maxd, *args, **kwargs):
        print(f"🔄 BUILD NAV BUTTONS: step={step}, use_jdate={self.use_jdate}, current_date={self.current_date}")

        text = self.nav_buttons[step]
        print(f"📝 Button text: {text}")

        # Labels
        if self.use_jdate:
            month_name = self.months['fa'][self.current_date.month - 1]
            data = {"year": str(self.current_date.year),
                    "month": month_name,
                    "day": str(self.current_date.day)}
            print(f"📊 Jalali labels: year={data['year']}, month={data['month']}")
        else:
            month_name = self.months[self.locale][self.current_date.month - 1]
            data = {"year": str(self.current_date.year),
                    "month": month_name,
                    "day": str(self.current_date.day)}
            print(f"📊 Gregorian labels: year={data['year']}, month={data['month']}")

        # Prev / Next pages
        if self.use_jdate:
            print("🟢 Building Jalali navigation buttons")
            curr_page = self.current_date

            if step == YEAR:
                prev_page = self.current_date.replace(year=self.current_date.year - diff.years)
                next_page = self.current_date.replace(year=self.current_date.year + diff.years)
                print(f"📊 Jalali YEAR nav: prev={prev_page.year}, curr={curr_page.year}, next={next_page.year}")
            elif step == MONTH:
                # For months, we need to handle year boundaries
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
                print(f"📊 Jalali MONTH nav: prev={prev_page}, curr={curr_page}, next={next_page}")
            else:  # DAY
                prev_page = self.current_date - relativedelta(days=diff.days)
                next_page = self.current_date + relativedelta(days=diff.days)
                print(f"📊 Jalali DAY nav: prev={prev_page}, curr={curr_page}, next={next_page}")

            prev_exists = (prev_page >= self.min_date) if self.min_date else True
            next_exists = (next_page <= self.max_date) if self.max_date else True
            print(f"📊 Jalali nav exists: prev={prev_exists}, next={next_exists}")
        else:
            print("🔵 Building Gregorian navigation buttons")
            curr_page = self.current_date
            prev_page = self.current_date - diff
            next_page = self.current_date + diff

            prev_exists = (prev_page >= self.min_date) if self.min_date else True
            next_exists = (next_page <= self.max_date) if self.max_date else True
            print(f"📊 Gregorian nav: prev={prev_page}, curr={curr_page}, next={next_page}")
            print(f"📊 Gregorian nav exists: prev={prev_exists}, next={next_exists}")

        buttons = [[
            self._build_button(text[0].format(**data) if prev_exists else self.empty_nav_button,
                               GOTO if prev_exists else NOTHING, step, prev_page),
            self._build_button(text[1].format(**data),
                               PREV_ACTIONS[step], PREV_STEPS[step], curr_page),
            self._build_button(text[2].format(**data) if next_exists else self.empty_nav_button,
                               GOTO if next_exists else NOTHING, step, next_page),
        ]]

        print(f"✅ NAV BUTTONS COMPLETE: step={step}\n")
        return buttons

    def _build_button(self, text, action, step=None, date_obj=None, is_random=False, *args, **kwargs):
        print(
            f"🔘 BUILD BUTTON: text='{text}', action='{action}', step='{step}', date_obj='{date_obj}', use_jdate={self.use_jdate}")

        if action == NOTHING:
            print(f"   ↳ NOTHING button - text: {text}")
            return {"text": text, "callback_data": NOTHING}

        if not date_obj:
            print("   ↳ ❌ ERROR: No date_obj provided")
            return {"text": text, "callback_data": NOTHING}

        # Ensure date_obj is the correct type for the current calendar mode
        if self.use_jdate and isinstance(date_obj, date):
            print("   ↳ 🔄 Converting Gregorian to Jalali for button")
            date_obj = jdate.fromgregorian(date=date_obj)
        elif not self.use_jdate and isinstance(date_obj, jdate):
            print("   ↳ 🔄 Converting Jalali to Gregorian for button")
            date_obj = date_obj.togregorian()

        print(f"   ↳ Final date_obj: {date_obj} (type: {type(date_obj)})")

        # Build the callback data WITH CALENDAR TYPE
        calendar_type = 'j' if self.use_jdate else 'g'  # Add this line
        callback_data = "_".join([
            "CALENDAR",
            str(self.calendar_id),
            calendar_type,  # ← ADD THIS: 'j' for Jalali, 'g' for Gregorian
            action,
            step if step else "",
            str(date_obj.year),
            str(date_obj.month),
            str(date_obj.day)
        ])

        print(f"   ↳ Callback data: {callback_data}")
        return {"text": text, "callback_data": callback_data}

    def _process(self, call_data):
        print(f"\n🎯 PROCESS CALLBACK: call_data='{call_data}', use_jdate={self.use_jdate}")
        print(f"📅 BEFORE PROCESS: current_date={self.current_date}, type={type(self.current_date)}")

        params = call_data.split("_")
        print(f"📋 Raw params: {params}")

        # Updated expected params with calendar type
        expected_params = ["start", "calendar_id", "calendar_type", "action", "step", "year", "month", "day"]

        if len(params) < len(expected_params):
            print(f"❌ WARNING: Not enough parameters. Expected {len(expected_params)}, got {len(params)}")
            params.extend([""] * (len(expected_params) - len(params)))

        params = dict(zip(expected_params, params))
        print(f"📋 Parsed params: {params}")

        # SET CALENDAR TYPE FROM CALLBACK DATA
        calendar_type = params.get('calendar_type', 'g')  # Default to Gregorian if missing
        self.use_jdate = (calendar_type == 'j')
        print(f"🔄 SET CALENDAR TYPE FROM CALLBACK: {calendar_type} -> use_jdate={self.use_jdate}")

        if params['action'] == NOTHING:
            print("❌ ACTION: NOTHING - returning None")
            return None, None, None

        step = params['step']
        try:
            year = int(params['year'])
            month = int(params['month'])
            day = int(params['day'])
        except (ValueError, TypeError) as e:
            print(f"❌ ERROR parsing date: {e}")
            print(f"❌ Year: {params['year']}, Month: {params['month']}, Day: {params['day']}")
            return None, None, None

        print(f"📊 Processing: step={step}, year={year}, month={month}, day={day}")

        # CRITICAL: Preserve Jalali setting when processing callback data
        if self.use_jdate:
            print("🟢 Creating Jalali date from callback data")
            try:
                self.current_date = jdatetime.date(year, month, day)
                print(f"✅ Jalali date created: {self.current_date}")
            except Exception as e:
                print(f"❌ ERROR creating Jalali date: {e}")
                self.current_date = jdatetime.date.today()
        else:
            print("🔵 Creating Gregorian date from callback data")
            try:
                self.current_date = date(year, month, day)
                print(f"✅ Gregorian date created: {self.current_date}")
            except Exception as e:
                print(f"❌ ERROR creating Gregorian date: {e}")
                self.current_date = date.today()

        print(f"📅 AFTER DATE SET: current_date={self.current_date}, type={type(self.current_date)}")

        if params['action'] == GOTO:
            print(f"🔄 ACTION: GOTO - rebuilding for step={step}")
            self._build(step=step)
            return None, self._keyboard, step

        if params['action'] == SELECT:
            print(f"✅ ACTION: SELECT - step={step}")
            if step in STEPS:
                next_step = STEPS[step]
                print(f"📈 Moving to next step: {step} -> {next_step}")
                self._build(step=next_step)
                return None, self._keyboard, next_step
            else:
                print(f"🎉 Final selection: {self.current_date}")
                return self.current_date, None, step

    def _build(self, step=None):
        print(f"\n🏗️ BUILD CALLED: step={step}, use_jdate={self.use_jdate}")
        if not step:
            step = self.first_step
        self.step = step

        if step == YEAR:
            print("📅 Building YEARS view")
            self._build_years()
        elif step == MONTH:
            print("📅 Building MONTHS view")
            self._build_months()
        elif step == DAY:
            print("📅 Building DAYS view")
            self._build_days()
        else:
            print(f"❌ UNKNOWN STEP: {step}")

    def _build_months(self):
        print(f"\n📅 BUILD MONTHS: use_jdate={self.use_jdate}, current_date={self.current_date}")

        months_buttons = []
        for i in range(1, 13):
            # Create the date object correctly for Jalali
            if self.use_jdate:
                d = jdatetime.date(self.current_date.year, i, 1)  # FIXED: use jdatetime.date instead of jdate
            else:
                d = date(self.current_date.year, i, 1)

            if self._valid_date(d):
                month_name = self.months['fa'][i - 1] if self.use_jdate else self.months[self.locale][i - 1]
                months_buttons.append(self._build_button(month_name, SELECT, MONTH, d))
                print(f"📋 Month {i}: {month_name} - VALID - Date: {d}")
            else:
                months_buttons.append(self._build_button(self.empty_month_button, NOTHING))
                print(f"📋 Month {i}: EMPTY - INVALID")

        months_buttons = rows(months_buttons, self.size_month)

        # Create start date correctly
        if self.use_jdate:
            start = jdatetime.date(self.current_date.year, 1, 1)  # FIXED: use jdatetime.date instead of jdate
            maxd = jdatetime.date(self.current_date.year, 12, 1)  # FIXED: use jdatetime.date instead of jdate
        else:
            start = date(self.current_date.year, 1, 1)
            maxd = date(self.current_date.year, 12, 1)

        nav_buttons = self._build_nav_buttons(MONTH, diff=relativedelta(months=12),
                                              mind=min_date(start, MONTH), maxd=maxd)

        self._keyboard = self._build_keyboard(months_buttons + nav_buttons)
        print(f"✅ BUILD MONTHS COMPLETE\n")

    def _build_days(self):
        print(f"\n📅 BUILD DAYS: use_jdate={self.use_jdate}, current_date={self.current_date}")

        if self.use_jdate:
            days_num = jdatetime.j_days_in_month[self.current_date.month - 1]
            if self.current_date.month == 12 and self.current_date.isleap():
                days_num += 1
            print(f"📊 Jalali month days: {days_num}")
            start = jdatetime.date(self.current_date.year, self.current_date.month,
                                   1)  # FIXED: use jdatetime.date instead of jdate
        else:
            days_num = monthrange(self.current_date.year, self.current_date.month)[1]
            print(f"📊 Gregorian month days: {days_num}")
            start = date(self.current_date.year, self.current_date.month, 1)

        days = self._get_period(DAY, start, days_num)

        days_buttons = rows(
            [self._build_button(d.day if d else self.empty_day_button, SELECT if d else NOTHING, DAY, d)
             for d in days],
            self.size_day
        )

        # Use correct locale for days of week
        locale_key = 'fa' if self.use_jdate else self.locale
        days_of_week_buttons = [[self._build_button(self.days_of_week[locale_key][i], NOTHING) for i in range(7)]]
        print(f"📊 Days of week locale: {locale_key}")

        mind = min_date(start, MONTH)
        maxd_date = start.replace(day=days_num) if self.use_jdate else date(self.current_date.year,
                                                                            self.current_date.month, days_num)

        nav_buttons = self._build_nav_buttons(DAY, diff=relativedelta(months=1),
                                              mind=mind, maxd=max_date(maxd_date, MONTH))

        self._keyboard = self._build_keyboard(days_of_week_buttons + days_buttons + nav_buttons)
        print(f"✅ BUILD DAYS COMPLETE\n")

    def _get_period(self, step, start, count):
        """Override _get_period to handle Jalali dates correctly"""
        print(f"🔍 _GET_PERIOD CALLED: step={step}, start={start}, count={count}, use_jdate={self.use_jdate}")

        result = []
        for i in range(count):
            if step == YEAR:
                if self.use_jdate:
                    current = jdatetime.date(start.year + i, 1, 1)  # FIXED: use jdatetime.date instead of jdate
                else:
                    current = date(start.year + i, 1, 1)
            elif step == MONTH:
                if self.use_jdate:
                    year = start.year + (start.month + i - 1) // 12
                    month = (start.month + i - 1) % 12 + 1
                    current = jdatetime.date(year, month, 1)  # FIXED: use jdatetime.date instead of jdate
                else:
                    year = start.year + (start.month + i - 1) // 12
                    month = (start.month + i - 1) % 12 + 1
                    current = date(year, month, 1)
            else:  # DAY
                if self.use_jdate:
                    current = start + relativedelta(days=i)
                else:
                    current = start + relativedelta(days=i)

            # Validate the date
            if self._valid_date(current):
                result.append(current)
                print(f"✅ Period {i}: {current} - VALID")
            else:
                result.append(None)
                print(f"❌ Period {i}: {current} - INVALID")

        print(f"🔍 _GET_PERIOD RESULT: {result}")
        return result

    def _valid_date(self, date_obj):
        """Check if date is valid considering min_date and max_date constraints"""
        if date_obj is None:
            return False

        if self.min_date and date_obj < self.min_date:
            return False

        if self.max_date and date_obj > self.max_date:
            return False

        # Additional validation for Jalali dates
        if self.use_jdate and isinstance(date_obj, jdatetime.date):
            try:
                jdatetime.date(date_obj.year, date_obj.month, date_obj.day)
                return True
            except:
                return False
        elif not self.use_jdate and isinstance(date_obj, date):
            try:
                date(date_obj.year, date_obj.month, date_obj.day)
                return True
            except:
                return False

        return True