from datetime import datetime
from zoneinfo import ZoneInfo
import calendar

def now():
    return datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(timespec='seconds')

def today():
    return datetime.now(ZoneInfo('Asia/Kolkata')).date()

def month_bounds(value):
    return value.replace(day=1), value.replace(day=calendar.monthrange(value.year,value.month)[1])

def percent(present, total):
    return round(100*present/total,2) if total else 0.0
