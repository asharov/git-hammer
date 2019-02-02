import os

from .hammer_test import HammerTest


class HammerRepositoryTest(HammerTest):

    def setUp(self):
        super().setUp()
        self.hammer.add_repository(os.path.join(self.current_directory, 'data', 'repository'))

    def test_repository_is_processed_into_database_after_adding(self):
        self.assertIsNotNone(self.hammer.head_commit())
