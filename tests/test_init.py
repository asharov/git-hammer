import os
import tempfile
import unittest

from githammer import Hammer, DatabaseNotInitializedError


class HammerInitTest(unittest.TestCase):

    def setUp(self):
        self.workingDirectory = tempfile.TemporaryDirectory(prefix='git-hammer-')
        self.server_url = 'sqlite:///' + self.workingDirectory.name + '/'
        self.hammer = Hammer('test', self.server_url)

    def test_plain_init_does_not_create_database(self):
        self.assertFalse(os.listdir(self.workingDirectory.name))

    def test_update_fails_when_database_not_created(self):
        with self.assertRaises(DatabaseNotInitializedError):
            self.hammer.update_data()

    def tearDown(self):
        self.workingDirectory.cleanup()
