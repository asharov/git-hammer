import os

from .hammer_test import HammerTest


class HammerRepositoryTest(HammerTest):

    def setUp(self):
        super().setUp()
        self.hammer.add_repository(os.path.join(self.current_directory, 'data', 'repository'))

    def test_repository_is_processed_into_database_after_adding(self):
        self.assertIsNotNone(self.hammer.head_commit())

    def test_commit_timestamps_have_correct_time(self):
        initial_commit = next(c for c in self.hammer.iter_individual_commits() if c.hexsha == 'd28b4923a3a60bb272928a93ff3101a518f3ecbb')
        print(initial_commit.commit_time_tz())
        self.assertEqual(initial_commit.commit_time_tz().hour, 11)
