import os
import datetime

from .hammer_test import HammerTest


class HammerLimitedTest(HammerTest):
    def setUp(self):
        super().setUp()
        self.hammer.add_repository(os.path.join(self.current_directory, 'data', 'repository'),
                                   os.path.join(self.current_directory, 'data', 'repo-config.json'),
                                   earliest_date=datetime.datetime(2018, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc))

    def test_limiting_by_date_includes_only_commits_after(self):
        commits = list(self.hammer.iter_individual_commits())
        self.assertEqual(len(commits), 3)
