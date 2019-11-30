import os

from .hammer_test import HammerTest


class HammerRepositoryTest(HammerTest):

    def _initial_commit(self):
        return next(c for c in self.hammer.iter_individual_commits() if c.hexsha == 'c153f2881f0f0025a9ff5754e74111333ce859cd')

    def setUp(self):
        super().setUp()
        self.hammer.add_repository(os.path.join(self.current_directory, 'data', 'repository'))

    def test_repository_is_processed_into_database_after_adding(self):
        self.assertIsNotNone(self.hammer.head_commit())

    def test_commit_timestamps_have_correct_time(self):
        initial_commit = self._initial_commit()
        print(initial_commit.commit_time_tz())
        self.assertEqual(initial_commit.commit_time_tz().hour, 11)

    def test_initial_commit_line_counts_are_correct(self):
        initial_commit = self._initial_commit()
        author = initial_commit.author
        self.assertEqual(initial_commit.line_counts[author], 14)
