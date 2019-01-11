from enum import Enum

from dateutil.relativedelta import relativedelta


class Frequency(Enum):
    daily = 1
    weekly = 2
    monthly = 3
    yearly = 4

    def next_instance(self, dt):
        if self is Frequency.daily:
            return dt + relativedelta(days=1)
        elif self is Frequency.weekly:
            return dt + relativedelta(weeks=1)
        elif self is Frequency.monthly:
            return dt + relativedelta(months=1)
        elif self is Frequency.yearly:
            return dt + relativedelta(years=1)
