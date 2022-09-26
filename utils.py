import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

def time_duration(func):
    def wrapper(*args, **kwargs):
        t1 = time.time()
        result = func(*args, **kwargs)
        t2 = time.time()
        print(f"Function {func.__name__} has spent {round(t2-t1, 4)} seconds.")
        return result
    return wrapper


def get_past_date(str_to_date):
    TODAY = datetime.today()
    split = str_to_date.split()
    if len(split) == 1 and split[0].lower() == "today":
        return str(TODAY.isoformat())
    elif len(split) == 1 and split[0].lower() == "yesterday":
        date = TODAY - relativedelta(days = 1)
        return str(date.isoformat())
    elif split[1].lower() in ['days', 'day']:
        date = TODAY - relativedelta(days = int(split[0]))
        return str(date.isoformat())
    elif split[1].lower() in ['hours', 'hour']:
        date = TODAY - relativedelta(hours=int(split[0]))
        return str(date.isoformat())
    elif split[1].lower() in ['months', 'month']:
        date = TODAY - relativedelta(months = int(split[0]))
        return str(date.isoformat())
    elif split[1].lower() in ['years', 'year']:
        date = TODAY - relativedelta(years = int(split[0]))
        return str(date.isoformat())
    elif split[1].lower() in ['minutes', 'minute']:
        date = TODAY - relativedelta(minutes = int(split[0]))
        return str(date.isoformat())
    else:
        return "Wrong format: " + str(str_to_date)