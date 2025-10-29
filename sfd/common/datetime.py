import calendar
import datetime


def format_hhmm(td: datetime.timedelta) -> str:
    """Format a timedelta as HH:MM string."""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"{hours:02}:{minutes:02}"


def month_dates(given_date: datetime.date) -> list[datetime.date]:
    """Return a list of all dates in the month of the given date."""
    year = given_date.year
    month = given_date.month

    # Get number of days in this month
    days_in_month = calendar.monthrange(year, month)[1]

    return [datetime.date(year, month, day) for day in range(1, days_in_month + 1)]
