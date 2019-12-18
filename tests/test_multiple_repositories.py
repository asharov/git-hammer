import os
import datetime

from githammer import Frequency

from .hammer_test import HammerTest


class HammerMultipleRepositoriesTest(HammerTest):
    def setUp(self):
        super().setUp()
        self.hammer.add_repository(os.path.join(self.current_directory, 'data', 'repository'),
                                   os.path.join(self.current_directory, 'data', 'repo-config.json'))
        self.hammer.add_repository(os.path.join(self.current_directory, 'data', 'subrepository'))
        self._expected_dates = [
            datetime.datetime(2017, 11, 22, 7, 22, 33, tzinfo=datetime.timezone.utc),
            datetime.datetime(2017, 12, 4, 7, 10, 11, tzinfo=datetime.timezone.utc),
            datetime.datetime(2017, 12, 6, 3, 33, 44, tzinfo=datetime.timezone.utc),
            datetime.datetime(2017, 12, 14, 10, 54, 55, tzinfo=datetime.timezone.utc)
        ]
        self._expected_offsets = [14400, 7200, -18000, 14400]

    def test_commits_are_combined_with_correct_dates(self):
        initial_commits = list(self.hammer.iter_commits())[:4]
        self.assertEqual([commit.commit_time for commit in initial_commits], self._expected_dates)
        self.assertEqual([commit.commit_time_utc_offset for commit in initial_commits], self._expected_offsets)

    def test_combined_commits_are_produced_with_correct_frequency(self):
        initial_commits = list(self.hammer.iter_commits(frequency=Frequency.weekly))[:3]
        del self._expected_dates[2]
        del self._expected_offsets[2]
        self.assertEqual([commit.commit_time for commit in initial_commits], self._expected_dates)
        self.assertEqual([commit.commit_time_utc_offset for commit in initial_commits], self._expected_offsets)
