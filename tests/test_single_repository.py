import os

from .hammer_test import HammerTest

_initial_commit_hexsha = 'c153f2881f0f0025a9ff5754e74111333ce859cd'
_second_commit_hexsha = '5151985f7e3551c73ccb65cda2b021194b30b30a'


class HammerRepositoryTest(HammerTest):

    def _fetch_commit(self, hexsha):
        return next(c for c in self.hammer.iter_individual_commits() if c.hexsha == hexsha)

    def setUp(self):
        super().setUp()
        self.hammer.add_repository(os.path.join(self.current_directory, 'data', 'repository'))

    def test_repository_is_processed_into_database_after_adding(self):
        self.assertIsNotNone(self.hammer.head_commit())

    def test_commit_timestamps_have_correct_time(self):
        initial_commit = self._fetch_commit(_initial_commit_hexsha)
        print(initial_commit.commit_time_tz())
        self.assertEqual(initial_commit.commit_time_tz().hour, 11)

    def test_initial_commit_line_counts_are_correct(self):
        initial_commit = self._fetch_commit(_initial_commit_hexsha)
        author = initial_commit.author
        self.assertEqual(initial_commit.line_counts[author], 14)

    def test_second_commit_line_counts_are_correct(self):
        initial_commit = self._fetch_commit(_initial_commit_hexsha)
        second_commit = self._fetch_commit(_second_commit_hexsha)
        self.assertEqual(second_commit.line_counts[initial_commit.author], 10)
        self.assertEqual(second_commit.line_counts[second_commit.author], 4)
