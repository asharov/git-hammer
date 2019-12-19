import datetime
import unittest

from githammer import Frequency


class FrequencyTest(unittest.TestCase):
    def setUp(self) -> None:
        print()
        print(self.id())
        self.initial_date = datetime.datetime(2019, 10, 10, 10, 10, 10, tzinfo=datetime.timezone.utc)
        self.year_start_date = datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        self.year_start_week_date = datetime.datetime(2019, 1, 7, 0, 0, 0, tzinfo=datetime.timezone.utc)

    def test_correct_start_of_interval(self):
        self.assertEqual(Frequency.daily.start_of_interval(self.initial_date),
                         datetime.datetime(2019, 10, 10, 0, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(Frequency.weekly.start_of_interval(self.initial_date),
                         datetime.datetime(2019, 10, 7, 0, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(Frequency.monthly.start_of_interval(self.initial_date),
                         datetime.datetime(2019, 10, 1, 0, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(Frequency.yearly.start_of_interval(self.initial_date),
                         datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc))

    def test_correct_next_instance(self):
        self.assertEqual(Frequency.daily.next_instance(self.year_start_date),
                         datetime.datetime(2019, 1, 2, 0, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(Frequency.weekly.next_instance(self.year_start_week_date),
                         datetime.datetime(2019, 1, 14, 0, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(Frequency.monthly.next_instance(self.year_start_date),
                         datetime.datetime(2019, 2, 1, 0, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(Frequency.yearly.next_instance(self.year_start_date),
                         datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc))
