import os

from githammer import DatabaseNotInitializedError
from .hammer_test import HammerTest


class HammerInitTest(HammerTest):

    def test_plain_init_does_not_create_database(self):
        self.assertFalse(os.listdir(self.working_directory.name))

    def test_update_fails_when_database_not_created(self):
        with self.assertRaises(DatabaseNotInitializedError):
            self.hammer.update_data()
